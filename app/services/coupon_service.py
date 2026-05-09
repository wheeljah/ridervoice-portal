"""
RiderVoiceAI Backend Coupon Service
쿠폰 관련 비즈니스 로직
"""
import time
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Coupon, User, RedemptionLog
from app.config import get_settings

settings = get_settings()


class CouponService:
    """쿠폰 서비스"""

    # 쿠폰 유형 정의
    COUPON_TYPES = {
        "PAU4": {"name": "4시간 멈춤", "duration_hours": 4},
        "PAU1": {"name": "1일 멈춤", "duration_hours": 24},
        "PAU3": {"name": "3일 멈춤", "duration_hours": 72},
        "PAU5": {"name": "5일 멈춤", "duration_hours": 120},
    }

    @classmethod
    def get_type_info(cls, type_code: str) -> Optional[dict]:
        """쿠폰 유형 정보 반환"""
        return cls.COUPON_TYPES.get(type_code)

    @classmethod
    def is_valid_coupon_type(cls, type_code: str) -> bool:
        """유효한 쿠폰 유형인지 확인"""
        return type_code in cls.COUPON_TYPES

    @classmethod
    def get_available_coupons(cls) -> List[dict]:
        """사용 가능한 쿠폰 목록 반환"""
        return [
            {
                "coupon_type": coupon_type,
                "display_name": info["name"],
                "duration_hours": info["duration_hours"]
            }
            for coupon_type, info in cls.COUPON_TYPES.items()
        ]

    @classmethod
    def calculate_pause_times(
        cls,
        coupon_type: str,
        pause_start_time: Optional[int] = None
    ) -> tuple:
        """
        일시정지 시간 계산

        Args:
            coupon_type: 쿠폰 유형
            pause_start_time: 시작 시간 (밀리초), None이면 현재 시간

        Returns:
            (pause_start_time, pause_end_time) 튜플
        """
        type_info = cls.get_type_info(coupon_type)
        if not type_info:
            raise ValueError(f"Invalid coupon type: {coupon_type}")

        if pause_start_time is None:
            pause_start_time = int(time.time() * 1000)

        duration_ms = type_info["duration_hours"] * 60 * 60 * 1000
        pause_end_time = pause_start_time + duration_ms

        return pause_start_time, pause_end_time

    @classmethod
    def redeem_coupon(
        cls,
        db: Session,
        coupon_code: str,
        device_id: str,
        pause_start_time: Optional[int] = None,
        ip_address: str = None
    ) -> dict:
        """
        쿠폰 사용

        Args:
            db: 데이터베이스 세션
            coupon_code: 쿠폰 코드
            device_id: 디바이스 ID
            pause_start_time: 멈춤 시작 시간
            ip_address: IP 주소

        Returns:
            결과 딕셔너리
        """
        from app.services.license_service import LicenseService

        # 쿠폰 검증
        validation = LicenseService.validate_license_key(coupon_code)
        if not validation.valid:
            cls._log_redemption(
                db, coupon_code, "", device_id,
                False, validation.error_message, ip_address
            )
            return {
                "success": False,
                "message": validation.error_message or "쿠폰 검증에 실패했습니다"
            }

        # 쿠폰 유형 확인
        if not validation.is_coupon:
            cls._log_redemption(
                db, coupon_code, validation.license_type, device_id,
                False, "사용권은 쿠폰으로 사용할 수 없습니다", ip_address
            )
            return {
                "success": False,
                "message": "사용권은 쿠폰으로 사용할 수 없습니다"
            }

        # 이미 사용된 쿠폰인지 확인
        coupon = db.query(Coupon).filter(Coupon.coupon_code == coupon_code).first()
        if coupon and coupon.is_redeemed:
            cls._log_redemption(
                db, coupon_code, validation.license_type, device_id,
                False, "이미 사용된 쿠폰입니다", ip_address
            )
            return {
                "success": False,
                "message": "이미 사용된 쿠폰입니다"
            }

        type_info = cls.get_type_info(validation.license_type)

        # 일시정지 시간 계산
        pause_start, pause_end = cls.calculate_pause_times(
            validation.license_type, pause_start_time
        )

        # 쿠폰 저장 또는 업데이트
        if coupon:
            coupon.is_redeemed = True
            coupon.redeemed_at = int(time.time() * 1000)
            coupon.redeemed_by_device = device_id
            coupon.pause_start_time = pause_start
            coupon.pause_end_time = pause_end
        else:
            coupon = Coupon(
                coupon_code=coupon_code,
                coupon_type=validation.license_type,
                issued_at=int(time.time() * 1000) - (365 * 24 * 60 * 60 * 1000),
                expires_at=int(time.time() * 1000),
                is_redeemed=True,
                redeemed_at=int(time.time() * 1000),
                redeemed_by_device=device_id,
                pause_start_time=pause_start,
                pause_end_time=pause_end
            )
            db.add(coupon)

        # 사용자 멈춤 상태 업데이트
        cls._update_user_pause(db, device_id, pause_start, pause_end, validation.license_type)

        db.commit()
        cls._log_redemption(
            db, coupon_code, validation.license_type, device_id,
            True, None, ip_address
        )

        return {
            "success": True,
            "message": f"{type_info['name']} 쿠폰이 적용되었습니다",
            "coupon_type": validation.license_type,
            "duration_hours": type_info["duration_hours"],
            "pause_start_time": pause_start,
            "pause_end_time": pause_end
        }

    @staticmethod
    def _update_user_pause(
        db: Session,
        device_id: str,
        pause_start: int,
        pause_end: int,
        coupon_type: str
    ):
        """사용자 멈춤 상태 업데이트"""
        user = db.query(User).filter(User.device_id == device_id).first()

        if user:
            user.is_paused = True
            user.pause_start_time = pause_start
            user.pause_end_time = pause_end
            user.current_license_type = coupon_type
        else:
            user = User(
                device_id=device_id,
                is_paused=True,
                pause_start_time=pause_start,
                pause_end_time=pause_end,
                current_license_type=coupon_type
            )
            db.add(user)

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