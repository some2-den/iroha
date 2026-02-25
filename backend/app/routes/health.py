from fastapi import APIRouter
from app.config import VERSION

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
def health_check():
    """ヘルスチェック"""
    return {"status": "ok", "version": VERSION}
