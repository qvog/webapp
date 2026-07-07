from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
import os

from py_clob_client_v2 import OrderArgs, PartialCreateOrderOptions, OrderType
from py_clob_client_v2.order_builder.constants import BUY, SELL

from src.api.client import get_clob_client, run_sync
from src.workers.monitor import monitor_and_manage_position
from src.database.db import SessionLocal
from src.database.models import Position

router = APIRouter()

class TradeRequest(BaseModel):
    token_id: str
    price: float
    side: str
    bankroll: float
    risk_percent: float
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    strategy: str = "custom"
    is_custom_limit: bool = False
    condition_id: Optional[str] = None

class PanicRequest(BaseModel):
    order_id: str

@router.post("/api/trade")
async def place_order(req: TradeRequest, background_tasks: BackgroundTasks):
    safe_price = round(float(req.price), 2)
    side_const = BUY if req.side.upper() == "BUY" else SELL
    
    strategy = req.strategy 
    
    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}
        
    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    safe_size = round(actual_invest / safe_price, 2)
    
    try:
        client = get_clob_client()
        
        # 🎯 ПОДТЯГИВАЕМ BUILDER CODE
        builder_code = os.getenv("BUILDER_CODE", "0x0000000000000000000000000000000000000000000000000000000000000000")
        
        is_neg_risk = await run_sync(client.get_neg_risk, str(req.token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        # 🎯 ВСТАВЛЯЕМ BUILDER CODE В АРГУМЕНТЫ
        main_args = OrderArgs(price=safe_price, size=safe_size, side=side_const, token_id=str(req.token_id), builder_code=builder_code)
        resp = await run_sync(client.create_and_post_order, order_args=main_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            main_order_id = resp.get('orderID')
            safe_tp_price = round(float(req.take_profit_price), 2) if req.take_profit_price else None
            
            if req.stop_loss_price is not None:
                sl_price = round(float(req.stop_loss_price), 2)
            else:
                sl_price = safe_price - 0.12
            
            sl_price = max(0.01, round(sl_price, 2))

            db = SessionLocal()
            try:
                new_pos = Position(
                    order_id=main_order_id, 
                    token_id=str(req.token_id), 
                    condition_id=req.condition_id,
                    strategy=strategy,
                    entry_price=safe_price, 
                    size=safe_size, 
                    tp_price=safe_tp_price,
                    sl_trigger_price=sl_price, 
                    status="PENDING"
                )
                db.add(new_pos)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"⚠️ Ошибка БД: {e}")
            finally: db.close()
            
            background_tasks.add_task(
                monitor_and_manage_position, order_id=main_order_id, entry_price=safe_price,
                tp_price=safe_tp_price, sl_price=sl_price, original_size=safe_size, token_id=str(req.token_id), 
                options=options, strategy=strategy
            )
            return {"success": True, "order_id": main_order_id}
        else:
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/panic_sell")
async def panic_sell_position(req: PanicRequest):
    db = SessionLocal()
    try:
        pos = db.query(Position).filter(Position.order_id == req.order_id).first()
        if not pos:
            return {"success": False, "error": "Позиция не найдена в базе данных"}

        client = get_clob_client()
        token_id = pos.token_id
        size_to_sell = pos.size
        
        # 🎯 ПОДТЯГИВАЕМ BUILDER CODE ДЛЯ ПАНИК СЕЛЛА
        builder_code = os.getenv("BUILDER_CODE", "0x0000000000000000000000000000000000000000000000000000000000000000")

        try:
            order_info = await run_sync(client.get_order, req.order_id)
            order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
            
            if order_data and isinstance(order_data, dict):
                matched = float(order_data.get('size_matched', 0))
                status = order_data.get('status')
                
                if matched == 0 and status in ['LIVE', 'OPEN']:
                    await run_sync(client.cancel_orders, [req.order_id])
                    pos.status = "CANCELED"
                    db.commit()
                    return {"success": True, "message": "Отменено (покупок не было)."}
                elif matched > 0:
                    size_to_sell = matched
        except Exception as e:
            err_msg = str(e).lower()
            if "invalid token id" in err_msg or "400" in err_msg:
                print(f"🧹 [СБРОС] Токен {token_id} больше не существует на бирже. Принудительная очистка.")
                pos.status = "RESOLVED"
                pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (токен сгорел/рынок закрыт)."}

        try: await run_sync(client.cancel_market_orders, asset_id=str(token_id))
        except: 
            try: await run_sync(client.cancel_all)
            except: pass
            
        await asyncio.sleep(1.0) 
        
        try:
            is_neg_risk = await run_sync(client.get_neg_risk, str(token_id))
            options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)
            # 🎯 ВСТАВЛЯЕМ BUILDER CODE
            sell_args = OrderArgs(price=0.01, size=size_to_sell, side=SELL, token_id=str(token_id), builder_code=builder_code)
            resp = await run_sync(client.create_and_post_order, order_args=sell_args, options=options, order_type=OrderType.GTC)
            
            if resp and resp.get("success"):
                try:
                    ob = await run_sync(client.get_order_book, str(token_id))
                    bids = ob.get("bids", [])
                    best_bid = max([float(b['price']) for b in bids]) if bids else 0.01
                except:
                    best_bid = 0.01

                pos.status = "PANIC_SELL"
                pos.exit_price = best_bid
                db.commit()
                return {"success": True, "message": "Сброшено по рынку!"}
            
            error_msg = str(resp).lower()
            if "invalid token id" in error_msg or "resolved" in error_msg or "closed" in error_msg:
                pos.status = "RESOLVED"
                pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (рынок завершен)."}
                
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid token id" in error_msg or "invalid_token" in error_msg:
                print(f"🧹 [СБРОС] Перехвачена ошибка клиринга токена. Закрываем сделку.")
                pos.status = "RESOLVED"
                pos.exit_price = 1.0 
                db.commit()
                return {"success": True, "message": "Очищено (продано вручную)."}
            
            return {"success": False, "error": f"Ошибка Polymarket: {str(e)}"}
            
        return {"success": False, "error": "Неизвестная ошибка при отправке ордера"}
            
    except Exception as e:
        return {"success": False, "error": f"Внутренняя ошибка сервера: {str(e)}"}
    finally:
        db.close()

@router.get("/api/positions")
async def get_open_positions():
    db = SessionLocal()
    try:
        positions = db.query(Position).filter(Position.status.in_(["OPEN", "PENDING"])).all()
        
        pos_list = []
        for p in positions:
            pos_list.append({
                "order_id": p.order_id,
                "token_id": p.token_id,
                "entry_price": p.entry_price,
                "size": p.size,
                "tp_price": p.tp_price,
                "sl_trigger_price": p.sl_trigger_price,
                "strategy": p.strategy,
                "status": p.status
            })
            
        return {"success": True, "positions": pos_list}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()