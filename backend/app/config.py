import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales.db")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
# CORSで全てのオリジンを許可（別のPCからのアクセスに対応）
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") != "*" else ["*"]
