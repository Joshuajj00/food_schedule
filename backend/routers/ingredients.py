from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database import get_db, Ingredient
from backend.models import IngredientCreate, IngredientResponse, IngredientUpdate, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.ingredients')
router = APIRouter(prefix='/api/ingredients', tags=['ingredients'])


@router.get('', response_model=List[IngredientResponse])
async def get_ingredients(
    search: Optional[str] = Query(None, description='식재료명 검색어'),
    category: Optional[str] = Query(None, description='카테고리 필터'),
    db: Session = Depends(get_db),
):
    query = db.query(Ingredient)
    if search:
        query = query.filter(Ingredient.name.contains(search))
    if category:
        query = query.filter(Ingredient.category == category)
    ingredients = query.order_by(Ingredient.created_at.desc()).all()
    logger.debug(f"식재료 목록 조회: {len(ingredients)}종 (검색={search}, 카테고리={category})")
    return ingredients


@router.post('', response_model=IngredientResponse)
async def add_ingredient(ingredient: IngredientCreate, db: Session = Depends(get_db)):
    db_ingredient = Ingredient(
        name=ingredient.name,
        quantity=ingredient.quantity,
        unit=ingredient.unit,
        category=ingredient.category,
        expiry_date=ingredient.expiry_date,
    )
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    logger.info(f"식재료 추가: {ingredient.name} {ingredient.quantity}{ingredient.unit} [{ingredient.category}]")
    return db_ingredient


@router.put('/{ingredient_id}', response_model=IngredientResponse)
async def update_ingredient(ingredient_id: int, body: IngredientUpdate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail='식재료를 찾을 수 없습니다.')
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    logger.info(f"식재료 수정: {ingredient.name} (id={ingredient_id})")
    return ingredient


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
