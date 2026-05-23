"""Buff163 adapter.

Buff163 has no public API and requires login cookies for most endpoints.
This adapter makes a best-effort attempt against their public goods search.
If the request fails (common without cookies), it returns None gracefully.

Set BUFF_COOKIE env var to a valid session cookie string to enable Buff data.
"""
from __future__ import annotations

import logging
import os
import urllib.parse

import httpx

from . import cache

log = logging.getLogger(__name__)

BASE = "https://buff.163.com"
_cookie = os.getenv("BUFF_COOKIE", "")

# Approximate CNY→USD rate; update via BUFF_CNY_RATE env var if needed
CNY_RATE = float(os.getenv("BUFF_CNY_RATE", "0.138"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://buff.163.com/market/",
}


async def get_price(market_hash_name: str) -> tuple[float | None, float | None]:
    """Return (price_cny, price_usd) or (None, None) if unavailable."""
    if not _cookie:
        log.debug("BUFF_COOKIE not set — skipping Buff data")
        return None, None

    cache_key = f"buff_price_{market_hash_name}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached.get("cny"), cached.get("usd")

    encoded = urllib.parse.quote(market_hash_name)
    url = f"{BASE}/api/market/goods?game=csgo&search={encoded}&page_num=1&page_size=5"
    headers = {**HEADERS, "Cookie": _cookie}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            items = data.get("data", {}).get("items", [])
            if not items:
                return None, None

            # Find the best match by name
            match = next(
                (i for i in items if i.get("market_hash_name", "").lower() == market_hash_name.lower()),
                items[0],
            )
            sell_min = match.get("sell_min_price")
            if sell_min is None:
                return None, None

            cny = float(sell_min)
            usd = round(cny * CNY_RATE, 2)
            cache.set(cache_key, {"cny": cny, "usd": usd})
            return cny, usd
    except Exception as exc:
        log.debug("Buff error for %s: %s", market_hash_name, exc)
        return None, None
