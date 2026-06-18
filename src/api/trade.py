import os
import time
import asyncio
import functools

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from eth_account import Account

from py_clob_client_v2 import ClobClient, OrderArgs, PartialCreateOrderOptions, OrderType, SignatureTypeV2, ApiCreds
from py_clob_client_v2.order_builder.constants import BUY, SELL

# 🎯 Загружаем переменные из .env файла
load_dotenv()

PROXY_URL = os.getenv("POLY_PROXY")
if PROXY_URL:
    os.environ["http_proxy"] = PROXY_URL
    os.environ["https_proxy"] = PROXY_URL
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    print(f"✅ ПРОКСИ УСПЕШНО ЗАГРУЖЕН: {PROXY_URL}") # <--- ДОБАВЬТЕ ЭТО
else:
    print("❌ ВНИМАНИЕ: ПРОКСИ НЕ НАЙДЕН В .env! Работаю с реального IP!")

pk = os.getenv("POLY_PRIVATE_KEY")
my_account = Account.from_key(pk)
print('Derived address:', my_account.address)

router = APIRouter()
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
FUNDER_ADDRESS = os.getenv("POLY_FUNDER_ADDRESS")


# ==========================================
# ОПТИМИЗАЦИЯ 1: Обертка для синхронных вызовов библиотеки
# ==========================================
async def run_sync(func, *args, **kwargs):
    """Выполняет синхронные вызовы ClobClient в фоновом пуле потоков, не блокируя сервер."""
    loop = asyncio.get_running_loop()
    pfunc = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, pfunc)


# ==========================================
# ОПТИМИЗАЦИЯ 2: Глобальный (кэшированный) клиент
# ==========================================
_clob_client = None

def get_clob_client() -> ClobClient:
    """Инициализирует клиент 1 раз при первом обращении, экономя время на SSL и память."""
    global _clob_client
    if _clob_client is None:
        if not PRIVATE_KEY or not FUNDER_ADDRESS:
            raise ValueError("Не настроены приватные ключи в .env")
        _clob_client = ClobClient(host=HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, signature_type=SignatureTypeV2.POLY_1271, funder=FUNDER_ADDRESS)
        api_creds = ApiCreds(api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_API_SECRET"), api_passphrase=os.getenv("POLY_API_PASSPHRASE"))
        _clob_client.set_api_creds(api_creds)
    return _clob_client


class TradeRequest(BaseModel):
    token_id: str
    price: float
    side: str
    bankroll: float
    risk_percent: float
    take_profit_price: Optional[float] = None
    is_custom_limit: bool = False


# ==========================================
# ОПТИМИЗАЦИЯ 3: Полностью асинхронный воркер
# ==========================================
async def monitor_and_manage_position(order_id: str, entry_price: float, tp_price: float, original_size: float, token_id: str, options, strategy: str):
    print(f"👀 [Воркер] Наблюдаю за входом {order_id} (Стратегия: {strategy.upper()})...")
    
    client = get_clob_client()
    
    # ФАЗА 1: ЖДЕМ ПОКУПКУ
    actual_size = 0
    is_filled = False
    
    for _ in range(86400):
        try:
            # Асинхронный вызов синхронного метода API
            order_info = await run_sync(client.get_order, order_id)
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
        
        await asyncio.sleep(1) # Неблокирующая пауза!
        
    if not is_filled or actual_size == 0:
        print(f"⏳ [Воркер] Истек TTL ожидания покупки. Отключаюсь.")
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
                else:
                    print(f"⚠️ [Воркер] Ошибка ТП, пробую еще раз: {tp_resp}")
            except Exception as e:
                print(f"⚠️ [Воркер] Исключение при выставлении ТП: {e}")
                
            await asyncio.sleep(1.5)

    # ФАЗА 3: СТОП-ЛОСС РАДАР (Логика сохранена на 100%)
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
    sl_confirmations = 0 # 🎯 НОВОЕ: Счетчик подтверждений для защиты от пустых стаканов

    while time.time() < end_time:
        try:
            # 1. БЕЗОПАСНАЯ Проверка Тейк-Профита
            if tp_order_id and check_tp_counter % 5 == 0:
                try:
                    tp_info = client.get_order(tp_order_id)
                    tp_data = tp_info[0] if isinstance(tp_info, list) and len(tp_info) > 0 else tp_info
                    
                    if isinstance(tp_data, dict): # 🛡️ Защита от 'NoneType'
                        if tp_data.get('status') in ['MATCHED', 'FILLED']:
                            print(f"💰 [Воркер] ТЕЙК-ПРОФИТ СРАБОТАЛ! Позиция закрыта в плюс. Успех!")
                            return 
                except Exception:
                    pass # Игнорируем глюки API Полимаркета, проверим на следующем круге
            
            # 🎯 Теперь счетчик тикает ВСЕГДА, предотвращая зависание цикла!        
            check_tp_counter += 1 

            # 2. Сканируем стакан
            ob = client.get_order_book(token_id)
            if not isinstance(ob, dict): 
                time.sleep(2)
                continue

            bids = ob.get("bids", [])
            asks = ob.get("asks", []) 
            
            if bids:
                best_bid = max([float(b['price']) for b in bids])
                best_ask = min([float(a['price']) for a in asks]) if asks else 1.0
                
                spread = best_ask - best_bid 
                
                # ТРИГГЕР СТОП-ЛОССА
                if 0 < best_bid <= sl_trigger_price:
                    
                    if spread > 0.35: 
                        print(f"⚠️ [Воркер] Игнорирую Стоп-Лосс! Аномальный спред: {spread:.2f}$. Жду возврата ликвидности...")
                        sl_confirmations = 0 # Сбрасываем счетчик при сквизе
                        time.sleep(2)
                        continue 
                        
                    # 🎯 УМНЫЙ СТОП-ЛОСС: Требуем 3 подтверждения падения цены
                    sl_confirmations += 1
                    if sl_confirmations < 3:
                        print(f"⚠️ [Воркер] Внимание! Цена ({best_bid}$) ниже стоп-лосса. Жду подтверждения {sl_confirmations}/3...")
                        time.sleep(1.5)
                        continue
                        
                    # Если мы дошли сюда, значит стакан был пуст 3 раза подряд (цена реально рухнула)
                    print(f"🚨 [Воркер] СТОП-ЛОСС ПРОБИТ И ПОДТВЕРЖДЕН! Рынок рухнул до {best_bid}$ (Триггер: {sl_trigger_price}$)")
                    
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
                    
                    return 
                    
                else:
                    # Если цена прыгнула вниз и сразу вернулась обратно (стакан пересобрался)
                    if sl_confirmations > 0:
                        print(f"✅ [Воркер] Ложная тревога. Цена вернулась в норму ({best_bid}$). Стоп-лосс отменен.")
                    sl_confirmations = 0

        except Exception as e:
            print(f"⚠️ [Воркер] Внутренняя ошибка в цикле слежения: {e}")
            
        time.sleep(2)


@router.post("/api/trade")
async def place_order(req: TradeRequest, background_tasks: BackgroundTasks):
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
        client = get_clob_client() # Переиспользуем кэшированный инстанс
        
        is_neg_risk = await run_sync(client.get_neg_risk, str(req.token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        main_args = OrderArgs(price=safe_price, size=safe_size, side=side_const, token_id=str(req.token_id))
        resp = await run_sync(client.create_and_post_order, order_args=main_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            main_order_id = resp.get('orderID')
            print(f"✅ ВХОД УСПЕШНО ОТПРАВЛЕН! ID: {main_order_id}")
            
            safe_tp_price = round(float(req.take_profit_price), 2) if req.take_profit_price else None
            
            # FastAPI умеет корректно запускать async функции как BackgroundTasks
            background_tasks.add_task(
                monitor_and_manage_position,
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
async def panic_sell_position(req: PanicRequest):
    try:
        client = get_clob_client() # Переиспользуем кэшированный инстанс
        
        order_info = await run_sync(client.get_order, req.order_id)
        order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
        
        token_id = order_data.get('asset_id') or order_data.get('token_id')
        size_to_sell = float(order_data.get('size_matched', 0))
        
        if size_to_sell == 0:
            return {"success": False, "error": "Ордер еще не исполнен или объем нулевой"}

        # 🎯 ИСПРАВЛЕНИЕ: снимаем лимитки перед ударом по рынку
        try:
            await run_sync(client.cancel_market_orders, asset_id=str(token_id))
        except AttributeError:
            await run_sync(client.cancel_all) # Фоллбэк
            
        await asyncio.sleep(1.5) 
        
        is_neg_risk = await run_sync(client.get_neg_risk, str(token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)
        sell_args = OrderArgs(price=0.01, size=size_to_sell, side=SELL, token_id=str(token_id))
        
        resp = await run_sync(client.create_and_post_order, order_args=sell_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            return {"success": True, "message": "Сброшено!"}
        else:
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}