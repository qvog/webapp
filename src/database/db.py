import os
from sqlalchemy import create_engine, event
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

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL") # Ускоряет параллельную запись
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema() -> None:
    """Create tables and apply lightweight SQLite column migrations."""
    Base.metadata.create_all(bind=engine)
    # SQLite create_all does not add new columns to existing tables.
    with engine.begin() as conn:
        cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(positions)").fetchall()
        }
        if cols and "tp_order_id" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE positions ADD COLUMN tp_order_id VARCHAR"
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()