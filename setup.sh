#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  売上実績管理システム - セットアップ"
echo "  (オンプレミス版)"
echo "========================================"
echo ""

# ── Python インストール確認 ─────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[エラー] Python がインストールされていません"
    echo ""
    echo "  Debian/Ubuntu: sudo apt install python3 python3-pip"
    echo "  RHEL/Fedora:   sudo dnf install python3 python3-pip"
    echo "  macOS:         brew install python3"
    echo ""
    exit 1
fi

echo "[OK] Python が見つかりました: $($PYTHON --version)"
echo ""

# ── pip の確認 ─────────────────────────────────────────────
if ! $PYTHON -m pip --version &>/dev/null; then
    echo "[エラー] pip が見つかりません"
    echo ""
    echo "  Debian/Ubuntu: sudo apt install python3-pip"
    echo "  RHEL/Fedora:   sudo dnf install python3-pip"
    echo ""
    exit 1
fi
echo "[OK] pip が利用可能です"
echo ""

# ── 依存パッケージのインストール ──────────────────────────
echo "[処理] Python 依存パッケージをインストール中..."
echo "       (初回は数分かかる場合があります)"
echo ""
cd "$(dirname "$0")/backend"
$PYTHON -m pip install -r requirements.txt
cd ..
echo ""
echo "[OK] パッケージのインストールが完了しました"
echo ""

# ── .env ファイルの作成 ────────────────────────────────────
if [ ! -f backend/.env ]; then
    if [ -f backend/.env.example ]; then
        cp backend/.env.example backend/.env
        echo "[OK] backend/.env を作成しました"
        echo ""
        echo "  ★ 重要: backend/.env を開き、以下の項目を必ず変更してください ★"
        echo "     SECRET_KEY= の値をランダムな文字列に変更する"
        echo "     （例: python3 -c \"import secrets; print(secrets.token_hex(32))\"）"
        echo ""
    else
        echo "[警告] backend/.env.example が見つかりません"
        echo "       backend/.env を手動で作成してください"
        echo ""
    fi
else
    echo "[OK] backend/.env は既に存在します"
    echo ""
fi

# ── 実行権限の付与 ─────────────────────────────────────────
chmod +x run.sh 2>/dev/null || true

echo "========================================"
echo "  セットアップが完了しました！"
echo "========================================"
echo ""
echo "[起動方法]"
echo "  ./run.sh"
echo ""
echo "[アクセス方法]"
echo "  このPC:     http://localhost:10168"
echo "  他のPCから: http://<このPCのIPアドレス>:10168"
echo ""
echo "[停止方法]"
echo "  サーバーウィンドウで Ctrl+C を押してください"
echo ""
