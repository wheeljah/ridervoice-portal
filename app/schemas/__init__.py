"""
RiderVoiceAI Backend Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== License Schemas =====

class LicenseRedeemRequest(BaseModel):
    """라이선스 키 Redemption 요청"""
    license_key: str = Field(..., description="라이선스 키")
    device_id: Optional[str] = Field(None, description="디바이스 ID")
    pause_start_time: Optional[int] = Field(None, description="쿠폰 적용 시작 시간 (밀리초)")


class LicenseRedeemResponse(BaseModel):
    """라이선스 Redemption 응답"""
    success: bool
    message: str
    license_type: Optional[str] = None
    expires_at: Optional[int] = None
    pause_start_time: Optional[int] = None
    pause_end_time: Optional[int] = None


class LicenseStatusResponse(BaseModel):
    """라이선스 상태 응답"""
    device_id: str
    has_active_license: bool
    license_type: Optional[str] = None
    license_expires_at: Optional[int] = None
    is_paused: bool
    pause_start_time: Optional[int] = None
    pause_end_time: Optional[int] = None
    remaining_days: Optional[int] = None
    remaining_time_string: Optional[str] = None


class LicenseValidateRequest(BaseModel):
    """라이선스 키 검증 요청"""
    license_key: str = Field(..., description="검증할 라이선스 키")


class LicenseValidateResponse(BaseModel):
    """라이선스 키 검증 응답"""
    valid: bool
    license_type: Optional[str] = None
    is_coupon: bool = False
    duration_hours: Optional[int] = None
    error_message: Optional[str] = None


# ===== Coupon Schemas =====

class CouponRedeemRequest(BaseModel):
    """쿠폰 Redemption 요청"""
    coupon_code: str = Field(..., description="쿠폰 코드")
    device_id: Optional[str] = Field(None, description="디바이스 ID")
    pause_start_time: Optional[int] = Field(None, description="멈춤 시작 시간 (밀리초, 생략시 즉시 시작)")


class CouponRedeemResponse(BaseModel):
    """쿠폰 Redemption 응답"""
    success: bool
    message: str
    coupon_type: Optional[str] = None
    duration_hours: Optional[int] = None
    pause_start_time: Optional[int] = None
    pause_end_time: Optional[int] = None


class AvailableCoupon(BaseModel):
    """사용 가능한 쿠폰 정보"""
    coupon_type: str
    display_name: str
    duration_hours: int


class AvailableCouponsResponse(BaseModel):
    """사용 가능한 쿠폰 목록 응답"""
    coupons: List[AvailableCoupon]


# ===== Price Schemas =====

class PriceItem(BaseModel):
    """가격 항목"""
    license_type: str
    display_name: str
    duration_days: int
    price: int  # KRW


class PriceResponse(BaseModel):
    """가격 응답"""
    prices: List[PriceItem]
    updated_at: Optional[datetime] = None


class PriceUpdateRequest(BaseModel):
    """가격 변경 요청"""
    license_type: str = Field(..., description="라이선스 유형")
    price: int = Field(..., ge=0, description="새 가격 (KRW)")


# ===== Common Schemas =====

class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    timestamp: int
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
    timestamp: int


# ===== Notification Raw Data Schemas =====

class NotificationRawDataCreate(BaseModel):
    """알림 원본 데이터 생성 요청"""
    device_id: str = Field(..., description="디바이스 ID")
    app_package: str = Field(..., description="알림 앱 패키지명")
    app_name: Optional[str] = Field(None, description="알림 앱 이름")
    title: Optional[str] = Field(None, description="알림 제목")
    text: Optional[str] = Field(None, description="알림 내용")
    sub_text: Optional[str] = Field(None, description="알림 서브 텍스트")
    big_text: Optional[str] = Field(None, description="알림 대テキスト")
    extra_text: Optional[str] = Field(None, description="추가 텍스트")
    raw_data: Optional[str] = Field(None, description="원본 JSON 데이터")
    timestamp: int = Field(..., description="알림 시간 (밀리초)")


class NotificationRawDataResponse(BaseModel):
    """알림 원본 데이터 응답"""
    id: int
    device_id: str
    app_package: str
    app_name: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    sub_text: Optional[str] = None
    big_text: Optional[str] = None
    extra_text: Optional[str] = None
    raw_data: Optional[str] = None
    timestamp: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationRawDataBatchCreate(BaseModel):
    """알림 원본 데이터 일괄 생성 요청"""
    notifications: List[NotificationRawDataCreate] = Field(..., description="알림 데이터 목록")


# ===== Demo Monitoring Schemas =====

class DemoEventCreate(BaseModel):
    """데모 이벤트 단건 생성"""
    device_id:   str            = Field(..., description="디바이스 ID")
    app_version: Optional[str]  = Field(None, description="앱 버전")
    session_id:  Optional[str]  = Field(None, description="세션 ID")

    # CALL_DETECTED | CALL_ACCEPTED | CALL_REJECTED | APP_STARTED | APP_STOPPED
    event_type: str = Field(..., description="이벤트 유형")

    platform:           Optional[str]   = Field(None, description="플랫폼 (BAEMIN|COUPANG|YOGIYO)")
    pickup_address:     Optional[str]   = None
    delivery_address:   Optional[str]   = None
    estimated_fee:      Optional[int]   = Field(None, description="예상 금액 (원)")
    estimated_time_min: Optional[int]   = Field(None, description="예상 소요 시간 (분)")
    distance_km:        Optional[float] = Field(None, description="거리 (km)")

    ai_recommended:   Optional[bool]  = None
    ai_confidence:    Optional[float] = None
    ai_reason:        Optional[str]   = None
    efficiency_score: Optional[int]   = None

    # ACCEPTED | REJECTED | IGNORED
    rider_action: Optional[str] = None

    # 라이더 위치 (핫존 히트맵용)
    rider_lat: Optional[float] = Field(None, description="라이더 위도")
    rider_lng: Optional[float] = Field(None, description="라이더 경도")

    # 파싱 품질 — Android NotificationParser 결과
    raw_notification_text: Optional[str]   = Field(None, description="원본 알림 텍스트 (재파싱용)", max_length=2000)
    parse_confidence:      Optional[float] = Field(None, description="파싱 신뢰도 0.0~1.0")
    parse_warnings:        Optional[str]   = Field(None, description="파싱 경고 목록 (|구분)")

    timestamp: int = Field(..., description="이벤트 발생 시각 (ms)")


class DemoEventBatchCreate(BaseModel):
    """데모 이벤트 일괄 생성"""
    events: List[DemoEventCreate] = Field(..., description="이벤트 목록")


class RiderDemoStats(BaseModel):
    """라이더 1명의 데모 통계"""
    device_id:    str
    first_seen:   Optional[int] = None   # ms
    last_seen:    Optional[int] = None   # ms
    is_active:    bool = False           # 최근 24h 활동 여부

    total_sessions:    int   = 0
    total_detected:    int   = 0
    total_accepted:    int   = 0
    total_rejected:    int   = 0
    acceptance_rate:   float = 0.0       # %
    ai_match_rate:     float = 0.0       # AI 추천과 라이더 행동 일치율 (%)

    avg_fee_accepted:     Optional[float] = None   # 수락한 주문 평균 단가
    avg_efficiency_score: Optional[float] = None   # 평균 효율 점수
    avg_distance_km:      Optional[float] = None

    platform_breakdown: dict = Field(default_factory=dict)  # {"BAEMIN": 30, "COUPANG": 17}


class DemoSummary(BaseModel):
    """전체 데모 요약"""
    total_riders:          int   = 0
    active_riders_24h:     int   = 0
    total_calls_detected:  int   = 0
    total_accepted:        int   = 0
    total_rejected:        int   = 0
    overall_acceptance_rate: float = 0.0
    overall_ai_match_rate:   float = 0.0
    platform_breakdown:    dict  = Field(default_factory=dict)
    riders:                List[RiderDemoStats] = Field(default_factory=list)


# ===== Delivery Tracking Schemas =====

class TrackingPointCreate(BaseModel):
    """GPS 포인트 단건"""
    lat:       float = Field(..., description="위도")
    lng:       float = Field(..., description="경도")
    accuracy:  Optional[float] = Field(None, description="GPS 정확도 (m)")
    # START | WAYPOINT | COMPLETE
    point_type: str  = Field(..., description="포인트 종류")
    actual_duration_min: Optional[int]   = Field(None, description="실제 소요 시간 (분, COMPLETE만)")
    actual_distance_km:  Optional[float] = Field(None, description="실제 이동 거리 (km, COMPLETE만)")
    timestamp: int = Field(..., description="이벤트 시각 (ms)")


class TrackingBatchCreate(BaseModel):
    """GPS 포인트 일괄 업로드"""
    device_id:           str = Field(..., description="디바이스 ID")
    session_id:          Optional[str] = None
    delivery_session_id: str = Field(..., description="건별 배달 세션 ID")
    # START 포인트에 포함되는 주문 메타
    platform:         Optional[str] = None
    estimated_fee:    Optional[int] = None
    pickup_address:   Optional[str] = None
    delivery_address: Optional[str] = None
    points: List[TrackingPointCreate] = Field(..., description="GPS 포인트 목록")


class TrackingPoint(BaseModel):
    """GPS 포인트 응답"""
    lat:        float
    lng:        float
    accuracy:   Optional[float] = None
    point_type: str
    actual_duration_min: Optional[int]   = None
    actual_distance_km:  Optional[float] = None
    timestamp:  int

    class Config:
        from_attributes = True


class DeliverySession(BaseModel):
    """배달 1건의 GPS 세션"""
    delivery_session_id: str
    platform:            Optional[str] = None
    estimated_fee:       Optional[int] = None
    pickup_address:      Optional[str] = None
    delivery_address:    Optional[str] = None
    started_at:          Optional[int] = None
    completed_at:        Optional[int] = None
    actual_duration_min: Optional[int] = None
    actual_distance_km:  Optional[float] = None
    points:              List[TrackingPoint] = Field(default_factory=list)


# ===== Earnings Dashboard Schemas =====

class EarningsPeriod(BaseModel):
    """기간별 수익"""
    calls:        int   = 0
    earnings:     int   = 0    # 원
    avg_fee:      float = 0.0


class HourlyEarnings(BaseModel):
    """시간대별 수익"""
    hour:     int
    calls:    int
    earnings: int


class EarningsDashboard(BaseModel):
    """라이더 수익 대시보드"""
    device_id:    str
    today:        EarningsPeriod = Field(default_factory=EarningsPeriod)
    this_week:    EarningsPeriod = Field(default_factory=EarningsPeriod)
    this_month:   EarningsPeriod = Field(default_factory=EarningsPeriod)
    hourly_breakdown: List[HourlyEarnings] = Field(default_factory=list)
    best_hour:        Optional[int]  = None   # 수익 최고 시간대 (0~23)
    best_platform:    Optional[str]  = None   # 평균 단가 최고 플랫폼


# ===== Hotzone Schemas =====

class HotzoneCluster(BaseModel):
    """핫존 클러스터 (격자 집계)"""
    lat:     float
    lng:     float
    count:   int           # 해당 격자 내 주문 감지 건수
    avg_fee: Optional[float] = None


class HotzoneResponse(BaseModel):
    """핫존 히트맵 응답"""
    clusters: List[HotzoneCluster] = Field(default_factory=list)
    total_points: int = 0