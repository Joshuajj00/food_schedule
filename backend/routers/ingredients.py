from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db, Ingredient
from backend.models import IngredientCreate, IngredientResponse, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.ingredients')
router = APIRouter(prefix='/api/ingredients', tags=['ingredients'])


@router.get('', response_model=List[IngredientResponse])
async def get_ingredients(db: Session = Depends(get_db)):
    ingredients = db.query(Ingredient).order_by(Ingredient.created_at.desc()).all()
    logger.debug(f"식재료 목록 조회: {len(ingredients)}종")
    return ingredients


@router.post('', response_model=IngredientResponse)
async def add_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    db_ingredient = Ingredient(
        name=ingredient.name,
        quantity=ingredient.quantity,
        unit=ingredient.unit,
        expiry_date=ingredient.expiry_date,
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    logger.info(f"식재료 추가: {ingredient.name} {ingredient.quantity}{ingredient.unit}")
    return db_ingredient


@router.delete('/{ingredient_id}', response_model=MessageResponse)
async def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail='식재료를 찾을 수 없습니다.')
    name = ingredient.name
    db.delete(ingredient)
    db.commit()
    logger.info(f"식재료 삭제: {name} (id={ingredient_id})")
    return MessageResponse(message='식재료가 삭제되었습니다.', detail=f'ID: {ingredient_id}')
