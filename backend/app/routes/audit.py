from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.utils.jwt_auth import require_admin
from datetime import datetime, timedelta
from typing import List

router = APIRouter(prefix="/api", tags=["audit"])

@router.get("/admin/security-logs")
async def get_security_logs(
    request: Request,
    current_user=Depends(require_admin),
    event_type: str = Query(None),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """セキュリティログを取得（管理者のみ）"""
    # ログイン情報からIPアドレスとユーザーエージェントを取得
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # ログアクセスをログに記録
    from app.utils.audit_logger import log_event
    log_event(
        event_type="security_logs_accessed",
        ip_address=ip_address,
        user_id=current_user.id,
        username=current_user.username,
        user_agent=user_agent,
        resource="/admin/security-logs",
        action="GET",
        success=True,
        status_code=200
    )
    
    # 指定日数前から現在までのログを取得
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    # 新しいものから順に取得
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "username": log.username,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "resource": log.resource,
                "action": log.action,
                "success": log.success,
                "status_code": log.status_code,
                "details": log.details
            }
            for log in logs
        ],
        "total": len(logs),
        "days_lookback": days,
        "limit_used": limit
    }

@router.get("/admin/security-stats")
async def get_security_stats(
    current_user=Depends(require_admin),
    days: int = Query(7),
    db: Session = Depends(get_db)
):
    """セキュリティ統計を取得（管理者のみ）"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # 各種イベント数をカウント
    login_success = db.query(AuditLog).filter(
        AuditLog.event_type == "login_success",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    login_failure = db.query(AuditLog).filter(
        AuditLog.event_type == "login_failure",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    rate_limit_exceeded = db.query(AuditLog).filter(
        AuditLog.event_type == "login_rate_limit_exceeded",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    unauthorized_access = db.query(AuditLog).filter(
        AuditLog.event_type == "unauthorized_admin_access",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    user_deleted = db.query(AuditLog).filter(
        AuditLog.event_type == "user_deleted",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    csv_uploads = db.query(AuditLog).filter(
        AuditLog.event_type == "csv_uploaded",
        AuditLog.timestamp >= cutoff_date
    ).count()
    
    return {
        "stats": {
            "login_success": login_success,
            "login_failure": login_failure,
            "rate_limit_exceeded": rate_limit_exceeded,
            "unauthorized_access": unauthorized_access,
            "user_deleted": user_deleted,
            "csv_uploads": csv_uploads
        },
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.delete("/admin/security-logs/{log_id}")
async def delete_security_log(
    log_id: int,
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """セキュリティログを削除（管理者のみ）"""
    
    # ログを取得して削除
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="ログが見つかりません")
    
    db.delete(log)
    db.commit()
    
    # ログ削除をログに記録
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    from app.utils.audit_logger import log_event
    log_event(
        event_type="security_log_deleted",
        ip_address=ip_address,
        user_id=current_user.id,
        username=current_user.username,
        user_agent=user_agent,
        resource=f"/admin/security-logs/{log_id}",
        action="DELETE",
        success=True,
        status_code=200
    )
    
    return {"message": "ログを削除しました"}


@router.delete("/admin/security-logs-all")
async def clear_all_security_logs(
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    """すべてのセキュリティログを削除（管理者のみ）"""
    
    # すべてのログを取得して削除数をカウント
    logs = db.query(AuditLog).all()
    deleted_count = len(logs)
    
    # すべてのログを削除
    db.query(AuditLog).delete()
    db.commit()
    
    # ログクリアをログに記録
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    from app.utils.audit_logger import log_event
    log_event(
        event_type="security_logs_cleared",
        ip_address=ip_address,
        user_id=current_user.id,
        username=current_user.username,
        user_agent=user_agent,
        resource="/admin/security-logs",
        action="DELETE_ALL",
        success=True,
        status_code=200
    )
    
    return {"message": f"{deleted_count}件のログをクリアしました"}
