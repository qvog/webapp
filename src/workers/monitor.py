import time
import asyncio
import json
import websockets
import os
from datetime import datetime
from py_clob_client_v2 import OrderArgs, OrderType
from py_clob_client_v2.order_builder.constants import SELL

from src.api.client import get_clob_client, run_sync
from src.database.db import SessionLocal
from src.database.models import Position

POLY_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

async def monitor_and_manage_position(order_id: str, entry_price: float, tp_price: float, original_size: float, token_id: str, options, strategy: str):
    print(f"👀 [Воркер] Наблюдаю за входом {order_id} (Стратегия: {strategy.upper()})...")
    client = get_clob_client()
    
    actual_size = 0
    is_filled = False
    
    # ФАЗА 1: ЖДЕМ ПОКУПКУ (Опрос раз в 5 секунд - бережем лимиты)
    for _ in range(86400):
        try:
            order_info = await run_sync(client.get_order, order_id)
            order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
            status = order_data.get('status', '')
            
            if status in ['MATCHED', 'FILLED']:
                size_matched = order_data.get('size_matched')
                actual_size = int(float(size_matched) * 100) / 100.0 if size_matched and float(size_matched) > 0 else original_size
                is_filled = True
                print(f"⚙️ [Воркер] Позиция набрана. Куплено: {actual_size} акций.")
                break
            elif status in ['CANCELED', 'EXPIRED']:
                print(f"⚠️ [Воркер] Базовый ордер отменен. Отключаюсь.")
                db = SessionLocal()
                try:
                    pos = db.query(Position).filter(Position.order_id == order_id).first()
                    if pos:
                        pos.status = "CANCELED"
                        db.commit()
                finally: db.close()
                return
        except Exception: pass
        await asyncio.sleep(5) # 🎯 Снизили частоту спама в 5 раз!
        
    if not is_filled or actual_size == 0:
        db = SessionLocal()
        try:
            pos = db.query(Position).filter(Position.order_id == order_id).first()
            if pos: pos.status = "EXPIRED"; db.commit()
        finally: db.close()
        return

    # ФАЗА 2: ТЕЙК-ПРОФИТ
    tp_order_id = None
    if tp_price:
        for _ in range(10):
            try:
                tp_args = OrderArgs(price=tp_price, size=actual_size, side=SELL, token_id=token_id)
                tp_resp = await run_sync(client.create_and_post_order, order_args=tp_args, options=options, order_type=OrderType.GTC)
                if tp_resp and tp_resp.get("success"):
                    tp_order_id = tp_resp.get('orderID')
                    print(f"✅ [Воркер] ТЕЙК-ПРОФИТ ВЫСТАВЛЕН! ID: {tp_order_id}")
                    break
            except Exception: pass
            await asyncio.sleep(2)

    # ФАЗА 3: СТОП-ЛОСС РАДАР ЧЕРЕЗ WEBSOCKET (0 Задержки, 0 REST-запросов)
    sl_trigger_price, sell_ratio = 0, 1.0 
    if strategy in ['4c', '8c']: sl_trigger_price = entry_price - 0.12
    elif strategy == 'match': sl_trigger_price, sell_ratio = entry_price * 0.5, 0.5 
    elif strategy == 'sure': sl_trigger_price = entry_price * 0.5
    sl_trigger_price = max(0.01, round(sl_trigger_price, 2))
    
    print(f"🛡️ [Воркер] Стоп-Лосс АКТИВЕН: {sl_trigger_price}$ (Слушаю WebSocket...)")
    os.environ["no_proxy"] = "ws-subscriptions-clob.polymarket.com"

    bids_book = {}
    asks_book = {}
    sl_confirmations = 0
    empty_book_count = 0
    last_tp_check = time.time()

    # Сначала делаем ОДИН снимок стакана, чтобы заполнить данные
    try:
        ob = await run_sync(client.get_order_book, token_id)
        for b in ob.get("bids", []): bids_book[float(b['price'])] = float(b['size'])
        for a in ob.get("asks", []): asks_book[float(a['price'])] = float(a['size'])
    except: pass

    # Подключаемся к WebSocket для получения тиков
    while True: # Внешний цикл для реконнектов
        try:
            async with websockets.connect(POLY_WS_URL, ping_interval=None) as ws:
                await ws.send(json.dumps({"assets_ids": [token_id], "type": "market"}))
                
                async def ping_loop():
                    while True:
                        await asyncio.sleep(10)
                        try: await ws.send("PING")
                        except: break

                ping_task = asyncio.create_task(ping_loop())

                try:
                    while True:
                        # 1. Редкая проверка Тейк-Профита (раз в 15 секунд)
                        if tp_order_id and (time.time() - last_tp_check > 15):
                            last_tp_check = time.time()
                            try:
                                tp_info = await run_sync(client.get_order, tp_order_id)
                                tp_data = tp_info[0] if isinstance(tp_info, list) and len(tp_info) > 0 else tp_info
                                if isinstance(tp_data, dict):
                                    status = tp_data.get('status')
                                    if status in ['MATCHED', 'FILLED']:
                                        print(f"💰 [Воркер] ТЕЙК-ПРОФИТ СРАБОТАЛ!")
                                        db = SessionLocal()
                                        try:
                                            pos = db.query(Position).filter(Position.order_id == order_id).first()
                                            if pos:
                                                pos.status = "CLOSED_TP"
                                                pos.exit_price = float(tp_data.get('price', pos.tp_price))
                                                db.commit()
                                        finally: db.close()
                                        return 
                                    elif status in ['CANCELED', 'EXPIRED']:
                                        print(f"🏁 [Воркер] ТП отменен биржей. Матч завершен!")
                                        db = SessionLocal()
                                        try:
                                            pos = db.query(Position).filter(Position.order_id == order_id).first()
                                            if pos: pos.status = "RESOLVED"; pos.exit_price = 1.0; db.commit()
                                        finally: db.close()
                                        return
                            except: pass

                        # 2. Ловим цены из WebSocket
                        msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        if msg == "PONG": continue
                        
                        data = json.loads(msg)
                        events = data if isinstance(data, list) else [data]

                        for ev in events:
                            if ev.get("asset_id") and ev.get("asset_id") != token_id: continue
                            
                            if ev.get("event_type") == "book":
                                bids_book.clear(); asks_book.clear()
                                for b in ev.get("bids", []): bids_book[float(b['price'])] = float(b['size'])
                                for a in ev.get("asks", []): asks_book[float(a['price'])] = float(a['size'])
                            
                            elif ev.get("event_type") == "price_change":
                                changes = ev.get("changes", [])
                                if not changes:
                                    for b in ev.get("bids", []):
                                        p, s = float(b["price"]), float(b["size"])
                                        if s == 0: bids_book.pop(p, None)
                                        else: bids_book[p] = s
                                    for a in ev.get("asks", []):
                                        p, s = float(a["price"]), float(a["size"])
                                        if s == 0: asks_book.pop(p, None)
                                        else: asks_book[p] = s
                                else:
                                    for ch in changes:
                                        p, s = float(ch["price"]), float(ch["size"])
                                        side = ch.get("side")
                                        if side == "BUY":
                                            if s == 0: bids_book.pop(p, None)
                                            else: bids_book[p] = s
                                        elif side == "SELL":
                                            if s == 0: asks_book.pop(p, None)
                                            else: asks_book[p] = s

                        # 3. Логика Стоп-Лосса (Только если стакан живой)
                        if not bids_book and not asks_book:
                            empty_book_count += 1
                            if empty_book_count > 20: # 20 тиков тишины = Матч завершен
                                print(f"🏁 [Воркер] Стакан пуст. Матч завершен!")
                                db = SessionLocal()
                                try:
                                    pos = db.query(Position).filter(Position.order_id == order_id).first()
                                    if pos: pos.status = "RESOLVED"; pos.exit_price = 1.0; db.commit()
                                finally: db.close()
                                return
                            continue
                        else:
                            empty_book_count = 0

                        best_bid = max(bids_book.keys()) if bids_book else 0
                        best_ask = min(asks_book.keys()) if asks_book else 1
                        spread = best_ask - best_bid 
                        
                        # Защита от сквизов (Игнорируем пустые стаканы ММ)
                        if spread > 0.08:
                            sl_confirmations = 0
                            continue 
                        
                        if 0 < best_bid <= sl_trigger_price:
                            sl_confirmations += 1
                            if sl_confirmations < 4:
                                continue # Ждем подтверждения
                                
                            print(f"🚨 [Воркер] СТОП-ЛОСС ПРОБИТ! Цена: {best_bid}$")
                            if tp_order_id:
                                try: await run_sync(client.cancel_orders, [tp_order_id])
                                except: pass
                            
                            shares_to_sell = round(actual_size * sell_ratio, 2)
                            sell_args = OrderArgs(price=0.01, size=shares_to_sell, side=SELL, token_id=token_id)
                            sl_resp = await run_sync(client.create_and_post_order, order_args=sell_args, options=options, order_type=OrderType.GTC)
                            
                            if sl_resp and sl_resp.get("success"):
                                print(f"✅ [Воркер] Позиция ликвидирована.")
                                db = SessionLocal()
                                try:
                                    pos = db.query(Position).filter(Position.order_id == order_id).first()
                                    if pos:
                                        pos.status = "CLOSED_SL"
                                        pos.exit_price = best_bid
                                        db.commit()
                                finally: db.close()
                            return 
                        else:
                            sl_confirmations = 0

                finally:
                    ping_task.cancel()
        except Exception as e:
            # Если вебсокет порвался, тихо спим 2 секунды и цикл while True подключит его заново
            await asyncio.sleep(2)