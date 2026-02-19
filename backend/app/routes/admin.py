from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
from app.database import get_db
from app.models.admin import AdminUser
from app.models.sales import SalesTransaction
from app.models.store import Store

router = APIRouter(prefix="/api/admin", tags=["admin"])

# パスワードハッシング設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AdminLogin(BaseModel):
    password: str

class AdminChangePassword(BaseModel):
    old_password: str
    new_password: str

class StoreCreate(BaseModel):
    store_code: str
    store_name: str
    location: str
    phone: str = None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/verify-password")
async def verify_password_endpoint(data: AdminLogin, db: Session = Depends(get_db)):
    """管理者パスワードを検証"""
    admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    
    if not admin:
        # デフォルトパスワードで初期化
        default_admin = AdminUser(
            username="admin",
            password_hash=hash_password("admin123")
        )
        db.add(default_admin)
        db.commit()
        
        if verify_password(data.password, default_admin.password_hash):
            return {"success": True, "message": "ログインしました"}
        else:
            raise HTTPException(status_code=401, detail="パスワードが正しくありません")
    
    if verify_password(data.password, admin.password_hash):
        return {"success": True, "message": "ログインしました"}
    else:
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

@router.post("/change-password")
async def change_password_endpoint(data: AdminChangePassword, db: Session = Depends(get_db)):
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
async def get_sales_data(db: Session = Depends(get_db), store_code: str = None):
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
        raise HTTPException(status_code=500, detail=f"データ取得エラー: {str(e)}")

@router.post("/clear-data")
async def clear_data_endpoint(db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"データ削除エラー: {str(e)}")

@router.get("/stores")
async def get_stores(db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"店舗取得エラー: {str(e)}")

@router.post("/stores")
async def create_store(store: StoreCreate, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"店舗追加エラー: {str(e)}")

@router.delete("/delete-store")
async def delete_store(store_id: int, admin_user_id: int = None, db: Session = Depends(get_db)):
    """店舗を削除"""
    try:
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="店舗が見つかりません")
        
        # 監査ログに記録
        try:
            from app.models.audit_log import AuditLog
            from datetime import datetime
            log_entry = AuditLog(
                event_type='store_deleted',
                user_id=admin_user_id or 0,
                username='admin',
                ip_address='127.0.0.1',
                status='success',
                details=f"店舗削除: {store.store_code} ({store.store_name})",
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
        except:
            pass  # 監査ログの記録に失敗しても続行
        
        db.delete(store)
        db.commit()
        
        return {"success": True, "message": f"店舗「{store.store_name}」(コード: {store.store_code})を削除しました"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"店舗削除エラー: {str(e)}")
