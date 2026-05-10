"""
RiderVoiceAI Backend License Service
"""
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.models import License, Coupon, User, RedemptionLog
from app.schemas import (
    LicenseRedeemRequest, LicenseRedeemResponse,
    LicenseStatusResponse, LicenseValidateRequest, LicenseValidateResponse,
    CouponRedeemRequest, CouponRedeemResponse
)


class LicenseService:
    """라이선스 서비스"""
    
    # 라이선스 유형 정의
    LICENSE_TYPES = {
        # 일간 사용권
        "LD1": {"name": "1일", "duration_hours": 1 * 24, "is_coupon": False},
        "LD3": {"name": "3일", "duration_hours": 3 * 24, "is_coupon": False},
        "LD5": {"name": "5일", "duration_hours": 5 * 24, "is_coupon": False},
        "LD7": {"name": "7일", "duration_hours": 7 * 24, "is_coupon": False},
        "LD10": {"name": "10일", "duration_hours": 10 * 24, "is_coupon": False},
        # 월간 사용권
        "LM1": {"name": "1개월", "duration_hours": 30 * 24, "is_coupon": False},
        "LM3": {"name": "3개월", "duration_hours": 90 * 24, "is_coupon": False},
        "LM6": {"name": "6개월", "duration_hours": 180 * 24, "is_coupon": False},
        "LMY": {"name": "1년", "duration_hours": 365 * 24, "is_coupon": False},
        # 쿠폰
        "PAU4": {"name": "4시간 멈춤", "duration_hours": 4, "is_coupon": True},
        "PAU1": {"name": "1일 멈춤", "duration_hours": 24, "is_coupon": True},
        "PAU3": {"name": "3일 멈춤", "duration_hours": 72, "is_coupon": True},
        "PAU5": {"name": "5일 멈춤", "duration_hours": 120, "is_coupon": True},
    }
    
    @classmethod
    def get_type_info(cls, type_code: str) -> Optional[dict]:
        """라이선스 유형 정보 반환"""
        return cls.LICENSE_TYPES.get(type_code)
    
    @classmethod
    def is_valid_license_type(cls, type_code: str) -> bool:
        """유효한 라이선스 유형인지 확인"""
        return type_code in cls.LICENSE_TYPES
    
    @classmethod
    def is_coupon(cls, type_code: str) -> bool:
        """쿠폰인지 확인"""
        info = cls.get_type_info(type_code)
        return info.get("is_coupon", False) if info else False
    
    @classmethod
    def validate_license_key(cls, license_key: str, db: Session) -> LicenseValidateResponse:
        """라이선스 키 검증 (DB 조회 기반)"""
        # 포맷 체크: {type_code}-{random_token}
        parts = license_key.split("-")
        if len(parts) < 2:
            return LicenseValidateResponse(
                valid=False,
                error_message="잘못된 라이선스 형식입니다"
            )

        type_code = parts[0]
        type_info = cls.get_type_info(type_code)
        if not type_info:
            return LicenseValidateResponse(
                valid=False,
                error_message="알 수 없는 라이선스 유형입니다"
            )

        is_coupon = type_info["is_coupon"]
        now_ms = int(time.time() * 1000)

        if is_coupon:
            record = db.query(Coupon).filter(Coupon.coupon_code == license_key).first()
            if not record:
                return LicenseValidateResponse(
                    valid=False,
                    error_message="존재하지 않는 라이선스 키입니다"
                )
            if record.is_redeemed:
                return LicenseValidateResponse(
                    valid=False, license_type=type_code, is_coupon=True,
                    error_message="이미 사용된 쿠폰입니다"
                )
            if record.expires_at and now_ms > record.expires_at:
                return LicenseValidateResponse(
                    valid=False, license_type=type_code, is_coupon=True,
                    error_message="쿠폰이 만료되었습니다"
                )
        else:
            record = db.query(License).filter(License.license_key == license_key).first()
            if not record:
                return LicenseValidateResponse(
                    valid=False,
                    error_message="존재하지 않는 라이선스 키입니다"
                )
            if record.is_active:
                return LicenseValidateResponse(
                    valid=False, license_type=type_code,
                    error_message="이미 사용된 라이선스입니다"
                )

        return LicenseValidateResponse(
            valid=True,
            license_type=type_code,
            is_coupon=is_coupon,
            duration_hours=type_info["duration_hours"]
        )
    
    @classmethod
    def redeem_license(
        cls,
        db: Session,
        request: LicenseRedeemRequest,
        ip_address: str = None
    ) -> LicenseRedeemResponse:
        """라이선스 Redemption"""
        license_key = request.license_key
        device_id = request.device_id
        
        # 키 검증 (DB 조회)
        validation = cls.validate_license_key(license_key, db)
        if not validation.valid:
            cls._log_redemption(db, license_key, "", device_id, False, validation.error_message, ip_address)
            return LicenseRedeemResponse(
                success=False,
                message=validation.error_message or "라이선스 검증에 실패했습니다"
            )
        
        type_code = validation.license_type
        type_info = cls.get_type_info(type_code)
        
        if type_info["is_coupon"]:
            # 쿠폰 처리
            pause_start_time = request.pause_start_time or int(time.time() * 1000)
            pause_end_time = pause_start_time + (type_info["duration_hours"] * 60 * 60 * 1000)
            
            # 쿠폰 생성 또는 업데이트
            coupon = db.query(Coupon).filter(Coupon.coupon_code == license_key).first()
            if coupon:
                if coupon.is_redeemed:
                    cls._log_redemption(db, license_key, type_code, device_id, False, "이미 사용된 쿠폰입니다", ip_address)
                    return LicenseRedeemResponse(success=False, message="이미 사용된 쿠폰입니다")
                coupon.is_redeemed = True
                coupon.redeemed_at = int(time.time() * 1000)
                coupon.redeemed_by_device = device_id
                coupon.pause_start_time = pause_start_time
                coupon.pause_end_time = pause_end_time
            else:
                coupon = Coupon(
                    coupon_code=license_key,
                    coupon_type=type_code,
                    issued_at=int(time.time() * 1000) - (365 * 24 * 60 * 60 * 1000),  # Approximate
                    expires_at=int(time.time() * 1000),
                    is_redeemed=True,
                    redeemed_at=int(time.time() * 1000),
                    redeemed_by_device=device_id,
                    pause_start_time=pause_start_time,
                    pause_end_time=pause_end_time
                )
                db.add(coupon)
            
            # 사용자 멈춤 상태 업데이트
            cls._update_user_pause(db, device_id, pause_start_time, pause_end_time, type_code)
            
            db.commit()
            cls._log_redemption(db, license_key, type_code, device_id, True, None, ip_address)
            
            return LicenseRedeemResponse(
                success=True,
                message=f"{type_info['name']} 쿠폰이 적용되었습니다",
                license_type=type_code,
                pause_start_time=pause_start_time,
                pause_end_time=pause_end_time
            )
        else:
            # 사용권 처리
            current_timestamp = int(time.time() * 1000)
            duration_ms = type_info["duration_hours"] * 60 * 60 * 1000
            expires_at = current_timestamp + duration_ms

            license = db.query(License).filter(License.license_key == license_key).first()
            if license:
                # 기존 레코드 업데이트 (이전 오류로 is_active=False 상태인 경우)
                license.device_id = device_id
                license.issued_at = current_timestamp
                license.redeemed_at = current_timestamp
                license.redeemed_by_device = device_id
                license.expires_at = expires_at
                license.is_active = True
            else:
                license = License(
                    license_key=license_key,
                    license_type=type_code,
                    device_id=device_id,
                    issued_at=current_timestamp,
                    expires_at=expires_at,
                    is_active=True,
                    redeemed_at=current_timestamp,
                    redeemed_by_device=device_id
                )
                db.add(license)
            
            # 사용자 라이선스 상태 업데이트
            cls._update_user_license(db, device_id, type_code, expires_at)
            
            db.commit()
            cls._log_redemption(db, license_key, type_code, device_id, True, None, ip_address)
            
            return LicenseRedeemResponse(
                success=True,
                message=f"{type_info['name']} 라이선스가 활성화되었습니다",
                license_type=type_code,
                expires_at=expires_at
            )
    
    @classmethod
    def get_license_status(cls, db: Session, device_id: str) -> LicenseStatusResponse:
        """디바이스의 라이선스 상태 조회"""
        user = db.query(User).filter(User.device_id == device_id).first()
        
        if not user:
            return LicenseStatusResponse(
                device_id=device_id,
                has_active_license=False,
                is_paused=False
            )
        
        current_time = int(time.time() * 1000)
        
        return LicenseStatusResponse(
            device_id=device_id,
            has_active_license=user.current_license_expires_at > current_time if user.current_license_expires_at else False,
            license_type=user.current_license_type,
            license_expires_at=user.current_license_expires_at,
            is_paused=user.is_paused,
            pause_start_time=user.pause_start_time,
            pause_end_time=user.pause_end_time,
            remaining_days=cls._calculate_remaining_days(user.current_license_expires_at) if user.current_license_expires_at else None,
            remaining_time_string=cls._get_remaining_time_string(user)
        )
    
    @staticmethod
    def _update_user_license(db: Session, device_id: str, license_type: str, expires_at: int):
        """사용자 라이선스 상태 업데이트"""
        user = db.query(User).filter(User.device_id == device_id).first()

        if user:
            user.current_license_type = license_type
            user.current_license_expires_at = expires_at
            user.is_paused = False
            user.pause_start_time = None
            user.pause_end_time = None
        else:
            user = User(
                user_id=device_id,        # user_id는 NOT NULL/UNIQUE — device_id로 대체
                device_id=device_id,
                current_license_type=license_type,
                current_license_expires_at=expires_at,
                is_paused=False,
            )
            db.add(user)
    
    @staticmethod
    def _update_user_pause(db: Session, device_id: str, pause_start: int, pause_end: int, coupon_type: str):
        """사용자 멈춤 상태 업데이트"""
        user = db.query(User).filter(User.device_id == device_id).first()

        if user:
            user.is_paused = True
            user.pause_start_time = pause_start
            user.pause_end_time = pause_end
            user.current_license_type = coupon_type
        else:
            user = User(
                user_id=device_id,        # user_id는 NOT NULL/UNIQUE — device_id로 대체
                device_id=device_id,
                is_paused=True,
                pause_start_time=pause_start,
                pause_end_time=pause_end,
                current_license_type=coupon_type,
            )
            db.add(user)
    
    @staticmethod
    def _calculate_remaining_days(expires_at: int) -> int:
        """만료일까지 남은 일수 계산"""
        remaining_ms = expires_at - int(time.time() * 1000)
        if remaining_ms <= 0:
            return 0
        return remaining_ms // (24 * 60 * 60 * 1000)
    
    @staticmethod
    def _get_remaining_time_string(user: User) -> str:
        """남은 시간 문자열 반환"""
        if user.is_paused and user.pause_end_time:
            remaining = user.pause_end_time - int(time.time() * 1000)
            if remaining <= 0:
                return "멈춤 종료"
            hours = remaining // (60 * 60 * 1000)
            minutes = (remaining % (60 * 60 * 1000)) // (60 * 1000)
            return f"멈춤 중: {hours}시간 {minutes}분 남음"
        
        if user.current_license_expires_at:
            remaining = user.current_license_expires_at - int(time.time() * 1000)
            if remaining <= 0:
                return "만료됨"
            days = remaining // (24 * 60 * 60 * 1000)
            hours = (remaining % (24 * 60 * 60 * 1000)) // (60 * 60 * 1000)
            if days > 0:
                return f"{days}일 {hours}시간"
            return f"{hours}시간"
        
        return "만료됨"
    
    @staticmethod
    def _log_redemption(
        db: Session,
        license_key: str,
        license_type: str,
        device_id: str,
        success: bool,
        error_message: str,
        ip_address: str
    ):
        """Redemption 로그 기록"""
        log = RedemptionLog(
            license_key=license_key,
            license_type=license_type,
            device_id=device_id,
            success=success,
            error_message=error_message,
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
