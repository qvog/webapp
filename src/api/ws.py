from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from curl_cffi.requests import AsyncSession
import asyncio
import time 

router = APIRouter()

@router.websocket("/ws/market/{token_id}")
async def websocket_endpoint(websocket: WebSocket, token_id: str):
    await websocket.accept()
    
    clean_token = token_id.strip().strip('"').strip("'")
    print(f"\n🔌 [БЭКЕНД] Фронтенд затребовал стакан: {clean_token[:12]}...")
    
    url = f"https://clob.polymarket.com/book?token_id={clean_token}"
    
    try:
        async with AsyncSession(impersonate="chrome110") as session:
            error_logged = False
            
            while True:
                try: # 🎯 НОВОЕ: Внутренний try-except для защиты цикла
                    # СРЫВАЕМ КЭШ КАЖДЫЙ ЗАПРОС
                    req_url = f"{url}&_cb={int(time.time()*1000)}"
                    resp = await session.get(req_url, timeout=5)
                    
                    if resp.status_code == 200:
                        error_logged = False
                        data = resp.json()
                        bids = data.get("bids", [])
                        asks = data.get("asks", [])
                        
                        best_bid, best_bid_size = 0, 0
                        if bids:
                            best_bid_obj = max(bids, key=lambda x: float(x['price']))
                            best_bid = float(best_bid_obj['price'])
                            best_bid_size = float(best_bid_obj['size'])
                            
                        best_ask, best_ask_size = 0, 0
                        if asks:
                            best_ask_obj = min(asks, key=lambda x: float(x['price']))
                            best_ask = float(best_ask_obj['price'])
                            best_ask_size = float(best_ask_obj['size'])
                        
                        await websocket.send_json({
                            "type": "orderbook_update",
                            "bid": best_bid,
                            "ask": best_ask,
                            "bid_size": best_bid_size,
                            "ask_size": best_ask_size
                        })
                        print(f"📊 Живые цены -> Bid: {best_bid} (Vol: {best_bid_size}) | Ask: {best_ask} (Vol: {best_ask_size})")
                        
                    elif resp.status_code == 404:
                        if not error_logged:
                            print("⚠️ Стакан пуст (HTTP 404).")
                            error_logged = True
                        await websocket.send_json({
                            "type": "orderbook_update", 
                            "bid": 0, "ask": 0,
                            "bid_size": 0, "ask_size": 0
                        })
                        
                except Exception as inner_e:
                    # 🎯 НОВОЕ: Если прокси упал, пишем лог, спим 2 сек и идем на новый круг!
                    print(f"⚠️ [СЕТЬ] Ошибка получения стакана WS (таймаут/прокси). Ждем восстановления...")
                    await asyncio.sleep(2)
                    continue 
                    
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        print("❌ [БЭКЕНД] Трейдер закрыл терминал")
    except Exception as e:
        print(f"❌ [БЭКЕНД] Фатальная ошибка WS: {e}")