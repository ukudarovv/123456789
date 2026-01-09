import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TELEGRAM_TOKEN", "")
API_BASE_URL = os.getenv("BOT_API_BASE_URL", "http://localhost:8002/api")
API_KEY = os.getenv("BOT_API_KEY", "")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "RU")
OWNER_WHATSAPP_PHONE = os.getenv("OWNER_WHATSAPP_PHONE", "")

