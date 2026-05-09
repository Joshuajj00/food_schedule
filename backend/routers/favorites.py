"""식단 즐겨찾기 CRUD 라우터"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db, MealFavorite
from backend.models import MealFavoriteCreate, MealFavoriteResponse, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.favorites')
router = APIRouter(prefix='/api/favorites', tags=['favorites'])


@router.get('', response_model=List[MealFavoriteResponse])
async def get_favorites(db: Session = Depends(get_db)):
    favorites = db.query(MealFavorite).order_by(MealFavorite.created_at.desc()).all()
    logger.debug(f"즐겨찾기 조회: {len(favorites)}건")
    return favorites


@router.post('', response_model=MealFavoriteResponse)
async def add_favorite(body: MealFavoriteCreate, db: Session = Depends(get_db)):
    fav = MealFavorite(
        name=body.name,
        breakfast=body.breakfast,
        lunch=body.lunch,
        dinner=body.dinner,
        note=body.note,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    logger.info(f"즐겨찾기 추가: {body.name}")
    return fav


@router.delete('/{fav_id}', response_model=MessageResponse)
async def delete_favorite(fav_id: int, db: Session = Depends(get_db)):
    fav = db.query(MealFavorite).filter(MealFavorite.id == fav_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail='즐겨찾기를 찾을 수 없습니다.')
    db.delete(fav)
    db.commit()
    logger.info(f"즐겨찾기 삭제: id={fav_id}")
    return MessageResponse(message='즐겨찾기가 삭제되었습니다.', detail=f'ID: {fav_id}')
