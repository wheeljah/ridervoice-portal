"""
NotificationParser — Python 포팅 (Android NotificationParser.kt 동일 로직)

Android 빌드 없이 파싱 로직을 독립적으로 검증합니다.
시나리오 JSON의 expected 값과 비교해 정확도를 측정합니다.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

# ── 공통 패턴 ──────────────────────────────────────────────────────────────────

FEE_LABEL     = re.compile(r'배달(?:료|비|요금|팁)?[:\s]*₩?\s*([\d,]+)\s*원?', re.I)
FEE_WON       = re.compile(r'₩?\s*([\d,]{3,})\s*원?')       # ₩ 기호 또는 3자리+ 금액
FEE_GENERIC   = re.compile(r'([\d,]+)\s*원')

DIST_KM       = re.compile(r'([\d.]+)\s*(?:km|킬로|킬로미터)', re.I)
DIST_M        = re.compile(r'(\d+)\s*m(?!in|km|eter|\d)', re.I)
TIME_RE       = re.compile(r'(\d+)\s*(?:분|minute|min)', re.I)

PICKUP_LABELS = [
    re.compile(r'픽업[:\s]+([^\n,→]+)'),
    re.compile(r'수령지[:\s]+([^\n,→]+)'),
    re.compile(r'픽업\s*주소[:\s]+([^\n,→]+)'),
]
DELIVERY_LABELS = [
    re.compile(r'배달지?[:\s]+([^\n,]+)'),
    re.compile(r'도착지[:\s]+([^\n,]+)'),
    re.compile(r'배달\s*주소[:\s]+([^\n,]+)'),
]
ARROW_RE = re.compile(r'([^\n→]+)\s*→\s*([^\n]+)')

KR_ADDR = [
    re.compile(r'[가-힣]+(?:시|군|구)\s+[가-힣]+(?:동|읍|면|로|길)[가-힣\d\s\-]+'),
    re.compile(r'[가-힣]+(?:로|길)\s*\d+(?:-\d+)?'),
    re.compile(r'[가-힣]+(?:동|읍|면)\s*\d+(?:-\d+)?'),
    re.compile(r'[가-힣]+(?:타워|빌딩|센터|아파트|플라자)[가-힣\d\s]*'),
]

MENU_KEYWORDS = {
    '치킨','피자','짜장','짬뽕','보쌈','순대','샐러드','샌드위치',
    '떡볶이','만두','족발','국밥','초밥','햄버거','라멘','파스타',
    '스테이크','커피','음료','버거','도시락','김밥','우동','냉면',
    '삼겹살','갈비','닭발','곱창','쌀국수','스시','타코','케밥',
}


@dataclass
class ParseResult:
    fee:              Optional[int]   = None
    distance_km:      Optional[float] = None
    estimated_min:    Optional[int]   = None
    pickup_address:   Optional[str]   = None
    delivery_address: Optional[str]   = None
    menu:             Optional[str]   = None
    raw_text:         str             = ""
    parse_confidence: float           = 0.0
    field_confidence: dict            = field(default_factory=dict)
    warnings:         list            = field(default_factory=list)


def parse(platform: str, title: str = "", text: str = "",
          big_text: str = "", summary_text: str = "") -> ParseResult:
    """
    플랫폼 알림 텍스트를 파싱해 ParseResult를 반환합니다.
    platform: 'BAEMIN' | 'COUPANG_EATS' | 'YOGIYO' | 'UNKNOWN'
    """
    parts = list(dict.fromkeys(
        p.strip() for p in [big_text, text, title, summary_text] if p and p.strip()
    ))
    full = '\n'.join(parts)
    conf: dict = {}
    warns: list = []

    if platform == 'BAEMIN':
        result = _baemin(full, parts, conf, warns)
    elif platform == 'COUPANG_EATS':
        result = _coupang(full, parts, conf, warns)
    elif platform == 'YOGIYO':
        result = _yogiyo(full, parts, conf, warns)
    else:
        warns.append('UNKNOWN_PLATFORM')
        result = _generic(full, parts, conf, warns)

    overall = _overall(conf)
    result.raw_text         = full
    result.parse_confidence = overall
    result.field_confidence = conf
    result.warnings         = warns
    return result


# ── 플랫폼별 전략 ──────────────────────────────────────────────────────────────

def _baemin(full, parts, conf, warns):
    return ParseResult(
        fee              = _fee(full, conf, warns),
        distance_km      = _distance(full, conf, warns),
        estimated_min    = _time(full, conf, warns),
        pickup_address   = _labeled(full, PICKUP_LABELS, conf, 'pickup')
                           or _kr_addr(full, conf, 'pickup'),
        delivery_address = _labeled(full, DELIVERY_LABELS, conf, 'delivery')
                           or _kr_addr(full, conf, 'delivery', skip_first=True),
        menu             = _menu(full, parts, conf, warns),
    )

def _coupang(full, parts, conf, warns):
    fee   = _fee(full, conf, warns)
    dist  = _distance(full, conf, warns)
    time_ = _time(full, conf, warns)
    menu  = _menu(full, parts, conf, warns)

    m = ARROW_RE.search(full)
    if m:
        store_side    = m.group(1).strip()
        delivery_side = m.group(2).strip()
        pickup   = _kr_addr_from(store_side) or store_side[:50]
        delivery = _kr_addr_from(delivery_side) or delivery_side[:50]
        conf['pickup']   = 0.7 if pickup else 0.2
        conf['delivery'] = 0.8 if delivery else 0.2
    else:
        pickup   = _labeled(full, PICKUP_LABELS, conf, 'pickup') or _kr_addr(full, conf, 'pickup')
        delivery = _labeled(full, DELIVERY_LABELS, conf, 'delivery') or _kr_addr(full, conf, 'delivery', skip_first=True)

    return ParseResult(fee=fee, distance_km=dist, estimated_min=time_,
                       pickup_address=pickup, delivery_address=delivery, menu=menu)

def _yogiyo(full, parts, conf, warns):
    return _baemin(full, parts, conf, warns)  # 요기요는 배민과 유사한 레이블 구조

def _generic(full, parts, conf, warns):
    return ParseResult(
        fee              = _fee(full, conf, warns),
        distance_km      = _distance(full, conf, warns),
        estimated_min    = _time(full, conf, warns),
        pickup_address   = _kr_addr(full, conf, 'pickup'),
        delivery_address = _kr_addr(full, conf, 'delivery', skip_first=True),
        menu             = _menu(full, parts, conf, warns),
    )


# ── 공통 추출 함수 ─────────────────────────────────────────────────────────────

def _fee(text, conf, warns):
    # 1순위: 레이블 명시
    m = FEE_LABEL.search(text)
    if m:
        v = int(m.group(1).replace(',', ''))
        if 500 <= v <= 50_000:
            conf['fee'] = 0.95
            return v
    # 2순위: ₩ 기호
    for m in FEE_WON.finditer(text):
        v = int(m.group(1).replace(',', ''))
        if 500 <= v <= 50_000:
            conf['fee'] = 0.65
            return v
    # 3순위: 범용 — 배달료 범위 최솟값
    candidates = [
        int(m.group(1).replace(',', ''))
        for m in FEE_GENERIC.finditer(text)
        if 500 <= int(m.group(1).replace(',', '')) <= 50_000
    ]
    if candidates:
        if len(candidates) > 1:
            warns.append(f'FEE_AMBIGUOUS: {len(candidates)} candidates {candidates}')
        conf['fee'] = 0.40
        return min(candidates)
    conf['fee'] = 0.0
    warns.append('FEE_NOT_FOUND')
    return None

def _distance(text, conf, warns):
    m = DIST_KM.search(text)
    if m:
        v = float(m.group(1))
        if 0.1 <= v <= 50:
            conf['distance'] = 0.95
            return v
    m = DIST_M.search(text)
    if m:
        v = int(m.group(1))
        if 100 <= v <= 50_000:
            conf['distance'] = 0.80
            return round(v / 1000, 2)
    conf['distance'] = 0.0
    warns.append('DISTANCE_NOT_FOUND')
    return None

def _time(text, conf, warns):
    m = TIME_RE.search(text)
    if m:
        v = int(m.group(1))
        if 1 <= v <= 120:
            conf['time'] = 0.90
            return v
    conf['time'] = 0.0
    warns.append('TIME_NOT_FOUND')
    return None

def _labeled(text, patterns, conf, key):
    for p in patterns:
        m = p.search(text)
        if m:
            addr = m.group(1).strip()[:100]
            if len(addr) >= 4:
                conf[key] = 0.90
                return addr
    return None

def _kr_addr(text, conf, key, skip_first=False):
    for p in KR_ADDR:
        matches = [m.group().strip() for m in p.finditer(text) if len(m.group().strip()) >= 5]
        target = matches[1] if skip_first and len(matches) > 1 else (matches[0] if matches else None)
        if target:
            conf[key] = 0.60
            return target[:100]
    conf[key] = 0.0
    return None

def _kr_addr_from(text):
    for p in KR_ADDR:
        m = p.search(text)
        if m:
            return m.group().strip()[:100]
    return None

def _menu(text, parts, conf, warns):
    for line in text.split('\n'):
        line = line.strip()
        if any(kw in line for kw in MENU_KEYWORDS):
            conf['menu'] = 0.80
            return line[:100]
    # fallback: 주소/금액/시간 아닌 첫 번째 라인
    for line in text.split('\n'):
        line = line.strip()
        if (not FEE_LABEL.search(line) and not DIST_KM.search(line)
                and not TIME_RE.search(line)
                and not any(p.search(line) for p in KR_ADDR)
                and 2 <= len(line) <= 80):
            conf['menu'] = 0.30
            warns.append('MENU_INFERRED')
            return line
    conf['menu'] = 0.0
    warns.append('MENU_NOT_FOUND')
    return None

def _overall(conf):
    return min(1.0, (
        conf.get('fee',      0) * 0.35 +
        conf.get('distance', 0) * 0.25 +
        conf.get('pickup',   0) * 0.20 +
        conf.get('time',     0) * 0.10 +
        conf.get('menu',     0) * 0.10
    ))
