from sqlalchemy import Column, Integer, String
from app.database import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    store_code = Column(String, unique=True, index=True)
    store_name = Column(String)
    location = Column(String)  # 店舗所在地
    phone = Column(String, nullable=True)  # 店舗電話番号
    
    def __repr__(self):
        return f"<Store {self.store_code}: {self.store_name}>"
