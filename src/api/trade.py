import os
import time
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

# 🎯 Настройка прокси
PROXY_URL = "http://kAgPCqba:8pQt1Xa3@154.205.28.53:64082"
os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL

from py_clob_client_v2 import ClobClient, OrderArgs, PartialCreateOrderOptions, OrderType, SignatureTypeV2, ApiCreds
from py_clob_client_v2.order_builder.constants import BUY, SELL

router = APIRouter()
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

PRIVATE_KEY = "0xf6476e75f08e30ae522bf620df9c510fd2d51ddca943dba818fd447d46424d87" 
FUNDER_ADDRESS = "0x16c2349c55b3d8403fab3c66e260dc0d33688a72" 

class TradeRequest(BaseModel):
    token_id: str
    price: float
    side: str
    bankroll: float
    risk_percent: float
    take_profit_price: Optional[float] = None
    is_custom_limit: bool = False

# 🕵️‍♂️ Умный Воркер (С защитой от проблемы пыли / Dust Issue)
def monitor_and_place_tp(client: ClobClient, order_id: str, tp_price: float, original_size: float, token_id: str, options):
    print(f"👀 [Воркер] Наблюдаю за ордером {order_id} (Жду исполнения)...")
    
    for _ in range(86400):
        try:
            order_info = client.get_order(order_id)
            order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
            status = order_data.get('status', '')
            
            if status in ['MATCHED', 'FILLED']:
                # 🎯 ЛЕЧИМ ОШИБКУ БАЛАНСА: Берем реально купленный объем
                size_matched = order_data.get('size_matched')
                
                if size_matched and float(size_matched) > 0:
                    # Округляем СТРОГО ВНИЗ до 2 знаков (например 9.081554 -> 9.08)
                    actual_size = int(float(size_matched) * 100) / 100.0
                else:
                    actual_size = original_size
                    
                print(f"⚙️ [Воркер] Фактически куплено акций: {actual_size}. Отправляю Тейк-Профит...")
                
                tp_args = OrderArgs(price=tp_price, size=actual_size, side=SELL, token_id=token_id)
                tp_resp = client.create_and_post_order(order_args=tp_args, options=options, order_type=OrderType.GTC)
                
                if tp_resp and tp_resp.get("success"):
                    print(f"✅ [Воркер] ТЕЙК-ПРОФИТ {tp_price}$ УСПЕШНО ВЫСТАВЛЕН НА {actual_size} АКЦИЙ! ID: {tp_resp.get('orderID')}")
                    break
                else:
                    error_msg = str(tp_resp)
                    if "not enough balance" in error_msg:
                        print("⏳ [Воркер] Блокчейн докидывает последние копейки. Ждем 1 сек...")
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ [Воркер] Непредвиденная ошибка ТП: {error_msg}")
                        break
                        
            elif status in ['CANCELED', 'EXPIRED']:
                print(f"⚠️ [Воркер] Базовый ордер был отменен. Остановка слежения.")
                break
                
        except Exception as e:
            pass 
        
        time.sleep(1)


@router.post("/api/trade")
def place_order(req: TradeRequest, background_tasks: BackgroundTasks):
    safe_price = round(float(req.price), 2)
    side_const = BUY if req.side.upper() == "BUY" else SELL
    
    order_type_str = "ОТЛОЖЕННАЯ ЛИМИТКА" if req.is_custom_limit else "РЫНОЧНЫЙ ОРДЕР"
    print(f"\n🚀 Поступил {order_type_str}: {req.side} по цене {safe_price}$")
    
    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}
        
    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    safe_size = round(actual_invest / safe_price, 2)
    
    try:
        client = ClobClient(host=HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, signature_type=SignatureTypeV2.POLY_1271, funder=FUNDER_ADDRESS)
        api_creds = ApiCreds(api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_API_SECRET"), api_passphrase=os.getenv("POLY_API_PASSPHRASE"))
        client.set_api_creds(api_creds)
        
        is_neg_risk = client.get_neg_risk(str(req.token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        main_args = OrderArgs(price=safe_price, size=safe_size, side=side_const, token_id=str(req.token_id))
        resp = client.create_and_post_order(order_args=main_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            main_order_id = resp.get('orderID')
            print(f"✅ ОСНОВНОЙ ОРДЕР УСПЕШНО ОТПРАВЛЕН! ID: {main_order_id}")
            
            if req.take_profit_price and req.side.upper() == "BUY":
                safe_tp_price = round(float(req.take_profit_price), 2)
                print(f"⏳ Передаю Тейк-Профит на {safe_tp_price}$ фоновому Воркеру...")
                
                background_tasks.add_task(
                    monitor_and_place_tp,
                    client=client, 
                    order_id=main_order_id, 
                    tp_price=safe_tp_price, 
                    original_size=safe_size, 
                    token_id=str(req.token_id), 
                    options=options
                )
                
            return {"success": True, "order_id": main_order_id}
            
        else:
            print(f"❌ Отказ биржи: {resp}")
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        print(f"❌ Критическая ошибка торговли: {e}")
        return {"success": False, "error": str(e)}
    
