from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)  # ログインID
    password_hash = Column(String)  # パスワードハッシュ
    staff_id = Column(String, unique=True, index=True)
    staff_name = Column(String)
    store_code = Column(String)
    role = Column(String, default="user")  # 'admin' または 'user'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

