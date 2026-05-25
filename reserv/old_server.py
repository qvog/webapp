import uvicorn
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
# МАГИЯ ЗДЕСЬ: Импортируем бронебойный requests
from curl_cffi import requests as cureq 

app = FastAPI(title="Polymarket Dota Terminal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_game_category(title):
    t = title.lower()
    if any(k in t for k in ["dota", "dreamleague", "riyadh", "wallachia", "bb dacha", "international"]): 
        return "Dota 2"
    if any(k in t for k in ["cs2", "cs:go", "counter-strike", "blast", "iem", "major", "cologne"]): 
        return "CS2"
    if any(k in t for k in ["lol", "league of", "lcs", "lec", "lck", "lpl", "msi"]): 
        return "LoL"
    if any(k in t for k in ["valorant", "vct", "champions"]): 
        return "Valorant"
    return "Other Esports"

@app.get("/")
def serve_ui():
    """Отдает HTML-файл нашего дашборда"""
    # 1. Получаем абсолютный путь к папке, в которой лежит server.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Склеиваем путь безопасно для любой операционной системы (Windows/Linux)
    # Если папка называется fronted (без n), поменяй слово ниже!
    file_path = os.path.join(base_dir, "frontend", "index.html")
    
    return FileResponse(file_path)

@app.get("/api/markets")
def get_markets():
    try:
        url = "https://gamma-api.polymarket.com/events"
        params = {
            "closed": "false",
            "limit": 100,
            "tag_slug": "esports"
        }
        
        print("⏳ Стучимся в Полимаркет (обход Cloudflare)...")
        
        # МАГИЯ 2: impersonate="chrome110" заставляет Cloudflare думать, 
        # что запрос делает реальный Google Chrome.
        resp = cureq.get(url, params=params, impersonate="chrome110", timeout=15)
        
        if resp.status_code != 200:
            print(f"❌ Ошибка API: {resp.status_code}")
            return {"error": f"Ошибка API: {resp.status_code}"}
            
        data = resp.json()
        print(f"✅ Получено {len(data)} событий. Фильтруем...")
        
        esports_matches = []
        for event in data:
            title = event.get("title", "")
            game_category = get_game_category(title)
            
            markets = event.get("markets", [])
            if markets:
                main_market = markets[0]
                esports_matches.append({
                    "event_id": event.get("id"),
                    "title": title,
                    "condition_id": main_market.get("conditionId"),
                    "status": "LIVE" if event.get("active") else "Upcoming",
                    "game": game_category
                })
        
        # Оставляем тестовые данные на случай, если реальных матчей 0
        if len(esports_matches) == 0:
            esports_matches.extend([
                {"event_id": "test-1", "title": "[ТЕСТ] Team Spirit vs BetBoom", "condition_id": "0x00...1", "status": "LIVE", "game": "Dota 2"},
                {"event_id": "test-2", "title": "[ТЕСТ] NAVI vs FaZe", "condition_id": "0x00...2", "status": "Upcoming", "game": "CS2"}
            ])
            
        return {"matches": esports_matches}
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Запускаем торговый терминал...")
    uvicorn.run("server:app", host="127.0.0.1", port=8080, reload=True)