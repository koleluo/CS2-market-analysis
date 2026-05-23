"""Skinport API adapter.

Public endpoint: https://api.skinport.com/v1/items
Rate limit: 10 requests/minute (no API key required for read-only endpoints).
"""
from __future__ import annotations

import logging
import os
import urllib.parse

import httpx

from . import cache

log = logging.getLogger(__name__)

BASE = "https://api.skinport.com/v1"
APP_ID = os.getenv("STEAM_APP_ID", "730")

HEADERS = {
    "User-Agent": "CS2SkinTracker/1.0",
    "Accept": "application/json",
}

_api_key = os.getenv("SKINPORT_API_KEY", "")


def _auth_headers() -> dict:
    if _api_key:
        return {**HEADERS, "Authorization": f"Basic {_api_key}"}
    return HEADERS


async def get_item(market_hash_name: str) -> dict | None:
    """Return Skinport item data (suggested_price, avg_sale_price, etc.)."""
    cache_key = f"skinport_item_{market_hash_name}"
    cached = cache.get(cache_key)
    if cached is not None:
        log.debug("skinport cache hit: %s", market_hash_name)
        return cached

    encoded = urllib.parse.quote(market_hash_name)
    url = f"{BASE}/items?app_id={APP_ID}&currency=USD&market_hash_name={encoded}"
    try:
        async with httpx.AsyncClient(headers=_auth_headers(), timeout=15) as client:
            r = await client.get(url)
            r.raise_for_status()
            items: list = r.json()
            if not items:
                return None
            item = items[0]
            cache.set(cache_key, item)
            return item
    except Exception as exc:
        log.error("Skinport error for %s: %s", market_hash_name, exc)
        return None


async def get_suggested_price(market_hash_name: str) -> float | None:
    item = await get_item(market_hash_name)
    if not item:
        return None
    return item.get("suggested_price")


async def get_avg_sale_price(market_hash_name: str) -> float | None:
    item = await get_item(market_hash_name)
    if not item:
        return None
    return item.get("avg_sale_price") or item.get("mean_price")
