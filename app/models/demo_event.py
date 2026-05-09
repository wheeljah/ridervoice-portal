"""
Demo event tracking model - 데모 기간 라이더 활동 수집
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger
from app.database import Base


class DemoEvent(Base):
    __tablename__ = "demo_events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 기기/세션 ──────────────────────────────────────
    device_id   = Column(String(255), nullable=False, index=True)
    app_version = Column(String(50),  nullable=True)
    session_id  = Column(String(100), nullable=True, index=True)

    # ── 이벤트 종류 ────────────────────────────────────
    # CALL_DETECTED | CALL_ACCEPTED | CALL_REJECTED
    # APP_STARTED   | APP_STOPPED
    event_type = Column(String(50), nullable=False, index=True)

    # ── 주문 정보 (CALL_* 이벤트에만 사용) ────────────
    platform           = Column(String(50),   nullable=True)  # BAEMIN | COUPANG | YOGIYO
    pickup_address     = Column(String(500),  nullable=True)
    delivery_address   = Column(String(500),  nullable=True)
    estimated_fee      = Column(Integer,      nullable=True)  # 원
    estimated_time_min = Column(Integer,      nullable=True)  # 분
    distance_km        = Column(Float,        nullable=True)

    # ── AI 추천 정보 ───────────────────────────────────
    ai_recommended   = Column(Boolean, nullable=True)
    ai_confidence    = Column(Float,   nullable=True)  # 0.0~1.0
    ai_reason        = Column(String(500), nullable=True)
    efficiency_score = Column(Integer, nullable=True)  # 0~100

    # ── 라이더 행동 ────────────────────────────────────
    # ACCEPTED | REJECTED | IGNORED
    rider_action = Column(String(50), nullable=True)

    # ── 라이더 위치 (핫존 히트맵용) ───────────────────
    rider_lat = Column(Float, nullable=True)
    rider_lng = Column(Float, nullable=True)

    # ── 파싱 품질 (유연한 재파싱 지원) ───────────────
    raw_notification_text = Column(String(2000), nullable=True)  # 원본 알림 텍스트 전체
    parse_confidence      = Column(Float,        nullable=True)  # 0.0~1.0 파싱 신뢰도
    parse_warnings        = Column(String(500),  nullable=True)  # 경고 목록 (|구분)

    # ── 시간 ──────────────────────────────────────────
    timestamp  = Column(BigInteger, nullable=False, index=True)  # 이벤트 발생 시각 (ms)
    created_at = Column(BigInteger, nullable=True)               # 서버 수신 시각 (ms)
