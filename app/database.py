"""
Database connection and session management for RiderVoice AI Backend
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# DEBUG: 실제 DATABASE_URL 확인
print(f"[DEBUG] Final DATABASE_URL: {settings.DATABASE_URL}")
print(f"[DEBUG] is_postgres: {settings.is_postgres}")

if settings.is_postgres:
    print(f"[DEBUG] Creating PostgreSQL engine with pool settings...")
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # 끊어진 커넥션 자동 감지
    )
else:
    print(f"[DEBUG] Creating SQLite engine (fallback mode)...")
    # 로컬 개발용 SQLite fallback
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    # 컬럼 마이그레이션
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS delivery_accounts JSONB DEFAULT '[]'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_license_type VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_license_expires_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS pause_start_time TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS pause_end_time TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception:
                pass
        conn.commit()
