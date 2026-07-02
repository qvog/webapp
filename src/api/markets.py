import httpx
import asyncio
from fastapi import APIRouter, Query
from datetime import datetime, timezone
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

def safe_parse(val):
    if isinstance(val, str):
        try: return json.loads(val)
        except: return []
    return val if isinstance(val, list) else []

@router.get("/markets")
async def get_markets(category: str = Query("most_traded"), subcategory: str = Query("all")):
    url = "https://gamma-api.polymarket.com/events"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    slugs_to_fetch = []
    sub = subcategory.lower()

    # 1. 🎯 ГЛОБАЛЬНЫЙ МАППИНГ ТЕГОВ
    if category == "most_traded":
        slugs_to_fetch = [None] 
        
    elif category == "crypto":
        # Таймфреймы на полимаркете часто используют тег prices или прямые слаги
        crypto_map = {
            "5 min": "5-min", "15 min": "15-min", "hourly": "hourly", 
            "4 hour": "4-hour", "daily": "daily", "weekly": "weekly", 
            "monthly": "monthly", "pre-market": "pre-market", "etf": "etf"
        }
        if sub == "all": slugs_to_fetch = ["crypto", "bitcoin", "ethereum", "solana", "prices"]
        else: slugs_to_fetch = [crypto_map.get(sub, sub.replace(" ", "-"))]
            
    elif category == "sports":
        sports_map = {
            "ucl": "soccer", "footbal": "soccer", "football": "soccer",
            "basketbal": "basketball", "formula 1": "f1"
        }
        if sub in ["all", "live", "starting soon"]: 
            slugs_to_fetch = ["sports", "soccer", "basketball", "tennis", "mma", "nfl", "baseball"]
        else: 
            slugs_to_fetch = [sports_map.get(sub, sub.replace(" ", "-"))]
            
    elif category == "esports":
        # 🎯 ИСПРАВЛЕН ТЕГ CS2 (Был csgo, стал cs2)
        esports_map = {
            "league of legend": "league-of-legends", "cs2": "cs2", 
            "rainbow six siege": "rainbow-six", "starcraft ii": "starcraft-2", 
            "mobile legends: bang bang": "mobile-legends", "honor of kings": "honor-of-kings", 
            "call of duty": "call-of-duty"
        }
        if sub in ["all", "starting soon", "live"]: 
            slugs_to_fetch = ["esports", "dota-2", "cs2", "valorant", "league-of-legends"]
        else: 
            slugs_to_fetch = [esports_map.get(sub, sub.replace(" ", "-"))]
            
    elif category == "others":
        if sub == "all": slugs_to_fetch = ["politics", "pop-culture", "business", "science"]
        else: slugs_to_fetch = [sub.replace(" ", "-")]

    raw_data = []
    
    # 2. Асинхронное скачивание
    async with httpx.AsyncClient() as client:
        tasks = []
        for slug in slugs_to_fetch:
            params = {
                "active": "true",
                "closed": "false",
                "limit": 50 if category == "most_traded" else 100,
                "order": "volume_24hr",
                "ascending": "false"
            }
            if slug: params["tag_slug"] = slug
            tasks.append(client.get(url, params=params, headers=headers, timeout=15.0))
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for resp in responses:
                if isinstance(resp, httpx.Response) and resp.status_code == 200:
                    raw_data.extend(resp.json())
        except Exception as e:
            logger.error(f"API Error: {e}")
            return []

    seen_ids = set()
    events = []
    now = datetime.now(timezone.utc)
    
    for ev in raw_data:
        ev_id = ev.get('id')
        if ev_id in seen_ids: continue
        seen_ids.add(ev_id)

        target_date_str = ev.get('endDate') or ev.get('resolutionDate') or ev.get('startDate')
        tags_lower = [t.get('label', '').lower() if isinstance(t, dict) else t.lower() for t in ev.get('tags', [])]

        is_live = 'live' in tags_lower

        if target_date_str:
            try:
                target_time = datetime.strptime(target_date_str.split('.')[0].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                target_time = target_time.replace(tzinfo=timezone.utc)
                diff_seconds = (now - target_time).total_seconds()
                
                if -7200 <= diff_seconds <= 14400 and category in ["sports", "esports"]:
                    is_live = True
                    
                if diff_seconds > 7 * 86400 and category in ["sports", "esports"]:
                    continue
            except:
                pass

        sub_markets = []
        for m in ev.get('markets', []):
            if str(m.get('closed', 'false')).lower() == 'true': continue
            
            outcomes = safe_parse(m.get('outcomes', []))
            prices = safe_parse(m.get('outcomePrices', []))
            token_ids = safe_parse(m.get('clobTokenIds', []))

            if len(outcomes) >= 2 and len(token_ids) >= 2:
                try: p_yes, p_no = float(prices[0]) if len(prices) > 0 else 0.5, float(prices[1]) if len(prices) > 1 else 0.5
                except: p_yes, p_no = 0.5, 0.5

                if p_yes >= 0.99 or p_yes <= 0.01: continue

                sub_markets.append({
                    "condition_id": str(m.get('conditionId', '')),
                    "question": m.get('question', ev.get('title', 'Unknown')),
                    "token_id_yes": str(token_ids[0]),
                    "token_id_no": str(token_ids[1]),
                    "out1": str(outcomes[0]).upper(),
                    "out2": str(outcomes[1]).upper(),
                    "price_yes": p_yes,
                    "price_no": p_no
                })

        if not sub_markets: continue

        try: total_volume = float(ev.get('volume_24hr') or ev.get('volumeNum') or ev.get('volume') or 0)
        except: total_volume = 0.0

        events.append({
            "event_id": ev.get('id'),
            "title": ev.get('title'),
            "image": ev.get('image'),
            "total_volume": total_volume,
            "start_date": target_date_str,
            "is_live": is_live,
            "sub_markets": sub_markets
        })
        
    events.sort(key=lambda x: x["total_volume"], reverse=True)
    return events[:50] if category == "most_traded" else events[:100]