"""
RiderVoiceAI Backend API - Main Entry Point
"""
import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers import licenses, coupons, prices, admin, health, notifications, demo, tracking, auth, delivery_accounts
from app.schemas import HealthResponse, ErrorResponse
from app.config import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="RiderVoiceAI Backend API",
    description="RiderVoiceAI 앱의 백엔드 API 서버 - 라이선스/쿠폰/데모 모니터링",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청 로깅"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=int(time.time() * 1000)
        ).model_dump()
    )


# 라우터 등록
app.include_router(health.router)       # /health
app.include_router(auth.router)         # /api/v1/auth
app.include_router(licenses.router)    # /api/v1/licenses
app.include_router(coupons.router)     # /api/v1/coupons
app.include_router(prices.router)      # /api/v1/prices
app.include_router(admin.router)       # /api/v1/admin
app.include_router(notifications.router) # /api/notifications
app.include_router(demo.router)          # /api/v1/demo
app.include_router(tracking.router)     # /api/v1/tracking
app.include_router(delivery_accounts.router)  # /api/v1/delivery-accounts


@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        print(f"[ERROR] init_db 실패 - {e}")


@app.get("/", response_model=HealthResponse)
def root():
    """루트 엔드포인트 - 헬스 체크"""
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time() * 1000)
    )


@app.get("/health", response_model=HealthResponse)
def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=int(time.time() * 1000)
    )


if __name__ == "__main__":
    import uvicorn

    # Leapcell environment detection
    host = "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=settings.DEBUG
    )