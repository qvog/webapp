import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_clob_client_v2 import PartialCreateOrderOptions

from src.database.db import engine, Base, SessionLocal
from src.database.models import Position
from src.api import trade, markets
from src.workers.monitor import monitor_and_manage_position
from src.api.client import get_clob_client, run_sync

# Создаем таблицы базы данных
Base.metadata.create_all(bind=engine)

app = FastAPI(title="qScalp Terminal API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(trade.router, prefix="/api")
app.include_router(markets.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """
    При запуске сервера проверяем БД на наличие зависших (открытых) сделок.
    Если они есть, воскрешаем для каждой из них асинхронный радар (monitor_and_manage_position).
    """
    print("🔄 [СИСТЕМА] Проверка зависших сделок после перезагрузки...")
    db = SessionLocal()
    try:
        open_positions = db.query(Position).filter(Position.status.in_(["OPEN", "PENDING"])).all()
        if not open_positions:
            print("✅ [СИСТЕМА] Открытых сделок нет. Чистый старт.")
            return

        print(f"⚠️ [СИСТЕМА] Найдено {len(open_positions)} активных сделок! Воскрешаем воркеры...")
        
        client = get_clob_client()
        
        for pos in open_positions:
            is_neg_risk = await run_sync(client.get_neg_risk, str(pos.token_id))
            options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

            # Воскрешаем индивидуальный радар для позиции
            asyncio.create_task(
                monitor_and_manage_position(
                    order_id=pos.order_id, 
                    entry_price=pos.entry_price, 
                    tp_price=pos.tp_price,
                    sl_price=pos.sl_trigger_price, 
                    original_size=pos.size, 
                    token_id=pos.token_id, 
                    options=options, 
                    strategy=pos.strategy
                )
            )
            print(f"🟢 [СИСТЕМА] Радар для ордера {pos.order_id} успешно перезапущен!")
            
    except Exception as e:
        print(f"❌ [СИСТЕМА] Ошибка при восстановлении воркеров: {e}")
    finally:
        db.close()