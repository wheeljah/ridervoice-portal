"""
RiderVoiceAI Backend API Routers - Auth Endpoints
회원가입 / 로그인 / 토큰 갱신 / 내 정보 조회
"""
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24   # 24시간
REFRESH_TOKEN_EXPIRE_DAYS = 30          # 30일

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ──────────────────────────────────────────────
# Pydantic 스키마
# ──────────────────────────────────────────────
class DeliveryAccount(BaseModel):
    platform: str
    account_id: Optional[str] = None
    password: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str = Field(..., description="아이디 (로그인 ID)")
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6자)")
    name: Optional[str] = Field(None, description="이름")
    phone: Optional[str] = Field(None, description="전화번호")
    birth_date: Optional[str] = Field(None, description="생년월일")
    device_id: Optional[str] = Field(None, description="디바이스 ID")
    delivery_accounts: Optional[List[DeliveryAccount]] = Field(None, description="배달 계정 목록")


class LoginRequest(BaseModel):
    username: str = Field(..., description="아이디")
    password: str = Field(..., description="비밀번호")
    device_id: Optional[str] = Field(None, description="디바이스 ID (선택)")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="갱신 토큰")


class MeResponse(BaseModel):
    user_id: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    device_id: Optional[str] = None
    current_license_type: Optional[str] = None
    current_license_expires_at: Optional[int] = None
    is_paused: bool = False
    created_at: int


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str) -> str:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise credentials_exc
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
        return user_id
    except JWTError:
        raise credentials_exc


# ──────────────────────────────────────────────
# 현재 유저 가져오기 (의존성)
# ──────────────────────────────────────────────
def get_current_user(
    authorization: str = Header(..., description="Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더 형식 오류. 'Bearer <token>'")
    token = authorization[7:]
    user_id = decode_token(token, "access")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    회원가입
    - username 중복 확인 후 계정 생성
    - access_token + refresh_token 반환
    """
    existing = db.query(User).filter(User.user_id == request.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")

    delivery_json = None
    if request.delivery_accounts:
        delivery_json = json.dumps(
            [a.model_dump() for a in request.delivery_accounts],
            ensure_ascii=False
        )

    user = User(
        user_id=request.username,
        password_hash=hash_password(request.password),
        name=request.name,
        phone=request.phone,
        birth_date=request.birth_date,
        device_id=request.device_id,
        delivery_accounts=delivery_json,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_access_token(user.user_id),
        "refresh_token": create_refresh_token(user.user_id),
        "token_type": "bearer",
        "user": {
            "username": user.user_id,
            "name": user.name,
        }
    }


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    로그인
    - username + 비밀번호 검증
    - access_token + refresh_token 반환
    """
    user = db.query(User).filter(User.user_id == request.username).first()
    if not user or not verify_password(request.password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    if request.device_id and user.device_id != request.device_id:
        user.device_id = request.device_id
        user.updated_at = int(time.time() * 1000)
        db.commit()

    return {
        "access_token": create_access_token(user.user_id),
        "refresh_token": create_refresh_token(user.user_id),
        "token_type": "bearer",
        "user": {
            "username": user.user_id,
            "name": user.name,
        }
    }


@router.post("/refresh")
def refresh_tokens(request: RefreshRequest, db: Session = Depends(get_db)):
    """토큰 갱신"""
    user_id = decode_token(request.refresh_token, "refresh")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    return {
        "access_token": create_access_token(user.user_id),
        "refresh_token": create_refresh_token(user.user_id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회 (Authorization: Bearer <token>)"""
    return MeResponse(
        user_id=current_user.user_id,
        username=current_user.user_id,
        name=current_user.name,
        phone=current_user.phone,
        birth_date=current_user.birth_date,
        device_id=current_user.device_id,
        current_license_type=current_user.current_license_type,
        current_license_expires_at=current_user.current_license_expires_at,
        is_paused=current_user.is_paused or False,
        created_at=current_user.created_at,
    )


@router.post("/logout", status_code=204)
def logout():
    """로그아웃 (stateless JWT — 클라이언트에서 토큰 삭제)"""
    return
