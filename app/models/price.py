"""
Price model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from app.database import Base


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_type = Column(String(20), unique=True, nullable=False)  # LM1, LM3, LM6, LMY
    display_name = Column(String(50), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)  # 원화 (KRW)
    is_active = Column(Boolean, default=True)
    updated_at = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        import time
        kwargs['updated_at'] = int(time.time() * 1000)
        super().__init__(**kwargs)