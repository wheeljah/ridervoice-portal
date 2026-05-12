"""
RiderVoiceAI Backend API Routers - Delivery Accounts Endpoints
배달 계정 연동 관리 (배민, 쿠팡이츠 등 복수 계정/복수 기기 지원)
"""
import json
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/delivery-accounts", tags=["delivery-accounts"])

VALID_PLATFORMS = {"baemin", "coupang", "yogiyo", "wemakeprice"}
VALID_STATUSES  = {"connected", "disconnected", "error"}


# ── 스키마 ──
class DeliveryAccountIn(BaseModel):
    platform:  str
    username:  str
    password:  Optional[str] = None
    device_id: Optional[str] = None  # 연동한 기기 ID


class DeliveryAccountStatusPatch(BaseModel):
    status: str  # "connected" | "disconnected" | "error"


class DeliveryAccountOut(BaseModel):
    id:         int
    platform:   str
    username:   str
    status:     str
    linked_at:  int           # ms timestamp
    device_id:  Optional[str] = None


# ── 엔드포인트 ──

@router.get("", response_model=List[DeliveryAccountOut])
def list_delivery_accounts(
    current_user: User = Depends(get_current_user),
):
    """내 배달 계정 목록 조회"""
    accounts = _load_accounts(current_user)
    return [_to_out(i, a) for i, a in enumerate(accounts)]


@router.post("", response_model=DeliveryAccountOut, status_code=201)
def add_delivery_account(
    body: DeliveryAccountIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배달 계정 추가 (플랫폼당 복수 계정 허용)"""
    if body.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 플랫폼입니다: {body.platform}")

    accounts = _load_accounts(current_user)
    new_id = len(accounts)
    new_account = {
        "platform":  body.platform,
        "username":  body.username,
        "account_id": body.username,
        "password":  body.password,
        "status":    "connected",
        "linked_at": int(time.time() * 1000),
        "device_id": body.device_id,
    }
    accounts.append(new_account)
    _save_accounts(db, current_user, accounts)
    return _to_out(new_id, new_account)


@router.patch("/{account_id}/status", response_model=DeliveryAccountOut)
def update_account_status(
    account_id: int,
    body: DeliveryAccountStatusPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """배달 계정 연동 상태 업데이트"""
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태: {body.status}")
    accounts = _load_accounts(current_user)
    if account_id < 0 or account_id >= len(accounts):
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다.")
    accounts[account_id]["status"] = body.status
    _save_accounts(db, current_user, accounts)
    return _to_out(account_id, accounts[account_id])


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

def _to_out(idx: int, a: dict) -> DeliveryAccountOut:
    return DeliveryAccountOut(
        id=idx,
        platform=a.get("platform", ""),
        username=a.get("username") or a.get("account_id", ""),
        status=a.get("status", "connected"),
        linked_at=a.get("linked_at", 0),
        device_id=a.get("device_id"),
    )


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
