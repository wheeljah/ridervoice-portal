"""
RiderVoiceAI Backend Notification Raw Data API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.notification import NotificationRawData
from app.schemas import NotificationRawDataCreate, NotificationRawDataResponse, NotificationRawDataBatchCreate

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/raw-data", response_model=NotificationRawDataResponse, status_code=status.HTTP_201_CREATED)
def create_notification_raw_data(
    notification: NotificationRawDataCreate,
    db: Session = Depends(get_db)
):
    """
    알림 원본 데이터를 저장합니다.
    테스트 기간 중 수집한 알림 데이터를 백엔드에 저장합니다.
    """
    db_notification = NotificationRawData(
        device_id=notification.device_id,
        app_package=notification.app_package,
        app_name=notification.app_name,
        title=notification.title,
        text=notification.text,
        sub_text=notification.sub_text,
        big_text=notification.big_text,
        extra_text=notification.extra_text,
        raw_data=notification.raw_data,
        timestamp=notification.timestamp,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


@router.post("/raw-data/batch", response_model=List[NotificationRawDataResponse], status_code=status.HTTP_201_CREATED)
def create_notification_raw_data_batch(
    request: NotificationRawDataBatchCreate,
    db: Session = Depends(get_db)
):
    """
    알림 원본 데이터를 일괄 저장합니다.
    여러 개의 알림 데이터를 한 번의 요청으로 저장합니다.
    """
    db_notifications = []
    for notification in request.notifications:
        db_notification = NotificationRawData(
            device_id=notification.device_id,
            app_package=notification.app_package,
            app_name=notification.app_name,
            title=notification.title,
            text=notification.text,
            sub_text=notification.sub_text,
            big_text=notification.big_text,
            extra_text=notification.extra_text,
            raw_data=notification.raw_data,
            timestamp=notification.timestamp,
        )
        db_notifications.append(db_notification)
    
    db.add_all(db_notifications)
    db.commit()
    for n in db_notifications:
        db.refresh(n)
    
    return db_notifications


@router.get("/raw-data", response_model=List[NotificationRawDataResponse])
def get_notification_raw_data(
    device_id: str = None,
    app_package: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    저장된 알림 원본 데이터 목록을 조회합니다.
    """
    query = db.query(NotificationRawData)
    
    if device_id:
        query = query.filter(NotificationRawData.device_id == device_id)
    if app_package:
        query = query.filter(NotificationRawData.app_package == app_package)
    
    return query.order_by(NotificationRawData.timestamp.desc()).offset(offset).limit(limit).all()


@router.get("/raw-data/{notification_id}", response_model=NotificationRawDataResponse)
def get_notification_raw_data_by_id(
    notification_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 알림 원본 데이터를 조회합니다.
    """
    notification = db.query(NotificationRawData).filter(NotificationRawData.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("/stats")
def get_notification_stats(
    device_id: str = None,
    db: Session = Depends(get_db)
):
    """
    알림 데이터 수집 통계 정보를 반환합니다.
    """
    query = db.query(NotificationRawData)
    
    if device_id:
        query = query.filter(NotificationRawData.device_id == device_id)
    
    total_count = query.count()
    
    # 앱별 통계
    from sqlalchemy import func
    app_stats = db.query(
        NotificationRawData.app_package,
        NotificationRawData.app_name,
        func.count(NotificationRawData.id).label('count')
    ).group_by(
        NotificationRawData.app_package,
        NotificationRawData.app_name
    ).all()
    
    return {
        "total_count": total_count,
        "app_stats": [{"app_package": s[0], "app_name": s[1], "count": s[2]} for s in app_stats]
    }


@router.delete("/raw-data", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification_raw_data(
    device_id: str = None,
    before_timestamp: int = None,
    db: Session = Depends(get_db)
):
    """
    저장된 알림 원본 데이터를 삭제합니다.
    device_id 또는 before_timestamp를 기준으로 필터링할 수 있습니다.
    """
    query = db.query(NotificationRawData)
    
    if device_id:
        query = query.filter(NotificationRawData.device_id == device_id)
    if before_timestamp:
        query = query.filter(NotificationRawData.timestamp < before_timestamp)
    
    query.delete()
    db.commit()
    return None