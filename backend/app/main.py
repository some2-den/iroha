from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from app.config import DEBUG, CORS_ORIGINS, VERSION
from app.database import engine, Base
from app.routes import sales, health, admin, auth, audit
# モデルをインポート（テーブル作成のため）
from app.models.sales import SalesTransaction
from app.models.user import User
from app.models.admin import AdminUser
from app.models.store import Store
from app.models.audit_log import AuditLog

# テーブル作成
Base.metadata.create_all(bind=engine)

# デフォルトの管理ユーザーを作成（存在しない場合）
from sqlalchemy.orm import Session
from app.database import SessionLocal
from passlib.context import CryptContext
import secrets, string
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _random_password(length: int = 16) -> str:
    """英字+数字を必ず含むランダムパスワードを生成"""
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = ''.join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw):
            return pw

def _create_default_admin():
    db: Session = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == 'admin').first()
        if not admin_exists:
            init_pw = _random_password()
            default = User(
                username='admin',
                password_hash=pwd_context.hash(init_pw),
                staff_id='admin',
                staff_name='管理者',
                store_code='',
                role='admin',
                is_active=True
            )
            db.add(default)
            db.commit()
            print(f"[INIT] 初期管理者アカウントを作成しました")
            print(f"[INIT] username: admin")
            print(f"[INIT] password: {init_pw}  ← 必ず変更してください")
    except Exception as e:
        print(f"Warning: Could not create default admin: {e}")
        db.rollback()
    finally:
        db.close()

_create_default_admin()

# HTTPセキュリティヘッダーミドルウェア
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

# DEBUGモード時のみドキュメントエンドポイントを公開
app = FastAPI(
    title="Sales Performance API",
    description="CSV実績データの管理・分析API",
    version=VERSION,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

# セキュリティヘッダーミドルウェア（CORSより前に登録）
app.add_middleware(SecurityHeadersMiddleware)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ルート登録
app.include_router(health.router)
app.include_router(sales.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(audit.router)

# フロントエンド配信
@app.get("/")
async def root():
    """インデックスページ"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    return FileResponse(template_path)

@app.get("/index.html")
async def index_page():
    """インデックスページ"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    return FileResponse(template_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=DEBUG)
