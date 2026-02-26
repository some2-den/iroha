from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from passlib.context import CryptContext
from app.database import get_db
from app.models.admin import AdminUser
from app.models.sales import SalesTransaction
from app.models.store import Store
from app.utils.jwt_auth import get_current_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

# パスワードハッシング設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AdminLogin(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)

class AdminChangePassword(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError("パスワードには数字を1文字以上含めてください")
        if not any(c.isalpha() for c in v):
            raise ValueError("パスワードには英字を1文字以上含めてください")
        return v

class StoreCreate(BaseModel):
    store_code: str = Field(..., min_length=1, max_length=32)
    store_name: str = Field(..., min_length=1, max_length=128)
    location: str = Field(default="", max_length=256)
    phone: str = Field(default=None, max_length=32)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/verify-password")
async def verify_password_endpoint(data: AdminLogin, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """管理者パスワードを検証"""
    admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    
    if not admin:
        # ランダムな初期パスワードで初期化（admin123 ハードコードを廃止）
        import secrets, string
        alphabet = string.ascii_letters + string.digits
        init_pw = ''.join(secrets.choice(alphabet) for _ in range(16))
        default_admin = AdminUser(
            username="admin",
            password_hash=hash_password(init_pw)
        )
        db.add(default_admin)
        db.commit()
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")
    
    if verify_password(data.password, admin.password_hash):
        return {"success": True, "message": "ログインしました"}
    else:
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

@router.post("/change-password")
async def change_password_endpoint(data: AdminChangePassword, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """管理者パスワードを変更"""
    admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    
    if not admin:
        raise HTTPException(status_code=404, detail="管理者が見つかりません")
    
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=401, detail="古いパスワードが正しくありません")
    
    admin.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"success": True, "message": "パスワードを変更しました"}

@router.get("/sales-data")
async def get_sales_data(current_user=Depends(require_admin), db: Session = Depends(get_db), store_code: str = None):
    """すべての売上データを取得"""
    try:
        from sqlalchemy.orm import joinedload
        from sqlalchemy import outerjoin
        
        query = db.query(SalesTransaction).outerjoin(Store, SalesTransaction.store_code == Store.store_code)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        transactions = query.all()
        result = []
        for t in transactions:
            # 店舗情報を取得（なければNone）
            store = db.query(Store).filter(Store.store_code == t.store_code).first()
            store_name = store.store_name if store else t.store_code
            
            result.append({
                "id": t.id,
                "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                "store_code": t.store_code,
                "store_name": store_name,
                "product_code": t.product_code,
                "product_name": t.product_name,
                "quantity": t.quantity,
                "unit_price": t.unit_price,
                "total_price": t.total_price,
                "gross_profit": t.gross_profit,
                "staff_id": t.staff_id,
                "staff_name": t.staff_name,
                "ticket_number": t.ticket_number,
                "large_category": t.large_category,
                "small_category": t.small_category,
                "procedure_name": t.procedure_name,
                "procedure_name_2": t.procedure_name_2,
                "service_category": t.service_category,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return {"data": result, "count": len(result)}
    except Exception as e:
        print(f"[ERROR] /admin/sales-data: {e}")
        raise HTTPException(status_code=500, detail="データ取得中にエラーが発生しました")

@router.post("/clear-data")
async def clear_data_endpoint(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """すべての売上データをクリア"""
    try:
        # 全トランザクションを削除
        db.query(SalesTransaction).delete()
        db.commit()
        
        # 削除前の数を返す（ログ用）
        return {
            "success": True,
            "message": "すべての売上データを削除しました"
        }
    except Exception as e:
        db.rollback()
        print(f"[ERROR] /admin/clear-data: {e}")
        raise HTTPException(status_code=500, detail="データ削除中にエラーが発生しました")

@router.get("/stores")
async def get_stores(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """店舗一覧を取得"""
    try:
        stores = db.query(Store).all()
        result = []
        for store in stores:
            result.append({
                "id": store.id,
                "store_code": store.store_code,
                "store_name": store.store_name,
                "location": store.location,
                "phone": store.phone,
            })
        return {"data": result, "count": len(result)}
    except Exception as e:
        print(f"[ERROR] /admin/stores GET: {e}")
        raise HTTPException(status_code=500, detail="店舗情報の取得中にエラーが発生しました")

@router.post("/stores")
async def create_store(store: StoreCreate, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """新規店舗を追加"""
    try:
        # 重複チェック
        existing = db.query(Store).filter(Store.store_code == store.store_code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"店舗コード '{store.store_code}' は既に存在します")
        
        new_store = Store(
            store_code=store.store_code,
            store_name=store.store_name,
            location=store.location,
            phone=store.phone,
        )
        db.add(new_store)
        db.commit()
        db.refresh(new_store)
        
        return {"success": True, "message": f"店舗 '{store.store_name}' を追加しました", "store": {
            "id": new_store.id,
            "store_code": new_store.store_code,
            "store_name": new_store.store_name,
            "location": new_store.location,
            "phone": new_store.phone,
        }}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] /admin/stores POST: {e}")
        raise HTTPException(status_code=500, detail="店舗追加中にエラーが発生しました")

@router.delete("/delete-store")
async def delete_store(request: Request, store_id: int, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """店舗を削除"""
    try:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="店舗が見つかりません")
        
        # 監査ログに記録
        try:
            from app.models.audit_log import AuditLog
            from app.utils.audit_logger import log_event
            from datetime import datetime
            log_event(
                event_type='store_deleted',
                ip_address=request.client.host if request.client else 'unknown',
                user_id=current_user.id,
                username=current_user.username,
                resource=f'/admin/delete-store',
                action='DELETE',
                details={"store_code": store.store_code, "store_name": store.store_name},
                success=True,
                status_code=200
            )
        except Exception as log_err:
            print(f"Warning: audit log failed: {log_err}")
        
        db.delete(store)
        db.commit()
        
        return {"success": True, "message": f"店舗「{store.store_name}」(コード: {store.store_code})を削除しました"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] /admin/delete-store: {e}")
        raise HTTPException(status_code=500, detail="店舗削除中にエラーが発生しました")
