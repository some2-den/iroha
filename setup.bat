@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   売上実績管理システム - セットアップ
echo   (オンプレミス版)
echo ========================================
echo.

REM ── Python インストール確認 ─────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python がインストールされていないか、PATH に追加されていません
    echo.
    echo  1. https://www.python.org/downloads/ から Python 3.10 以上をダウンロード
    echo  2. インストール時に「Add Python to PATH」にチェックを入れてください
    echo  3. インストール後、このバッチを再実行してください
    echo.
    pause
    exit /b 1
)

echo [OK] Python がインストールされています
python --version
echo.

REM ── pip の確認・アップグレード ─────────────────────────────
echo [処理] pip を確認中...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] pip が見つかりません。Python を再インストールしてください
    pause
    exit /b 1
)
echo [OK] pip が利用可能です
echo.

REM ── 依存パッケージのインストール ──────────────────────────
echo [処理] Python 依存パッケージをインストール中...
echo        (初回は数分かかる場合があります)
echo.
cd backend
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [エラー] パッケージのインストールに失敗しました
    echo          インターネット接続を確認してから再実行してください
    cd ..
    pause
    exit /b 1
)
cd ..
echo.
echo [OK] パッケージのインストールが完了しました
echo.

REM ── .env ファイルの作成 ────────────────────────────────────
if not exist backend\.env (
    if exist backend\.env.example (
        echo [処理] 設定ファイル (.env) を作成中...
        copy backend\.env.example backend\.env >nul
        echo [OK] backend\.env を作成しました
        echo.
        echo  ★ 重要: backend\.env を開き、以下の項目を必ず変更してください ★
        echo     SECRET_KEY= の値をランダムな文字列に変更する
        echo     （例: python -c "import secrets; print(secrets.token_hex(32))"）
        echo.
    ) else (
        echo [警告] backend\.env.example が見つかりません
        echo        backend\.env を手動で作成してください
        echo.
    )
) else (
    echo [OK] backend\.env は既に存在します
    echo.
)

echo ========================================
echo   セットアップが完了しました！
echo ========================================
echo.
echo [起動方法]
echo   同じフォルダにある run.bat をダブルクリックしてください
echo.
echo [アクセス方法]
echo   このPC:     http://localhost:10168
echo   他のPCから: http://^<このPCのIPアドレス^>:10168
echo.
echo [停止方法]
echo   サーバーウィンドウで Ctrl+C を押してください
echo.
pause
