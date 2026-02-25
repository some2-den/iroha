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
from app.utils.jwt_auth import create_access_token, get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])

# パスワードハッシング設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# スキーマ
class UserLogin(BaseModel):
    username: str
    password: str

def _validate_password_strength(password: str) -> str:
    """パスワード強度を検証する共通バリデーター"""
    if len(password) < 8:
        raise ValueError("パスワードは8文字以上にしてください")
    if not any(c.isdigit() for c in password):
        raise ValueError("パスワードには数字を1文字以上含めてください")
    if not any(c.isalpha() for c in password):
        raise ValueError("パスワードには英字を1文字以上含めてください")
    return password

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        return _validate_password_strength(v)

class UserCreate(BaseModel):
    username: str
    password: str
    staff_id: str
    staff_name: str
    store_code: str
    role: str = "user"  # 'admin', 'manager', または 'user'

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password_strength(v)

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
    
    access_token = create_access_token({"sub": str(user.id)})

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
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
async def change_password(data: UserChangePassword, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """パスワード変更（一般ユーザー用）"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="現在のパスワードが正しくありません")
    
    current_user.password_hash = hash_password(data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "パスワードを変更しました"}

@router.post("/admin/create-user")
async def create_user(data: UserCreate, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """ユーザー作成（管理者用）"""
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
async def reset_password(request: Request, data: UserReset, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """パスワードリセット（管理者用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # ユーザーを取得
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # ランダムな初期パスワードを生成（英字 + 数字 各4文字ずつ = 8文字）
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    while True:
        default_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        # 英字と数字が両方含まれることを保証
        if any(c.isalpha() for c in default_password) and any(c.isdigit() for c in default_password):
            break
    user.password_hash = hash_password(default_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    log_event(
        event_type="password_reset",
        ip_address=ip_address,
        user_id=current_user.id,
        username=current_user.username,
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
        "temporary_password": default_password,
        "username": user.username
    }

@router.get("/admin/users")
async def list_users(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """ユーザー一覧を取得（管理者用）"""
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
async def delete_user(request: Request, username: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """ユーザーを削除（管理者用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # ユーザーを取得
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # 管理者自身は削除不可
    if user.id == current_user.id:
        log_event(
            event_type="user_delete_failure",
            ip_address=ip_address,
            user_id=current_user.id,
            username=current_user.username,
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
        user_id=current_user.id,
        username=current_user.username,
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
    store_code: str = None

@router.put("/admin/users/{username}")
async def update_user(request: Request, username: str, data: UserUpdate, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """ユーザー情報を更新（管理者用）"""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # ユーザーを取得
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    old_staff_name = user.staff_name
    old_store_code = user.store_code
    changed = {}

    # スタッフ名を更新
    if data.staff_name is not None:
        user.staff_name = data.staff_name
        changed["staff_name"] = {"old": old_staff_name, "new": data.staff_name}

    # 店舗コードを更新
    if data.store_code is not None:
        user.store_code = data.store_code
        changed["store_code"] = {"old": old_store_code, "new": data.store_code}

    if changed:
        user.updated_at = datetime.utcnow()
    
    db.commit()
    
    log_event(
        event_type="user_updated",
        ip_address=ip_address,
        user_id=current_user.id,
        username=current_user.username,
        user_agent=user_agent,
        resource=f"/auth/admin/users/{username}",
        action="PUT",
        details={"target_user": username, **changed},
        success=True,
        status_code=200
    )
    
    return {
        "success": True,
        "message": f"ユーザー '{username}' を更新しました",
        "staff_name": user.staff_name,
        "store_code": user.store_code
    }
