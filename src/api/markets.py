import httpx
from fastapi import APIRouter, Query
from datetime import datetime, timezone
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/markets")
async def get_markets(category: str = Query("crypto"), subcategory: str = Query("all")):
    url = "https://gamma-api.polymarket.com/events"
    
    slug_map = {
        "all": category.lower(),
        "dota 2": "dota-2",
        "basketball": "basketball",
        "soccer": "soccer",
        "tennis": "tennis",
        "mma": "mma",
        "bitcoin": "bitcoin",
        "ethereum": "ethereum"
    }
    
    target_slug = slug_map.get(subcategory.lower(), category.lower())

    params = {
        "active": "true",
        "closed": "false",
        "limit": 100,
        "tag_slug": target_slug
    }
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"\n📡 [СКАНИРОВАНИЕ] Запрашиваем рынки по тегу: {target_slug.upper()}...")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=15.0)
            resp.raise_for_status() 
            data = resp.json()
            print(f"✅ [УСПЕХ] Биржа прислала {len(data)} событий по тегу '{target_slug}'.")
        except Exception as e:
            print(f"❌ [ОШИБКА API] Сбой соединения: {e}")
            return []

    events = []
    now = datetime.now(timezone.utc)
    
    for ev in data:
        is_live = False
        start_date_str = ev.get('startDate')
        
        # 🎯 УМНАЯ РАБОТА С ДАТОЙ (LIVE и удаление старья)
        if start_date_str:
            try:
                start_time = datetime.strptime(start_date_str.split('.')[0].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                start_time = start_time.replace(tzinfo=timezone.utc)
                diff_seconds = (now - start_time).total_seconds()
                
                # Если это СПОРТ и матч начался больше 7 дней назад -> СТИРАЕМ (Не выводим старье)
                if category == "sports" and diff_seconds > 7 * 86400:
                    continue
                
                # Если матч начался в пределах 48 часов (172800 секунд) -> Значит он LIVE
                if category == "sports" and 0 <= diff_seconds <= 172800:
                    is_live = True
            except:
                pass

        sub_markets = []
        for m in ev.get('markets', []):
            if str(m.get('closed', 'false')).lower() == 'true':
                continue
            
            # Распаковка массивов-строк Полимаркета
            import json
            def safe_parse(val):
                if isinstance(val, str):
                    try: return json.loads(val)
                    except: return []
                return val if isinstance(val, list) else []

            outcomes = safe_parse(m.get('outcomes', []))
            prices = safe_parse(m.get('outcomePrices', []))
            token_ids = safe_parse(m.get('clobTokenIds', []))

            if len(outcomes) >= 2 and len(token_ids) >= 2:
                try:
                    p_yes = float(prices[0]) if len(prices) > 0 else 0.5
                    p_no = float(prices[1]) if len(prices) > 1 else 0.5
                except:
                    p_yes, p_no = 0.5, 0.5

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

        raw_volume = ev.get('volumeNum') or ev.get('volume') or 0
        try: total_volume = float(raw_volume)
        except: total_volume = 0.0

        events.append({
            "event_id": ev.get('id'),
            "title": ev.get('title'),
            "image": ev.get('image'),
            "total_volume": total_volume,
            "start_date": start_date_str,
            "is_live": is_live,
            "sub_markets": sub_markets
        })
        
    events.sort(key=lambda x: x["total_volume"], reverse=True)
    return events[:100]