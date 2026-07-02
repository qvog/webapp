import time
import logging
from src.api.client import get_clob_client
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL

logger = logging.getLogger(__name__)

class TradeWorker:
    def __init__(self):
        try:
            self.client = get_clob_client()
        except Exception as e:
            logger.error(f"Ошибка инициализации клиента: {e}")
            self.client = None

    def place_order(self, token_id: str, price: float, size: float, side: str = "BUY"):
        if not self.client:
            return {"success": False, "error": "Клиент не инициализирован"}
        try:
            resp = self.client.create_and_post_order(
                OrderArgs(
                    price=price,
                    size=size,
                    side=BUY if side == "BUY" else SELL,
                    token_id=token_id
                )
            )
            return {"success": True, "orderID": resp.get("orderID", "unknown")}
        except Exception as e:
            logger.error(f"Ошибка размещения ордера: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.cancel(order_id)
            return True
        except Exception as e:
            logger.error(f"Ошибка отмены ордера {order_id}: {e}")
            return False

    def run(self):
        logger.info("Фоновый воркер запущен (Минимальный стабильный режим)")
        while True:
            time.sleep(3)