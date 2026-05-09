"""
RiderVoiceAI Backend API Routers - Admin Endpoints
"""
import hashlib
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import License, Coupon
from app.config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
settings = get_settings()


class GenerateKeysRequest(BaseModel):
    """키 생성 요청"""
    license_type: str = Field(..., description="라이선스 유형 (LM1, LM3, LM6, LMY, PAU4, PAU1, PAU3, PAU5)")
    quantity: int = Field(..., ge=1, le=100, description="생성할 키 수량 (1-100)")


class AdminStatsResponse(BaseModel):
    """관리자 통계 응답"""
    total_licenses: int
    active_licenses: int
    total_coupons: int
    redeemed_coupons: int


class LicenseListResponse(BaseModel):
    """라이선스 목록 응답"""
    licenses: List[dict]
    total: int


class CouponListResponse(BaseModel):
    """쿠폰 목록 응답"""
    coupons: List[dict]
    total: int


def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Admin 키 검증"""
    if x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
    return x_admin_key


def generate_signature(type_code: str, timestamp: int) -> str:
    """시그니처 생성"""
    data = f"{type_code}:{timestamp}:{settings.SECRET_KEY}"
    digest = hashlib.sha256(data.encode()).digest()
    return digest[:8].hex().upper()


@router.post("/keys/generate")
def generate_license_keys(
    request: GenerateKeysRequest,
    admin_key: str = Depends(verify_admin_key),
    db: Session = Depends(get_db)
):
    """
    라이선스 키 일괄 생성

    관리자만 사용할 수 있는 API입니다.
    지정된 수만큼 라이선스 키를 생성합니다.
    """
    license_type = request.license_type
    quantity = request.quantity

    # 라이선스 유형 검증
    valid_types = ["LD1", "LD3", "LD7", "LD10", "LM1", "LM3", "LM6", "LMY", "PAU4", "PAU1", "PAU3", "PAU5"]
    if license_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid license type. Valid types: {valid_types}"
        )

    if quantity < 1 or quantity > 100:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be between 1 and 100"
        )

    # 키 생성
    keys = []

    for i in range(quantity):
        timestamp = int(time.time()) + i
        signature = generate_signature(license_type, timestamp)
        license_key = f"{license_type}-{timestamp}-{signature}"
        keys.append(license_key)

        # DB에 저장
        if license_type.startswith("PAU"):
            # 쿠폰
            coupon = Coupon(
                coupon_code=license_key,
                coupon_type=license_type,
                issued_at=timestamp * 1000,
                expires_at=(timestamp + 365 * 24 * 60 * 60) * 1000,
                is_redeemed=False
            )
            db.add(coupon)
        else:
            # 사용권
            license = License(
                license_key=license_key,
                license_type=license_type,
                issued_at=timestamp,
                is_active=False
            )
            db.add(license)

    db.commit()

    return {
        "success": True,
        "license_type": license_type,
        "quantity": quantity,
        "keys": keys
    }


@router.get("/stats")
def get_admin_stats(
    admin_key: str = Depends(verify_admin_key),
    db: Session = Depends(get_db)
):
    """
    관리자 대시보드 통계 조회
    """
    total_licenses = db.query(License).count()
    active_licenses = db.query(License).filter(License.is_active == True).count()
    total_coupons = db.query(Coupon).count()
    redeemed_coupons = db.query(Coupon).filter(Coupon.is_redeemed == True).count()

    return {
        "total_licenses": total_licenses,
        "active_licenses": active_licenses,
        "total_coupons": total_coupons,
        "redeemed_coupons": redeemed_coupons
    }


@router.get("/licenses")
def list_licenses(
    admin_key: str = Depends(verify_admin_key),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """
    라이선스 목록 조회 (관리자)
    """
    query = db.query(License)

    if search:
        query = query.filter(License.license_key.ilike(f"%{search}%"))

    if is_active is not None:
        query = query.filter(License.is_active == is_active)

    total = query.count()
    licenses = query.order_by(License.issued_at.desc()).offset(offset).limit(limit).all()

    return {
        "licenses": [
            {
                "license_key": lic.license_key,
                "license_type": lic.license_type,
                "is_active": lic.is_active,
                "issued_at": lic.issued_at,
                "activated_at": lic.activated_at,
                "expires_at": lic.expires_at,
                "device_id": lic.device_id
            }
            for lic in licenses
        ],
        "total": total
    }


@router.get("/coupons")
def list_coupons(
    admin_key: str = Depends(verify_admin_key),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    is_redeemed: Optional[bool] = Query(None)
):
    """
    쿠폰 목록 조회 (관리자)
    """
    query = db.query(Coupon)

    if search:
        query = query.filter(Coupon.coupon_code.ilike(f"%{search}%"))

    if is_redeemed is not None:
        query = query.filter(Coupon.is_redeemed == is_redeemed)

    total = query.count()
    coupons = query.order_by(Coupon.issued_at.desc()).offset(offset).limit(limit).all()

    return {
        "coupons": [
            {
                "coupon_code": cpn.coupon_code,
                "coupon_type": cpn.coupon_type,
                "is_redeemed": cpn.is_redeemed,
                "issued_at": cpn.issued_at,
                "redeemed_at": cpn.redeemed_at,
                "redeemed_device_id": cpn.redeemed_device_id,
                "expires_at": cpn.expires_at
            }
            for cpn in coupons
        ],
        "total": total
    }


@router.delete("/coupons/{coupon_code}")
def delete_coupon(
    coupon_code: str,
    admin_key: str = Depends(verify_admin_key),
    db: Session = Depends(get_db)
):
    """
    쿠폰 삭제 (관리자)
    """
    coupon = db.query(Coupon).filter(Coupon.coupon_code == coupon_code).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    db.delete(coupon)
    db.commit()

    return {"success": True, "message": "Coupon deleted"}