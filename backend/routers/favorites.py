"""식단 즐겨찾기 CRUD 라우터"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db, MealFavorite
from backend.models import MealFavoriteCreate, MealFavoriteResponse, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.favorites')
router = APIRouter(prefix='/api/favorites', tags=['favorites'])


def _to_favorite_response(fav: MealFavorite) -> MealFavoriteResponse:
    data = {}
    for field in ('breakfast_data', 'lunch_data', 'dinner_data'):
        raw = getattr(fav, field)
        if raw:
            try:
                data[field] = json.loads(raw)
            except Exception:
                data[field] = None
        else:
            data[field] = None

    return MealFavoriteResponse(
        id=fav.id,
        name=fav.name,
        breakfast=fav.breakfast,
        lunch=fav.lunch,
        dinner=fav.dinner,
        breakfast_data=data['breakfast_data'],
        lunch_data=data['lunch_data'],
        dinner_data=data['dinner_data'],
        note=fav.note,
        created_at=fav.created_at,
    )


@router.get('', response_model=List[MealFavoriteResponse])
async def get_favorites(db: Session = Depends(get_db)):
    favorites = db.query(MealFavorite).order_by(MealFavorite.created_at.desc()).all()
    logger.debug(f"즐겨찾기 조회: {len(favorites)}건")
    return [_to_favorite_response(fav) for fav in favorites]


def _dump_meal_data(meal_data):
    if not meal_data:
        return None
    if hasattr(meal_data, 'model_dump'):
        return json.dumps(meal_data.model_dump())
    return json.dumps(meal_data)


@router.post('', response_model=MealFavoriteResponse)
async def add_favorite(body: MealFavoriteCreate, db: Session = Depends(get_db)):
    fav = MealFavorite(
        name=body.name,
        breakfast=body.breakfast or (body.breakfast_data.name if body.breakfast_data else None),
        lunch=body.lunch or (body.lunch_data.name if body.lunch_data else None),
        dinner=body.dinner or (body.dinner_data.name if body.dinner_data else None),
        note=body.note,
        breakfast_data=_dump_meal_data(body.breakfast_data),
        lunch_data=_dump_meal_data(body.lunch_data),
        dinner_data=_dump_meal_data(body.dinner_data),
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    logger.info(f"즐겨찾기 추가: {body.name}")
    return _to_favorite_response(fav)


@router.delete('/{fav_id}', response_model=MessageResponse)
async def delete_favorite(fav_id: int, db: Session = Depends(get_db)):
    fav = db.query(MealFavorite).filter(MealFavorite.id == fav_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail='즐겨찾기를 찾을 수 없습니다.')
    db.delete(fav)
    db.commit()
    logger.info(f"즐겨찾기 삭제: id={fav_id}")
    return MessageResponse(message='즐겨찾기가 삭제되었습니다.', detail=f'ID: {fav_id}')
