"""혈당 기록 CRUD 라우터"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from backend.database import get_db, BloodSugar
from backend.models import BloodSugarCreate, BloodSugarResponse, MessageResponse
from backend.logger import get_logger

logger = get_logger('routers.blood_sugar')
router = APIRouter(prefix='/api/blood-sugar', tags=['blood_sugar'])


@router.get('', response_model=List[BloodSugarResponse])
async def get_records(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
):
    query = db.query(BloodSugar)
    if start_date:
        query = query.filter(BloodSugar.date >= start_date)
    if end_date:
        query = query.filter(BloodSugar.date <= end_date)
    records = query.order_by(BloodSugar.date.desc(), BloodSugar.time.asc()).all()
    logger.debug(f"혈당 기록 조회: {len(records)}건")
    return records


@router.post('', response_model=BloodSugarResponse)
async def add_record(body: BloodSugarCreate, db: Session = Depends(get_db)):
    record = BloodSugar(
        date=body.date,
        time=body.time,
        level=body.level,
        note=body.note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"혈당 기록 추가: {body.date} {body.time} {body.level}mg/dL")
    return record


@router.delete('/{record_id}', response_model=MessageResponse)
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(BloodSugar).filter(BloodSugar.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail='혈당 기록을 찾을 수 없습니다.')
    db.delete(record)
    db.commit()
    logger.info(f"혈당 기록 삭제: id={record_id}")
    return MessageResponse(message='혈당 기록이 삭제되었습니다.', detail=f'ID: {record_id}')
