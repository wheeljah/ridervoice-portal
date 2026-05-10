"""
User model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    device_id = Column(String(100), nullable=True, index=True)

    # 프로필
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    birth_date = Column(String(20), nullable=True)

    # 배달 계정 (JSON 문자열로 저장)
    delivery_accounts = Column(Text, nullable=True)

    # License info
    current_license_type = Column(String(20), nullable=True)
    current_license_expires_at = Column(BigInteger, nullable=True)  # 밀리초 유지

    # Pause info
    is_paused = Column(Boolean, default=False)
    pause_start_time = Column(BigInteger, nullable=True)
    pause_end_time = Column(BigInteger, nullable=True)

    # Timestamps — DateTime으로 저장, API 응답 시 밀리초로 변환
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    def __init__(self, **kwargs):
        now = datetime.now(timezone.utc)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = now
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = now
        super().__init__(**kwargs)
