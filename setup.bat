@echo off
echo.
echo ========================================
echo   売上実績管理システム - セットアップ
echo   (オンプレミス版)
echo ========================================
echo.

REM Pythonのインストール確認
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python 3.8 以上がインストールされていません
    echo https://www.python.org からダウンロードしてインストールしてください
    pause
    exit /b 1
)

echo [OK] Python がインストールされています
python --version
echo.

REM 環境変数ファイルの作成確認
if not exist backend\.env (
    echo [情報] .env ファイルを作成します
    copy backend\.env.example backend\.env
    echo [OK] backend\.env を作成しました
    echo        必要に応じて設定を編集してください
    echo.
)

REM 依存パッケージのインストール
echo [処理] Python依存パッケージをインストール中...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [エラー] パッケージのインストールに失敗しました
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] パッケージのインストールが完了しました
echo.

echo ========================================
echo   セットアップが完了しました！
echo ========================================
echo.
echo [実行方法]
echo   backend を起動: python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
echo                 (backend ディレクトリで実行)
echo.
echo   ブラウザで以下にアクセス:
echo   http://localhost:8000
echo.
echo [停止方法]
echo   Ctrl+C でサーバーを停止できます
echo.
pause
