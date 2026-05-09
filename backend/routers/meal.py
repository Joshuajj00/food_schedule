from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from backend.database import get_db, Ingredient, MealHistory, LLMSettings
from backend.models import MealPlanListResponse, MealPlanOption, MealHistoryCreate, MealHistoryResponse, IngredientResponse, DecryptedLLMSettings
from backend.ai_client import ai_client
from backend.prompt_builder import build_meal_prompt
from backend.crypto_utils import decrypt
from backend.logger import get_logger

logger = get_logger('routers.meal')
router = APIRouter(prefix='/api/meal', tags=['meal'])


def _get_settings(db: Session) -> DecryptedLLMSettings:
    row = db.query(LLMSettings).first()
    if not row:
        raise HTTPException(
            status_code=503,
            detail='LLM 설정이 없습니다. 설정 탭에서 먼저 설정해주세요.'
        )
    if not row.model_name:
        raise HTTPException(
            status_code=503,
            detail='모델명이 설정되지 않았습니다. 설정 탭에서 모델명을 입력해주세요.'
        )
    return DecryptedLLMSettings(
        provider=row.provider,
        base_url=row.base_url,
        api_key=decrypt(row.api_key),
        model_name=row.model_name,
        api_format=row.api_format,
        streaming=row.streaming,
        thinking_mode=row.thinking_mode,
        thinking_budget=row.thinking_budget,
        reasoning_effort=row.reasoning_effort,
    )


@router.post('/generate', response_model=MealPlanListResponse)
async def generate_meal(db: Session = Depends(get_db)):
    ingredients = db.query(Ingredient).all()
    if not ingredients:
        raise HTTPException(status_code=400, detail='등록된 식재료가 없습니다. 식재료를 먼저 등록해주세요.')

    logger.info(f"식단 생성 요청: 식재료 {len(ingredients)}종")
    settings = _get_settings(db)
    ingredient_models = [IngredientResponse.model_validate(ing) for ing in ingredients]
    system_prompt, user_prompt = build_meal_prompt(ingredient_models)

    try:
        result = await ai_client.generate(system_prompt, user_prompt, settings)
        if 'error' in result and 'options' not in result:
            raise HTTPException(
                status_code=500,
                detail=f"AI 응답 파싱 오류: {result.get('raw_response', 'Unknown error')}"
            )

        options_data = result.get('options')
        if not isinstance(options_data, list) and 'breakfast' in result:
            options_data = [{
                'title': '옵션 1',
                'breakfast': result.get('breakfast', {}),
                'lunch': result.get('lunch', {}),
                'dinner': result.get('dinner', {}),
                'note': result.get('note', ''),
            }]

        options = []
        for idx, option_data in enumerate(options_data or []):
            try:
                option = MealPlanOption(
                    title=option_data.get('title', f'옵션 {idx + 1}'),
                    breakfast=option_data.get('breakfast', {}),
                    lunch=option_data.get('lunch', {}),
                    dinner=option_data.get('dinner', {}),
                    note=option_data.get('note', ''),
                )
                options.append(option)
            except Exception as ve:
                logger.warning(f"MealPlanOption 모델 검증 실패: {ve}")

        if len(options) < 3:
            raise HTTPException(
                status_code=500,
                detail='AI가 3가지 옵션을 모두 생성하지 못했습니다. 다시 시도해주세요.'
            )

        warnings: list[str] = []

        seen_signatures = set()
        for idx, option in enumerate(options):
            signature = f"{option.breakfast.name}|{option.lunch.name}|{option.dinner.name}"
            if signature in seen_signatures:
                warnings.append(f"옵션 {idx + 1}이 다른 옵션과 중복됩니다.")
            seen_signatures.add(signature)

            total_protein = (
                option.breakfast.nutrition.protein_g
                + option.lunch.nutrition.protein_g
                + option.dinner.nutrition.protein_g
            )
            if total_protein < 48:
                warnings.append(
                    f"옵션 {idx + 1}: 하루 단백질이 {total_protein:.1f}g으로 목표(48g) 미달입니다."
                )

            total_carbs = (
                option.breakfast.nutrition.carbs_g
                + option.lunch.nutrition.carbs_g
                + option.dinner.nutrition.carbs_g
            )
            if total_carbs > 15:
                warnings.append(
                    f"옵션 {idx + 1}: 하루 탄수화물이 {total_carbs:.1f}g으로 한도(15g) 초과입니다."
                )

        from backend.nutrition_client import calculate_meal_nutrition
        for option in options:
            try:
                for meal in [option.breakfast, option.lunch, option.dinner]:
                    ing_list = [(ing, 50.0) for ing in meal.ingredients if ing]
                    verified = await calculate_meal_nutrition(ing_list)
                    if verified['matched']:
                        t = verified['total']
                        meal.note = (
                            f"[식약처DB 추정 (재료 50g 가정)] "
                            f"열량 {t['calories']:.0f}kcal, "
                            f"단백질 {t['protein_g']:.1f}g, "
                            f"탄수 {t['carbs_g']:.1f}g, 지방 {t['fat_g']:.1f}g"
                        )
            except Exception as e:
                logger.warning(f"영양 검증 실패 (무시하고 계속): {e}")

        response = MealPlanListResponse(
            options=options,
            note=result.get('note', ''),
            warnings=warnings,
        )
        logger.info(f"식단 생성 완료: 옵션 {len(options)}개, 경고 {len(warnings)}건")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"식단 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f'식단 생성 중 오류: {str(e)}')


@router.get('/history', response_model=List[MealHistoryResponse])
async def get_meal_history(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
):
    query = db.query(MealHistory)
    if start_date:
        query = query.filter(MealHistory.date >= start_date)
    if end_date:
        query = query.filter(MealHistory.date <= end_date)
    records = query.order_by(MealHistory.date.desc()).all()
    logger.debug(f"식단 기록 조회: {len(records)}건")
    return records


@router.post('/history', response_model=MealHistoryResponse)
async def save_meal_history(meal_data: MealHistoryCreate, db: Session = Depends(get_db)):
    existing = db.query(MealHistory).filter(MealHistory.date == meal_data.date).first()
    if existing:
        existing.breakfast = meal_data.breakfast
        existing.lunch = meal_data.lunch
        existing.dinner = meal_data.dinner
        existing.note = meal_data.note
        db.commit()
        db.refresh(existing)
        logger.info(f"식단 기록 업데이트: {meal_data.date}")
        return existing

    new_history = MealHistory(
        date=meal_data.date,
        breakfast=meal_data.breakfast,
        lunch=meal_data.lunch,
        dinner=meal_data.dinner,
        note=meal_data.note,
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    logger.info(f"식단 기록 저장: {meal_data.date}")
    return new_history
