"""
User model for RiderVoice AI Backend
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    device_id = Column(String(100), nullable=True, index=True)
    
    # License info
    current_license_type = Column(String(20), nullable=True)
    current_license_expires_at = Column(BigInteger, nullable=True)
    
    # Pause info
    is_paused = Column(Boolean, default=False)
    pause_start_time = Column(BigInteger, nullable=True)
    pause_end_time = Column(BigInteger, nullable=True)
    
    # Timestamps
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        import time
        current_time = int(time.time() * 1000)
        self.created_at = kwargs.get('created_at', current_time)
        self.updated_at = kwargs.get('updated_at', current_time)
        super().__init__(**kwargs)