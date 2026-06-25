import uvicorn
import os
import asyncio

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.database import models
from src.database.db import engine, Base, SessionLocal
from src.database.models import Position
from src.workers.monitor import monitor_and_manage_position

from src.api.markets import router as markets_router
from src.api.trade import router as trade_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Polymarket Esports Terminal")

@app.on_event("startup")
async def restart_orphaned_workers():
    print("🔄 [СИСТЕМА] Проверка зависших сделок после перезагрузки сервера...")
    db = SessionLocal()
    try:
        open_positions = db.query(Position).filter(Position.status == "OPEN").all()
        if not open_positions:
            print("✅ [СИСТЕМА] Открытых сделок нет. Чистый старт.")
            return

        print(f"⚠️ [СИСТЕМА] Найдено {len(open_positions)} открытых сделок! Воскрешаем воркеры...")
        for pos in open_positions:
            from py_clob_client_v2 import PartialCreateOrderOptions
            from src.api.client import get_clob_client, run_sync
            client = get_clob_client()
            is_neg_risk = await run_sync(client.get_neg_risk, str(pos.token_id))
            options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

            asyncio.create_task(
                monitor_and_manage_position(
                    order_id=pos.order_id, entry_price=pos.entry_price, tp_price=pos.tp_price,
                    original_size=pos.size, token_id=pos.token_id, options=options, strategy=pos.strategy
                )
            )
            print(f"🟢 [СИСТЕМА] Воркер для ордера {pos.order_id} успешно перезапущен!")
    except Exception as e:
        print(f"❌ [СИСТЕМА] Ошибка при восстановлении воркеров: {e}")
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(markets_router)
app.include_router(trade_router)

@app.get("/")
def serve_ui():
    # Поднимаемся на одну папку вверх (из src/ в корень проекта)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Теперь ищем файл в правильной корневой папке frontend/
    file_path = os.path.join(base_dir, "frontend", "index.html")
    
    return FileResponse(file_path)