"""
License model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from app.database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String(100), unique=True, nullable=False, index=True)
    license_type = Column(String(20), nullable=False)  # LM1, LM3, LM6, LMY
    device_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    issued_at = Column(BigInteger, nullable=False)
    redeemed_at = Column(BigInteger, nullable=True)
    redeemed_by_device = Column(String(100), nullable=True)
    expires_at = Column(BigInteger, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=False)
    created_at = Column(BigInteger, nullable=False)

    def __init__(self, **kwargs):
        import time
        if 'created_at' not in kwargs:
            kwargs['created_at'] = int(time.time() * 1000)
        super().__init__(**kwargs)