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
async def get_markets(category: str = Query("crypto"), subcategory: str = Query("all")):
    url = "https://gamma-api.polymarket.com/events"
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # 1. Формируем пул тегов. Polymarket требует точных slugs.
    slugs_to_fetch = []
    sports_slugs = ["dota-2", "basketball", "soccer", "tennis", "mma", "esports", "csgo"]
    crypto_slugs = ["bitcoin", "ethereum", "crypto", "memecoin"]
    
    if category == "sports":
        if subcategory == "all": slugs_to_fetch = sports_slugs
        else: slugs_to_fetch = [subcategory.replace(" ", "-").lower()]
    elif category == "crypto":
        if subcategory == "all": slugs_to_fetch = crypto_slugs
        else: slugs_to_fetch = [subcategory.lower()]
    elif category == "live":
        slugs_to_fetch = sports_slugs # Для LIVE сканируем весь спорт

    raw_data = []
    
    # 2. Асинхронно скачиваем топ-ликвидность по нужным категориям
    async with httpx.AsyncClient() as client:
        tasks = []
        for slug in slugs_to_fetch:
            params = {
                "active": "true",
                "closed": "false",
                "limit": 100,
                "tag_slug": slug,
                "order": "volume_24hr", # Берем только то, что активно торгуется
                "ascending": "false"
            }
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
        if ev_id in seen_ids:
            continue
        seen_ids.add(ev_id)

        # 3. 🎯 ФАКТИЧЕСКАЯ ДАТА МАТЧА (Используем endDate, а не дату создания)
        target_date_str = ev.get('endDate') or ev.get('resolutionDate') or ev.get('startDate')
        
        tags_lower = []
        for t in ev.get('tags', []):
            if isinstance(t, dict): tags_lower.append(t.get('label', '').lower())
            elif isinstance(t, str): tags_lower.append(t.lower())

        # 4. 🎯 СТРОГАЯ ФИЛЬТРАЦИЯ (Защита от грязных API Полимаркета)
        # Если мы в Dota 2, а Полимаркет прислал Теннис - убиваем этот матч
        if subcategory != "all" and category != "live":
            search_kw = subcategory.lower()
            title_lower = ev.get('title', '').lower()
            has_match = search_kw in title_lower
            if not has_match:
                for t in tags_lower:
                    if search_kw in t or t in search_kw:
                        has_match = True
            if not has_match:
                continue # Полная очистка мусора

        # 5. 🎯 УМНЫЙ СТАТУС LIVE
        is_live = False
        if 'live' in tags_lower:
            is_live = True

        if target_date_str:
            try:
                target_time = datetime.strptime(target_date_str.split('.')[0].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                target_time = target_time.replace(tzinfo=timezone.utc)
                diff_seconds = (now - target_time).total_seconds()
                
                # Если матч фактически начался (в пределах от -2 часов до +4 часов от текущего момента)
                if -7200 <= diff_seconds <= 14400 and category in ["sports", "live"]:
                    is_live = True
                    
                # Убираем старье: если фактическая дата матча прошла более 7 дней назад
                if diff_seconds > 7 * 86400:
                    continue
            except:
                pass
        
        # Если открыта вкладка LIVE - отсекаем всё, что не идет прямо сейчас
        if category == "live" and not is_live:
            continue

        sub_markets = []
        for m in ev.get('markets', []):
            if str(m.get('closed', 'false')).lower() == 'true':
                continue
            
            outcomes = safe_parse(m.get('outcomes', []))
            prices = safe_parse(m.get('outcomePrices', []))
            token_ids = safe_parse(m.get('clobTokenIds', []))

            if len(outcomes) >= 2 and len(token_ids) >= 2:
                try:
                    p_yes = float(prices[0]) if len(prices) > 0 else 0.5
                    p_no = float(prices[1]) if len(prices) > 1 else 0.5
                except:
                    p_yes, p_no = 0.5, 0.5

                # 6. 🎯 УБИРАЕМ "МЕРТВЫЕ" ИСХОДЫ (Где матч уже 100% сыгран и нет волатильности)
                if p_yes >= 0.99 or p_yes <= 0.01:
                    continue

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

        if not sub_markets:
            continue

        raw_volume = ev.get('volume_24hr') or ev.get('volumeNum') or ev.get('volume') or 0
        try: total_volume = float(raw_volume)
        except: total_volume = 0.0

        events.append({
            "event_id": ev.get('id'),
            "title": ev.get('title'),
            "image": ev.get('image'),
            "total_volume": total_volume,
            "start_date": target_date_str, # Отправляем фактическую дату на фронтенд!
            "is_live": is_live,
            "sub_markets": sub_markets
        })
        
    events.sort(key=lambda x: x["total_volume"], reverse=True)
    return events[:100]