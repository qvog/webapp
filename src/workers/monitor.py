import time
import logging
from sqlalchemy.orm import Session
from src.database.db import engine
from src.database.models import Position
from src.api.client import get_clob_client
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL

logger = logging.getLogger(__name__)

class TradeWorker:
    def __init__(self):
        self.client = get_clob_client()

    def place_order(self, token_id: str, price: float, size: float, side: str = "BUY"):
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
            logger.error(f"Order placement error: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.client.cancel(order_id)
            return True
        except Exception as e:
            logger.error(f"Ошибка отмены ордера {order_id}: {e}")
            return False

    def check_tp_sl(self):
        try:
            # 🎯 Надежно открываем независимую сессию для фонового потока
            db = Session(bind=engine)
            try:
                open_positions = db.query(Position).filter(Position.status == 'OPEN').all()
                for pos in open_positions:
                    current_price = 0.5  # Заглушка, позже свяжем с живой ценой
                    
                    if pos.tp_price and current_price >= pos.tp_price:
                        logger.info(f"⚡ TAKE PROFIT Triggered for {pos.order_id}")
                        resp = self.place_order(token_id=pos.token_id, price=0.01, size=pos.size, side="SELL")
                        if resp and resp.get("success"):
                            pos.status = 'CLOSED_TP'
                            pos.exit_price = current_price
                            db.commit()
                        else:
                            err = resp.get("error", "").lower()
                            if "not enough balance" in err or "balance: 0" in err:
                                pos.status = 'CLOSED_EXTERNAL'
                                db.commit()

                    elif pos.sl_trigger_price and current_price <= pos.sl_trigger_price:
                        logger.info(f"⚡ STOP LOSS Triggered for {pos.order_id}")
                        resp = self.place_order(token_id=pos.token_id, price=0.01, size=pos.size, side="SELL")
                        if resp and resp.get("success"):
                            pos.status = 'CLOSED_SL'
                            pos.exit_price = current_price
                            db.commit()
                        else:
                            err = resp.get("error", "").lower()
                            if "not enough balance" in err or "balance: 0" in err:
                                pos.status = 'CLOSED_EXTERNAL'
                                db.commit()
            finally:
                db.close() # 🎯 Гарантированно закрываем сессию, чтобы не повесить БД
        except Exception as e:
            logger.error(f"Ошибка проверки TP/SL: {e}")

    def sync_positions(self):
        try:
            # 🎯 Надежно открываем сессию
            db = Session(bind=engine)
            try:
                open_positions = db.query(Position).filter(
                    Position.status.in_(['OPEN', 'PENDING'])
                ).all()

                for pos in open_positions:
                    if pos.status == 'PENDING':
                        try:
                            order_info = self.client.get_order(pos.order_id)
                            if order_info:
                                status = order_info.get('status')
                                if status in ['MATCHED', 'FILLED']:
                                    pos.status = 'OPEN'
                                    db.commit()
                                    logger.info(f"[СИНХРОНИЗАЦИЯ] Ордер {pos.order_id} ИСПОЛНЕН.")
                                elif status in ['CANCELED', 'EXPIRED', 'KILLED']:
                                    pos.status = 'CANCELED'
                                    db.commit()
                                    logger.info(f"[СИНХРОНИЗАЦИЯ] Ордер {pos.order_id} ОТМЕНЕН.")
                            else:
                                pos.status = 'CANCELED'
                                db.commit()
                        except Exception as e:
                            err = str(e).lower()
                            if "not found" in err or "invalid" in err:
                                pos.status = 'CANCELED'
                                db.commit()
                            logger.error(f"Ошибка проверки ордера {pos.order_id}: {e}")
            finally:
                db.close() # 🎯 Закрываем
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")

    def run(self):
        logger.info("Trade Worker started")
        while True:
            self.sync_positions()
            self.check_tp_sl()
            time.sleep(3)