from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base

class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    store_code = Column(String)
    product_code = Column(String)
    product_name = Column(String)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)
    total_price = Column(Float)
    gross_profit = Column(Float)
    staff_id = Column(String)
    staff_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # MNP判定関連のカラム
    ticket_number = Column(String)  # 売上伝票番号
    large_category = Column(String)  # 大分類名
    small_category = Column(String)  # 中分類名
    procedure_name = Column(String)  # 手続区分名
    procedure_name_2 = Column(String)  # 手続区分２名
    service_category = Column(String)  # サービスカテゴリ（MNP判定結果）
