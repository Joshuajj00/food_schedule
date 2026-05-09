"""백업/복원 라우터"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db, Ingredient, MealHistory, Budget, BloodSugar, MealFavorite
from backend.models import BackupData, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.backup')
router = APIRouter(prefix='/api/backup', tags=['backup'])


@router.get('/export', response_model=BackupData)
async def export_data(db: Session = Depends(get_db)):
    """모든 데이터를 JSON으로 내보내기"""
    data = BackupData(
        ingredients=db.query(Ingredient).all(),
        meal_history=db.query(MealHistory).all(),
        budget=db.query(Budget).all(),
        blood_sugar=db.query(BloodSugar).all(),
        favorites=db.query(MealFavorite).all(),
    )
    logger.info(f"백업 내보내기: 식재료 {len(data.ingredients)}종, 식단 {len(data.meal_history)}건, 예산 {len(data.budget)}건, 혈당 {len(data.blood_sugar)}건, 즐겨찾기 {len(data.favorites)}건")
    return data


@router.post('/import', response_model=MessageResponse)
async def import_data(data: BackupData, db: Session = Depends(get_db)):
    """JSON 데이터로 복원 (기존 데이터 삭제 후 가져오기)"""
    # savepoint로 원자성 보장: 중간에 예외 발생 시 기존 데이터 보존
    try:
        with db.begin_nested():
            # 기존 데이터 삭제
            db.query(MealFavorite).delete()
            db.query(BloodSugar).delete()
            db.query(Budget).delete()
            db.query(MealHistory).delete()
            db.query(Ingredient).delete()

            # 새 데이터 추가
            for ing in data.ingredients:
                db.add(Ingredient(name=ing.name, quantity=ing.quantity, unit=ing.unit,
                                  category=ing.category, expiry_date=ing.expiry_date))
            for mh in data.meal_history:
                db.add(MealHistory(date=mh.date, breakfast=mh.breakfast,
                                  lunch=mh.lunch, dinner=mh.dinner, note=mh.note))
            for b in data.budget:
                db.add(Budget(item=b.item, price=b.price, purchase_date=b.purchase_date))
            for bs in data.blood_sugar:
                db.add(BloodSugar(date=bs.date, time=bs.time, level=bs.level, note=bs.note))
            for fav in data.favorites:
                db.add(MealFavorite(name=fav.name, breakfast=fav.breakfast,
                                   lunch=fav.lunch, dinner=fav.dinner, note=fav.note,
                                   breakfast_data=fav.breakfast_data, lunch_data=fav.lunch_data,
                                   dinner_data=fav.dinner_data))
    except Exception:
        logger.exception("백업 복원 중 오류 발생, 롤백됨")
        raise HTTPException(status_code=500, detail='데이터 복원 중 오류가 발생하여 롤백되었습니다. 기존 데이터는 보존됩니다.')

    db.commit()
    logger.info(f"백업 복원 완료: 식재료 {len(data.ingredients)}종, 식단 {len(data.meal_history)}건, 예산 {len(data.budget)}건, 혈당 {len(data.blood_sugar)}건, 즐겨찾기 {len(data.favorites)}건")
    return MessageResponse(message='데이터 복원이 완료되었습니다.')
