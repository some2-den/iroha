from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SalesTransactionCreate(BaseModel):
    transaction_date: datetime
    store_code: str
    product_code: str
    product_name: str
    quantity: int = 1
    unit_price: float
    total_price: float
    gross_profit: float
    staff_id: str
    staff_name: str
    # MNP判定関連
    ticket_number: Optional[str] = None
    large_category: Optional[str] = None
    small_category: Optional[str] = None
    procedure_name: Optional[str] = None
    procedure_name_2: Optional[str] = None
    service_category: Optional[str] = None

class SalesTransactionRead(SalesTransactionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SalesSummary(BaseModel):
    date: datetime
    store_code: str
    total_sales: float
    gross_profit_total: float
    transaction_count: int
