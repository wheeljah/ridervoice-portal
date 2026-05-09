"""
RiderVoiceAI Backend Cryptography Utilities
서명 생성 및 검증 유틸리티
"""
import hashlib
import hmac
import secrets
import string
from typing import Tuple


class CryptoUtils:
    """암호화 유틸리티 클래스"""

    @staticmethod
    def generate_signature(type_code: str, timestamp: int, secret_key: str) -> str:
        """
        라이선스 키 서명 생성

        Args:
            type_code: 라이선스 유형 코드 (LM1, LM3, etc.)
            timestamp: 타임스탬프 (초)
            secret_key: 시크릿 키

        Returns:
            8자리 HEX 서명
        """
        data = f"{type_code}:{timestamp}:{secret_key}"
        digest = hashlib.sha256(data.encode()).digest()
        return digest[:8].hex().upper()

    @staticmethod
    def verify_signature(license_key: str, secret_key: str) -> bool:
        """
        라이선스 키 서명 검증

        Args:
            license_key: 라이선스 키 (형식: TYPE-TIMESTAMP-SIGNATURE)
            secret_key: 시크릿 키

        Returns:
            검증 성공 여부
        """
        try:
            parts = license_key.split("-")
            if len(parts) != 3:
                return False

            type_code, timestamp_str, provided_sig = parts
            timestamp = int(timestamp_str)

            expected_sig = CryptoUtils.generate_signature(type_code, timestamp, secret_key)
            return hmac.compare_digest(expected_sig, provided_sig)
        except Exception:
            return False

    @staticmethod
    def parse_license_key(license_key: str) -> Tuple[str, int, str]:
        """
        라이선스 키 파싱

        Args:
            license_key: 라이선스 키

        Returns:
            (type_code, timestamp, signature) 튜플
        """
        parts = license_key.split("-")
        if len(parts) != 3:
            raise ValueError("Invalid license key format")

        type_code, timestamp_str, signature = parts
        return type_code, int(timestamp_str), signature

    @staticmethod
    def generate_random_key(length: int = 16) -> str:
        """
        랜덤 키 생성

        Args:
            length: 키 길이

        Returns:
            랜덤 문자열
        """
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        API 키 생성

        Args:
            length: 키 길이

        Returns:
            랜덤 API 키
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_value(value: str, salt: str = "") -> str:
        """
        값 해시화

        Args:
            value: 해시할 값
            salt: 솔트 값

        Returns:
            SHA256 해시 (16진수)
        """
        data = f"{value}:{salt}".encode()
        return hashlib.sha256(data).hexdigest()