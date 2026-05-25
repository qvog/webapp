import json
import asyncio
import time
from fastapi import APIRouter, Query
from curl_cffi.requests import AsyncSession
from utils import get_game_category

router = APIRouter()

@router.get("/api/markets")
async def get_markets(game: str = Query("Dota 2")):
    try:
        url = "https://gamma-api.polymarket.com/events"
        
        if game == "Dota 2":
            target_tags = ["dota-2"]
            offsets = [0, 100, 200]
        elif game == "CS2":
            target_tags = ["csgo", "counter-strike"]
            offsets = [0, 100, 200]
        elif game == "LoL":
            target_tags = ["league-of-legends"]
            offsets = [0, 100, 200]
        else: 
            target_tags = ["esports", "dota-2", "csgo", "league-of-legends"]
            offsets = [0, 100] 
        
        print(f"⏳ [РАДАР] Интеллектуальная группировка событий по категории: {game}...")
        
        events_dict = {}
        
        async with AsyncSession(impersonate="chrome110") as session:
            tasks = []
            cb = int(time.time() * 1000)
            
            for tag in target_tags:
                for offset in offsets:
                    params = {"closed": "false", "limit": 100, "tag_slug": tag, "offset": offset, "_cb": cb}
                    tasks.append(session.get(url, params=params, timeout=15))
                    
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for resp in responses:
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                    
                data = resp.json()
                for event in data:
                    event_id = event.get("id")
                    title = event.get("title", "")
                    
                    # 🎯 ВЫТАСКИВАЕМ ВРЕМЯ НАЧАЛА МАТЧА
                    start_date = event.get("startDate") or event.get("endDate") or ""
                    
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
                            "event_id": event_id,
                            "title": title,
                            "game": game_category,
                            "start_date": start_date, # Передаем дату на фронт
                            "status": "EMPTY", 
                            "total_liquidity": 0.0,
                            "sub_markets": []
                        }
                    
                    for market in markets:
                        market_id = market.get("id")
                        
                        if any(m["market_id"] == market_id for m in events_dict[event_id]["sub_markets"]): continue
                            
                        market_question = market.get("question", title)
                        
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
                            
                        target_token = clob_token_ids[0]
                        liquidity = float(market.get("liquidity", 0))
                        volume = float(market.get("volume", 0))
                        
                        outcome_prices = market.get("outcomePrices", [])
                        if isinstance(outcome_prices, str):
                            try: outcome_prices = json.loads(outcome_prices)
                            except: outcome_prices = []
                            
                        current_price = float(outcome_prices[0]) if outcome_prices and len(outcome_prices) > 0 else 0.5
                        
                        if event.get("active") and market.get("active"):
                            if current_price >= 0.95 or current_price <= 0.05: m_status = "FINISHED" 
                            elif liquidity > 0 or volume > 0: m_status = "LIVE"
                            else: m_status = "EMPTY"
                        else:
                            m_status = "UPCOMING"
                        
                        events_dict[event_id]["total_liquidity"] += liquidity
                        
                        current_ev_status = events_dict[event_id]["status"]
                        if m_status == "LIVE" or current_ev_status == "EMPTY": events_dict[event_id]["status"] = m_status
                        elif m_status == "UPCOMING" and current_ev_status == "FINISHED": events_dict[event_id]["status"] = m_status

                        events_dict[event_id]["sub_markets"].append({
                            "market_id": market_id,
                            "condition_id": target_token,
                            "question": market_question,
                            "status": m_status,
                            "liquidity": liquidity,
                            "price": current_price,
                            "out1": out1,
                            "out2": out2
                        })

        final_events = [e for e in events_dict.values() if e["sub_markets"]]
        
        # Базовая сортировка (фронтенд будет её переопределять)
        final_events.sort(key=lambda x: (
            0 if x["status"] == "LIVE" else (1 if x["status"] == "UPCOMING" else (2 if x["status"] == "FINISHED" else 3)),
            -x["total_liquidity"]
        ))
        
        return {"matches": final_events}
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return {"error": str(e)}