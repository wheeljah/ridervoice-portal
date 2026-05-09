"""
RiderVoiceAI Backend API Routers - Coupon Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    CouponRedeemRequest, CouponRedeemResponse,
    AvailableCouponsResponse, AvailableCoupon,
    LicenseRedeemRequest
)
from app.services.license_service import LicenseService
from app.config import get_settings

router = APIRouter(prefix="/api/v1/coupons", tags=["coupons"])
settings = get_settings()


def verify_api_key(x_api_key: str = Header(..., alias=settings.API_KEY_HEADER)):
    """API 키 검증"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


@router.post("/redeem", response_model=CouponRedeemResponse)
def redeem_coupon(
    request: CouponRedeemRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    쿠폰 사용 (날짜 선택)

    멈춤 쿠폰을 사용하여 앱을 일시정지합니다.
    pause_start_time을 지정하여 언제 멈춤을 시작할지 선택할 수 있습니다.
    """
    redeem_request = LicenseRedeemRequest(
        license_key=request.coupon_code,
        device_id=request.device_id,
        pause_start_time=request.pause_start_time
    )
    result = LicenseService.redeem_license(db, redeem_request)

    if result.success:
        type_info = LicenseService.get_type_info(result.license_type)
        return CouponRedeemResponse(
            success=True,
            message=result.message,
            coupon_type=result.license_type,
            duration_hours=type_info["duration_hours"] if type_info else None,
            pause_start_time=result.pause_start_time,
            pause_end_time=result.pause_end_time
        )
    else:
        return CouponRedeemResponse(
            success=False,
            message=result.message
        )


@router.get("/available", response_model=AvailableCouponsResponse)
def get_available_coupons(
    api_key: str = Depends(verify_api_key)
):
    """
    사용 가능한 쿠폰 목록

    현재 사용 가능한 멈춤 쿠폰 유형을 반환합니다.
    """
    coupons = [
        AvailableCoupon(
            coupon_type="PAU4",
            display_name="4시간 멈춤",
            duration_hours=4
        ),
        AvailableCoupon(
            coupon_type="PAU1",
            display_name="1일 멈춤",
            duration_hours=24
        ),
        AvailableCoupon(
            coupon_type="PAU3",
            display_name="3일 멈춤",
            duration_hours=72
        ),
        AvailableCoupon(
            coupon_type="PAU5",
            display_name="5일 멈춤",
            duration_hours=120
        )
    ]
    return AvailableCouponsResponse(coupons=coupons)