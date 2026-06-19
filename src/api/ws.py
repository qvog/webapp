from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import websockets
import os

# Исключаем домен вебсокета из глобального прокси
os.environ["no_proxy"] = "ws-subscriptions-clob.polymarket.com"
os.environ["NO_PROXY"] = "ws-subscriptions-clob.polymarket.com"

router = APIRouter()
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

@router.websocket("/ws/market/{token_id}")
async def websocket_endpoint(websocket: WebSocket, token_id: str):
    await websocket.accept()
    
    # 🎯 ИСПРАВЛЕНИЕ 1: Сразу приводим токен от фронтенда к нижнему регистру
    clean_token = token_id.strip().strip('"').strip("'").lower()
    print(f"\n🔌 [БЭКЕНД] Открываем WS канал с Polymarket для: {clean_token[:12]}...")
    
    while True:
        bids_book = {}
        asks_book = {}
        
        try:
            async with websockets.connect(POLYMARKET_WS_URL, ping_interval=None) as poly_ws:
                subscribe_msg = {
                    "assets_ids": [clean_token],
                    "type": "market"
                }
                await poly_ws.send(json.dumps(subscribe_msg))
                
                async def send_pings():
                    while True:
                        await asyncio.sleep(10)
                        try:
                            await poly_ws.send("PING")
                        except:
                            break
                            
                ping_task = asyncio.create_task(send_pings())
                
                try:
                    while True:
                        message = await asyncio.wait_for(poly_ws.recv(), timeout=30.0)
                        
                        if message == "PONG":
                            continue
                            
                        data = json.loads(message)
                        events = data if isinstance(data, list) else [data]
                        updated = False
                        
                        for event in events:
                            # 🎯 ИСПРАВЛЕНИЕ 2: Приводим токен биржи к нижнему регистру для безопасного сравнения
                            event_asset_id = event.get("asset_id", "").lower()
                            if event_asset_id and event_asset_id != clean_token:
                                continue
                                
                            event_type = event.get("event_type")
                            
                            # 1. Полный снимок стакана
                            if event_type == "book":
                                bids_book.clear()
                                asks_book.clear()
                                for b in event.get("bids", []):
                                    bids_book[float(b["price"])] = float(b["size"])
                                for a in event.get("asks", []):
                                    asks_book[float(a["price"])] = float(a["size"])
                                updated = True
                                    
                            # 2. Дельты (изменения)
                            elif event_type == "price_change":
                                
                                # 🎯 ИСПРАВЛЕНИЕ 3: Поддержка обоих форматов API Полимаркета
                                b_changes = event.get("bids", [])
                                a_changes = event.get("asks", [])
                                
                                if "changes" in event:
                                    for ch in event["changes"]:
                                        if ch.get("side", "").upper() == "BUY": b_changes.append(ch)
                                        else: a_changes.append(ch)

                                for b in b_changes:
                                    try:
                                        p, s = float(b["price"]), float(b["size"])
                                        if s == 0: bids_book.pop(p, None)
                                        else: bids_book[p] = s
                                    except: pass

                                for a in a_changes:
                                    try:
                                        p, s = float(a["price"]), float(a["size"])
                                        if s == 0: asks_book.pop(p, None)
                                        else: asks_book[p] = s
                                    except: pass
                                    
                                updated = True
                                
                        # 3. Пушим новые цены на фронтенд
                        if updated:
                            best_bid, best_bid_size = 0, 0
                            if bids_book:
                                best_bid = max(bids_book.keys())
                                best_bid_size = bids_book[best_bid]
                                
                            best_ask, best_ask_size = 0, 0
                            if asks_book:
                                best_ask = min(asks_book.keys())
                                best_ask_size = asks_book[best_ask]
                                
                            if best_bid > 0 and best_ask > 0 and best_bid >= best_ask:
                                print(f"⚠️ [СЕТЬ] Скрещенный стакан (Bid {best_bid} >= Ask {best_ask}). Запрашиваю новый снимок...")
                                raise ValueError("Crossed book anomaly")
                            
                            await websocket.send_json({
                                "type": "orderbook_update",
                                "bid": best_bid,
                                "ask": best_ask,
                                "bid_size": best_bid_size,
                                "ask_size": best_ask_size
                            })
                            
                finally:
                    ping_task.cancel() 
                    
        except WebSocketDisconnect:
            print("❌ [БЭКЕНД] Трейдер закрыл окно терминала")
            return 
            
        except asyncio.TimeoutError:
            print("⚠️ [СЕТЬ] Polymarket WS завис (тишина 30 сек). Незаметный реконнект...")
            await asyncio.sleep(1)
            
        except Exception as e:
            await asyncio.sleep(1)