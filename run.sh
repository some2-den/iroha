#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  売上実績管理システム - 起動"
echo "========================================"
echo ""

# Python コマンドの解決
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[エラー] Python が見つかりません。setup.sh を先に実行してください"
    exit 1
fi

cd "$(dirname "$0")/backend"

echo "[処理] FastAPI サーバーを起動中..."
echo "[情報] ブラウザで http://localhost:10168 にアクセスしてください"
echo "[情報] 別のPCからは http://<PCのIPアドレス>:10168 でアクセスしてください"
echo "[停止] Ctrl+C で停止"
echo ""

$PYTHON -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10168
