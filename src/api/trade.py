from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database.db import get_db
from src.database.models import Position
from src.workers.monitor import TradeWorker

router = APIRouter()
trade_worker = TradeWorker()

class PlaceOrderRequest(BaseModel):
    token_id: str
    condition_id: str
    price: float
    side: str
    bankroll: float
    risk_percent: float = 100
    is_custom_limit: bool = False
    take_profit_price: float = None
    stop_loss_price: float = None
    strategy: str = "custom"

@router.post("/order")
async def place_order(req: PlaceOrderRequest, db: Session = Depends(get_db)):
    size = round(req.bankroll / req.price, 2)
    resp = trade_worker.place_order(
        token_id=req.token_id, price=req.price, size=size, side=req.side
    )
    
    if resp and resp.get('success'):
        new_pos = Position(
            order_id=resp['orderID'],
            token_id=req.token_id,
            entry_price=req.price,
            size=size,
            side=req.side,
            status='PENDING' if req.is_custom_limit else 'OPEN',
            tp_price=req.take_profit_price,
            sl_trigger_price=req.stop_loss_price,
            strategy=req.strategy
        )
        db.add(new_pos)
        db.commit()
        return {"success": True, "orderID": resp['orderID']}
    return {"success": False, "error": resp.get('error', 'Unknown Error')}

@router.get("/positions")
async def get_positions(db: Session = Depends(get_db)):
    positions = db.query(Position).filter(
        Position.status.in_(['OPEN', 'PENDING'])
    ).all()
    
    # 🎯 ЖЕЛЕЗОБЕТОННЫЙ ФИКС: Ручная упаковка данных, чтобы не отдавать внутренности БД
    result = []
    for p in positions:
        result.append({
            "order_id": p.order_id,
            "token_id": p.token_id,
            "entry_price": p.entry_price,
            "size": p.size,
            "side": p.side,
            "status": p.status,
            "tp_price": p.tp_price,
            "sl_trigger_price": p.sl_trigger_price,
            "exit_price": p.exit_price,
            "strategy": p.strategy
        })
    return {"success": True, "positions": result}

@router.post("/panic_sell/{order_id}")
async def panic_sell(order_id: str, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.order_id == order_id).first()
    if not pos:
        return {"success": False, "error": "Order not found"}

    if pos.status == 'PENDING':
        success = trade_worker.cancel_order(pos.order_id)
        if success:
            pos.status = 'CANCELED'
            db.commit()
            return {"success": True, "message": "Order canceled"}
        else:
            pos.status = 'CANCELED'
            db.commit()
            return {"success": True, "message": "Forced cancel (Not found)"}
            
    elif pos.status == 'OPEN':
        try:
            resp = trade_worker.place_order(token_id=pos.token_id, price=0.01, size=pos.size, side="SELL")
            if resp and resp.get('success'):
                pos.status = 'CLOSED_SL'
                pos.exit_price = 0.01
                db.commit()
                return {"success": True, "message": "Market Dump Executed"}
            else:
                err_msg = resp.get('error', '').lower()
                if "not enough balance" in err_msg or "balance: 0" in err_msg:
                    pos.status = 'CLOSED_EXTERNAL'
                    db.commit()
                    return {"success": True, "message": "Cleared (0 Balance)"}
                return {"success": False, "error": resp.get('error', '')}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Invalid status"}