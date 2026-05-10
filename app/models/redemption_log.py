"""
Redemption Log model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base


class RedemptionLog(Base):
    __tablename__ = "redemption_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String(100), nullable=True)
    license_type = Column(String(20), nullable=True)
    device_id = Column(String(100), nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        import time
        kwargs['created_at'] = int(time.time() * 1000)
        super().__init__(**kwargs)
