"""
User model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)  # username
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
    current_license_expires_at = Column(BigInteger, nullable=True)

    # Pause info
    is_paused = Column(Boolean, default=False)
    pause_start_time = Column(BigInteger, nullable=True)
    pause_end_time = Column(BigInteger, nullable=True)

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    def __init__(self, **kwargs):
        import time
        current_time = int(time.time() * 1000)
        if 'created_at' not in kwargs:
            kwargs['created_at'] = current_time
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = current_time
        super().__init__(**kwargs)
