# RiderVoiceAI Backend API

RiderVoiceAI 앱의 백엔드 API 서버입니다. 라이선스 및 쿠폰 관리를 위한 RESTful API를 제공합니다.

## 라이선스 유형

| 유형 | 설명 | 기간 |
|------|------|------|
| LM1 | 1개월 사용권 | 30일 |
| LM3 | 3개월 사용권 | 90일 |
| LM6 | 6개월 사용권 | 180일 |
| LMY | 1년 사용권 | 365일 |

## 쿠폰 유형

| 유형 | 설명 | 기간 |
|------|------|------|
| PAU4 | 4시간 멈춤 쿠폰 | 4시간 |
| PAU1 | 1일 멈춤 쿠폰 | 24시간 |
| PAU3 | 3일 멈춤 쿠폰 | 72시간 |
| PAU5 | 5일 멈춤 쿠폰 | 120시간 |

## 기술 스택

- **Framework**: FastAPI
- **Database**: SQLite (Leapcell 호환)
- **ORM**: SQLAlchemy
- **Validation**: Pydantic

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일을 편집하여 필요한 값 설정
```

### 3. 데이터베이스 초기화

```bash
# 앱 시작 시 자동으로 테이블이 생성됩니다
python -m app.main
```

## 실행

### 로컬 개발

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 헬스 체크

```
GET /health
```

### 라이선스 API

```
POST /api/v1/licenses/redeem
GET /api/v1/licenses/status/{device_id}
POST /api/v1/licenses/validate
```

### 쿠폰 API

```
POST /api/v1/coupons/redeem
GET /api/v1/coupons/available
```

### 가격 API

```
GET /api/v1/prices
PUT /api/v1/prices
```

### 관리자 API

```
POST /api/v1/admin/keys/generate
```

## API 인증

모든 API는 `X-API-Key` 헤더를 통한 인증이 필요합니다.

```
X-API-Key: your-api-key
```

관리자 API는 `X-Admin-Key` 헤더를 사용합니다.

```
X-Admin-Key: your-admin-key
```

## API 사용 예시

### 라이선스 키 redemption

```bash
curl -X POST http://localhost:8000/api/v1/licenses/redeem \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "license_key": "LM1-1234567890-ABCDEF12",
    "device_id": "device-123"
  }'
```

### 라이선스 상태 조회

```bash
curl -X GET "http://localhost:8000/api/v1/licenses/status/device-123" \
  -H "X-API-Key: your-api-key"
```

### 라이선스 키 검증

```bash
curl -X POST http://localhost:8000/api/v1/licenses/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "license_key": "LM1-1234567890-ABCDEF12"
  }'
```

### 관리자 키 생성

```bash
curl -X POST http://localhost:8000/api/v1/admin/keys/generate \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "license_type": "LM1",
    "quantity": 10
  }'
```

## Leapcell 배포 가이드

### 1. 프로젝트 구조

Leapcell에 배포할 때 다음과 같은 구조를 권장합니다:

```
ridervoiceai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── data/                    # SQLite 데이터베이스 디렉토리
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

### 2. Leapcell 설정

Leapcell 대시보드에서 다음 설정을 구성하세요:

**Build Command:**
```bash
pip install -r requirements.txt
```

**Run Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Environment Variables:**
```env
DATABASE_URL=sqlite:///./data/ridervoice.db
LEAPCELL=true
DEBUG=false
API_KEY=your-production-api-key
ADMIN_KEY=your-production-admin-key
LICENSE_SECRET_KEY=your-license-secret-key
```

### 3. SQLite 경로 설정

Leapcell에서는 파일 시스템 쓰기가 제한될 수 있으므로, `data/` 디렉토리에 데이터베이스를 저장하는 것을 권장합니다.

`config.py`에서 Leapcell 모드일 때 경로를 자동으로 조정합니다:

```python
if os.getenv("LEAPCELL", "false").lower() == "true":
    DATABASE_URL = "sqlite:///./data/ridervoice.db"
```

### 4. 첫 배포 시 데이터베이스테이블 생성

Leapcell의 첫 배포 후 `/health/db` 엔드포인트를 호출하여 테이블이 자동으로 생성되는지 확인하세요.

```bash
curl https://your-app.leapcell.dev/health/db
```

### 5. 관리자 키 생성

배포 후 관리자 API를 사용하여 라이선스 키를 생성하세요:

```bash
curl -X POST https://your-app.leapcell.dev/api/v1/admin/keys/generate \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-key" \
  -d '{
    "license_type": "LM1",
    "quantity": 100
  }'
```

## 라이선스 키 형식

라이선스 키는 다음 형식을 따릅니다:

```
{TYPE}-{TIMESTAMP}-{SIGNATURE}
```

예: `LM1-1234567890-ABCDEF12`

- **TYPE**: 라이선스 유형 (LM1, LM3, LM6, LMY, PAU4, PAU1, PAU3, PAU5)
- **TIMESTAMP**: 키 생성 시점 (Unix timestamp, 초)
- **SIGNATURE**: SHA256 기반 8자리 HMAC 서명

## 라이선스 키 생성 (서버 측)

서버에서 라이선스 키를 생성하려면 `LicenseService.generate_signature()` 메서드를 사용하세요:

```python
from app.services.license_service import LicenseService
import time

type_code = "LM1"
timestamp = int(time.time())
signature = LicenseService.generate_signature(type_code, timestamp)
license_key = f"{type_code}-{timestamp}-{signature}"
```

## 테스트

```bash
# 테스트 실행
pytest

# 특정 파일 테스트
pytest tests/test_licenses.py -v
```

## 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 설정 관리
│   ├── database.py          # DB 연결 및 세션
│   ├── models/              # SQLAlchemy 모델
│   │   ├── __init__.py
│   │   ├── coupon.py
│   │   ├── license.py
│   │   ├── price.py
│   │   ├── redemption_log.py
│   │   └── user.py
│   ├── routers/             # API 라우터
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── coupons.py
│   │   ├── health.py
│   │   ├── licenses.py
│   │   └── prices.py
│   ├── schemas/            # Pydantic 스키마
│   │   └── __init__.py
│   ├── services/            # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── coupon_service.py
│   │   ├── crypto.py
│   │   └── license_service.py
│   └── utils/               # 유틸리티
│       └── __init__.py
├── data/                    # SQLite 데이터베이스 (Leapcell)
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## 라이선스

이 프로젝트는 proprietary 소프트웨어입니다.