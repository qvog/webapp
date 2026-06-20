from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from .db import Base

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    
    # ID ордера на Полимаркете, по которому мы вошли
    order_id = Column(String, index=True, nullable=False, unique=True)
    token_id = Column(String, index=True, nullable=False)
    strategy = Column(String, nullable=False) # '4c', '8c', 'match'
    
    entry_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    
    # Триггеры для воркера
    tp_price = Column(Float, nullable=True)
    sl_trigger_price = Column(Float, nullable=True)
    
    # Статус сделки (OPEN, CLOSED_TP, CLOSED_SL, PANIC_SELL)
    status = Column(String, default="OPEN") 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)