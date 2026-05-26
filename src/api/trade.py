from fastapi import APIRouter
from pydantic import BaseModel
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client import ApiCreds

router = APIRouter()

# ⚠️ ВСТАВЬ СЮДА СВОИ КЛЮЧИ ИЗ НАСТРОЕК POLYMARKET
HOST = "https://clob.polymarket.com"
KEY = "ТВОЙ_API_KEY"
SECRET = "ТВОЙ_API_SECRET"
PASSPHRASE = "ТВОЙ_API_PASSPHRASE"
CHAIN_ID = 137 # Сеть Polygon

class TradeRequest(BaseModel):
    token_id: str
    price: float
    size: float
    side: str # "BUY" или "SELL"

@router.post("/api/trade")
async def place_order(req: TradeRequest):
    print(f"🚀 Поступил ордер: {req.side} {req.size} акций по цене {req.price}$")
    try:
        # Проверяем, вставил ли ты ключи
        if KEY == "ТВОЙ_API_KEY":
            return {"success": False, "error": "Вставь API-ключи в файл trade.py!"}

        creds = ApiCreds(api_key=KEY, api_secret=SECRET, api_passphrase=PASSPHRASE)
        client = ClobClient(host=HOST, key=creds, chain_id=CHAIN_ID)
        
        # Формируем боевой ордер
        order_args = OrderArgs(
            price=req.price,
            size=req.size,
            side=req.side,
            token_id=req.token_id
        )
        
        # Подписываем приватным ключом и отправляем (GTC - Good Til Cancelled)
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            print(f"✅ ОРДЕР ИСПОЛНЕН! ID: {resp.get('orderID')}")
            return {"success": True, "order_id": resp.get("orderID")}
        else:
            print(f"❌ Ошибка биржи: {resp}")
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        print(f"❌ Критическая ошибка торговли: {e}")
        return {"success": False, "error": str(e)}