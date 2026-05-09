"""
Delivery Tracking API - 수락 후 픽업→완료까지 GPS 경로 기록 및 조회
"""
import time
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.delivery_tracking import DeliveryTracking
from app.schemas import (
    TrackingBatchCreate, DeliverySession, TrackingPoint,
)
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/tracking", tags=["tracking"])


# ── 인증 ─────────────────────────────────────────────────────────────────────

def _verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


def _verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


# ── GPS 포인트 수신 ───────────────────────────────────────────────────────────

@router.post("/points/batch", status_code=status.HTTP_201_CREATED)
def upload_tracking_points(
    body: TrackingBatchCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key),
):
    """
    Android 앱에서 배달 중 수집한 GPS 포인트를 일괄 업로드합니다.

    - START  : 주문 수락 직후 첫 포인트 (주문 메타 포함)
    - WAYPOINT: 이동 중 중간 포인트 (30초 간격)
    - COMPLETE: 배달 완료 포인트 (실제 소요 시간/거리 포함)
    """
    now = int(time.time() * 1000)

    # START 포인트에서 주문 메타 추출 (나머지 포인트에는 null)
    start_point = next((p for p in body.points if p.point_type == "START"), None)

    rows = []
    for p in body.points:
        is_start    = p.point_type == "START"
        is_complete = p.point_type == "COMPLETE"
        rows.append(DeliveryTracking(
            device_id            = body.device_id,
            session_id           = body.session_id,
            delivery_session_id  = body.delivery_session_id,
            lat                  = p.lat,
            lng                  = p.lng,
            accuracy             = p.accuracy,
            point_type           = p.point_type,
            actual_duration_min  = p.actual_duration_min if is_complete else None,
            actual_distance_km   = p.actual_distance_km  if is_complete else None,
            platform             = body.platform         if is_start else None,
            estimated_fee        = body.estimated_fee    if is_start else None,
            pickup_address       = body.pickup_address   if is_start else None,
            delivery_address     = body.delivery_address if is_start else None,
            timestamp            = p.timestamp,
            created_at           = now,
        ))

    db.add_all(rows)
    db.commit()
    return {"ok": True, "points_saved": len(rows)}


# ── 배달 세션 조회 ─────────────────────────────────────────────────────────────

@router.get("/{device_id}/sessions", response_model=List[DeliverySession])
def get_delivery_sessions(
    device_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """
    라이더의 배달 세션 목록 (최신순) + 각 세션의 GPS 경로를 반환합니다.
    """
    # 세션 ID 목록 (최신순)
    session_ids = (
        db.query(DeliveryTracking.delivery_session_id)
        .filter(DeliveryTracking.device_id == device_id)
        .distinct()
        .order_by(DeliveryTracking.delivery_session_id.desc())
        .limit(limit)
        .all()
    )

    sessions: List[DeliverySession] = []
    for (sid,) in session_ids:
        rows = (
            db.query(DeliveryTracking)
            .filter(
                DeliveryTracking.device_id == device_id,
                DeliveryTracking.delivery_session_id == sid,
            )
            .order_by(DeliveryTracking.timestamp.asc())
            .all()
        )
        if not rows:
            continue

        start_row    = next((r for r in rows if r.point_type == "START"),    None)
        complete_row = next((r for r in rows if r.point_type == "COMPLETE"), None)

        sessions.append(DeliverySession(
            delivery_session_id = sid,
            platform            = start_row.platform         if start_row else None,
            estimated_fee       = start_row.estimated_fee    if start_row else None,
            pickup_address      = start_row.pickup_address   if start_row else None,
            delivery_address    = start_row.delivery_address if start_row else None,
            started_at          = rows[0].timestamp,
            completed_at        = complete_row.timestamp     if complete_row else None,
            actual_duration_min = complete_row.actual_duration_min if complete_row else None,
            actual_distance_km  = complete_row.actual_distance_km  if complete_row else None,
            points=[
                TrackingPoint(
                    lat        = r.lat,
                    lng        = r.lng,
                    accuracy   = r.accuracy,
                    point_type = r.point_type,
                    actual_duration_min = r.actual_duration_min,
                    actual_distance_km  = r.actual_distance_km,
                    timestamp  = r.timestamp,
                )
                for r in rows
            ],
        ))

    return sessions


# ── 전체 활성 배달 현황 (실시간 모니터링) ────────────────────────────────────

@router.get("/active")
def get_active_deliveries(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """
    현재 배달 중인 라이더 목록과 마지막 GPS 포인트를 반환합니다.
    (START 이후 COMPLETE 없는 세션 = 배달 진행 중)
    """
    from sqlalchemy import func

    # 세션별 START/COMPLETE 존재 여부 확인
    all_sessions = (
        db.query(
            DeliveryTracking.device_id,
            DeliveryTracking.delivery_session_id,
            func.max(
                (DeliveryTracking.point_type == "COMPLETE").cast(db.bind.dialect.name == "postgresql" and "int" or "integer")
            ).label("has_complete"),
            func.max(DeliveryTracking.timestamp).label("last_ts"),
            func.max(DeliveryTracking.lat).label("last_lat"),
            func.max(DeliveryTracking.lng).label("last_lng"),
        )
        .group_by(DeliveryTracking.device_id, DeliveryTracking.delivery_session_id)
        .all()
    )

    now = int(time.time() * 1000)
    _30MIN_MS = 30 * 60 * 1000

    active = [
        {
            "device_id":           r.device_id,
            "delivery_session_id": r.delivery_session_id,
            "last_seen":           r.last_ts,
            "last_lat":            r.last_lat,
            "last_lng":            r.last_lng,
        }
        for r in all_sessions
        if not r.has_complete and (now - (r.last_ts or 0)) < _30MIN_MS
    ]
    return {"active_deliveries": active, "count": len(active)}
