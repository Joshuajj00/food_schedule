"""식품의약품안전처 식품영양성분DB API 클라이언트 (I2790).

응답 필드:
- DESC_KOR: 식품명
- SERVING_WT: 1회 섭취 참고량 (g)
- NUTR_CONT1: 에너지 (kcal)
- NUTR_CONT2: 탄수화물 (g)
- NUTR_CONT3: 단백질 (g)
- NUTR_CONT4: 지방 (g)
- NUTR_CONT5: 당류 (g)
"""
import os
import httpx
import time
from typing import Optional
from dataclasses import dataclass
from urllib.parse import quote

from backend.logger import get_logger

logger = get_logger('nutrition_client')

API_KEY = os.getenv('FOOD_API_KEY', '').strip()
BASE_URL = 'http://openapi.foodsafetykorea.go.kr/api'
SERVICE_ID = 'I2790'


@dataclass
class NutritionInfo:
    """100g당 영양 정보로 정규화된 결과"""
    name: str
    serving_g: float
    calories: float
    carbs_g: float
    protein_g: float
    fat_g: float
    sugar_g: float = 0.0
    matched_score: int = 0


_cache: dict[str, tuple[float, Optional[NutritionInfo]]] = {}
_CACHE_TTL = 86400


async def fetch_nutrition(query: str, top_k: int = 5) -> Optional[NutritionInfo]:
    """식품명으로 검색 → 100g 기준 정규화된 결과 1개 반환. 실패 시 None."""
    if not API_KEY:
        logger.warning("FOOD_API_KEY 환경변수 미설정. 영양 조회 건너뜀.")
        return None

    query = query.strip()
    if not query:
        return None

    now = time.time()
    if query in _cache:
        ts, val = _cache[query]
        if now - ts < _CACHE_TTL:
            logger.debug(f"영양 캐시 히트: {query}")
            return val

    encoded = quote(query)
    url = f"{BASE_URL}/{API_KEY}/{SERVICE_ID}/json/1/{top_k}/DESC_KOR={encoded}"
    logger.debug(f"영양 API 호출: {query}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.warning(f"영양 API 요청 실패 [{query}]: {e}")
        _cache[query] = (now, None)
        return None
    except ValueError as e:
        logger.warning(f"영양 API 응답 파싱 실패 [{query}]: {e}")
        return None

    body = data.get(SERVICE_ID, {})
    result_meta = body.get('RESULT', {})
    code = result_meta.get('CODE', '')
    if code and code != 'INFO-000':
        logger.debug(f"영양 검색 결과 없음: {query} (code={code})")
        _cache[query] = (now, None)
        return None

    rows = body.get('row', [])
    if not rows:
        _cache[query] = (now, None)
        return None

    best = _pick_best_match(query, rows)
    if not best:
        _cache[query] = (now, None)
        return None

    info = _row_to_nutrition(best, query)
    _cache[query] = (now, info)
    return info


def _pick_best_match(query: str, rows: list[dict]) -> Optional[dict]:
    """완전 일치 > 부분 일치 > 첫 번째."""
    q = query.replace(' ', '').lower()
    exact, partial = [], []
    for row in rows:
        name = row.get('DESC_KOR', '').replace(' ', '').lower()
        if name == q:
            exact.append(row)
        elif q in name or name in q:
            partial.append(row)
    return exact[0] if exact else (partial[0] if partial else (rows[0] if rows else None))


def _row_to_nutrition(row: dict, query: str) -> NutritionInfo:
    """API 행을 100g 기준 NutritionInfo로 변환."""
    def f(key: str, default: float = 0.0) -> float:
        v = row.get(key, '')
        try:
            return float(v) if v not in ('', None) else default
        except (ValueError, TypeError):
            return default

    serving = f('SERVING_WT', 100.0)
    if serving <= 0:
        serving = 100.0
    factor = 100.0 / serving

    name = row.get('DESC_KOR', query)
    q = query.replace(' ', '').lower()
    n = name.replace(' ', '').lower()
    score = 100 if n == q else (80 if (q in n or n in q) else 50)

    return NutritionInfo(
        name=name,
        serving_g=serving,
        calories=f('NUTR_CONT1') * factor,
        carbs_g=f('NUTR_CONT2') * factor,
        protein_g=f('NUTR_CONT3') * factor,
        fat_g=f('NUTR_CONT4') * factor,
        sugar_g=f('NUTR_CONT5') * factor,
        matched_score=score,
    )


async def calculate_meal_nutrition(
    ingredients_with_grams: list[tuple[str, float]],
) -> dict:
    """(재료명, 사용량g) 리스트 → 합산 영양 정보. 100g 기준으로 조회 후 비례 계산."""
    total = {'calories': 0.0, 'carbs_g': 0.0, 'protein_g': 0.0, 'fat_g': 0.0, 'sugar_g': 0.0}
    matched_items = []
    unmatched = []

    for name, grams in ingredients_with_grams:
        info = await fetch_nutrition(name)
        if info is None:
            unmatched.append(name)
            continue
        ratio = grams / 100.0
        total['calories'] += info.calories * ratio
        total['carbs_g'] += info.carbs_g * ratio
        total['protein_g'] += info.protein_g * ratio
        total['fat_g'] += info.fat_g * ratio
        total['sugar_g'] += info.sugar_g * ratio
        matched_items.append({'name': name, 'matched': info.name, 'grams': grams, 'score': info.matched_score})

    return {'total': total, 'matched': matched_items, 'unmatched': unmatched}
