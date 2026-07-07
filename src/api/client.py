import os
import logging
from dotenv import load_dotenv

# 🎯 Убрали проблемный импорт SignatureType!
try:
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import ApiCreds
except ImportError:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds

logger = logging.getLogger(__name__)

# Принудительно грузим .env из корня проекта
load_dotenv()

def get_clob_client():
    host = os.getenv("POLY_HOST", "https://clob.polymarket.com")
    chain_id = int(os.getenv("POLY_CHAIN_ID", 137))
    
    # 1. НАСТРОЙКА ПРОКСИ
    proxy_url = os.getenv("POLY_PROXY")
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        logger.info("🌐 Трафик Polymarket маршрутизируется через приватный прокси.")

    # 2. ПРИВАТНЫЙ КЛЮЧ И ФУНДЕР
    pk = os.getenv("POLY_PRIVATE_KEY")
    funder = os.getenv("POLY_FUNDER_ADDRESS")
    
    if not pk:
        logger.error("🚨 КРИТИЧЕСКАЯ ОШИБКА: POLY_PRIVATE_KEY не найден в .env!")
        raise ValueError("A private key is needed to interact with this endpoint!")

    # 3. ЗАГРУЗКА L2 КЛЮЧЕЙ
    api_key = os.getenv("POLY_API_KEY")
    api_secret = os.getenv("POLY_API_SECRET")
    api_passphrase = os.getenv("POLY_API_PASSPHRASE")

    creds = None
    if api_key and api_secret and api_passphrase:
        creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
        )

    # 🎯 4. БРОНЕБОЙНАЯ ИНИЦИАЛИЗАЦИЯ
    # Передаем signature_type=3 (POLY_1271 / Deposit Wallet Flow) как обычную цифру.
    # Это решает и проблему импорта, и проблему "maker address not allowed".
    client = ClobClient(
        host, 
        key=pk, 
        chain_id=chain_id, 
        creds=creds, 
        funder=funder,         # Возвращаем твой адрес смарт-контракта
        signature_type=3       # 3 = Официальный Deposit Wallet
    )
    
    return client