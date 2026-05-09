"""
Coupon model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from app.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coupon_code = Column(String(100), unique=True, nullable=False, index=True)
    coupon_type = Column(String(20), nullable=False)  # PAU4, PAU1, PAU3, PAU5
    device_id = Column(String(100), nullable=True, index=True)
    
    # Duration info
    duration_hours = Column(Integer, nullable=False)
    
    # Status
    is_redeemed = Column(Boolean, default=False)
    redeemed_at = Column(BigInteger, nullable=True)
    
    # Pause schedule (user can select date when applying)
    pause_start_time = Column(BigInteger, nullable=True)
    pause_end_time = Column(BigInteger, nullable=True)
    
    # Timestamps
    created_at = Column(BigInteger, nullable=False)

    def __init__(self, **kwargs):
        import time
        if 'created_at' not in kwargs:
            kwargs['created_at'] = int(time.time() * 1000)
        super().__init__(**kwargs)