import os
import asyncio
import functools
from dotenv import load_dotenv
from py_clob_client_v2 import ClobClient, SignatureTypeV2, ApiCreds

load_dotenv()

PROXY_URL = os.getenv("POLY_PROXY")
if PROXY_URL:
    os.environ["http_proxy"] = PROXY_URL
    os.environ["https_proxy"] = PROXY_URL
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
FUNDER_ADDRESS = os.getenv("POLY_FUNDER_ADDRESS")

_clob_client = None

def get_clob_client() -> ClobClient:
    """Инициализирует клиент 1 раз при первом обращении (Singleton)."""
    global _clob_client
    if _clob_client is None:
        if not PRIVATE_KEY or not FUNDER_ADDRESS:
            raise ValueError("Не настроены приватные ключи в .env")
        _clob_client = ClobClient(
            host=HOST, 
            key=PRIVATE_KEY, 
            chain_id=CHAIN_ID, 
            signature_type=SignatureTypeV2.POLY_1271, 
            funder=FUNDER_ADDRESS
        )
        api_creds = ApiCreds(
            api_key=os.getenv("POLY_API_KEY"), 
            api_secret=os.getenv("POLY_API_SECRET"), 
            api_passphrase=os.getenv("POLY_API_PASSPHRASE")
        )
        _clob_client.set_api_creds(api_creds)
    return _clob_client

async def run_sync(func, *args, **kwargs):
    """Выполняет синхронные вызовы ClobClient в фоновом пуле потоков."""
    loop = asyncio.get_running_loop()
    pfunc = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, pfunc)