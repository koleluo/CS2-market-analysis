"""Aggregate data from all providers into a SkinMarketData object."""
from __future__ import annotations

import asyncio
import logging

from src.models import PricePoint, SkinMarketData

from . import buff, csfloat, skinport, steam

log = logging.getLogger(__name__)


def _parse_name_wear(market_hash_name: str) -> tuple[str, str]:
    """Split 'AK-47 | Redline (Field-Tested)' into name + wear."""
    if "(" in market_hash_name and market_hash_name.endswith(")"):
        name_part, wear_part = market_hash_name.rsplit("(", 1)
        return name_part.strip(), wear_part.rstrip(")").strip()
    return market_hash_name, "Unknown"


async def fetch_skin(market_hash_name: str) -> SkinMarketData:
    name, wear = _parse_name_wear(market_hash_name)
    result = SkinMarketData(name=name, wear=wear, market_hash_name=market_hash_name)

    steam_price_task = steam.get_current_price(market_hash_name)
    steam_history_task = steam.get_price_history(market_hash_name)
    skinport_task = skinport.get_item(market_hash_name)
    csfloat_task = csfloat.get_listings(market_hash_name)
    buff_task = buff.get_price(market_hash_name)

    (
        (steam_price, steam_vol),
        history,
        sp_item,
        cf_listings,
        (buff_cny, buff_usd),
    ) = await asyncio.gather(
        steam_price_task,
        steam_history_task,
        skinport_task,
        csfloat_task,
        buff_task,
    )

    # Steam
    if steam_price is not None:
        result.steam_price = steam_price
        result.data_sources.append("Steam")
    if steam_vol is not None:
        result.steam_volume_24h = steam_vol
    result.steam_price_history = [
        PricePoint(timestamp=pt["timestamp"], price=pt["price"]) for pt in history
    ]

    p7d, p30d, _ = steam.derive_changes(history)
    result.price_7d_ago = p7d
    result.price_30d_ago = p30d

    # Skinport
    if sp_item:
        result.skinport_suggested_price = sp_item.get("suggested_price")
        result.skinport_avg_sale_price = sp_item.get("avg_sale_price") or sp_item.get("mean_price")
        result.data_sources.append("Skinport")

    # CSFloat
    if cf_listings:
        stats = csfloat.derive_float_stats(cf_listings)
        result.csfloat_avg_float = stats["avg_float"]
        result.csfloat_min_float = stats["min_float"]
        result.csfloat_listing_count = stats["listing_count"]
        result.csfloat_lowest_price = stats["lowest_price"]
        result.data_sources.append("CSFloat")

    # Buff
    if buff_cny is not None:
        result.buff_price_cny = buff_cny
        result.buff_price_usd = buff_usd
        result.data_sources.append("Buff163")

    log.info(
        "Fetched %s — price=$%.2f sources=%s",
        market_hash_name,
        result.steam_price or 0,
        result.data_sources,
    )
    return result
