import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.db import engine, Base
from src.api import trade, markets

# 🎯 ИМПОРТИРУЕМ НОВЫЙ КЛАСС ВМЕСТО СТАРОЙ ФУНКЦИИ
from src.workers.monitor import TradeWorker

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
def startup_event():
    """Запускаем фоновый мониторинг через класс TradeWorker"""
    worker = TradeWorker()
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()
    print("🚀 Background TradeWorker started successfully!")