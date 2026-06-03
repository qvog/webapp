import os

from fastapi import APIRouter
from pydantic import BaseModel

from py_clob_client_v2 import ClobClient, OrderArgs, PartialCreateOrderOptions, OrderType, SignatureTypeV2, ApiCreds
from py_clob_client_v2.order_builder.constants import BUY, SELL


# ПРОКСИ
PROXY_URL = os.getenv("POLY_PROXY")
os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL

router = APIRouter()
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

FUNDER_ADDRESS=os.getenv("POLY_FUNDER_ADDRESS")
PRIVATE_KEY=os.getenv("POLY_PRIVATE_KEY")

print("=== РАСШИРЕННАЯ ПРОВЕРКА ОБКРУЖЕНИЯ ===")
print("Прокси:", os.getenv("POLY_PROXY"))
print("Адрес депозита:", os.getenv("POLY_FUNDER_ADDRESS"))
print("Приватник загружен?:", os.getenv("POLY_PRIVATE_KEY") is not None)
print("API Key загружен?:", os.getenv("POLY_API_KEY") is not None)
print("API Secret загружен?:", os.getenv("POLY_API_SECRET") is not None)
print("API Passphrase загружен?:", os.getenv("POLY_API_PASSPHRASE") is not None)
print("=======================================")

class TradeRequest(BaseModel):
    token_id: str
    price: float
    side: str
    bankroll: float      # Твой текущий депозит (например, 100.0)
    risk_percent: float  # Процент от банка (например, 2.0 или 5.0)

@router.post("/api/trade")
def place_order(req: TradeRequest):
    safe_price = round(float(req.price), 2)
    side_const = BUY if req.side.upper() == "BUY" else SELL
    
    print(f"\n🚀 Поступил запрос на ордер: {req.side} по цене {safe_price}$")
    
    # 🎯 1. Базовая защита
    if req.bankroll < 5.00:
        error_msg = f"Банкролл ({req.bankroll}$) меньше минимального порога биржи ($5)."
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}
        
    # 🎯 2. Идеальная формула сайзинга
    target_invest = req.bankroll * (req.risk_percent / 100)
    
    # Берем максимум между 5$ и расчетным таргетом, 
    # но ограничиваем сверху общим размером банкролла
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    
    # 🎯 3. Переводим инвестицию в количество акций
    safe_size = round(actual_invest / safe_price, 2)
    effective_risk = round((actual_invest / req.bankroll) * 100, 2)
    
    print(f"🧮 Идеальный риск: {req.risk_percent}%. Фактический риск: {effective_risk}%")
    print(f"💰 Сумма в сделку: {actual_invest:.2f}$. Акций (Size): {safe_size}")
    
    try:
        print("⚙️ Инициализация клиента: Deposit Wallet Flow (POLY_1271)...")
        client = ClobClient(
            host=HOST,
            key=PRIVATE_KEY,
            chain_id=CHAIN_ID,
            signature_type=SignatureTypeV2.POLY_1271,
            funder=FUNDER_ADDRESS                     
        )
        
        print("🔐 Подключение рабочих браузерных ключей API...")
        # ❗️ Передаем ключи напрямую, минуя забагованный метод create_or_derive
        api_creds = ApiCreds(
            api_key=os.getenv("POLY_API_KEY"),
            api_secret=os.getenv("POLY_API_SECRET"),
            api_passphrase=os.getenv("POLY_API_PASSPHRASE")
        )
        client.set_api_creds(api_creds)
        
        is_neg_risk = client.get_neg_risk(str(req.token_id))
        print(f"⚖️ Статус Negative Risk для токена: {is_neg_risk}")
        
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        order_args = OrderArgs(
            price=safe_price,
            size=safe_size,
            side=side_const,
            token_id=str(req.token_id)
        )
        
        print("📝 Подпись и отправка ордера в стакан...")
        resp = client.create_and_post_order(
            order_args=order_args,
            options=options,
            order_type=OrderType.GTC
        )
        
        if resp and resp.get("success"):
            print(f"✅ ОРДЕР ИСПОЛНЕН! ID: {resp.get('orderID')}")
            return {"success": True, "order_id": resp.get("orderID")}
        else:
            print(f"❌ Отказ биржи: {resp}")
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        print(f"❌ Критическая ошибка торговли V2: {e}")
        return {"success": False, "error": str(e)}
    
