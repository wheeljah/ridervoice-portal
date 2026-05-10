"""
RiderVoiceAI Backend API Routers - Delivery Accounts Endpoints
배달 계정 연동 관리 (배민, 쿠팡이츠)
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/v1/delivery-accounts", tags=["delivery-accounts"])
settings = get_settings()


# ── 스키마 ──
class DeliveryAccountIn(BaseModel):
    platform: str          # "baemin" | "coupang"
    username: str
    password: Optional[str] = None


class DeliveryAccountOut(BaseModel):
    id: int
    platform: str
    username: str


# ── 엔드포인트 ──

@router.get("", response_model=List[DeliveryAccountOut])
def list_delivery_accounts(
    current_user: User = Depends(get_current_user),
):
    """내 배달 계정 목록 조회"""
    accounts = _load_accounts(current_user)
    return [
        DeliveryAccountOut(id=i, platform=a.get("platform",""), username=a.get("username", a.get("account_id","")))
        for i, a in enumerate(accounts)
    ]


@router.post("", response_model=DeliveryAccountOut, status_code=201)
def add_delivery_account(
    body: DeliveryAccountIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배달 계정 추가"""
    accounts = _load_accounts(current_user)
    new_id = len(accounts)
    accounts.append({
        "platform": body.platform,
        "username": body.username,
        "account_id": body.username,
        "password": body.password,
    })
    _save_accounts(db, current_user, accounts)
    return DeliveryAccountOut(id=new_id, platform=body.platform, username=body.username)


@router.delete("/{account_id}", status_code=204)
def delete_delivery_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배달 계정 삭제"""
    accounts = _load_accounts(current_user)
    if account_id < 0 or account_id >= len(accounts):
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")
    accounts.pop(account_id)
    _save_accounts(db, current_user, accounts)


# ── 헬퍼 ──

def _load_accounts(user: User) -> list:
    if not user.delivery_accounts:
        return []
    try:
        data = json.loads(user.delivery_accounts)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_accounts(db: Session, user: User, accounts: list):
    user.delivery_accounts = json.dumps(accounts, ensure_ascii=False)
    db.commit()
