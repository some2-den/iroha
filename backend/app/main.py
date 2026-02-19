from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.config import DEBUG, CORS_ORIGINS
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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _create_default_admin():
    db: Session = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == 'admin').first()
        if not admin_exists:
            default = User(
                username='admin',
                password_hash=pwd_context.hash('admin123'),
                staff_id='admin',
                staff_name='管理者',
                store_code='',
                role='admin',
                is_active=True
            )
            db.add(default)
            db.commit()
    except Exception as e:
        print(f"Warning: Could not create default admin: {e}")
        db.rollback()
    finally:
        db.close()

_create_default_admin()

app = FastAPI(
    title="Sales Performance API",
    description="CSV実績データの管理・分析API",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
