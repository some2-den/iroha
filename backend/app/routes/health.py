from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
def health_check():
    """ヘルスチェック"""
    return {"status": "ok"}
