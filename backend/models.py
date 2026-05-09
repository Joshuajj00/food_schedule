from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime

# ========== 식재료 관련 모델 ==========

class IngredientCreate(BaseModel):
    """식재료 생성 요청"""
    name: str
    quantity: float
    unit: str
    category: str = '기타'   # 단백질 / 채소 / 탄수화물 / 유제품 / 양념 / 기타
    expiry_date: Optional[date] = None

class IngredientResponse(BaseModel):
    """식재료 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    quantity: float
    unit: str
    category: str = '기타'
    expiry_date: Optional[date] = None
    created_at: datetime

# ========== 식단 관련 모델 ==========

class MealNutrition(BaseModel):
    """영양소 정보"""
    calories: int = 0
    protein_g: int = 0
    carbs_g: int = 0
    fat_g: int = 0

class MealItem(BaseModel):
    """개별 식단 아이템"""
    name: str = ''
    ingredients: list[str] = Field(default_factory=list)
    how_to: str = ''
    nutrition: MealNutrition = Field(default_factory=MealNutrition)

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
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

# ========== 예산 관련 모델 ==========

class BudgetCreate(BaseModel):
    """예산 기록 생성 요청"""
    item: str
    price: int
    purchase_date: date

class BudgetResponse(BaseModel):
    """예산 기록 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: str
    price: int
    purchase_date: date
    created_at: datetime

class WeeklyBudgetResponse(BaseModel):
    """주간 예산 현황 응답"""
    total_spent: int
    items: list[BudgetResponse]

# ========== LLM 설정 모델 ==========

class LLMSettingsUpdate(BaseModel):
    # Pydantic v2는 'model_' 접두사를 내부 네임스페이스로 예약 — model_name 필드 경고 억제
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime

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

# ========== 식재료 업데이트 모델 ==========

class IngredientUpdate(BaseModel):
    """식재료 수정 요청"""
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    expiry_date: Optional[date] = None

# ========== 혈당 모델 ==========

class BloodSugarCreate(BaseModel):
    """혈당 기록 생성 요청"""
    date: date
    time: str   # 아침식전 / 아침식후 / 점심식전 / 점심식후 / 저녁식전 / 저녁식후 / 취침전
    level: int
    note: Optional[str] = None

class BloodSugarResponse(BaseModel):
    """혈당 기록 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    time: str
    level: int
    note: Optional[str] = None
    created_at: datetime

# ========== 즐겨찾기 모델 ==========

class MealFavoriteCreate(BaseModel):
    """즐겨찾기 생성 요청"""
    name: str
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    note: Optional[str] = None

class MealFavoriteResponse(BaseModel):
    """즐겨찾기 응답"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    breakfast: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

# ========== 백업 모델 ==========

class BackupData(BaseModel):
    """백업 데이터"""
    ingredients: list[IngredientResponse]
    meal_history: list[MealHistoryResponse]
    budget: list[BudgetResponse]
    blood_sugar: list[BloodSugarResponse]
    favorites: list[MealFavoriteResponse]
