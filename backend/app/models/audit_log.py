from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from app.database import Base
from datetime import datetime

class AuditLog(Base):
    """監査ログテーブル"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)  # login_success, login_failure, api_access, user_created, user_deleted, csv_upload, etc.
    user_id = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    ip_address = Column(String)
    user_agent = Column(String, nullable=True)
    resource = Column(String, nullable=True)  # API endpoint or resource被accessed
    action = Column(String, nullable=True)  # GET, POST, PUT, DELETE, etc.
    details = Column(JSON, nullable=True)  # 追加の詳細情報
    success = Column(Boolean, default=False)
    status_code = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, username={self.username}, timestamp={self.timestamp})>"
