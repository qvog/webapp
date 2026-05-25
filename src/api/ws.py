from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from curl_cffi.requests import AsyncSession
import asyncio
import time # Добавили импорт времени

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
                # 🎯 СРЫВАЕМ КЭШ КАЖДЫЙ ЗАПРОС
                req_url = f"{url}&_cb={int(time.time()*1000)}"
                resp = await session.get(req_url, timeout=5)
                
                if resp.status_code == 200:
                    error_logged = False
                    data = resp.json()
                    bids = data.get("bids", [])
                    asks = data.get("asks", [])
                    
                    best_bid = max([float(b['price']) for b in bids]) if bids else 0
                    best_ask = min([float(a['price']) for a in asks]) if asks else 0
                    
                    await websocket.send_json({
                        "type": "orderbook_update",
                        "bid": best_bid,
                        "ask": best_ask
                    })
                    print(f"📊 Живые цены -> Bid: {best_bid} | Ask: {best_ask}")
                    
                elif resp.status_code == 404:
                    if not error_logged:
                        print("⚠️ Стакан пуст (HTTP 404).")
                        error_logged = True
                    await websocket.send_json({"type": "orderbook_update", "bid": 0, "ask": 0})
                        
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        print("❌ [БЭКЕНД] Трейдер закрыл терминал")
    except Exception as e:
        pass