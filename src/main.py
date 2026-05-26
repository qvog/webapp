import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.markets import router as markets_router
from api.ws import router as ws_router
from api.trade import router as trade_router # ДОБАВИЛИ ИМПОРТ

app = FastAPI(title="Polymarket Esports Terminal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markets_router)
app.include_router(ws_router)
app.include_router(trade_router) # ПОДКЛЮЧИЛИ ТОРГОВЛЮ

@app.get("/")
def serve_ui():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "frontend", "index.html")
    return FileResponse(file_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)