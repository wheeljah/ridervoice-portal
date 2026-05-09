"""
RiderVoiceAI Backend API Routers - Price Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PriceResponse, PriceItem, PriceUpdateRequest
from app.models import Price
from app.config import get_settings
from datetime import datetime

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])
settings = get_settings()


def verify_api_key(x_api_key: str = Header(..., alias=settings.API_KEY_HEADER)):
    """API 키 검증"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# 기본 가격표
DEFAULT_PRICES = {
    # 일간 사용권
    "LD1": {"name": "1일", "duration_days": 1, "price": 1500},
    "LD3": {"name": "3일", "duration_days": 3, "price": 3500},
    "LD7": {"name": "7일", "duration_days": 7, "price": 6500},
    "LD10": {"name": "10일", "duration_days": 10, "price": 8500},
    # 월간 사용권
    "LM1": {"name": "1개월", "duration_days": 30, "price": 4900},
    "LM3": {"name": "3개월", "duration_days": 90, "price": 12900},
    "LM6": {"name": "6개월", "duration_days": 180, "price": 22900},
    "LMY": {"name": "1년", "duration_days": 365, "price": 39900},
}


@router.get("", response_model=PriceResponse)
def get_prices(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    현재 가격 조회
    
    모든 사용권의 현재 가격을 반환합니다.
    가격은 DB에서 가져오며, 없으면 기본값을 반환합니다.
    """
    prices = []
    
    for license_type, info in DEFAULT_PRICES.items():
        db_price = db.query(Price).filter(Price.license_type == license_type).first()
        price = db_price.price if db_price else info["price"]
        
        prices.append(PriceItem(
            license_type=license_type,
            display_name=info["name"],
            duration_days=info["duration_days"],
            price=price
        ))
    
    # 마지막 업데이트 시간
    last_updated = db.query(Price).order_by(Price.updated_at.desc()).first()
    
    return PriceResponse(
        prices=prices,
        updated_at=last_updated.updated_at if last_updated else None
    )


@router.put("", response_model=PriceResponse)
def update_price(
    request: PriceUpdateRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    가격 변경
    
    특정 사용권의 가격을 변경합니다.
    이 API는 관리자만 호출해야 합니다.
    """
    if request.license_type not in DEFAULT_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid license type. Valid types: {list(DEFAULT_PRICES.keys())}"
        )
    
    if request.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    
    # DB에서 찾거나 생성
    db_price = db.query(Price).filter(Price.license_type == request.license_type).first()
    
    if db_price:
        db_price.price = request.price
    else:
        db_price = Price(
            license_type=request.license_type,
            price=request.price,
            is_active=True
        )
        db.add(db_price)
    
    db.commit()
    db.refresh(db_price)
    
    # 전체 가격 반환
    return get_prices(db, api_key)
