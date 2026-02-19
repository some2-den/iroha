from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.csv_service import CSVService
from app.services.sales_service import SalesService
from app.models.sales import SalesTransaction
from app.models.store import Store
from app.schemas import SalesTransactionRead
from typing import List

router = APIRouter(prefix="/api", tags=["sales"])

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), user_id: int = Query(None), db: Session = Depends(get_db)):
    """CSVファイルをアップロードして販売データを登録
    
    user_idが与えられた場合、権限チェックを実施します。
    一般ユーザー(role != 'admin')は自身の店舗のデータのみアップロード可能です。
    CSVに複数の店舗が含まれている場合、一般ユーザーの場合は自身の店舗のデータのみを抽出します。
    """
    try:
        import hashlib
        from app.models.user import User
        
        print(f"📤 CSV Upload started - user_id: {user_id} (type: {type(user_id).__name__})")
        
        # ファイルをバイナリで読み込み
        content = await file.read()
        
        # CSVから店舗情報を抽出
        store_info_list = CSVService.extract_store_info(content)
        
        # ユーザー情報取得
        user = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
        
        # 抽出した店舗情報をDBに登録（一般ユーザーは自身の店舗のみ）
        registered_stores = []
        for store_info in store_info_list:
            # 非管理者ユーザーの場合、自身の店舗のみ処理
            if user and user.role != 'admin' and store_info['store_code'] != user.store_code:
                print(f"⚠️ スキップ: {store_info['store_name']} ({store_info['store_code']}) - ユーザーの店舗ではありません")
                continue
            
            existing_store = db.query(Store).filter(Store.store_code == store_info['store_code']).first()
            if not existing_store:
                new_store = Store(
                    store_code=store_info['store_code'],
                    store_name=store_info['store_name'],
                    location=store_info.get('location', '未設定')
                )
                db.add(new_store)
                registered_stores.append(f"新規：{store_info['store_name']} ({store_info['store_code']})")
            else:
                # 既存店舗の場合は店舗名を更新
                if existing_store.store_name.startswith('店舗 ') and store_info['store_name']:
                    existing_store.store_name = store_info['store_name']
                    db.add(existing_store)
                    registered_stores.append(f"更新：{store_info['store_name']} ({store_info['store_code']})")
        
        db.commit()
        
        # CSV解析（エンコーディング自動検出）
        transactions = CSVService.parse_sales_csv(content)
        
        # 既存データのハッシュを取得（完全重複を検出するため）
        existing_hashes = set()
        existing_records = db.query(SalesTransaction).all()
        for record in existing_records:
            # レコードの主要な情報でハッシュを作成
            hash_data = f"{record.transaction_date}_{record.ticket_number}_{record.staff_id}_{record.product_code}_{record.quantity}_{record.total_price}"
            existing_hashes.add(hashlib.md5(hash_data.encode()).hexdigest())
        
        # 新規レコードのみをフィルタリング
        new_transactions = []
        duplicate_count = 0
        filtered_out_count = 0
        
        for transaction in transactions:
            # 非管理者ユーザーがアップロードする場合、ユーザーの店舗のデータのみを抽出
            if user and user.role != 'admin' and transaction.store_code != user.store_code:
                filtered_out_count += 1
                continue

            # トランザクションのハッシュを作成
            hash_data = f"{transaction.transaction_date}_{transaction.ticket_number}_{transaction.staff_id}_{transaction.product_code}_{transaction.quantity}_{transaction.total_price}"
            tx_hash = hashlib.md5(hash_data.encode()).hexdigest()
            
            if tx_hash not in existing_hashes:
                new_transactions.append(transaction)
                existing_hashes.add(tx_hash)
            else:
                duplicate_count += 1
        
        # データベースに保存
        for transaction in new_transactions:
            db_transaction = SalesTransaction(**transaction.dict())
            db.add(db_transaction)
        
        db.commit()
        
        message = f"Successfully uploaded {len(new_transactions)} new transactions"
        if duplicate_count > 0:
            message += f" (skipped {duplicate_count} duplicates)"
        if filtered_out_count > 0:
            message += f" (filtered out {filtered_out_count} records from other stores)"
        
        store_message = ""
        if registered_stores:
            store_message = "; " + ", ".join(registered_stores)
        
        return {
            "message": message + store_message,
            "count": len(new_transactions),
            "store_count": len(registered_stores),
            "stores": registered_stores,
            "duplicates": duplicate_count,
            "filtered_out": filtered_out_count
        }
    except Exception as e:
        import traceback
        print(f"❌ CSV Upload Error: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        db.rollback()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=400, detail=error_detail)

@router.get("/transactions", response_model=List[SalesTransactionRead])
def get_transactions(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """販売トランザクション一覧を取得"""
    transactions = db.query(SalesTransaction).offset(skip).limit(limit).all()
    return transactions

@router.get("/summary/daily")
def get_daily_summary(
    db: Session = Depends(get_db),
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """日別売上サマリーを取得"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    summary = SalesService.get_daily_summary(db, store_code, start, end)
    
    return [
        {
            "date": row[0],
            "store_code": row[1],
            "total_sales": float(row[2]) if row[2] else 0,
            "gross_profit": float(row[3]) if row[3] else 0,
            "transaction_count": row[4]
        }
        for row in summary
    ]

@router.get("/summary/product")
def get_product_summary(
    db: Session = Depends(get_db),
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """商品別売上サマリーを取得"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    summary = SalesService.get_product_summary(db, store_code, start, end)
    
    return [
        {
            "product_code": row[0],
            "product_name": row[1],
            "total_quantity": row[2],
            "total_sales": float(row[3]) if row[3] else 0,
            "total_gross_profit": float(row[4]) if row[4] else 0
        }
        for row in summary
    ]

@router.get("/summary/staff-list")
def get_staff_list(
    db: Session = Depends(get_db),
    store_code: str = None
):
    """スタッフ一覧を取得"""
    staff_list = SalesService.get_staff_list(db, store_code)
    
    return [
        {
            "staff_id": staff[0],
            "staff_name": staff[1],
            "store_code": staff[2]
        }
        for staff in staff_list
    ]

@router.get("/summary/staff-performance")
def get_staff_performance(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """スタッフ別成績を取得（サービス種別ごとの詳細）"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    performance = SalesService.get_staff_performance(db, staff_id, store_code, start, end)
    
    return [
        {
            "staff_id": result[0],
            "staff_name": result[1],
            "product_name": result[2],
            "count": result[3] or 0,
            "gross_profit": float(result[4]) if result[4] else 0,
            "total_sales": float(result[5]) if result[5] else 0
        }
        for result in performance
    ]

@router.get("/summary/staff-aggregated")
def get_staff_aggregated(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """スタッフ別集計成績（サービス別集計済み）"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    performance = SalesService.aggregate_staff_performance(db, staff_id, store_code, start, end)
    
    result_list = []
    for staff_data in performance:
        # サービス別集計を整形
        services_formatted = {}
        for service_name, metrics in staff_data['services'].items():
            services_formatted[service_name] = {
                'count': metrics.get('count', 0),
                'gross_profit': metrics.get('gross_profit', 0)
            }
        
        result_list.append({
            "staff_id": staff_data['staff_id'],
            "staff_name": staff_data['staff_name'],
            "services": services_formatted,
            "total_sales": float(staff_data['total_sales']),
            "total_gross_profit": float(staff_data['total_gross_profit'])
        })
    
    return result_list

@router.get("/au1-collection/summary")
def get_au1_collection_summary(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """au+1Collection実績サマリー"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_au_plus_one_collection_summary(db, staff_id, store_code, start, end)
    
    return [
        {
            "staff_id": result.staff_id,
            "staff_name": result.staff_name,
            "transaction_count": result.transaction_count or 0,
            "total_sales": float(result.total_sales) if result.total_sales else 0,
            "gross_profit": float(result.gross_profit) if result.gross_profit else 0
        }
        for result in results
    ]


@router.get("/au1-collection/detail")
def get_au1_collection_detail(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """au+1Collection詳細統計（商品別）"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_au_plus_one_collection_detail(db, staff_id, store_code, start, end)
    
    return [
        {
            "staff_id": result.staff_id,
            "staff_name": result.staff_name,
            "product_name": result.product_name,
            "category": result.small_category,
            "transaction_count": result.transaction_count or 0,
            "total_sales": float(result.total_sales) if result.total_sales else 0,
            "gross_profit": float(result.gross_profit) if result.gross_profit else 0
        }
        for result in results
    ]


@router.get("/au1-collection/category")
def get_au1_collection_category(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """au+1Collection中分類別集計"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_au_plus_one_collection_by_category(db, staff_id, store_code, start, end)
    
    return [
        {
            "staff_id": result.staff_id,
            "staff_name": result.staff_name,
            "category": result.small_category,
            "transaction_count": result.transaction_count or 0,
            "total_sales": float(result.total_sales) if result.total_sales else 0,
            "gross_profit": float(result.gross_profit) if result.gross_profit else 0
        }
        for result in results
    ]


@router.get("/au1-collection/daily")
def get_au1_collection_daily(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """au+1Collection日別推移"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_au_plus_one_collection_daily(db, staff_id, store_code, start, end)
    
    return [
        {
            "date": str(result.date),
            "transaction_count": result.transaction_count or 0,
            "total_sales": float(result.total_sales) if result.total_sales else 0,
            "gross_profit": float(result.gross_profit) if result.gross_profit else 0
        }
        for result in results
    ]


@router.get("/au1-collection/total")
def get_au1_collection_total(
    db: Session = Depends(get_db),
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """au+1Collection全体統計（全スタッフ合計）"""
    from datetime import datetime
    from sqlalchemy import func
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    query = db.query(
        func.count(SalesTransaction.id).label("transaction_count"),
        func.sum(SalesTransaction.total_price).label("total_sales"),
        func.sum(SalesTransaction.gross_profit).label("gross_profit")
    ).filter(SalesTransaction.large_category == 'au+1 Collection')
    
    if store_code:
        query = query.filter(SalesTransaction.store_code == store_code)
    
    if start:
        query = query.filter(SalesTransaction.transaction_date >= start)
    
    if end:
        query = query.filter(SalesTransaction.transaction_date <= end)
    
    result = query.first()
    
    transaction_count = result[0] or 0
    total_sales = float(result[1]) if result[1] else 0
    gross_profit = float(result[2]) if result[2] else 0
    
    return {
        "transaction_count": transaction_count,
        "total_sales": total_sales,
        "gross_profit": gross_profit
    }

@router.get("/smartphone/unit-price")
def get_smartphone_unit_price(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """スマートフォン台当たり単価（au+1 Collection粗利 ÷ スマートフォン台数）"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_unit_price_per_smartphone(db, staff_id, store_code, start, end)
    
    return results

@router.get("/smartphone/summary")
def get_smartphone_sales_summary(
    db: Session = Depends(get_db),
    staff_id: str = None,
    store_code: str = None,
    start_date: str = None,
    end_date: str = None
):
    """スマートフォン販売（移動機 + iPhone/スマートフォン）実績サマリー"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    results = SalesService.get_smartphone_sales_summary(db, staff_id, store_code, start, end)
    
    result_list = []
    for result in results:
        total_quantity = result.total_quantity or 0
        
        result_list.append({
            "staff_id": result.staff_id,
            "staff_name": result.staff_name,
            "total_quantity": int(total_quantity),
            "total_gross_profit": 0,  # スマートフォン分の粗利は0円
            "gross_profit_per_unit": 0,  # 台当たり粗利も0円
            "total_sales": float(result.total_sales) if result.total_sales else 0
        })
    
    return result_list