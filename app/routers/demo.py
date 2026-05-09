"""
Demo Monitoring API - 데모 기간 라이더 활동 수집 및 통계 조회
"""
import time
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models.demo_event import DemoEvent
from app.schemas import (
    DemoEventCreate, DemoEventBatchCreate,
    RiderDemoStats, DemoSummary,
    EarningsDashboard, EarningsPeriod, HourlyEarnings,
    HotzoneResponse, HotzoneCluster,
)
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

_24H_MS  = 24 * 60 * 60 * 1000
_7D_MS   =  7 * 24 * 60 * 60 * 1000
_30D_MS  = 30 * 24 * 60 * 60 * 1000


# ── 인증 헬퍼 ───────────────────────────────────────────────────────────────

def _verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


def _verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


# ── 이벤트 수신 (Android → Backend) ────────────────────────────────────────

@router.post("/events", status_code=status.HTTP_201_CREATED)
def receive_event(
    event: DemoEventCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key),
):
    """Android 앱에서 단건 이벤트를 수신합니다."""
    now = int(time.time() * 1000)
    db.add(DemoEvent(**event.model_dump(), created_at=now))
    db.commit()
    return {"ok": True}


@router.post("/events/batch", status_code=status.HTTP_201_CREATED)
def receive_events_batch(
    body: DemoEventBatchCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key),
):
    """Android 앱에서 이벤트를 일괄 수신합니다 (오프라인 큐 flush용)."""
    now = int(time.time() * 1000)
    db.add_all([DemoEvent(**e.model_dump(), created_at=now) for e in body.events])
    db.commit()
    return {"ok": True, "count": len(body.events)}


# ── 라이더별 통계 ────────────────────────────────────────────────────────────

def _build_rider_stats(device_id: str, db: Session) -> RiderDemoStats:
    rows = db.query(DemoEvent).filter(DemoEvent.device_id == device_id).all()
    if not rows:
        return RiderDemoStats(device_id=device_id)

    now = int(time.time() * 1000)
    timestamps = [r.timestamp for r in rows]

    call_rows    = [r for r in rows if r.event_type == "CALL_DETECTED"]
    accepted     = [r for r in rows if r.rider_action == "ACCEPTED"]
    rejected     = [r for r in rows if r.rider_action == "REJECTED"]
    session_rows = [r for r in rows if r.event_type == "APP_STARTED"]

    total_detected = len(call_rows)
    total_accepted = len(accepted)
    total_rejected = len(rejected)
    acceptance_rate = (total_accepted / total_detected * 100) if total_detected else 0.0

    # AI 일치율: rider_action 이 있는 CALL 이벤트 중 AI 추천 == 라이더 행동
    with_action = [r for r in call_rows if r.rider_action and r.ai_recommended is not None]
    if with_action:
        matched = sum(
            1 for r in with_action
            if (r.ai_recommended and r.rider_action == "ACCEPTED")
            or (not r.ai_recommended and r.rider_action == "REJECTED")
        )
        ai_match_rate = matched / len(with_action) * 100
    else:
        ai_match_rate = 0.0

    avg_fee = (
        sum(r.estimated_fee for r in accepted if r.estimated_fee) / len(accepted)
        if accepted else None
    )
    avg_eff = (
        sum(r.efficiency_score for r in call_rows if r.efficiency_score is not None)
        / len([r for r in call_rows if r.efficiency_score is not None])
        if any(r.efficiency_score is not None for r in call_rows) else None
    )
    avg_dist = (
        sum(r.distance_km for r in call_rows if r.distance_km)
        / len([r for r in call_rows if r.distance_km])
        if any(r.distance_km for r in call_rows) else None
    )

    platform_breakdown: dict = {}
    for r in call_rows:
        if r.platform:
            platform_breakdown[r.platform] = platform_breakdown.get(r.platform, 0) + 1

    return RiderDemoStats(
        device_id=device_id,
        first_seen=min(timestamps),
        last_seen=max(timestamps),
        is_active=(now - max(timestamps)) < _24H_MS,
        total_sessions=len(session_rows),
        total_detected=total_detected,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        acceptance_rate=round(acceptance_rate, 1),
        ai_match_rate=round(ai_match_rate, 1),
        avg_fee_accepted=round(avg_fee, 0) if avg_fee else None,
        avg_efficiency_score=round(avg_eff, 1) if avg_eff else None,
        avg_distance_km=round(avg_dist, 2) if avg_dist else None,
        platform_breakdown=platform_breakdown,
    )


@router.get("/stats/{device_id}", response_model=RiderDemoStats)
def get_rider_stats(
    device_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """라이더 1명의 데모 통계를 반환합니다."""
    return _build_rider_stats(device_id, db)


# ── 전체 데모 요약 ────────────────────────────────────────────────────────────

@router.get("/summary", response_model=DemoSummary)
def get_demo_summary(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """전체 데모 현황 요약을 반환합니다."""
    device_ids: List[str] = [
        row[0] for row in db.query(DemoEvent.device_id).distinct().all()
    ]

    rider_stats = [_build_rider_stats(did, db) for did in device_ids]

    now           = int(time.time() * 1000)
    active_24h    = sum(1 for r in rider_stats if r.is_active)
    total_detected = sum(r.total_detected for r in rider_stats)
    total_accepted = sum(r.total_accepted for r in rider_stats)
    total_rejected = sum(r.total_rejected for r in rider_stats)

    overall_acceptance = (total_accepted / total_detected * 100) if total_detected else 0.0

    # 전체 AI 일치율 평균
    valid_ai = [r for r in rider_stats if r.total_detected > 0]
    overall_ai = (
        sum(r.ai_match_rate for r in valid_ai) / len(valid_ai) if valid_ai else 0.0
    )

    # 전체 플랫폼 합산
    platform_total: dict = {}
    for r in rider_stats:
        for platform, cnt in r.platform_breakdown.items():
            platform_total[platform] = platform_total.get(platform, 0) + cnt

    return DemoSummary(
        total_riders=len(device_ids),
        active_riders_24h=active_24h,
        total_calls_detected=total_detected,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        overall_acceptance_rate=round(overall_acceptance, 1),
        overall_ai_match_rate=round(overall_ai, 1),
        platform_breakdown=platform_total,
        riders=rider_stats,
    )


# ── 라이더 목록 ──────────────────────────────────────────────────────────────

@router.get("/riders")
def list_riders(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """데모에 참여한 라이더 device_id 목록과 마지막 활동 시각을 반환합니다."""
    rows = (
        db.query(DemoEvent.device_id, func.max(DemoEvent.timestamp).label("last_seen"))
        .group_by(DemoEvent.device_id)
        .order_by(func.max(DemoEvent.timestamp).desc())
        .all()
    )
    now = int(time.time() * 1000)
    return [
        {
            "device_id": r.device_id,
            "last_seen": r.last_seen,
            "is_active": (now - r.last_seen) < _24H_MS,
        }
        for r in rows
    ]


# ── 수익 대시보드 ─────────────────────────────────────────────────────────────

@router.get("/earnings/{device_id}", response_model=EarningsDashboard)
def get_earnings(
    device_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key),   # 라이더 본인도 조회 가능
):
    """
    라이더 수익 대시보드를 반환합니다.
    - 오늘 / 이번 주 / 이번 달 수익
    - 시간대별 수익 분석
    - 최고 수익 시간대 / 플랫폼
    """
    now = int(time.time() * 1000)
    accepted = (
        db.query(DemoEvent)
        .filter(
            DemoEvent.device_id  == device_id,
            DemoEvent.rider_action == "ACCEPTED",
            DemoEvent.estimated_fee != None,
        )
        .all()
    )

    def _period(rows, since_ms: int) -> EarningsPeriod:
        filtered = [r for r in rows if r.timestamp >= since_ms]
        fees = [r.estimated_fee for r in filtered if r.estimated_fee]
        return EarningsPeriod(
            calls    = len(filtered),
            earnings = sum(fees),
            avg_fee  = round(sum(fees) / len(fees), 0) if fees else 0.0,
        )

    today_period = _period(accepted, now - _24H_MS)
    week_period  = _period(accepted, now - _7D_MS)
    month_period = _period(accepted, now - _30D_MS)

    # 시간대별 집계 (0~23)
    from collections import defaultdict
    hourly: dict = defaultdict(lambda: {"calls": 0, "earnings": 0})
    for r in accepted:
        if r.timestamp >= now - _30D_MS:
            import datetime
            hour = datetime.datetime.fromtimestamp(r.timestamp / 1000).hour
            hourly[hour]["calls"]    += 1
            hourly[hour]["earnings"] += r.estimated_fee or 0

    hourly_list = [
        HourlyEarnings(hour=h, calls=v["calls"], earnings=v["earnings"])
        for h, v in sorted(hourly.items())
    ]
    best_hour = max(hourly, key=lambda h: hourly[h]["earnings"], default=None)

    # 플랫폼별 평균 단가
    platform_fees: dict = defaultdict(list)
    for r in accepted:
        if r.platform and r.estimated_fee:
            platform_fees[r.platform].append(r.estimated_fee)
    best_platform = max(
        platform_fees,
        key=lambda p: sum(platform_fees[p]) / len(platform_fees[p]),
        default=None,
    ) if platform_fees else None

    return EarningsDashboard(
        device_id        = device_id,
        today            = today_period,
        this_week        = week_period,
        this_month       = month_period,
        hourly_breakdown = hourly_list,
        best_hour        = best_hour,
        best_platform    = best_platform,
    )


# ── 핫존 히트맵 ───────────────────────────────────────────────────────────────

@router.get("/hotzone", response_model=HotzoneResponse)
def get_hotzone(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """
    전체 라이더의 주문 감지 위치를 격자(500m 단위)로 집계해 핫존 히트맵 데이터를 반환합니다.
    """
    GRID = 0.005  # 약 500m 격자

    rows = (
        db.query(DemoEvent)
        .filter(
            DemoEvent.event_type == "CALL_DETECTED",
            DemoEvent.rider_lat  != None,
            DemoEvent.rider_lng  != None,
        )
        .all()
    )

    from collections import defaultdict
    grid: dict = defaultdict(lambda: {"count": 0, "fees": []})

    for r in rows:
        # 격자 좌표로 스냅
        glat = round(round(r.rider_lat / GRID) * GRID, 4)
        glng = round(round(r.rider_lng / GRID) * GRID, 4)
        key  = (glat, glng)
        grid[key]["count"] += 1
        if r.estimated_fee:
            grid[key]["fees"].append(r.estimated_fee)

    clusters = [
        HotzoneCluster(
            lat     = k[0],
            lng     = k[1],
            count   = v["count"],
            avg_fee = round(sum(v["fees"]) / len(v["fees"]), 0) if v["fees"] else None,
        )
        for k, v in sorted(grid.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    return HotzoneResponse(clusters=clusters, total_points=len(rows))


# ── 이벤트 로그 (디버그용) ───────────────────────────────────────────────────

@router.get("/events/{device_id}")
def get_device_events(
    device_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_key),
):
    """특정 라이더의 이벤트 로그를 최신순으로 반환합니다."""
    events = (
        db.query(DemoEvent)
        .filter(DemoEvent.device_id == device_id)
        .order_by(DemoEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
    return events
