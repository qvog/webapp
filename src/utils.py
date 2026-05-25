# utils.py

def get_game_category(title: str) -> str:
    """Определяет киберспортивную дисциплину по названию"""
    t = title.lower()
    
    # 1. Сначала отсекаем ЛоЛ (чтобы Фейкер не улетал в Доту)
    if any(k in t for k in ["lol", "league of", "lcs", "lec", "lck", "lpl", "msi", "faker"]): 
        return "LoL"
        
    # 2. Ищем CS2 (уточняем, что blast premier - это кс)
    if any(k in t for k in ["cs2", "cs:go", "counter-strike", "blast premier", "iem", "major", "cologne"]): 
        return "CS2"
        
    # 3. Ищем Доту (добавили blast slam, исправили international на the international)
    if any(k in t for k in ["dota", "dreamleague", "riyadh", "wallachia", "bb dacha", "the international", "blast slam"]): 
        return "Dota 2"
        
    # 4. Валорант
    if any(k in t for k in ["valorant", "vct", "champions"]): 
        return "Valorant"
        
    return "Other Esports"