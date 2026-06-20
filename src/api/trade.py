from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio

from py_clob_client_v2 import OrderArgs, PartialCreateOrderOptions, OrderType
from py_clob_client_v2.order_builder.constants import BUY, SELL

# Импорты наших новых модулей
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
    is_custom_limit: bool = False

class PanicRequest(BaseModel):
    order_id: str

@router.post("/api/trade")
async def place_order(req: TradeRequest, background_tasks: BackgroundTasks):
    safe_price = round(float(req.price), 2)
    side_const = BUY if req.side.upper() == "BUY" else SELL
    
    strategy = "match"
    if req.risk_percent == 2.5: strategy = "4c"
    elif req.risk_percent == 1.5: strategy = "8c"
    elif req.risk_percent == 5.0: strategy = "match"
    elif req.risk_percent == 20.0: strategy = "sure"
    
    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}
        
    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    safe_size = round(actual_invest / safe_price, 2)
    
    try:
        client = get_clob_client()
        is_neg_risk = await run_sync(client.get_neg_risk, str(req.token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

        main_args = OrderArgs(price=safe_price, size=safe_size, side=side_const, token_id=str(req.token_id))
        resp = await run_sync(client.create_and_post_order, order_args=main_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            main_order_id = resp.get('orderID')
            safe_tp_price = round(float(req.take_profit_price), 2) if req.take_profit_price else None
            
            # Запись в БД
            sl_price = 0
            if strategy in ['4c', '8c']: sl_price = safe_price - 0.12
            elif strategy in ['match', 'sure']: sl_price = safe_price * 0.5
            sl_price = max(0.01, round(sl_price, 2))

            db = SessionLocal()
            try:
                new_pos = Position(
                    order_id=main_order_id, token_id=str(req.token_id), strategy=strategy,
                    entry_price=safe_price, size=safe_size, tp_price=safe_tp_price,
                    sl_trigger_price=sl_price, status="OPEN"
                )
                db.add(new_pos)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"⚠️ Ошибка БД: {e}")
            finally: db.close()
            
            # Запуск вынесенного воркера
            background_tasks.add_task(
                monitor_and_manage_position, order_id=main_order_id, entry_price=safe_price,
                tp_price=safe_tp_price, original_size=safe_size, token_id=str(req.token_id), 
                options=options, strategy=strategy
            )
            return {"success": True, "order_id": main_order_id}
        else:
            return {"success": False, "error": str(resp)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/panic_sell")
async def panic_sell_position(req: PanicRequest):
    try:
        client = get_clob_client()
        order_info = await run_sync(client.get_order, req.order_id)
        order_data = order_info[0] if isinstance(order_info, list) and len(order_info) > 0 else order_info
        
        token_id = order_data.get('asset_id') or order_data.get('token_id')
        size_to_sell = float(order_data.get('size_matched', 0))
        
        if size_to_sell == 0:
            return {"success": False, "error": "Ордер еще не исполнен или объем нулевой"}

        try: await run_sync(client.cancel_market_orders, asset_id=str(token_id))
        except: await run_sync(client.cancel_all)
            
        await asyncio.sleep(1.5) 
        
        is_neg_risk = await run_sync(client.get_neg_risk, str(token_id))
        options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)
        sell_args = OrderArgs(price=0.01, size=size_to_sell, side=SELL, token_id=str(token_id))
        resp = await run_sync(client.create_and_post_order, order_args=sell_args, options=options, order_type=OrderType.GTC)
        
        if resp and resp.get("success"):
            # Обновляем БД
            db = SessionLocal()
            try:
                pos = db.query(Position).filter(Position.order_id == req.order_id).first()
                if pos:
                    pos.status = "PANIC_SELL"
                    db.commit()
            finally: db.close()
            return {"success": True, "message": "Сброшено!"}
        else:
            return {"success": False, "error": str(resp)}
    except Exception as e:
        return {"success": False, "error": str(e)}