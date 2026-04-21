from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from backend.database import get_db, Ingredient, MealHistory, LLMSettings
from backend.models import MealPlan, MealHistoryCreate, MealHistoryResponse, IngredientResponse
from backend.ai_client import ai_client
from backend.prompt_builder import build_meal_prompt
from backend.logger import get_logger

logger = get_logger('routers.meal')
router = APIRouter(prefix='/api/meal', tags=['meal'])


def _get_settings(db: Session) -> LLMSettings:
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
    return row


@router.post('/generate', response_model=MealPlan)
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
        if 'error' in result and 'breakfast' not in result:
            raise HTTPException(
                status_code=500,
                detail=f"AI 응답 파싱 오류: {result.get('raw_response', 'Unknown error')}"
            )
        meal_plan = MealPlan(
            breakfast=result.get('breakfast', {}),
            lunch=result.get('lunch', {}),
            dinner=result.get('dinner', {}),
            note=result.get('note', ''),
        )
        logger.info(f"식단 생성 완료: 아침={meal_plan.breakfast.name}, 점심={meal_plan.lunch.name}, 저녁={meal_plan.dinner.name}")
        return meal_plan
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
