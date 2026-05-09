"""백업/복원 라우터"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Ingredient, MealHistory, Budget, BloodSugar, MealFavorite
from backend.models import BackupData, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.backup')
router = APIRouter(prefix='/api/backup', tags=['backup'])


def _parse_json(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _to_json(data) -> str | None:
    if data is None:
        return None
    if hasattr(data, 'model_dump'):
        return json.dumps(data.model_dump(), ensure_ascii=False)
    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False)
    return None


@router.get('/export', response_model=BackupData)
async def export_data(db: Session = Depends(get_db)):
    """모든 데이터를 JSON으로 내보내기"""
    ingredients = db.query(Ingredient).all()
    meal_history_rows = db.query(MealHistory).all()
    budget_rows = db.query(Budget).all()
    blood_sugar_rows = db.query(BloodSugar).all()
    favorite_rows = db.query(MealFavorite).all()

    # _data 컬럼이 JSON 문자열이므로 직접 파싱해서 Pydantic 검증 우회
    meal_history_dicts = [
        {
            'id': r.id, 'date': r.date,
            'breakfast': r.breakfast, 'lunch': r.lunch, 'dinner': r.dinner,
            'note': r.note, 'created_at': r.created_at,
            'breakfast_data': _parse_json(r.breakfast_data),
            'lunch_data': _parse_json(r.lunch_data),
            'dinner_data': _parse_json(r.dinner_data),
        }
        for r in meal_history_rows
    ]
    favorite_dicts = [
        {
            'id': r.id, 'name': r.name,
            'breakfast': r.breakfast, 'lunch': r.lunch, 'dinner': r.dinner,
            'note': r.note, 'created_at': r.created_at,
            'breakfast_data': _parse_json(r.breakfast_data),
            'lunch_data': _parse_json(r.lunch_data),
            'dinner_data': _parse_json(r.dinner_data),
        }
        for r in favorite_rows
    ]

    data = BackupData(
        ingredients=ingredients,
        meal_history=meal_history_dicts,
        budget=budget_rows,
        blood_sugar=blood_sugar_rows,
        favorites=favorite_dicts,
    )
    logger.info(
        f"백업 내보내기: 식재료 {len(ingredients)}종, 식단 {len(meal_history_rows)}건, "
        f"예산 {len(budget_rows)}건, 혈당 {len(blood_sugar_rows)}건, 즐겨찾기 {len(favorite_rows)}건"
    )
    return data


@router.post('/import', response_model=MessageResponse)
async def import_data(data: BackupData, db: Session = Depends(get_db)):
    """JSON 데이터로 복원 (기존 데이터 삭제 후 가져오기)"""
    try:
        with db.begin_nested():
            db.query(MealFavorite).delete()
            db.query(BloodSugar).delete()
            db.query(Budget).delete()
            db.query(MealHistory).delete()
            db.query(Ingredient).delete()

            for ing in data.ingredients:
                db.add(Ingredient(
                    name=ing.name, quantity=ing.quantity, unit=ing.unit,
                    category=ing.category, expiry_date=ing.expiry_date,
                ))
            for mh in data.meal_history:
                db.add(MealHistory(
                    date=mh.date, breakfast=mh.breakfast,
                    lunch=mh.lunch, dinner=mh.dinner, note=mh.note,
                    breakfast_data=_to_json(mh.breakfast_data),
                    lunch_data=_to_json(mh.lunch_data),
                    dinner_data=_to_json(mh.dinner_data),
                ))
            for b in data.budget:
                db.add(Budget(item=b.item, price=b.price, purchase_date=b.purchase_date))
            for bs in data.blood_sugar:
                db.add(BloodSugar(date=bs.date, time=bs.time, level=bs.level, note=bs.note))
            for fav in data.favorites:
                db.add(MealFavorite(
                    name=fav.name, breakfast=fav.breakfast,
                    lunch=fav.lunch, dinner=fav.dinner, note=fav.note,
                    breakfast_data=_to_json(fav.breakfast_data),
                    lunch_data=_to_json(fav.lunch_data),
                    dinner_data=_to_json(fav.dinner_data),
                ))
    except Exception:
        logger.exception("백업 복원 중 오류 발생, 롤백됨")
        raise HTTPException(
            status_code=500,
            detail='데이터 복원 중 오류가 발생하여 롤백되었습니다. 기존 데이터는 보존됩니다.',
        )

    db.commit()
    logger.info(
        f"백업 복원 완료: 식재료 {len(data.ingredients)}종, 식단 {len(data.meal_history)}건, "
        f"예산 {len(data.budget)}건, 혈당 {len(data.blood_sugar)}건, 즐겨찾기 {len(data.favorites)}건"
    )
    return MessageResponse(message='데이터 복원이 완료되었습니다.')
