from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.utils.rate_limiter import login_limiter
from app.utils.audit_logger import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])

# パスワードハッシング設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# スキーマ
class UserLogin(BaseModel):
    username: str
    password: str

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    staff_id: str
    staff_name: str
    store_code: str
    role: str = "user"  # 'admin', 'manager', または 'user'
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = {'admin', 'manager', 'user'}
        if v not in allowed_roles:
            raise ValueError(f"role must be one of {allowed_roles}")
        return v

class UserReset(BaseModel):
    username: str

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/login")
async def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    """ユーザーログイン"""
    # IPアドレス取得
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # ブルートフォース対策：IP単位でレート制限
    if not login_limiter.is_allowed(ip_address):
        remaining = login_limiter.get_remaining_time(ip_address)
        log_event(
            event_type="login_rate_limit_exceeded",
            ip_address=ip_address,
            username=data.username,
            user_agent=user_agent,
            success=False,
            status_code=429
        )
        raise HTTPException(
            status_code=429,
            detail=f"ログイン試行回数が多すぎます。{remaining}秒後に再度お試しください"
        )
    
    user = db.query(User).filter(User.username == data.username).first()
    
    if not user or not verify_password(data.password, user.password_hash):
        log_event(
            event_type="login_failure",
            ip_address=ip_address,
            username=data.username,
            user_agent=user_agent,
            success=False,
            status_code=401,
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(status_code=401, detail="ユーザー名またはパスワードが正しくありません")
    
    if not user.is_active:
        log_event(
            event_type="login_failure",
            ip_address=ip_address,
            username=data.username,
            user_id=user.id,
            user_agent=user_agent,
            success=False,
            status_code=403,
            details={"reason": "user_inactive"}
        )
        raise HTTPException(status_code=403, detail="このユーザーはアクティブではありません")
    
    # ログイン成功をログに記録
    log_event(
        event_type="login_success",
        ip_address=ip_address,
        user_id=user.id,
        username=data.username,
        user_agent=user_agent,
        success=True,
        status_code=200
    )
    
    return {
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "staff_name": user.staff_name,
        "store_code": user.store_code,
        "role": user.role
    }

@router.post("/logout")
async def logout():
    """ユーザーログアウト"""
    return {"success": True, "message": "ログアウトしました"}

@router.post("/change-password")
async def change_password(data: UserChangePassword, user_id: int = Query(None), db: Session = Depends(get_db)):
    """パスワード変更（一般ユーザー用）"""
    if not user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="現在のパスワードが正しくありません")
    
    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "パスワードを変更しました"}

@router.post("/admin/create-user")
async def create_user(data: UserCreate, admin_user_id: int = Query(None), db: Session = Depends(get_db)):
    """ユーザー作成（特権ユーザー用）"""
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    # 管理者ユーザーであることを確認
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or admin.role != "admin":
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    
    # ユーザーが既に存在するか確認
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="このユーザー名は既に存在します")
    
    # 新規ユーザーを作成
    new_user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        staff_id=data.staff_id,
        staff_name=data.staff_name,
        store_code=data.store_code,
        role=data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "success": True,
        "message": f"ユーザー '{data.username}' を作成しました",
        "user_id": new_user.id
    }

@router.post("/admin/reset-password")
async def reset_password(request: Request, data: UserReset, admin_user_id: int = Query(None), db: Session = Depends(get_db)):
    """パスワードリセット（特権ユーザー用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    # 管理者ユーザーであることを確認
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or admin.role != "admin":
        log_event(
            event_type="unauthorized_admin_access",
            ip_address=ip_address,
            user_id=admin_user_id,
            user_agent=user_agent,
            resource="/auth/admin/reset-password",
            action="POST",
            success=False,
            status_code=403
        )
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    
    # ユーザーを取得
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # デフォルトパスワードにリセット
    default_password = "password123"
    user.password_hash = hash_password(default_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_event(
        event_type="password_reset",
        ip_address=ip_address,
        user_id=admin_user_id,
        username=admin.username,
        user_agent=user_agent,
        resource=f"/auth/admin/reset-password",
        action="POST",
        details={"target_user": data.username},
        success=True,
        status_code=200
    )
    
    return {
        "success": True,
        "message": f"パスワードをリセットしました",
        "default_password": default_password,
        "username": user.username
    }

@router.get("/admin/users")
async def list_users(admin_user_id: int = Query(None), db: Session = Depends(get_db)):
    """ユーザー一覧を取得（特権ユーザー用）"""
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    # 管理者ユーザーであることを確認
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or admin.role != "admin":
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "staff_name": u.staff_name,
            "store_code": u.store_code,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]

@router.delete("/admin/users/{username}")
async def delete_user(request: Request, username: str, admin_user_id: int = Query(None), db: Session = Depends(get_db)):
    """ユーザーを削除（特権ユーザー用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    # 管理者ユーザーであることを確認
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or admin.role != "admin":
        log_event(
            event_type="unauthorized_admin_access",
            ip_address=ip_address,
            user_id=admin_user_id,
            user_agent=user_agent,
            resource=f"/auth/admin/users/{username}",
            action="DELETE",
            success=False,
            status_code=403
        )
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    
    # ユーザーを取得
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # 管理者自身は削除不可
    if user.id == admin_user_id:
        log_event(
            event_type="user_delete_failure",
            ip_address=ip_address,
            user_id=admin_user_id,
            username=admin.username,
            user_agent=user_agent,
            resource=f"/auth/admin/users/{username}",
            action="DELETE",
            details={"reason": "self_delete_attempt"},
            success=False,
            status_code=400
        )
        raise HTTPException(status_code=400, detail="自分自身は削除できません")
    
    # ユーザーを削除
    db.delete(user)
    db.commit()
    
    log_event(
        event_type="user_deleted",
        ip_address=ip_address,
        user_id=admin_user_id,
        username=admin.username,
        user_agent=user_agent,
        resource=f"/auth/admin/users/{username}",
        action="DELETE",
        details={"deleted_user": username, "deleted_user_role": user.role},
        success=True,
        status_code=200
    )
    
    return {
        "success": True,
        "message": f"ユーザー '{username}' を削除しました"
    }

class UserUpdate(BaseModel):
    staff_name: str = None

@router.put("/admin/users/{username}")
async def update_user(request: Request, username: str, data: UserUpdate, admin_user_id: int = Query(None), db: Session = Depends(get_db)):
    """ユーザー情報を更新（特権ユーザー用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    if not admin_user_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    # 管理者ユーザーであることを確認
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or admin.role != "admin":
        log_event(
            event_type="unauthorized_admin_access",
            ip_address=ip_address,
            user_id=admin_user_id,
            user_agent=user_agent,
            resource=f"/auth/admin/users/{username}",
            action="PUT",
            success=False,
            status_code=403
        )
        raise HTTPException(status_code=403, detail="管理者権限がありません")
    
    # ユーザーを取得
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    old_staff_name = user.staff_name
    
    # スタッフ名を更新
    if data.staff_name is not None:
        user.staff_name = data.staff_name
        user.updated_at = datetime.utcnow()
    
    db.commit()
    
    log_event(
        event_type="user_updated",
        ip_address=ip_address,
        user_id=admin_user_id,
        username=admin.username,
        user_agent=user_agent,
        resource=f"/auth/admin/users/{username}",
        action="PUT",
        details={
            "target_user": username,
            "old_staff_name": old_staff_name,
            "new_staff_name": data.staff_name
        },
        success=True,
        status_code=200
    )
    
    return {
        "success": True,
        "message": f"ユーザー '{username}' を更新しました",
        "staff_name": user.staff_name
    }
