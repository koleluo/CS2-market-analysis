"""CSFloat API adapter.

Public listing endpoint doesn't require an API key for basic queries.
With CSFLOAT_API_KEY set, rate limits are relaxed significantly.
"""
from __future__ import annotations

import logging
import os
import urllib.parse

import httpx

from . import cache

log = logging.getLogger(__name__)

BASE = "https://csfloat.com/api/v1"
_api_key = os.getenv("CSFLOAT_API_KEY", "")

HEADERS = {
    "User-Agent": "CS2SkinTracker/1.0",
    "Accept": "application/json",
}


def _auth_headers() -> dict:
    if _api_key:
        return {**HEADERS, "Authorization": _api_key}
    return HEADERS


async def get_listings(market_hash_name: str, limit: int = 50) -> list[dict]:
    """Return current active listings for the skin."""
    cache_key = f"csfloat_listings_{market_hash_name}"
    cached = cache.get(cache_key)
    if cached is not None:
        log.debug("csfloat cache hit: %s", market_hash_name)
        return cached

    encoded = urllib.parse.quote(market_hash_name)
    url = f"{BASE}/listings?market_hash_name={encoded}&limit={limit}&sort_by=lowest_price"
    try:
        async with httpx.AsyncClient(headers=_auth_headers(), timeout=15) as client:
            r = await client.get(url)
            if r.status_code == 429:
                log.warning("CSFloat rate-limited for %s", market_hash_name)
                return []
            r.raise_for_status()
            data = r.json()
            listings = data.get("data", []) if isinstance(data, dict) else data
            cache.set(cache_key, listings)
            return listings
    except Exception as exc:
        log.error("CSFloat listings error for %s: %s", market_hash_name, exc)
        return []


def derive_float_stats(listings: list[dict]) -> dict:
    """Compute avg/min float and listing count from raw listings."""
    floats = []
    prices = []
    for item in listings:
        item_info = item.get("item", {})
        f = item_info.get("float_value")
        p = item.get("price")
        if f is not None:
            floats.append(float(f))
        if p is not None:
            prices.append(float(p) / 100)  # CSFloat prices in cents

    return {
        "listing_count": len(listings),
        "avg_float": round(sum(floats) / len(floats), 6) if floats else None,
        "min_float": round(min(floats), 6) if floats else None,
        "lowest_price": min(prices) if prices else None,
    }
