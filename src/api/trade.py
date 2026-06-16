import os
import time
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# 🎯 Загружаем переменные из .env файла
load_dotenv()

PROXY_URL = os.getenv("POLY_PROXY")
if PROXY_URL:
    os.environ["http_proxy"] = PROXY_URL
    os.environ["https_proxy"] = PROXY_URL
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

from py_clob_client_v2 import ClobClient, OrderArgs, PartialCreateOrderOptions, OrderType, SignatureTypeV2, ApiCreds
from py_clob_client_v2.order_builder.constants import BUY, SELL

router = APIRouter()
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
FUNDER_ADDRESS = os.getenv("POLY_FUNDER_ADDRESS")

class TradeRequest(BaseModel):
    token_id: str
    price: float
    side: str
    bankroll: float
    risk_percent: float
    take_profit_price: Optional[float] = None
    is_custom_limit: bool = False

def monitor_and_manage_position(client: ClobClient, order_id: str, entry_price: float, tp_price: float, original_size: float, token_id: str, options, strategy: str):
    print(f"👀 [Воркер] Наблюдаю за входом {order_id} (Стратегия: {strategy.upper()})...")
    
    # ==========================================
    # ФАЗА 1: ЖДЕМ ПОКУПКУ
    # ==========================================
    actual_size = 0
    is_filled = False
    
    for _ in range(86400):
        try:
            order_info = client.get_order(order_id)
            order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
            status = order_data.get('status', '')
            
            if status in ['MATCHED', 'FILLED']:
                size_matched = order_data.get('size_matched')
                if size_matched and float(size_matched) > 0:
                    actual_size = int(float(size_matched) * 100) / 100.0
                else:
                    actual_size = original_size
                
                is_filled = True
                print(f"⚙️ [Воркер] Позиция набрана. Куплено: {actual_size} акций.")
                break
                
            elif status in ['CANCELED', 'EXPIRED']:
                print(f"⚠️ [Воркер] Базовый ордер отменен. Отключаюсь.")
                return
        except Exception: pass
        time.sleep(1)
        
    if not is_filled or actual_size == 0:
        print(f"⏳ [Воркер] Истек TTL ожидания покупки. Отключаюсь.")
        return

    # ==========================================
    # ФАЗА 2: ТЕЙК-ПРОФИТ
    # ==========================================
    tp_order_id = None
    if tp_price:
        for _ in range(10):
            try:
                tp_args = OrderArgs(price=tp_price, size=actual_size, side=SELL, token_id=token_id)
                tp_resp = client.create_and_post_order(order_args=tp_args, options=options, order_type=OrderType.GTC)
                
                if tp_resp and tp_resp.get("success"):
                    tp_order_id = tp_resp.get('orderID')
                    print(f"✅ [Воркер] ТЕЙК-ПРОФИТ ВЫСТАВЛЕН! ID: {tp_order_id}")
                    break
                elif "not enough balance" in str(tp_resp):
                    time.sleep(1)
            except Exception: pass

    # ==========================================
    # ФАЗА 3: СТОП-ЛОСС РАДАР
    # ==========================================
    sl_trigger_price = 0
    sell_ratio = 1.0 
    
    if strategy in ['4c', '8c']:
        sl_trigger_price = entry_price - 0.12
        sell_ratio = 1.0
    elif strategy == 'match':
        sl_trigger_price = entry_price * 0.5
        sell_ratio = 0.5 
    elif strategy == 'sure':
        sl_trigger_price = entry_price * 0.5
        sell_ratio = 1.0
        
    sl_trigger_price = max(0.01, round(sl_trigger_price, 2))
    
    print(f"🛡️ [Воркер] Стоп-Лосс АКТИВЕН: Сброс {sell_ratio*100}% при падении до {sl_trigger_price}$ и ниже.")

    end_time = time.time() + (14 * 86400)
    check_tp_counter = 0

    while time.time() < end_time:
        try:
            # 1. Проверяем, не закрылся ли Тейк-Профит
            if tp_order_id and check_tp_counter % 5 == 0:
                tp_info = client.get_order(tp_order_id)
                tp_data = tp_info[0] if isinstance(tp_info, list) and len(tp_info) > 0 else tp_info
                if tp_data.get('status') in ['MATCHED', 'FILLED']:
                    print(f"💰 [Воркер] ТЕЙК-ПРОФИТ СРАБОТАЛ! Позиция закрыта в плюс. Успех!")
                    return 
            check_tp_counter += 1

            # 2. Сканируем стакан
            # 2. Сканируем стакан
            ob = client.get_order_book(token_id)
            bids = ob.get("bids", [])
            asks = ob.get("asks", []) # 🎯 Теперь берем и продавцов тоже
            
            if bids:
                best_bid = max([float(b['price']) for b in bids])
                best_ask = min([float(a['price']) for a in asks]) if asks else 1.0
                
                spread = best_ask - best_bid # 🎯 Высчитываем ширину дыры в стакане
                
                # 🚨 ТРИГГЕР СТОП-ЛОССА С ЗАЩИТОЙ ОТ СКВИЗОВ
                if 0 < best_bid <= sl_trigger_price:
                    
                    if spread > 0.35: # 🛡️ АНТИ-СКВИЗ: Если спред больше 15 центов, это ложная тревога
                        print(f"⚠️ [Воркер] Игнорирую Стоп-Лосс! Аномальный спред: {spread:.2f}$. Жду возврата ликвидности...")
                        time.sleep(2)
                        continue # Пропускаем продажу и идем на следующий круг цикла
                        
                    print(f"🚨 [Воркер] СТОП-ЛОСС ПРОБИТ! Рынок рухнул до {best_bid}$ (Триггер: {sl_trigger_price}$)")
                    
                    # Разблокировка акций
                    if tp_order_id:
                        print(f"⚙️ [Воркер] Снимаем ловушку Тейк-Профита...")
                        try:
                            client.cancel(tp_order_id)
                        except Exception as e:
                            print(f"⚠️ Ошибка точечной отмены ({e}). Делаю полную очистку ордеров токена...")
                            client.cancel_all_orders(token_id=str(token_id))
                        time.sleep(1.5)
                    
                    # Экстренная продажа
                    shares_to_sell = round(actual_size * sell_ratio, 2)
                    print(f"🔥 [Воркер] АВАРИЙНЫЙ СБРОС ПО РЫНКУ: Кидаем {shares_to_sell} акций в стакан!")
                    
                    sell_args = OrderArgs(price=0.01, size=shares_to_sell, side=SELL, token_id=token_id)
                    sl_resp = client.create_and_post_order(order_args=sell_args, options=options, order_type=OrderType.GTC)
                    
                    if sl_resp and sl_resp.get("success"):
                        print(f"✅ [Воркер] Стоп-Лосс успешно ликвидировал позицию.")
                    else:
                        print(f"❌ [Воркер] ОШИБКА ПРИ СБРОСЕ (Ордер отклонен): {sl_resp}")
                    
                    return # Убиваем процесс, защита отработала!

        except Exception as e:
            # Больше никаких скрытых ошибок! Все выводим на экран.
            print(f"⚠️ [Воркер] Внутренняя ошибка в цикле слежения: {e}")
            
        time.sleep(2)
        
    print("⏳ [Воркер] Истек TTL (14 дней). Воркер отключен.")


@router.post("/api/trade")
def place_order(req: TradeRequest, background_tasks: BackgroundTasks):
    safe_price = round(float(req.price), 2)
    side_const = BUY if req.side.upper() == "BUY" else SELL
    
    strategy = "match"
    if req.risk_percent == 2.5: strategy = "4c"
    elif req.risk_percent == 1.5: strategy = "8c"
    elif req.risk_percent == 5.0: strategy = "match"
    elif req.risk_percent == 20.0: strategy = "sure"
    
    order_type_str = "ОТЛОЖЕННАЯ ЛИМИТКА" if req.is_custom_limit else "РЫНОЧНЫЙ ОРДЕР"
    print(f"\n🚀 Поступил {order_type_str}: {req.side} по цене {safe_price}$ (Стратегия: {strategy})")
    
    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}
        
    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    safe_size = round(actual_invest / safe_price, 2)
    
    try:
        if not PRIVATE_KEY or not FUNDER_ADDRESS:
            return {"success": False, "error": "Не настроены приватные ключи в .env"}

        client = ClobClient(host=HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, signature_type=SignatureTypeV2.POLY_1271, funder=FUNDER_ADDRESS)
        api_creds = ApiCreds(api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_API_SECRET"), api_passphrase=os.getenv("POLY_API_PASSPHRASE"))
        client.set_api_creds(api_creds)
        
        is_neg_risk = client.get_neg_risk(str(req.token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        main_args = OrderArgs(price=safe_price, size=safe_size, side=side_const, token_id=str(req.token_id))
        resp = client.create_and_post_order(order_args=main_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            main_order_id = resp.get('orderID')
            print(f"✅ ВХОД УСПЕШНО ОТПРАВЛЕН! ID: {main_order_id}")
            
            safe_tp_price = round(float(req.take_profit_price), 2) if req.take_profit_price else None
            
            background_tasks.add_task(
                monitor_and_manage_position,
                client=client, 
                order_id=main_order_id, 
                entry_price=safe_price,
                tp_price=safe_tp_price, 
                original_size=safe_size, 
                token_id=str(req.token_id), 
                options=options,
                strategy=strategy
            )
            
            return {"success": True, "order_id": main_order_id}
            
        else:
            print(f"❌ Отказ биржи: {resp}")
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        print(f"❌ Критическая ошибка торговли: {e}")
        return {"success": False, "error": str(e)}

class PanicRequest(BaseModel):
    order_id: str

@router.post("/api/panic_sell")
def panic_sell_position(req: PanicRequest):
    try:
        client = ClobClient(host=HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, signature_type=SignatureTypeV2.POLY_1271, funder=FUNDER_ADDRESS)
        api_creds = ApiCreds(api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_API_SECRET"), api_passphrase=os.getenv("POLY_API_PASSPHRASE"))
        client.set_api_creds(api_creds)
        
        order_info = client.get_order(req.order_id)
        order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
        
        token_id = order_data.get('asset_id') or order_data.get('token_id')
        size_to_sell = float(order_data.get('size_matched', 0))
        
        if size_to_sell == 0:
            return {"success": False, "error": "Ордер еще не исполнен или объем нулевой"}

        client.cancel_all_orders(token_id=str(token_id))
        time.sleep(1.5) 
        
        is_neg_risk = client.get_neg_risk(str(token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)
        sell_args = OrderArgs(price=0.01, size=size_to_sell, side=SELL, token_id=str(token_id))
        
        resp = client.create_and_post_order(order_args=sell_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            return {"success": True, "message": "Сброшено!"}
        else:
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}