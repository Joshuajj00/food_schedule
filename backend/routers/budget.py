from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Budget, LLMSettings, Ingredient
from backend.models import (
    BudgetCreate, BudgetResponse, WeeklyBudgetResponse, MessageResponse,
    BudgetRecommendRequest, BudgetRecommendItem, BudgetRecommendResponse,
    IngredientResponse,
)
from backend.ai_client import ai_client
from backend.prompt_builder import build_budget_prompt
from backend.logger import get_logger

logger = get_logger('routers.budget')
router = APIRouter(prefix='/api/budget', tags=['budget'])


def _get_settings(db: Session) -> LLMSettings:
    row = db.query(LLMSettings).first()
    if not row:
        raise HTTPException(status_code=503, detail='LLM 설정이 없습니다. 설정 탭에서 먼저 설정해주세요.')
    if not row.model_name:
        raise HTTPException(status_code=503, detail='모델명이 설정되지 않았습니다.')
    return row


@router.post('/recommend', response_model=BudgetRecommendResponse)
async def recommend_purchases(body: BudgetRecommendRequest, db: Session = Depends(get_db)):
    logger.info(f"구매 추천 요청: 예산={body.budget:,}원")
    settings = _get_settings(db)
    ingredients = db.query(Ingredient).all()
    ingredient_models = [IngredientResponse.model_validate(ing) for ing in ingredients]
    logger.debug(f"보유 식재료: {len(ingredient_models)}종")

    system_prompt, user_prompt = build_budget_prompt(body.budget, ingredient_models)
    try:
        result = await ai_client.generate(system_prompt, user_prompt, settings)
        if 'error' in result and 'items' not in result:
            raise HTTPException(
                status_code=500,
                detail=f"AI 응답 파싱 오류: {result.get('raw_response', '')[:200]}"
            )

        items = []
        for item in result.get('items', []):
            try:
                items.append(BudgetRecommendItem(**item))
            except Exception as e:
                logger.warning(f"추천 항목 파싱 건너뜀: {item} — {e}")

        response = BudgetRecommendResponse(
            items=items,
            total_estimated=result.get('total_estimated', 0),
            note=result.get('note', ''),
        )
        logger.info(f"구매 추천 완료: {len(items)}종, 총 예상 ₩{response.total_estimated:,}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"구매 추천 실패: {e}")
        raise HTTPException(status_code=500, detail=f'추천 생성 중 오류: {str(e)}')


@router.get('/weekly', response_model=WeeklyBudgetResponse)
async def get_weekly_budget(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    items = db.query(Budget).filter(
        Budget.purchase_date >= start_of_week,
        Budget.purchase_date <= end_of_week
    ).order_by(Budget.purchase_date.desc()).all()

    total = sum(b.price for b in items)
    logger.debug(f"주간 예산 조회: {len(items)}건, 합계 ₩{total:,}")
    return WeeklyBudgetResponse(
        total_spent=total,
        items=[BudgetResponse.model_validate(b) for b in items]
    )


@router.post('/purchase', response_model=BudgetResponse)
async def add_purchase(purchase: BudgetCreate, db: Session = Depends(get_db)):
    new_purchase = Budget(
        item=purchase.item,
        price=purchase.price,
        purchase_date=purchase.purchase_date,
    )
    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)
    logger.info(f"구매 기록 추가: {purchase.item} ₩{purchase.price:,}")
    return new_purchase


@router.delete('/{budget_id}', response_model=MessageResponse)
async def delete_purchase(budget_id: int, db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail='구매 기록을 찾을 수 없습니다.')
    db.delete(budget)
    db.commit()
    logger.info(f"구매 기록 삭제: id={budget_id}")
    return MessageResponse(message='구매 기록이 삭제되었습니다.', detail=f'ID: {budget_id}')
