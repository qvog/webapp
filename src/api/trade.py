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
        token_id=req.token_id,
        price=req.price,
        size=size,
        side=req.side
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
    return {"success": True, "positions": [p.__dict__ for p in positions]}

@router.post("/panic_sell/{order_id}")
async def panic_sell(order_id: str, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.order_id == order_id).first()
    if not pos:
        return {"success": False, "error": "Позиция не найдена"}

    if pos.status == 'PENDING':
        success = trade_worker.cancel_order(pos.order_id)
        if success:
            pos.status = 'CANCELED'
            db.commit()
            return {"success": True, "message": "Ордер отменен"}
        else:
            try:
                order_info = trade_worker.client.get_order(pos.order_id)
                if order_info:
                    st = order_info.get('status')
                    if st in ['CANCELED', 'EXPIRED', 'KILLED']:
                        pos.status = 'CANCELED'
                        db.commit()
                        return {"success": True, "message": "Ордер уже отменен на бирже"}
                    elif st in ['MATCHED', 'FILLED']:
                        pos.status = 'OPEN'
                        db.commit()
                        return {"success": False, "error": "Ордер уже исполнился, теперь это позиция"}
                else:
                    pos.status = 'CANCELED'
                    db.commit()
                    return {"success": True, "message": "Ордер не найден на бирже, удален"}
            except Exception as e:
                if "not found" in str(e).lower() or "invalid" in str(e).lower():
                    pos.status = 'CANCELED'
                    db.commit()
                    return {"success": True, "message": "Ордер удален (не найден)"}
            return {"success": False, "error": "Ошибка отмены ордера"}
            
    elif pos.status == 'OPEN':
        try:
            side = "SELL"
            price = 0.01  # Для дампа бьем по рынку
            
            resp = trade_worker.place_order(
                token_id=pos.token_id,
                price=price,
                size=pos.size,
                side=side
            )
            
            if resp and resp.get('success'):
                pos.status = 'CLOSED_SL'
                pos.exit_price = price
                db.commit()
                return {"success": True, "message": "Позиция сброшена"}
            else:
                err_msg = resp.get('error', '').lower()
                # 🎯 Главный фикс: если баланса нет, значит токен уже продан
                if "not enough balance" in err_msg or "balance: 0" in err_msg:
                    pos.status = 'CLOSED_EXTERNAL'
                    db.commit()
                    return {"success": True, "message": "Позиция удалена (уже закрыта на сайте Polymarket)"}
                
                return {"success": False, "error": resp.get('error', '')}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Неверный статус позиции"}