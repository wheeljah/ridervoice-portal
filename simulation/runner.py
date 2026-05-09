"""
RiderVoice AI 시뮬레이션 러너
=================================
사용법:
  python simulation/runner.py                  # 전체 실행
  python simulation/runner.py --parse-only     # 파싱 검증만
  python simulation/runner.py --api-only       # API 플로우만
  python simulation/runner.py --platform baemin   # 특정 플랫폼만
  python simulation/runner.py --url http://localhost:8000  # 로컬 서버 대상

환경변수:
  API_KEY   = X-API-Key 헤더값  (기본: .env 파일 또는 하드코딩값)
  ADMIN_KEY = X-Admin-Key 헤더값
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import requests

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent
SCENARIOS = ROOT / "scenarios"
sys.path.insert(0, str(ROOT))

from parser import parse as parse_notification

# ── ANSI 컬러 ──────────────────────────────────────────────────────────────────
G  = "\033[92m"   # 초록
R  = "\033[91m"   # 빨강
Y  = "\033[93m"   # 노랑
B  = "\033[94m"   # 파랑
C  = "\033[96m"   # 하늘
W  = "\033[97m"   # 흰색
DIM= "\033[2m"    # 흐리게
END= "\033[0m"

OK  = f"{G}✅{END}"
FAIL= f"{R}❌{END}"
WARN= f"{Y}⚠️ {END}"
INFO= f"{B}ℹ️ {END}"

# ── 기본 설정 ──────────────────────────────────────────────────────────────────
DEFAULT_URL       = os.getenv("API_URL",   "http://localhost:8000")
DEFAULT_API_KEY   = os.getenv("API_KEY",   "rv-api-key-change-in-production-2026")
DEFAULT_ADMIN_KEY = os.getenv("ADMIN_KEY", "rv-admin-key-change-in-production-2026")
DEMO_DEVICE_ID    = f"sim-{uuid.uuid4().hex[:8]}"


# ══════════════════════════════════════════════════════════════════════════════
# 섹션 1: 파싱 검증
# ══════════════════════════════════════════════════════════════════════════════

def run_parse_tests(platform_filter: str | None = None) -> tuple[int, int]:
    """시나리오 파일을 읽어 파싱 정확도를 검증합니다."""
    print(f"\n{C}{'═'*60}{END}")
    print(f"{C}  📋 파싱 검증 (NotificationParser){END}")
    print(f"{C}{'═'*60}{END}")

    scenario_files = list(SCENARIOS.glob("*.json"))
    if not scenario_files:
        print(f"{WARN} scenarios/ 디렉토리에 JSON 파일이 없습니다.")
        return 0, 0

    passed = failed = 0

    for f in sorted(scenario_files):
        platform_name = f.stem.upper()          # 'baemin' → 'BAEMIN'
        if platform_filter and platform_filter.upper() not in platform_name:
            continue

        scenarios = json.loads(f.read_text(encoding="utf-8"))
        print(f"\n{W}[{f.stem.upper()}]{END}  {DIM}({len(scenarios)}개 시나리오){END}")

        for s in scenarios:
            result, ok = _run_one_parse(s)
            passed += ok
            failed += (1 - ok)

    return passed, failed


def _run_one_parse(s: dict) -> tuple[dict, int]:
    name     = s["name"]
    platform = s["platform"]
    exp      = s.get("expected", {})

    r = parse_notification(
        platform    = platform,
        title       = s.get("title",       ""),
        text        = s.get("text",        ""),
        big_text    = s.get("big_text",    ""),
        summary_text= s.get("summary_text",""),
    )

    errors  = []
    notices = []

    # ── 필드 검증 ────────────────────────────────────────────────────────────
    def _check_exact(key_exp, key_res, label):
        expected_val = exp.get(key_exp)
        if expected_val is None:
            return
        actual = getattr(r, key_res)
        if actual != expected_val:
            errors.append(f"{label}: 기대={expected_val}, 실제={actual}")

    def _check_contains(key_exp, key_res, label):
        expected_sub = exp.get(key_exp)
        if expected_sub is None:
            return
        actual = getattr(r, key_res) or ""
        if expected_sub not in actual:
            errors.append(f"{label} '{expected_sub}' 미포함: 실제='{actual}'")

    def _check_null(key_exp, key_res, label):
        if exp.get(key_exp) is None and key_exp in exp:
            actual = getattr(r, key_res)
            if actual is not None:
                errors.append(f"{label}: null 기대, 실제={actual}")

    _check_exact("fee",          "fee",          "배달료")
    _check_exact("distance_km",  "distance_km",  "거리(km)")
    _check_exact("estimated_min","estimated_min","소요시간(분)")
    _check_contains("pickup_contains",   "pickup_address",   "픽업주소")
    _check_contains("delivery_contains", "delivery_address", "배달지")
    _check_contains("menu_contains",     "menu",             "메뉴")
    _check_null("fee",          "fee",          "배달료")
    _check_null("distance_km",  "distance_km",  "거리")
    _check_null("estimated_min","estimated_min","소요시간")

    # 신뢰도
    min_conf = exp.get("min_confidence")
    max_conf = exp.get("max_confidence")
    if min_conf is not None and r.parse_confidence < min_conf:
        errors.append(f"신뢰도 낮음: {r.parse_confidence:.2f} < {min_conf}")
    if max_conf is not None and r.parse_confidence > max_conf:
        errors.append(f"신뢰도 너무 높음: {r.parse_confidence:.2f} > {max_conf}")

    # 경고 표시
    if r.warnings:
        notices = r.warnings

    ok = 1 if not errors else 0
    icon = OK if ok else FAIL
    conf_color = G if r.parse_confidence >= 0.7 else (Y if r.parse_confidence >= 0.4 else R)

    print(f"  {icon} {name}")
    print(f"     {DIM}신뢰도:{END} {conf_color}{r.parse_confidence:.2f}{END}  "
          f"{DIM}배달료:{END} {_fmt(r.fee,'원')}  "
          f"{DIM}거리:{END} {_fmt(r.distance_km,'km')}  "
          f"{DIM}시간:{END} {_fmt(r.estimated_min,'분')}")

    if r.pickup_address or r.delivery_address:
        print(f"     {DIM}픽업:{END} {r.pickup_address or '—'}  "
              f"{DIM}배달:{END} {r.delivery_address or '—'}")
    if r.menu:
        print(f"     {DIM}메뉴:{END} {r.menu}")

    for e in errors:
        print(f"     {FAIL} {e}")
    for n in notices:
        print(f"     {WARN} {n}")
    if s.get("note"):
        print(f"     {DIM}📌 {s['note']}{END}")

    return vars(r), ok


# ══════════════════════════════════════════════════════════════════════════════
# 섹션 2: API 플로우 검증
# ══════════════════════════════════════════════════════════════════════════════

class ApiClient:
    def __init__(self, base: str, api_key: str, admin_key: str):
        self.base      = base.rstrip("/")
        self.api_hdrs  = {"X-API-Key": api_key,   "Content-Type": "application/json"}
        self.adm_hdrs  = {"X-Admin-Key": admin_key,"Content-Type": "application/json"}

    def get(self, path, admin=False, **kw):
        h = self.adm_hdrs if admin else self.api_hdrs
        return requests.get(self.base + path, headers=h, timeout=10, **kw)

    def post(self, path, data, admin=False, **kw):
        h = self.adm_hdrs if admin else self.api_hdrs
        return requests.post(self.base + path, json=data, headers=h, timeout=10, **kw)


def run_api_tests(api: ApiClient) -> tuple[int, int]:
    print(f"\n{C}{'═'*60}{END}")
    print(f"{C}  🌐 API 플로우 검증{END}")
    print(f"{C}{'═'*60}{END}")

    passed = failed = 0
    device = DEMO_DEVICE_ID

    steps = [
        ("헬스체크",          _test_health),
        ("이벤트: APP_STARTED",_test_app_started),
        ("이벤트: CALL_DETECTED (배민 고수익)", _test_call_detected_accept),
        ("이벤트: CALL_ACCEPTED",              _test_call_accepted),
        ("이벤트: CALL_DETECTED (쿠팡 장거리)", _test_call_detected_reject),
        ("이벤트: CALL_REJECTED",              _test_call_rejected),
        ("이벤트: APP_STOPPED",               _test_app_stopped),
        ("배치 이벤트 전송",                   _test_batch_events),
        ("라이더 통계 조회",                   _test_rider_stats),
        ("수익 대시보드 조회",                 _test_earnings),
        ("전체 데모 요약 조회",                _test_summary),
        ("핫존 히트맵 조회",                   _test_hotzone),
        ("트래킹 포인트 업로드",               _test_tracking),
        ("라이더 배달 세션 조회",              _test_tracking_sessions),
    ]

    for label, fn in steps:
        ok = fn(api, device)
        icon = OK if ok else FAIL
        print(f"  {icon} {label}")
        passed += ok
        failed += (1 - ok)

    return passed, failed


# ── 개별 API 테스트 함수 ─────────────────────────────────────────────────────

def _test_health(api, device):
    try:
        r = api.get("/health")
        ok = r.status_code == 200
        if not ok:
            _err(f"HTTP {r.status_code}")
        return ok
    except Exception as e:
        _err(str(e)); return False


def _event(api, device, event_type, extra: dict = None):
    payload = {
        "device_id":   device,
        "session_id":  "sim-session",
        "event_type":  event_type,
        "app_version": "sim-1.0",
        "timestamp":   _now_ms(),
    }
    if extra:
        payload.update(extra)
    try:
        r = api.post("/api/v1/demo/events", payload)
        if r.status_code not in (200, 201):
            _err(f"HTTP {r.status_code}: {r.text[:100]}")
            return False
        return True
    except Exception as e:
        _err(str(e)); return False


def _test_app_started(api, device):
    return _event(api, device, "APP_STARTED")

def _test_app_stopped(api, device):
    return _event(api, device, "APP_STOPPED")

def _test_call_detected_accept(api, device):
    return _event(api, device, "CALL_DETECTED", {
        "platform": "BAEMIN", "estimated_fee": 4500,
        "distance_km": 2.3,   "estimated_time_min": 18,
        "pickup_address": "강남구 테헤란로 123",
        "delivery_address": "서초구 서초대로 456",
        "ai_recommended": True, "ai_confidence": 0.87,
        "efficiency_score": 82,
        "rider_lat": 37.5068, "rider_lng": 127.0538,
        "raw_notification_text": "픽업: 강남구 테헤란로 123\n배달료 4,500원 | 2.3km | 18분",
        "parse_confidence": 0.92,
    })

def _test_call_accepted(api, device):
    return _event(api, device, "CALL_ACCEPTED", {
        "platform": "BAEMIN", "estimated_fee": 4500,
        "distance_km": 2.3,   "estimated_time_min": 18,
        "ai_recommended": True, "rider_action": "ACCEPTED",
        "rider_lat": 37.5068, "rider_lng": 127.0538,
    })

def _test_call_detected_reject(api, device):
    return _event(api, device, "CALL_DETECTED", {
        "platform": "COUPANG_EATS", "estimated_fee": 5500,
        "distance_km": 11.2, "estimated_time_min": 55,
        "pickup_address": "중구 명동",
        "delivery_address": "강동구 천호동 123",
        "ai_recommended": False, "ai_confidence": 0.91,
        "efficiency_score": 23,
        "rider_lat": 37.5608, "rider_lng": 126.9858,
        "parse_confidence": 0.88,
    })

def _test_call_rejected(api, device):
    return _event(api, device, "CALL_REJECTED", {
        "platform": "COUPANG_EATS", "estimated_fee": 5500,
        "distance_km": 11.2, "estimated_time_min": 55,
        "ai_recommended": False, "rider_action": "REJECTED",
    })

def _test_batch_events(api, device):
    events = [
        {"device_id": device, "event_type": "CALL_DETECTED", "platform": "BAEMIN",
         "estimated_fee": 3800, "distance_km": 3.1, "estimated_time_min": 20,
         "ai_recommended": True, "efficiency_score": 71,
         "rider_lat": 37.5276, "rider_lng": 127.0278,
         "timestamp": _now_ms() - 60_000, "parse_confidence": 0.85},
        {"device_id": device, "event_type": "CALL_ACCEPTED", "platform": "BAEMIN",
         "estimated_fee": 3800, "rider_action": "ACCEPTED",
         "ai_recommended": True,
         "timestamp": _now_ms() - 55_000},
    ]
    try:
        r = api.post("/api/v1/demo/events/batch", {"events": events})
        return r.status_code in (200, 201)
    except Exception as e:
        _err(str(e)); return False

def _test_rider_stats(api, device):
    try:
        r = api.get(f"/api/v1/demo/stats/{device}", admin=True)
        if r.status_code != 200:
            _err(f"HTTP {r.status_code}"); return False
        d = r.json()
        total = d.get("total_detected", 0)
        accepted = d.get("total_accepted", 0)
        if total > 0:
            print(f"       {DIM}감지:{total}건  수락:{accepted}건  "
                  f"수락률:{d.get('acceptance_rate',0):.1f}%  "
                  f"AI일치:{d.get('ai_match_rate',0):.1f}%{END}")
        return True
    except Exception as e:
        _err(str(e)); return False

def _test_earnings(api, device):
    try:
        r = api.get(f"/api/v1/demo/earnings/{device}")
        if r.status_code != 200:
            _err(f"HTTP {r.status_code}"); return False
        d = r.json()
        today = d.get("today", {})
        print(f"       {DIM}오늘: {today.get('calls',0)}건  "
              f"₩{today.get('earnings',0):,}  "
              f"평균 ₩{int(today.get('avg_fee',0)):,}{END}")
        return True
    except Exception as e:
        _err(str(e)); return False

def _test_summary(api, device):
    try:
        r = api.get("/api/v1/demo/summary", admin=True)
        if r.status_code != 200:
            _err(f"HTTP {r.status_code}"); return False
        d = r.json()
        print(f"       {DIM}전체 라이더:{d.get('total_riders',0)}명  "
              f"감지:{d.get('total_calls_detected',0)}건  "
              f"수락률:{d.get('overall_acceptance_rate',0):.1f}%{END}")
        return True
    except Exception as e:
        _err(str(e)); return False

def _test_hotzone(api, device):
    try:
        r = api.get("/api/v1/demo/hotzone", admin=True)
        if r.status_code != 200:
            _err(f"HTTP {r.status_code}"); return False
        d = r.json()
        clusters = d.get("clusters", [])
        print(f"       {DIM}클러스터 {len(clusters)}개  총 포인트:{d.get('total_points',0)}{END}")
        return True
    except Exception as e:
        _err(str(e)); return False

def _test_tracking(api, device):
    dsid = f"delivery-{uuid.uuid4().hex[:8]}"
    payload = {
        "device_id":            device,
        "delivery_session_id":  dsid,
        "platform":             "BAEMIN",
        "estimated_fee":        4500,
        "pickup_address":       "강남구 테헤란로 123",
        "delivery_address":     "서초구 서초대로 456",
        "points": [
            {"lat":37.5068,"lng":127.0538,"point_type":"START",
             "accuracy":8.0,"timestamp":_now_ms()-300_000},
            {"lat":37.5002,"lng":127.0490,"point_type":"WAYPOINT",
             "accuracy":6.0,"timestamp":_now_ms()-240_000},
            {"lat":37.4956,"lng":127.0420,"point_type":"WAYPOINT",
             "accuracy":5.0,"timestamp":_now_ms()-180_000},
            {"lat":37.4922,"lng":127.0078,"point_type":"COMPLETE",
             "actual_duration_min":18,"actual_distance_km":2.4,
             "accuracy":5.0,"timestamp":_now_ms()-60_000},
        ],
    }
    try:
        r = api.post("/api/v1/tracking/points/batch", payload)
        return r.status_code in (200, 201)
    except Exception as e:
        _err(str(e)); return False

def _test_tracking_sessions(api, device):
    try:
        r = api.get(f"/api/v1/tracking/{device}/sessions", admin=True)
        if r.status_code != 200:
            _err(f"HTTP {r.status_code}"); return False
        sessions = r.json()
        print(f"       {DIM}세션 {len(sessions)}개{END}")
        for s in sessions[:2]:
            dur = s.get('actual_duration_min','?')
            dist= s.get('actual_distance_km','?')
            pts = len(s.get('points',[]))
            print(f"       {DIM}  - {s.get('platform','?')} | "
                  f"{dur}분 | {dist}km | {pts}포인트{END}")
        return True
    except Exception as e:
        _err(str(e)); return False


# ══════════════════════════════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════════════════════════════

def _now_ms(): return int(time.time() * 1000)
def _err(msg): print(f"       {R}오류: {msg}{END}")
def _fmt(v, unit): return f"{v}{unit}" if v is not None else "—"


def _print_summary(parse_p, parse_f, api_p, api_f, skip_parse, skip_api):
    total_p = parse_p + api_p
    total_f = parse_f + api_f
    total   = total_p + total_f

    print(f"\n{C}{'═'*60}{END}")
    print(f"{C}  📊 최종 결과{END}")
    print(f"{C}{'═'*60}{END}")

    if not skip_parse:
        color = G if parse_f == 0 else (Y if parse_p >= parse_f else R)
        print(f"  파싱 검증  : {color}{parse_p} 통과  {parse_f} 실패{END}")
    if not skip_api:
        color = G if api_f == 0 else (Y if api_p >= api_f else R)
        print(f"  API 플로우 : {color}{api_p} 통과  {api_f} 실패{END}")

    color = G if total_f == 0 else (Y if total_p >= total_f else R)
    rate  = total_p / total * 100 if total else 0
    print(f"\n  {color}전체: {total_p}/{total} 통과  ({rate:.0f}%){END}")

    if total_f == 0:
        print(f"\n  {G}🎉 모든 검증 통과!{END}")
    elif rate >= 70:
        print(f"\n  {Y}⚠️  일부 항목 수정 필요{END}")
    else:
        print(f"\n  {R}🚨 주요 항목 실패 — 점검 필요{END}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="RiderVoice AI 시뮬레이션 러너")
    ap.add_argument("--url",       default=DEFAULT_URL,       help="백엔드 URL")
    ap.add_argument("--api-key",   default=DEFAULT_API_KEY,   help="X-API-Key")
    ap.add_argument("--admin-key", default=DEFAULT_ADMIN_KEY, help="X-Admin-Key")
    ap.add_argument("--parse-only",action="store_true", help="파싱 검증만 실행")
    ap.add_argument("--api-only",  action="store_true", help="API 플로우만 실행")
    ap.add_argument("--platform",  default=None, help="특정 플랫폼만 (baemin|coupang)")
    args = ap.parse_args()

    skip_parse = args.api_only
    skip_api   = args.parse_only

    print(f"\n{W}{'━'*60}{END}")
    print(f"{W}  🏍️  RiderVoice AI 시뮬레이션{END}")
    print(f"{W}{'━'*60}{END}")
    print(f"  대상 서버  : {args.url}")
    print(f"  테스트 기기: {DEMO_DEVICE_ID}")

    parse_p = parse_f = api_p = api_f = 0

    if not skip_parse:
        parse_p, parse_f = run_parse_tests(args.platform)

    if not skip_api:
        api = ApiClient(args.url, args.api_key, args.admin_key)
        api_p, api_f = run_api_tests(api)

    _print_summary(parse_p, parse_f, api_p, api_f, skip_parse, skip_api)
    sys.exit(0 if (parse_f + api_f) == 0 else 1)


if __name__ == "__main__":
    main()
