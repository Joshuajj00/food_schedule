from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db, LLMSettings as LLMSettingsDB
from backend.models import LLMSettingsUpdate, LLMSettingsResponse
from backend.ai_client import ai_client
from backend.logger import get_logger

logger = get_logger('routers.settings')
router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "provider": "openai",
    "base_url": "https://api.openai.com",
    "api_key": "",
    "model_name": "",
    "api_format": "openai",
    "streaming": False,
    "thinking_mode": "none",
    "thinking_budget": 8000,
    "reasoning_effort": "none",
}


def _get_or_create(db: Session) -> LLMSettingsDB:
    row = db.query(LLMSettingsDB).first()
    if not row:
        row = LLMSettingsDB(**DEFAULT_SETTINGS)
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("LLM 설정 초기값 생성")
    return row


@router.get("", response_model=LLMSettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    logger.debug(f"설정 조회: provider={row.provider}, model={row.model_name}")
    return row


@router.put("", response_model=LLMSettingsResponse)
async def update_settings(body: LLMSettingsUpdate, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    for field, value in body.model_dump().items():
        setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    logger.info(f"설정 업데이트: provider={body.provider}, model={body.model_name}, format={body.api_format}")
    return row


@router.post("/test")
async def test_connection(db: Session = Depends(get_db)):
    settings = _get_or_create(db)
    if not settings.model_name:
        raise HTTPException(status_code=400, detail="모델명이 설정되지 않았습니다.")

    logger.info(f"연결 테스트: provider={settings.provider}, model={settings.model_name}")
    test_system = "You are a test assistant. Respond only with valid JSON."
    test_user = 'Respond with exactly: {"ok": true}'

    try:
        result = await ai_client.generate(test_system, test_user, settings)
        if "error" in result and "ok" not in result:
            raise HTTPException(status_code=502, detail=f"API 응답 파싱 실패: {result.get('raw_response', '')[:200]}")
        logger.info(f"연결 테스트 성공: {settings.provider}/{settings.model_name}")
        return {"message": f"연결 성공 ({settings.provider} / {settings.model_name})"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"연결 테스트 실패: {e}")
        raise HTTPException(status_code=502, detail=str(e))
