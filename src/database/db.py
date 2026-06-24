import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Высчитываем абсолютный путь к корню твоего проекта (/home/qvog/webapp)
# db.py лежит в src/database/, поэтому поднимаемся на 2 папки вверх
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "trades.db")

# 2. Формируем путь (ровно 3 слеша + абсолютный путь)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False нужен, чтобы FastAPI и воркеры не ругались на потоки
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()