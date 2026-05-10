"""
RiderVoiceAI Backend API Routers - License Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas import (
    LicenseRedeemRequest, LicenseRedeemResponse,
    LicenseStatusResponse, LicenseValidateRequest, LicenseValidateResponse
)
from app.services.license_service import LicenseService
from app.config import get_settings

router = APIRouter(prefix="/api/v1/licenses", tags=["licenses"])
settings = get_settings()


def verify_api_key(x_api_key: str = Header(..., alias=settings.API_KEY_HEADER)):
    """API 키 검증"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


@router.post("/redeem", response_model=LicenseRedeemResponse)
def redeem_license(
    request: LicenseRedeemRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    req: Request = None
):
    """
    라이선스 키 Redemption
    
    사용권 또는 쿠폰 키를 입력받아 활성화합니다.
    - 사용권: 라이선스 활성화 (발급 시점부터 기간 적용)
    - 쿠폰: 멈춤 모드 시작 (날짜 선택 가능)
    """
    ip_address = req.client.host if req else None
    return LicenseService.redeem_license(db, request, ip_address)


@router.get("/status/{device_id}", response_model=LicenseStatusResponse)
def get_license_status(
    device_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    라이선스 상태 조회
    
    디바이스 ID로 현재 라이선스/쿠폰 상태를 조회합니다.
    """
    return LicenseService.get_license_status(db, device_id)


@router.post("/validate", response_model=LicenseValidateResponse)
def validate_license_key(
    request: LicenseValidateRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    라이선스 키 검증

    라이선스 키의 유효성을 DB에서 확인합니다.
    (존재 여부 및 사용 여부 포함)
    """
    return LicenseService.validate_license_key(request.license_key, db)
