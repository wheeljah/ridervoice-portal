"""
RiderVoiceAI Backend API Routers - Health Check Endpoints
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas import HealthResponse, ErrorResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    기본 헬스 체크

    서버가 정상적으로 동작하고 있는지 확인합니다.
    """
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time() * 1000),
        version="1.0.0"
    )


@router.get("/health/db", response_model=HealthResponse)
def health_check_with_db(db: Session = Depends(get_db)):
    """
    데이터베이스 포함 헬스 체크

    서버와 데이터베이스 연결이 정상적인지 확인합니다.
    """
    try:
        # DB 연결 테스트
        db.execute(text("SELECT 1"))
        return HealthResponse(
            status="healthy",
            timestamp=int(time.time() * 1000),
            version="1.0.0"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=int(time.time() * 1000),
            version="1.0.0"
        )


# Leapcell health check 엔드포인트 (typo 포함된 경로도 지원)
@router.get("/kaithheathcheck", response_model=HealthResponse)
@router.get("/kaithhealthcheck", response_model=HealthResponse)
def leapcell_health_check():
    """
    Leapcell 플랫폼 health check 엔드포인트
    
    Leapcell이 요청하는 /kaithheathcheck 경로에 응답합니다.
    서버가 포트 8000에서 응답하면 Leapcell 프록시가 서버에 도달한 것으로 인식합니다.
    """
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time() * 1000),
        version="1.1.0"
    )