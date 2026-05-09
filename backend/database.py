from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, func, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/diet.db')

engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False, 'timeout': 30},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    if 'sqlite' not in DATABASE_URL:
        return
    cursor = dbapi_connection.cursor()
    pragmas = [
        "PRAGMA journal_mode=WAL",
        "PRAGMA synchronous=NORMAL",
        "PRAGMA foreign_keys=ON",
        "PRAGMA busy_timeout=30000",
    ]
    for pragma in pragmas:
        try:
            cursor.execute(pragma)
        except Exception as e:
            import logging
            logging.getLogger('backend.database').warning(
                f"PRAGMA 설정 실패 ({pragma}): {e} — DB 디렉토리 쓰기 권한을 확인하세요."
            )
    cursor.close()

# 식재료 테이블
class Ingredient(Base):
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    category = Column(String, default='기타')
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())

# 식단 기록 테이블
class MealHistory(Base):
    __tablename__ = 'meal_history'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    breakfast = Column(String, nullable=True)
    lunch = Column(String, nullable=True)
    dinner = Column(String, nullable=True)
    note = Column(String, nullable=True)
    breakfast_data = Column(String, nullable=True)  # JSON: 재료·조리법 포함 MealItem
    lunch_data = Column(String, nullable=True)
    dinner_data = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

# 예산 기록 테이블
class Budget(Base):
    __tablename__ = 'budget'
    
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    purchase_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=func.now())

# LLM 설정 테이블
class LLMSettings(Base):
    __tablename__ = 'llm_settings'

    id               = Column(Integer, primary_key=True)
    provider         = Column(String, default='openai')
    base_url         = Column(String, default='https://api.openai.com')
    api_key          = Column(String, default='')
    model_name       = Column(String, default='')
    api_format       = Column(String, default='openai')   # openai | anthropic
    streaming        = Column(Boolean, default=False)
    thinking_mode    = Column(String, default='none')     # none | cot | think
    thinking_budget  = Column(Integer, default=8000)
    reasoning_effort = Column(String, default='none')     # none | low | medium | high
    food_api_key     = Column(String, default='')         # 식약처 식품영양성분DB API 키 (암호화)
    updated_at       = Column(DateTime, default=func.now())

# 혈당 기록 테이블
class BloodSugar(Base):
    __tablename__ = 'blood_sugar'

    id        = Column(Integer, primary_key=True, index=True)
    date      = Column(Date, nullable=False)
    time      = Column(String, nullable=False)            # 아침식전 / 아침식후 / 점심식전 / 점심식후 / 저녁식전 / 저녁식후 / 취침전
    level     = Column(Integer, nullable=False)           # mg/dL
    note      = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

# 식단 즐겨찾기 테이블
class MealFavorite(Base):
    __tablename__ = 'meal_favorite'

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False)            # 즐겨찾기 이름
    breakfast      = Column(String, nullable=True)
    lunch          = Column(String, nullable=True)
    dinner         = Column(String, nullable=True)
    breakfast_data = Column(String, nullable=True)
    lunch_data     = Column(String, nullable=True)
    dinner_data    = Column(String, nullable=True)
    note           = Column(String, nullable=True)
    created_at     = Column(DateTime, default=func.now())

# DB 초기화 함수
def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate(engine)


def _migrate(engine):
    """기존 DB에 누락된 컬럼 추가 (SQLite는 ALTER TABLE ADD COLUMN만 지원)"""
    import sqlite3
    migrations = [
        # (테이블명, 컬럼명, 컬럼정의)
        ('ingredients', 'category', 'VARCHAR DEFAULT \'기타\''),
        ('meal_favorite', 'breakfast_data', 'TEXT'),
        ('meal_favorite', 'lunch_data', 'TEXT'),
        ('meal_favorite', 'dinner_data', 'TEXT'),
        ('meal_history', 'breakfast_data', 'TEXT'),
        ('meal_history', 'lunch_data', 'TEXT'),
        ('meal_history', 'dinner_data', 'TEXT'),
        ('llm_settings', 'food_api_key', "TEXT DEFAULT ''"),
    ]
    with engine.connect() as conn:
        for table, column, col_def in migrations:
            try:
                conn.exec_driver_sql(f'ALTER TABLE {table} ADD COLUMN {column} {col_def}')
            except Exception:
                pass  # 컬럼이 이미 존재하면 무시
        conn.commit()

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
