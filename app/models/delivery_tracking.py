"""
Delivery Tracking model - 수락 후 픽업→완료까지 GPS 경로 기록
"""
from sqlalchemy import Column, Integer, String, Float, BigInteger
from app.database import Base


class DeliveryTracking(Base):
    __tablename__ = "delivery_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 식별 ──────────────────────────────────────────
    device_id          = Column(String(255), nullable=False, index=True)
    session_id         = Column(String(100), nullable=True,  index=True)  # 앱 세션
    delivery_session_id= Column(String(100), nullable=False, index=True)  # 건별 배달 세션

    # ── GPS 포인트 ─────────────────────────────────────
    lat      = Column(Float, nullable=False)
    lng      = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)   # 정확도 (m)

    # START | WAYPOINT | COMPLETE
    point_type = Column(String(20), nullable=False, index=True)

    # ── 완료 정보 (COMPLETE 포인트에만 사용) ──────────
    actual_duration_min = Column(Integer, nullable=True)   # 실제 소요 시간 (분)
    actual_distance_km  = Column(Float,   nullable=True)   # 실제 이동 거리 (km)

    # ── 주문 메타 (START 포인트에 저장) ───────────────
    platform         = Column(String(50),  nullable=True)
    estimated_fee    = Column(Integer,     nullable=True)
    pickup_address   = Column(String(500), nullable=True)
    delivery_address = Column(String(500), nullable=True)

    # ── 시간 ──────────────────────────────────────────
    timestamp  = Column(BigInteger, nullable=False, index=True)
    created_at = Column(BigInteger, nullable=True)
