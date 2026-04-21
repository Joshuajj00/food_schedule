from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime

# ========== 식재료 관련 모델 ==========

class IngredientCreate(BaseModel):
    """식재료 생성 요청"""
    name: str
    quantity: float
    unit: str
    expiry_date: Optional[date] = None

class IngredientResponse(BaseModel):
    """식재료 응답"""
    id: int
    name: str
    quantity: float
    unit: str
    expiry_date: Optional[date] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== 식단 관련 모델 ==========

class MealItem(BaseModel):
    """개별 식단 아이템"""
    name: str = ''
    ingredients: list[str] = Field(default_factory=list)
    how_to: str = ''

class MealPlan(BaseModel):
    """식단 계획"""
    breakfast: MealItem = Field(default_factory=MealItem)
    lunch: MealItem = Field(default_factory=MealItem)
    dinner: MealItem = Field(default_factory=MealItem)
    note: str = ''

class MealHistoryCreate(BaseModel):
    """식단 기록 생성 요청"""
    date: date
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    note: Optional[str] = None

class MealHistoryResponse(BaseModel):
    """식단 기록 응답"""
    id: int
    date: date
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== 예산 관련 모델 ==========

class BudgetCreate(BaseModel):
    """예산 기록 생성 요청"""
    item: str
    price: int
    purchase_date: date

class BudgetResponse(BaseModel):
    """예산 기록 응답"""
    id: int
    item: str
    price: int
    purchase_date: date
    created_at: datetime
    
    class Config:
        from_attributes = True

class WeeklyBudgetResponse(BaseModel):
    """주간 예산 현황 응답"""
    total_spent: int
    items: list[BudgetResponse]

# ========== LLM 설정 모델 ==========

class LLMSettingsUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str = 'openai'
    base_url: str = 'https://api.openai.com'
    api_key: str = ''
    model_name: str = ''
    api_format: str = 'openai'
    streaming: bool = False
    thinking_mode: str = 'none'
    thinking_budget: int = 8000
    reasoning_effort: str = 'none'

class LLMSettingsResponse(LLMSettingsUpdate):
    """LLM 설정 응답"""
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# ========== 예산 추천 모델 ==========

class BudgetRecommendRequest(BaseModel):
    budget: int

class BudgetRecommendItem(BaseModel):
    name: str
    quantity: float
    unit: str
    estimated_price: int
    reason: str = ''

class BudgetRecommendResponse(BaseModel):
    items: list[BudgetRecommendItem]
    total_estimated: int
    note: str = ''

# ========== 공통 응답 모델 ==========

class MessageResponse(BaseModel):
    """메시지 응답"""
    message: str
    detail: Optional[str] = None
