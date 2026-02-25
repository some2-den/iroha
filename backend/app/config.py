import os
from dotenv import load_dotenv

load_dotenv()

# アプリケーションバージョン
VERSION = "beta-1.6.8.1"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales.db")
# 本番環境では必ず環境変数 DEBUG=false を設定すること
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
# 本番環境では環境変数 CORS_ORIGINS にドメインを指定すること（例: https://example.com）
# デフォルトは空白（同一オリジンのみ許可）
_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = _cors_env.split(",") if _cors_env else []

# JWT認証設定
# 本番環境では必ず環境変数 SECRET_KEY に長いランダム文字列を設定すること
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-32chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# CSVアップロード制限
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))  # デフォルト10MB
