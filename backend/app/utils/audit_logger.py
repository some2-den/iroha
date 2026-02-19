from datetime import datetime
from typing import Optional, Dict, Any
import threading

def log_event(
    event_type: str,
    ip_address: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    user_agent: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = False,
    status_code: Optional[int] = None,
    db = None
):
    """イベントをログに記録（非同期で実行）"""
    def _log():
        try:
            from app.models.audit_log import AuditLog
            
            if db is None:
                from app.database import SessionLocal
                session = SessionLocal()
                should_close = True
            else:
                session = db
                should_close = False
            
            try:
                log = AuditLog(
                    timestamp=datetime.utcnow(),
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    resource=resource,
                    action=action,
                    details=details or {},
                    success=success,
                    status_code=status_code
                )
                
                session.add(log)
                session.commit()
                print(f"📝 Log recorded: {event_type} - {username} ({ip_address})")
            except Exception as e:
                session.rollback()
                print(f"⚠️ Error logging event (will continue): {e}")
            finally:
                if should_close:
                    session.close()
        except Exception as e:
            print(f"⚠️ Unexpected error in logging: {e}")
    
    # バックグラウンドスレッドでログを記録
    thread = threading.Thread(target=_log, daemon=True)
    thread.start()

