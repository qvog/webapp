import time
import asyncio
from datetime import datetime
from py_clob_client_v2 import OrderArgs, OrderType
from py_clob_client_v2.order_builder.constants import SELL

# Импортируем нашего клиента и БД
from src.api.client import get_clob_client, run_sync
from src.database.db import SessionLocal
from src.database.models import Position

async def monitor_and_manage_position(order_id: str, entry_price: float, tp_price: float, original_size: float, token_id: str, options, strategy: str):
    print(f"👀 [Воркер] Наблюдаю за входом {order_id} (Стратегия: {strategy.upper()})...")
    client = get_clob_client()
    
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
                break
            elif status in ['CANCELED', 'EXPIRED']:
                print(f"⚠️ [Воркер] Базовый ордер отменен. Отключаюсь.")
                return
        except Exception: pass
        await asyncio.sleep(1)
        
    if not is_filled or actual_size == 0:
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
            except Exception as e: print(f"⚠️ [Воркер] Исключение ТП: {e}")
            await asyncio.sleep(1.5)

    # ФАЗА 3: СТОП-ЛОСС РАДАР
    sl_trigger_price, sell_ratio = 0, 1.0 
    if strategy in ['4c', '8c']: sl_trigger_price = entry_price - 0.12
    elif strategy == 'match': sl_trigger_price, sell_ratio = entry_price * 0.5, 0.5 
    elif strategy == 'sure': sl_trigger_price = entry_price * 0.5
    sl_trigger_price = max(0.01, round(sl_trigger_price, 2))
    
    print(f"🛡️ [Воркер] Стоп-Лосс АКТИВЕН: Триггер {sl_trigger_price}$")

    end_time = time.time() + (14 * 86400)
    check_tp_counter, sl_confirmations = 0, 0

    while time.time() < end_time:
        try:
            # 1. Проверка Тейк-Профита
            if tp_order_id and check_tp_counter % 5 == 0:
                try:
                    tp_info = await run_sync(client.get_order, tp_order_id)
                    tp_data = tp_info[0] if isinstance(tp_info, list) and len(tp_info) > 0 else tp_info
                    if isinstance(tp_data, dict) and tp_data.get('status') in ['MATCHED', 'FILLED']:
                        print(f"💰 [Воркер] ТЕЙК-ПРОФИТ СРАБОТАЛ!")
                        db = SessionLocal()
                        try:
                            pos = db.query(Position).filter(Position.order_id == order_id).first()
                            if pos:
                                pos.status = "CLOSED_TP"
                                pos.updated_at = datetime.utcnow()
                                db.commit()
                        finally: db.close()
                        return 
                except Exception: pass
            check_tp_counter += 1 

            # 2. Проверка стакана (Стоп-Лосс)
            ob = await run_sync(client.get_order_book, token_id)
            if not isinstance(ob, dict): 
                await asyncio.sleep(2)
                continue

            bids, asks = ob.get("bids", []), ob.get("asks", []) 
            if bids:
                best_bid = max([float(b['price']) for b in bids])
                best_ask = min([float(a['price']) for a in asks]) if asks else 1.0
                spread = best_ask - best_bid 
                
                if 0 < best_bid <= sl_trigger_price:
                    if spread > 0.35: 
                        sl_confirmations = 0
                        await asyncio.sleep(2)
                        continue 
                        
                    sl_confirmations += 1
                    if sl_confirmations < 3:
                        await asyncio.sleep(1.5)
                        continue
                        
                    print(f"🚨 [Воркер] СТОП-ЛОСС ПРОБИТ! Цена: {best_bid}$")
                    
                    if tp_order_id:
                        try: await run_sync(client.cancel_orders, [tp_order_id])
                        except: 
                            try: await run_sync(client.cancel_market_orders, asset_id=str(token_id))
                            except: await run_sync(client.cancel_all)
                        await asyncio.sleep(1.5)
                    
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
                                pos.updated_at = datetime.utcnow()
                                db.commit()
                        finally: db.close()
                    return 
                else:
                    sl_confirmations = 0

        except Exception as e: print(f"⚠️ [Воркер] Ошибка в цикле: {e}")
        await asyncio.sleep(2)