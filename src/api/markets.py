import json
import asyncio
import time
from fastapi import APIRouter, Query
from curl_cffi.requests import AsyncSession
from src.utils import get_game_category

router = APIRouter()

# 🎯 Глобальный кэш (Спасет от бана)
CACHE_TTL = 30 # Кэш живет 30 секунд
markets_cache = {}
last_fetch_time = {}

@router.get("/api/markets")
async def get_markets(game: str = Query("Dota 2")):
    try:
        current_time = time.time()
        # Если данные свежие - отдаем моментально из ОЗУ сервера
        if game in markets_cache and (current_time - last_fetch_time.get(game, 0)) < CACHE_TTL:
            print(f"⚡ [КЭШ] Отдаю матчи {game} из памяти (0 мс)")
            return {"matches": markets_cache[game]}

        url = "https://gamma-api.polymarket.com/events"
        
        if game == "Dota 2": target_tags = ["dota-2", "esports"]; offsets = [0, 100]
        elif game == "CS2": target_tags = ["csgo", "counter-strike", "esports"]; offsets = [0, 100]
        elif game == "LoL": target_tags = ["league-of-legends", "esports"]; offsets = [0, 100]
        else: target_tags = ["esports", "dota-2", "csgo", "league-of-legends"]; offsets = [0, 100] 
        
        print(f"\n⏳ [РАДАР] Запрос дисциплины: {game}. Качаем свежие данные...")
        events_dict = {}
        
        async with AsyncSession(impersonate="chrome110") as session:
            tasks = []
            cb = int(time.time() * 1000)
            
            for tag in target_tags:
                for offset in offsets:
                    params = {"closed": "false", "limit": 100, "tag_slug": tag, "offset": offset, "_cb": cb}
                    tasks.append(session.get(url, params=params, timeout=15))
                    
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, resp in enumerate(responses):
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                    
                data = resp.json()
                for event in data:
                    event_id = event.get("id")
                    title = event.get("title", "")
                    start_date = event.get("startDate") or ""
                    
                    tags = event.get("tags", [])
                    tag_slugs = [str(t.get("slug", "")).lower() for t in tags]
                    
                    if "dota-2" in tag_slugs: game_category = "Dota 2"
                    elif "csgo" in tag_slugs or "counter-strike" in tag_slugs: game_category = "CS2"
                    elif "league-of-legends" in tag_slugs: game_category = "LoL"
                    elif "valorant" in tag_slugs: game_category = "Valorant"
                    else: game_category = get_game_category(title)
                    
                    if game != "Все игры" and game_category != game: continue
                    if game_category == "Other Esports" and "esports" not in tag_slugs: continue
                        
                    markets = event.get("markets", [])
                    if not markets: continue
                        
                    if event_id not in events_dict:
                        events_dict[event_id] = {
                            "event_id": event_id, "title": title, "game": game_category,
                            "start_date": start_date, "status": "UPCOMING", "total_volume": 0.0, "sub_markets": []
                        }
                    
                    for market in markets:
                        if market.get("resolved") is True or market.get("closed") is True: continue
                        market_id = market.get("id")
                        if any(m["market_id"] == market_id for m in events_dict[event_id]["sub_markets"]): continue
                            
                        market_question = market.get("question", title)
                        q_low = market_question.lower()
                        
                        is_junk = any(k in q_low for k in [
                            "kill", "first blood", "handicap", "pistol", "score", 
                            "total", "duration", "knife", "overtime", "round", 
                            "quadro", "ace", "map count", "correct score"
                        ])
                        
                        if is_junk: continue 
                        
                        outcome_prices = market.get("outcomePrices", [])
                        if isinstance(outcome_prices, str):
                            try: outcome_prices = json.loads(outcome_prices)
                            except: outcome_prices = []
                            
                        current_price = float(outcome_prices[0]) if outcome_prices and len(outcome_prices) > 0 else 0.5
                        if current_price >= 0.99 or current_price <= 0.01: continue

                        raw_outcomes = market.get("outcomes", ["YES", "NO"])
                        if isinstance(raw_outcomes, str):
                            try: outcomes = json.loads(raw_outcomes)
                            except: outcomes = ["YES", "NO"]
                        else: outcomes = raw_outcomes
                            
                        out1 = outcomes[0] if len(outcomes) > 0 else "YES"
                        out2 = outcomes[1] if len(outcomes) > 1 else "NO"

                        raw_tokens = market.get("clobTokenIds", [])
                        if isinstance(raw_tokens, str):
                            try: clob_token_ids = json.loads(raw_tokens)
                            except: clob_token_ids = []
                        else: clob_token_ids = raw_tokens
                            
                        if not clob_token_ids or len(clob_token_ids) == 0: continue
                            
                        token_yes = clob_token_ids[0]
                        token_no = clob_token_ids[1] if len(clob_token_ids) > 1 else ""
                        
                        liquidity = float(market.get("liquidity") or 0.0)
                        volume = float(market.get("volume") or 0.0)
                        
                        if volume == 0.0: continue
                        
                        events_dict[event_id]["total_volume"] += volume
                        events_dict[event_id]["sub_markets"].append({
                            "market_id": market_id, "condition_id": token_yes, 
                            "token_id_yes": token_yes, "token_id_no": token_no,
                            "question": market_question, "status": "LIVE" if (liquidity > 0 or volume > 0) else "UPCOMING",
                            "volume": volume, "price": current_price,
                            "out1": out1, "out2": out2
                        })

        final_events = [e for e in events_dict.values() if len(e["sub_markets"]) > 0]
        
        # 🎯 СОХРАНЯЕМ В КЭШ
        markets_cache[game] = final_events
        last_fetch_time[game] = current_time
        
        print(f"📊 Итог сканирования: Найдено {len(final_events)} активных матчей для {game}.\n")
        return {"matches": final_events}
    except Exception as e:
        print(f"❌ Критическая ошибка парсинга: {e}")
        return {"error": str(e)}