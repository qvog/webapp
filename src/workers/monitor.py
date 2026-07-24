import time
import asyncio
import json
import websockets
import os
import re 
from datetime import datetime
from py_clob_client_v2 import OrderArgs, OrderType
from py_clob_client_v2.order_builder.constants import SELL

from src.api.client import get_clob_client, run_sync
from src.database.db import SessionLocal
from src.database.models import Position

POLY_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

async def monitor_and_manage_position(order_id: str, entry_price: float, tp_price: float, sl_price: float, original_size: float, token_id: str, options, strategy: str):
    print(f"👀 [Воркер] Наблюдаю за входом {order_id} (Стратегия: {strategy.upper()})...")
    client = get_clob_client()
    builder_code = os.getenv("BUILDER_CODE", "0x0000000000000000000000000000000000000000000000000000000000000000")
    
    actual_size = 0
    is_filled = False
    
    # ФАЗА 1: ЖДЕМ ПОКУПКУ
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
                
                db = SessionLocal()
                try:
                    pos = db.query(Position).filter(Position.order_id == order_id).first()
                    if pos: 
                        pos.status = "OPEN"
                        pos.size = actual_size 
                        db.commit()
                finally: db.close()
                break 
                
            elif status in ['CANCELED', 'EXPIRED']:
                size_matched = order_data.get('size_matched')
                if size_matched and float(size_matched) > 0:
                    actual_size = int(float(size_matched) * 100) / 100.0
                    is_filled = True
                    print(f"⚠️ [Воркер] Базовый ордер отменен, но успели купить {actual_size} акций. Идем дальше!")
                    db = SessionLocal()
                    try:
                        pos = db.query(Position).filter(Position.order_id == order_id).first()
                        if pos: 
                            pos.status = "OPEN"
                            pos.size = actual_size 
                            db.commit()
                    finally: db.close()
                    break
                else:
                    print(f"⚠️ [Воркер] Базовый ордер отменен. Отключаюсь.")
                    db = SessionLocal()
                    try:
                        pos = db.query(Position).filter(Position.order_id == order_id).first()
                        if pos: pos.status = "CANCELED"; db.commit()
                    finally: db.close()
                    return
        except Exception: pass
        await asyncio.sleep(5) 
        
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
                tp_args = OrderArgs(price=tp_price, size=actual_size, side=SELL, token_id=token_id, builder_code=builder_code)
                tp_resp = await run_sync(client.create_and_post_order, order_args=tp_args, options=options, order_type=OrderType.GTC)
                if tp_resp and tp_resp.get("success"):
                    tp_order_id = tp_resp.get('orderID')
                    print(f"✅ [Воркер] ТЕЙК-ПРОФИТ ВЫСТАВЛЕН! ID: {tp_order_id}")
                    break
            except Exception: pass
            await asyncio.sleep(2)

    # ФАЗА 3: СТОП-ЛОСС РАДАР ЧЕРЕЗ WEBSOCKET
    sl_trigger_price, sell_ratio = sl_price, 1.0 
    if strategy == 'match': sell_ratio = 0.5 
    sl_trigger_price = max(0.01, round(sl_trigger_price, 2))
    
    print(f"🛡️ [Воркер] Стоп-Лосс АКТИВЕН: {sl_trigger_price}$ (Слушаю WebSocket...)")
    os.environ["no_proxy"] = "ws-subscriptions-clob.polymarket.com"

    bids_book = {}
    asks_book = {}
    sl_confirmations = 0
    empty_book_count = 0
    last_tp_check = time.time()

    try:
        ob = await run_sync(client.get_order_book, token_id)
        for b in ob.get("bids", []): bids_book[float(b['price'])] = float(b['size'])
        for a in ob.get("asks", []): asks_book[float(a['price'])] = float(a['size'])
    except: pass

    while True: 
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
                        if time.time() - last_tp_check > 15:
                            last_tp_check = time.time()
                            if tp_order_id:
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
                            
                            try:
                                ob = await run_sync(client.get_order_book, token_id)
                                if isinstance(ob, dict) and (ob.get("bids") or ob.get("asks")):
                                    bids_book.clear()
                                    asks_book.clear()
                                    for b in ob.get("bids", []): bids_book[float(b['price'])] = float(b['size'])
                                    for a in ob.get("asks", []): asks_book[float(a['price'])] = float(a['size'])
                            except: pass
                            
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

                        if not bids_book and not asks_book:
                            empty_book_count += 1
                            if empty_book_count > 20:
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
                        
                        if spread > 0.15:
                            sl_confirmations = 0
                            continue 
                        
                        if 0 < best_bid <= sl_trigger_price:
                            sl_confirmations += 1
                            if sl_confirmations < 2:
                                continue 
                                
                            print(f"🚨 [Воркер] СТОП-ЛОСС ПРОБИТ! Цена: {best_bid}$")
                            
                            # 🎯 ФИКС: Безопасная отмена ТП через синхронную обертку
                            if tp_order_id:
                                def sync_cancel_tp():
                                    class OrderProxy:
                                        def __init__(self, _id):
                                            self.orderID, self.id = _id, _id
                                    if hasattr(client, "cancel"):
                                        try: client.cancel(tp_order_id)
                                        except AttributeError:
                                            try: client.cancel(OrderProxy(tp_order_id))
                                            except: pass
                                    elif hasattr(client, "cancel_order"):
                                        try: client.cancel_order(tp_order_id)
                                        except AttributeError:
                                            try: client.cancel_order(OrderProxy(tp_order_id))
                                            except: pass
                                await run_sync(sync_cancel_tp)
                            
                            shares_to_sell = round(actual_size * sell_ratio, 2)
                            
                            async def safe_market_sell(t_size):
                                current_size = t_size
                                for _ in range(2): 
                                    try:
                                        s_args = OrderArgs(price=0.01, size=current_size, side=SELL, token_id=token_id, builder_code=builder_code)
                                        resp = await run_sync(client.create_and_post_order, order_args=s_args, options=options, order_type=OrderType.GTC)
                                        if resp and isinstance(resp, dict) and resp.get("error"):
                                            err = resp.get("error")
                                            if "balance" in err:
                                                m = re.search(r"balance:\s*(\d+)", err)
                                                if m:
                                                    current_size = int(int(m.group(1)) / 1000000.0 * 100) / 100.0
                                                    if current_size <= 0: return None
                                                    continue 
                                        return resp
                                    except Exception as e:
                                        err = str(e)
                                        if "balance" in err:
                                            m = re.search(r"balance:\s*(\d+)", err)
                                            if m:
                                                current_size = int(int(m.group(1)) / 1000000.0 * 100) / 100.0
                                                if current_size <= 0: return None
                                                continue
                                        return None
                                return None

                            sl_resp = await safe_market_sell(shares_to_sell)
                            
                            if sl_resp and (isinstance(sl_resp, dict) and (sl_resp.get("success") or sl_resp.get("orderID") or sl_resp.get("id"))):
                                print(f"✅ [Воркер] Позиция ликвидирована.")
                                db = SessionLocal()
                                try:
                                    pos = db.query(Position).filter(Position.order_id == order_id).first()
                                    if pos:
                                        pos.status = "CLOSED_SL"
                                        pos.exit_price = best_bid
                                        db.commit()
                                finally: db.close()
                            else:
                                print(f"❌ [Воркер] Ошибка при исполнении Стоп-Лосса.")
                            return 
                        else:
                            sl_confirmations = 0

                finally:
                    ping_task.cancel()
        except Exception as e:
            await asyncio.sleep(2)