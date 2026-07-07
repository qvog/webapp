import os
import time
import logging
from src.api.client import get_clob_client

from py_clob_client_v2.clob_types import OrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.constants import BUY, SELL

logger = logging.getLogger(__name__)

class TradeWorker:
    def __init__(self):
        try:
            self.client = get_clob_client()
            
            # Проверяем L2 ключи
            if self.client and getattr(self.client, "creds", None) is None:
                logger.info("🔑 Генерируем торговые API-ключи (L2 Credentials)...")
                creds = self.client.create_or_derive_api_creds()
                self.client.set_api_creds(creds)
                logger.info("✅ Торговые ключи успешно установлены!")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации клиента: {e}")
            self.client = None

    def place_order(self, token_id: str, price: float, size: float, side: str = "BUY"):
        if not self.client:
            return {"success": False, "error": "Клиент не инициализирован"}
            
        try:
            # 1. Загрузка Builder Code
            builder_code = os.getenv("BUILDER_CODE", "0x0000000000000000000000000000000000000000000000000000000000000000")
            
            # 2. Формирование ордера
            order_args = OrderArgs(
                price=price,
                size=size,
                side=BUY if side.upper() == "BUY" else SELL,
                token_id=token_id,
                builder_code=builder_code
            )
            
            options = PartialCreateOrderOptions(
                tick_size="0.01", 
                neg_risk=False
            )

            # 3. Отправка на биржу
            resp = self.client.create_and_post_order(
                order_args,
                options=options,
                order_type=OrderType.GTC
            )
            
            order_id = resp.get("orderID")
            if order_id:
                logger.info(f"✅ Ордер размещен. ID: {order_id} (Builder: {builder_code[:6]}...)")
                return {"success": True, "orderID": order_id}
            else:
                err_msg = resp.get("errorMsg", "Неизвестная ошибка биржи")
                logger.error(f"❌ Ошибка биржи: {err_msg}")
                return {"success": False, "error": err_msg}
                
        except Exception as e:
            logger.error(f"❌ Ошибка размещения ордера: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        if not self.client:
            return False
            
        # 🎯 ХАК-КЛАСС для обхода багов типизации в библиотеке Полимаркета
        class OrderProxy:
            def __init__(self, oid):
                self.orderID = oid
                self.id = oid

        logger.info(f"⏳ Пытаемся отменить ордер {order_id}...")

        # ---------------------------------------------------------
        # СТРАТЕГИЯ 1: Официальный метод V2 (client.cancel)
        # ---------------------------------------------------------
        if hasattr(self.client, "cancel"):
            try:
                self.client.cancel(order_id)
                logger.info("✅ Ордер успешно отменен (Стратегия 1: cancel, str)")
                return True
            except AttributeError as e:
                # Перехватываем ту самую ошибку "'str' object has no attribute"
                if "orderID" in str(e) or "id" in str(e):
                    try:
                        self.client.cancel(OrderProxy(order_id))
                        logger.info("✅ Ордер успешно отменен (Стратегия 1: cancel, proxy)")
                        return True
                    except Exception:
                        pass
            except Exception:
                pass

        # ---------------------------------------------------------
        # СТРАТЕГИЯ 2: Старый метод V1 (client.cancel_order)
        # ---------------------------------------------------------
        if hasattr(self.client, "cancel_order"):
            try:
                self.client.cancel_order(order_id)
                logger.info("✅ Ордер успешно отменен (Стратегия 2: cancel_order, str)")
                return True
            except AttributeError as e:
                if "orderID" in str(e) or "id" in str(e):
                    try:
                        self.client.cancel_order(OrderProxy(order_id))
                        logger.info("✅ Ордер успешно отменен (Стратегия 2: cancel_order, proxy)")
                        return True
                    except Exception:
                        pass
            except Exception:
                pass
                
        # ---------------------------------------------------------
        # СТРАТЕГИЯ 3: Отправка через Словарь (dict)
        # ---------------------------------------------------------
        if hasattr(self.client, "cancel"):
            try:
                self.client.cancel({"orderID": order_id, "id": order_id})
                logger.info("✅ Ордер успешно отменен (Стратегия 3: cancel, dict)")
                return True
            except Exception:
                pass

        logger.error(f"❌ Не удалось отменить ордер {order_id}: все 3 стратегии провалились")
        return False

    def run(self):
        logger.info("Фоновый воркер запущен (V2 API Mode)")
        while True:
            time.sleep(3)