@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   売上実績管理システム - 起動
echo ========================================
echo.

cd backend
echo [処理] FastAPI サーバーを起動中...
echo [情報] ブラウザで http://localhost:10168 にアクセスしてください
echo [情報] 別のPCからは http://<PCのIPアドレス>:10168 でアクセスしてください
echo [停止] Ctrl+C で停止
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10168

pause