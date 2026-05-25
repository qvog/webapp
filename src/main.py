# main.py
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Импортируем наши "кусочки" (роутеры) из папки api
from api.markets import router as markets_router
from api.ws import router as ws_router

app = FastAPI(title="Polymarket Esports Terminal")

# Настройка безопасности (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# "Пристегиваем" роутеры к основному приложению
app.include_router(markets_router)
app.include_router(ws_router)

# Единственный эндпоинт, который остался здесь — это отдача фронтенда
@app.get("/")
def serve_ui():
    """Отдает HTML-файл нашего дашборда"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "frontend", "index.html")
    return FileResponse(file_path)

if __name__ == "__main__":
    print("🚀 Запускаем торговый терминал (Модульная архитектура)...")
    # Важно: теперь мы запускаем main:app, а не server:app
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)