"""
Configuration settings for RiderVoice AI Backend
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Leapcell PostgreSQL 프로덕션 설정"""

    # ===== Database (PostgreSQL - Leapcell) =====
    # Leapcell 대시보드 > Database > Connection String 값을 환경변수로 설정
    DATABASE_URL: str = "sqlite:///./app.db"

    # ===== Connection Pool (PostgreSQL) =====
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30분마다 커넥션 재생성

    # ===== Security =====
    API_KEY: str = "rv-api-key-change-in-production-2026"
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_KEY: str = "rv-admin-key-change-in-production-2026"
    SECRET_KEY: str = "rv-secret-key-for-signature-2026"

    # ===== Server =====
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # ===== Rate Limiting =====
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # ===== License Settings =====
    LICENSE_SIGNATURE_EXPIRY_DAYS: int = 365
    MAX_COUPONS_PER_REQUEST: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
