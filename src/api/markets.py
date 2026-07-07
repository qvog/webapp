import httpx
import asyncio
from fastapi import APIRouter, Query
from datetime import datetime, timezone
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# 🎯 IN-MEMORY БАЗА ДАННЫХ (RAM)
GLOBAL_EVENTS_DB = {}
UPDATER_TASK = None
IS_FETCHING = False

def safe_parse(val):
    if isinstance(val, str):
        try: return json.loads(val)
        except: return []
    return val if isinstance(val, list) else []

# Точный маппинг слагов
def get_slugs_for_request(category, subcategory):
    sub = subcategory.lower()
    if category == "most_traded": return [None]
    if category == "crypto":
        cmap = {"5 min": "5m", "15 min": "15m", "hourly": "1h", "4 hour": "4h", "daily": "1d", "weekly": "1w", "monthly": "1mo", "pre-market": "pre-market", "etf": "etf"}
        if sub == "all": return ["crypto", "bitcoin", "ethereum", "solana", "prices"]
        return [cmap.get(sub, sub.replace(" ", "-"))]
    if category == "sports":
        smap = {"ucl": "champions-league", "footbal": "soccer", "football": "soccer", "basketbal": "basketball", "formula 1": "f1", "hockey": "nhl", "baseball": "mlb"}
        if sub in ["all", "live", "starting soon"]: return ["sports", "soccer", "basketball", "tennis"]
        return [smap.get(sub, sub.replace(" ", "-"))]
    if category == "esports":
        emap = {"league of legend": "league-of-legends", "cs2": "cs2", "rainbow six siege": "rainbow-six", "starcraft ii": "starcraft-2", "mobile legends: bang bang": "mobile-legends", "honor of kings": "honor-of-kings", "call of duty": "call-of-duty"}
        if sub in ["all", "live", "starting soon"]: return ["esports", "dota-2", "cs2", "csgo"]
        mapped = emap.get(sub, sub.replace(" ", "-"))
        if mapped == "cs2": return ["cs2", "csgo", "counter-strike"] 
        return [mapped]
    if category == "others":
        if sub == "all": return ["politics", "pop-culture", "business", "science"]
        return [sub.replace(" ", "-")]
    return [None]

# Экстренный точечный парсер
async def fetch_specific_slugs(slugs, limit=100):
    url = "https://gamma-api.polymarket.com/events"
    headers = {"Accept": "application/json"}
    results = []
    async with httpx.AsyncClient() as client:
        tasks = []
        for slug in slugs:
            params = {"active": "true", "closed": "false", "limit": limit, "order": "volume_24hr", "ascending": "false"}
            if slug: params["tag_slug"] = slug
            tasks.append(client.get(url, params=params, headers=headers, timeout=5.0))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for resp in responses:
            if isinstance(resp, httpx.Response) and resp.status_code == 200:
                results.extend(resp.json())
    return results

# Глобальный фоновый парсер
async def fetch_pool():
    global GLOBAL_EVENTS_DB, IS_FETCHING
    if IS_FETCHING: return
    IS_FETCHING = True
    
    slugs = [
        None,
        "crypto", "bitcoin", "ethereum", "solana", "prices", "5m", "15m", "1h", "4h", "1d",
        "sports", "soccer", "basketball", "tennis", "mma", "nfl", "mlb", "nhl", "f1", "champions-league",
        "esports", "dota-2", "cs2", "csgo", "counter-strike", "valorant", "league-of-legends", "starcraft-2", "rainbow-six", "call-of-duty",
        "politics", "business"
    ]
    
    url = "https://gamma-api.polymarket.com/events"
    headers = {"Accept": "application/json"}
    
    async with httpx.AsyncClient() as client:
        tasks = []
        semaphore = asyncio.Semaphore(10)
        
        async def safe_fetch(slug):
            async with semaphore:
                for _ in range(2): 
                    try:
                        params = {"active": "true", "closed": "false", "limit": 100, "order": "volume_24hr", "ascending": "false"}
                        if slug: params["tag_slug"] = slug
                        resp = await client.get(url, params=params, headers=headers, timeout=8.0)
                        if resp.status_code == 200: return resp.json()
                    except:
                        await asyncio.sleep(0.5)
                return []

        for s in slugs: tasks.append(safe_fetch(s))
        responses = await asyncio.gather(*tasks)
        
        new_db = GLOBAL_EVENTS_DB.copy()
        added = 0
        for data in responses:
            for ev in data:
                new_db[ev['id']] = ev
                added += 1
        
        if added > 0:
            GLOBAL_EVENTS_DB = new_db
            logger.info(f"🔄 [SYNC] RAM Cache обновлен: {len(GLOBAL_EVENTS_DB)} уникальных рынков.")
            
    IS_FETCHING = False

async def background_updater():
    while True:
        await asyncio.sleep(15)
        try: await fetch_pool()
        except Exception as e: logger.error(f"❌ [SYNC ERROR] {e}")

# Функция фильтрации (вынесена отдельно, чтобы использовать дважды)
def filter_events(raw_data, category, subcategory, target_slugs):
    sub = subcategory.lower()
    events = []
    now = datetime.now(timezone.utc)
    
    crypto_tags = ["crypto", "prices", "bitcoin", "ethereum", "solana", "5m", "15m", "1h", "4h", "1d", "1w", "1mo"]
    sports_tags = ["sports", "soccer", "basketball", "tennis", "mma", "nfl", "mlb", "nhl", "f1", "champions-league"]
    esports_tags = ["esports", "dota-2", "csgo", "cs2", "counter-strike", "valorant", "league-of-legends", "starcraft-2", "rainbow-six", "call-of-duty", "mobile-legends", "honor-of-kings"]
    
    for ev in raw_data:
        target_date_str = ev.get('endDate') or ev.get('resolutionDate') or ev.get('startDate')
        tags_lower = [t.get('label', '').lower() if isinstance(t, dict) else t.lower() for t in ev.get('tags', [])]
        title_lower = ev.get('title', '').lower()

        if category == "crypto" and not any(t in tags_lower for t in crypto_tags): continue
        if category == "sports" and not any(t in tags_lower for t in sports_tags): continue
        if category == "esports" and not any(t in tags_lower for t in esports_tags): continue
        if category == "others" and not any(t in tags_lower for t in ["politics", "pop-culture", "business", "science"]): continue

        if sub not in ["all", "live", "starting soon"] and category != "most_traded":
            has_match = False
            for ts in target_slugs:
                if ts and ts in tags_lower:
                    has_match = True
                    break
            
            if not has_match:
                search_kw = sub
                aliases = {
                    "ucl": ["champions league", "champions-league"],
                    "footbal": ["football", "soccer"],
                    "football": ["soccer"],
                    "cs2": ["csgo", "counter-strike", "cs2"],
                    "league of legend": ["league of legends", "lol", "league-of-legends"],
                    "dota 2": ["dota", "dota-2"],
                    "starcraft ii": ["starcraft", "starcraft-2", "sc2"],
                    "rainbow six siege": ["rainbow six", "rainbow-six", "r6"],
                    "mobile legends: bang bang": ["mobile legends", "mobile-legends"],
                    "honor of kings": ["honor of kings", "honor-of-kings"],
                    "call of duty": ["call of duty", "call-of-duty"],
                    "formula 1": ["f1", "formula 1"]
                }
                match_words = [search_kw, search_kw.replace(" ", "-")] + aliases.get(search_kw, [])
                for word in match_words:
                    if word in title_lower or any(word in t for t in tags_lower):
                        has_match = True
                        break
                        
            if category == "crypto" and ("min" in search_kw or "hour" in search_kw):
                num = search_kw.split()[0]
                if f"{num}m" not in title_lower and f"{num} min" not in title_lower and f"{num}h" not in title_lower:
                    has_match = False

            if not has_match: continue

        is_live = 'live' in tags_lower
        if sub == "live" and category in ["sports", "esports"]:
            if not is_live: continue

        if target_date_str:
            try:
                target_time = datetime.strptime(target_date_str.split('.')[0].replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                target_time = target_time.replace(tzinfo=timezone.utc)
                diff_seconds = (target_time - now).total_seconds()
                
                if -14400 <= diff_seconds <= 7200 and category in ["sports", "esports"]:
                    is_live = True
                    
                if diff_seconds < -7 * 86400 and category in ["sports", "esports"]:
                    continue
            except:
                pass

        if sub == "live" and not is_live: continue

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
    return events


@router.get("/markets")
async def get_markets(category: str = Query("most_traded"), subcategory: str = Query("all")):
    global UPDATER_TASK, GLOBAL_EVENTS_DB
    
    if UPDATER_TASK is None:
        UPDATER_TASK = asyncio.create_task(background_updater())

    target_slugs = get_slugs_for_request(category, subcategory)

    # 1. Сначала пытаемся отфильтровать из оперативной памяти
    events = filter_events(list(GLOBAL_EVENTS_DB.values()), category, subcategory, target_slugs)

    # 2. 🚀 ЭКСТРЕННАЯ ЗАГРУЗКА: Если в памяти ничего нет (или она еще пустая)
    # МЫ НЕ ОТДАЕМ ПУСТОЙ ЭКРАН! Мы останавливаемся и качаем нужные рынки.
    if not events:
        fast_data = await fetch_specific_slugs(target_slugs, limit=100)
        
        # Добавляем экстренно скачанные данные в глобальную базу
        for ev in fast_data:
            GLOBAL_EVENTS_DB[ev['id']] = ev
            
        # Повторяем фильтрацию с новыми данными
        events = filter_events(fast_data, category, subcategory, target_slugs)

    return events[:50] if category == "most_traded" else events[:100]