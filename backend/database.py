from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# SQLite DB 경로 설정 (환경변수 또는 기본값)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/diet.db')

# SQLAlchemy 설정
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 식재료 테이블
class Ingredient(Base):
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# 식단 기록 테이블
class MealHistory(Base):
    __tablename__ = 'meal_history'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    breakfast = Column(String, nullable=True)
    lunch = Column(String, nullable=True)
    dinner = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# 예산 기록 테이블
class Budget(Base):
    __tablename__ = 'budget'
    
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    purchase_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    updated_at       = Column(DateTime, default=datetime.utcnow)

# DB 초기화 함수
def init_db():
    Base.metadata.create_all(bind=engine)

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
