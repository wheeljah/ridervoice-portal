"""
Database connection and session management for RiderVoice AI Backend
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

if settings.is_postgres:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )
else:
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

    # 컬럼 마이그레이션 (PostgreSQL 전용)
    if settings.is_postgres:
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date VARCHAR",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS delivery_accounts TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_license_type VARCHAR",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS current_license_expires_at BIGINT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS pause_start_time BIGINT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS pause_end_time BIGINT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
            # licenses 테이블 컬럼 추가
            "ALTER TABLE licenses ADD COLUMN IF NOT EXISTS redeemed_by_device VARCHAR",
            # redemption_logs 테이블 컬럼 추가
            "ALTER TABLE redemption_logs ADD COLUMN IF NOT EXISTS error_message TEXT",
            "ALTER TABLE redemption_logs ALTER COLUMN created_at TYPE BIGINT",
        ]
        with engine.connect() as conn:
            for sql in migrations:
                try:
                    conn.execute(text(sql))
                except Exception as e:
                    print(f"[MIGRATION] SKIP: {sql[:60]}… → {e}")
            conn.commit()
