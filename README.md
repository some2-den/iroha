# 売上実績管理Webアプリケーション

CSVファイルからの実績データアップロード・分析・ダッシュボード表示システムです。  
JWT認証・セキュリティヘッダー・監査ログを備えた本番運用対応の構成です。

## 技術スタック

| 区分 | 使用技術 |
|------|---------|
| バックエンド | Python 3.8+ / FastAPI / SQLAlchemy |
| フロントエンド | HTML5 / Vanilla JavaScript / Chart.js |
| データベース | SQLite（デフォルト） |
| 認証 | JWT（Bearer トークン / python-jose） |
| パスワード | bcrypt（passlib 経由） |
| コンテナ | Docker（オプション） |

## 機能

- **CSV アップロード**: 売上明細データを CSV で一括登録（拡張子・Content-Type・サイズ検証付き）
- **ダッシュボード**: 店舗別・日別・商品別の売上サマリー表示
- **グラフ分析**: 日別売上推移・商品別売上 TOP10
- **個人別成績**: スタッフ別のサービス成績集計（件数・粗利）
- **au+1コレクション分析**: カテゴリ別・日別・合計の集計
- **スマートフォン分析**: 機種別単価・サマリー集計
- **ユーザー管理**: 管理者によるアカウント作成・パスワードリセット・店舗コード変更
- **監査ログ**: ログイン・操作履歴の記録・参照
- **セキュリティヘッダー**: X-Frame-Options / X-Content-Type-Options / HSTS 等

## プロジェクト構成

```
.
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── admin.py        # AdminUser モデル
│   │   │   ├── audit_log.py    # 監査ログモデル
│   │   │   ├── sales.py        # 売上トランザクションモデル
│   │   │   ├── store.py        # 店舗モデル
│   │   │   └── user.py         # ユーザーモデル
│   │   ├── routes/
│   │   │   ├── admin.py        # 管理者向け操作 API
│   │   │   ├── audit.py        # 監査ログ API
│   │   │   ├── auth.py         # 認証・ユーザー管理 API
│   │   │   ├── health.py       # ヘルスチェック API
│   │   │   └── sales.py        # 売上データ API
│   │   ├── services/
│   │   │   ├── csv_service.py  # CSV 取込ロジック
│   │   │   └── sales_service.py# 集計・分析ロジック
│   │   ├── utils/
│   │   │   ├── jwt_auth.py     # JWT 生成・検証・認可デコレータ
│   │   │   ├── audit_logger.py # 監査ログ書込ユーティリティ
│   │   │   └── rate_limiter.py # レート制限
│   │   ├── templates/
│   │   │   └── index.html      # シングルページ フロントエンド
│   │   ├── config.py           # 環境変数設定
│   │   ├── database.py         # DB 接続・セッション管理
│   │   ├── main.py             # FastAPI アプリ本体・ミドルウェア
│   │   └── schemas.py          # Pydantic スキーマ
│   ├── requirements.txt
│   ├── reset_db.py             # DB 初期化スクリプト
│   ├── .env                    # 環境変数（Git 管理外）
│   └── .env.example            # 環境変数テンプレート
├── frontend/                   # React/TypeScript 版（オプション）
│   └── src/
│       └── App.tsx
├── setup.bat                   # Windows セットアップスクリプト
├── run.bat                     # Windows 起動スクリプト
├── setup.sh                    # Linux/macOS セットアップスクリプト
├── run.sh                      # Linux/macOS 起動スクリプト
└── README.md
```

## セットアップ

### 前提条件

- Python 3.8 以上
- pip

### 手順

#### 1. セットアップスクリプトを実行

**Windows:**
```bat
setup.bat
```

**Linux/macOS:**
```bash
chmod +x setup.sh run.sh
./setup.sh
```

スクリプトが以下を自動実行します：
- Python バージョン確認
- 依存パッケージインストール
- `backend/.env` ファイル作成

#### 2. 環境変数を設定（初回必須）

`backend/.env.example` をコピーして編集：

**Windows:**
```bat
copy backend\.env.example backend\.env
```

**Linux/macOS:**
```bash
cp backend/.env.example backend/.env
```

`backend/.env` を開き、最低限 `SECRET_KEY` を設定してください：

```env
DEBUG=true
SECRET_KEY=ここに32文字以上のランダムな文字列を設定する
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
MAX_UPLOAD_SIZE_MB=10
```

`SECRET_KEY` の生成例：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ `backend/.env` は絶対に Git にコミットしないこと。`.gitignore` に追加してください。

#### 3. 起動

**Windows:**
```bat
run.bat
```

**Linux/macOS:**
```bash
./run.sh
```

または直接起動：
```bash
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10168
```

ブラウザで `http://localhost:8000` にアクセスしてください。

### 初期管理者アカウント

初回起動時に管理者アカウントが自動作成されます。  
パスワードはサーバーの起動ログに **1 回だけ** 表示されます。必ずメモしてください。

```
INFO:     Created default admin user: admin / [ランダムパスワード]
```

---

## 認証

すべての API（ヘルスチェック・ログインを除く）は **JWT Bearer トークン認証** が必要です。

### ログインフロー

```
POST /api/auth/login
  → access_token を取得

以降のリクエストに Authorization: Bearer <access_token> ヘッダーを付与
```

### ユーザーロール

| ロール | 説明 |
|--------|------|
| `admin` | 全操作可能（ユーザー管理・データ削除・監査ログ等） |
| `manager` | 売上データ閲覧・CSV アップロード可能 |
| `user` | 売上データ閲覧のみ |

### トークン仕様

- 形式: HS256 JWT
- 有効期限: 8 時間
- ペイロード: `{"sub": "<user_id>", "exp": <timestamp>}`

---

## API エンドポイント一覧

### 認証不要

| メソッド | パス | 説明 |
|--------|------|------|
| `GET` | `/` | フロントエンド（ダッシュボード） |
| `GET` | `/api/health` | ヘルスチェック |
| `POST` | `/api/auth/login` | ログイン（JWT 取得） |
| `POST` | `/api/auth/logout` | ログアウト |

### 要認証（全ロール共通）

| メソッド | パス | 説明 |
|--------|------|------|
| `POST` | `/api/upload` | CSV アップロード |
| `GET` | `/api/transactions` | 売上トランザクション一覧 |
| `GET` | `/api/summary/daily` | 日別売上サマリー |
| `GET` | `/api/summary/product` | 商品別売上サマリー |
| `GET` | `/api/summary/staff-list` | スタッフ一覧 |
| `GET` | `/api/summary/staff-performance` | スタッフ別成績（詳細） |
| `GET` | `/api/summary/staff-aggregated` | スタッフ別成績（集計済み） |
| `GET` | `/api/au1-collection/summary` | au+1コレクション サマリー |
| `GET` | `/api/au1-collection/detail` | au+1コレクション 詳細 |
| `GET` | `/api/au1-collection/category` | au+1コレクション カテゴリ別 |
| `GET` | `/api/au1-collection/daily` | au+1コレクション 日別 |
| `GET` | `/api/au1-collection/total` | au+1コレクション 合計 |
| `GET` | `/api/smartphone/unit-price` | スマートフォン 機種別単価 |
| `GET` | `/api/smartphone/summary` | スマートフォン サマリー |
| `POST` | `/api/auth/change-password` | パスワード変更（自分） |
| `GET` | `/api/admin/stores` | 店舗一覧取得 |

### 要管理者権限（`admin` ロールのみ）

| メソッド | パス | 説明 |
|--------|------|------|
| `GET` | `/api/auth/admin/users` | ユーザー一覧 |
| `POST` | `/api/auth/admin/create-user` | ユーザー作成 |
| `PUT` | `/api/auth/admin/users/{username}` | ユーザー情報更新（名前・店舗コード） |
| `DELETE` | `/api/auth/admin/users/{username}` | ユーザー削除 |
| `POST` | `/api/auth/admin/reset-password` | パスワードリセット（一時パスワード発行） |
| `POST` | `/api/admin/verify-password` | 管理者パスワード確認 |
| `POST` | `/api/admin/change-password` | 管理者パスワード変更 |
| `GET` | `/api/admin/sales-data` | 全売上データ取得 |
| `POST` | `/api/admin/clear-data` | 売上データ全削除 |
| `POST` | `/api/admin/stores` | 店舗追加 |
| `DELETE` | `/api/admin/delete-store` | 店舗削除 |
| `GET` | `/api/admin/security-logs` | 監査ログ一覧（`days`・`limit` パラメータ対応） |
| `GET` | `/api/admin/security-stats` | 監査ログ統計 |
| `DELETE` | `/api/admin/security-logs/{log_id}` | 監査ログ個別削除 |
| `DELETE` | `/api/admin/security-logs-all` | 監査ログ全削除 |

**共通クエリパラメータ（売上データ系）:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `store_code` | string | 店舗コード |
| `start_date` | ISO 8601 | 集計開始日 |
| `end_date` | ISO 8601 | 集計終了日 |
| `staff_id` | string | スタッフ ID |

---

## CSV フォーマット

アップロードする CSV は以下のカラムを含む必要があります（ヘッダー行あり）：

```
販売日時,店舗コード,商品コード,商品名,数量,単価,合計金額,粗利,スタッフID,スタッフ名
2026-02-18 10:00:00,S001,P001,商品A,1,1000,1000,200,U001,田中太郎
```

- エンコーディング: UTF-8
- 最大ファイルサイズ: `MAX_UPLOAD_SIZE_MB`（デフォルト 10 MB）
- 許可される Content-Type: `text/csv` / `application/csv` / `text/plain`

---

## 本番環境・外部公開時の設定

外部に公開する場合は、**`backend/.env`** に以下を**必ず**設定してください。

```
プロジェクトルート/
└── backend/
    └── .env   ← このファイルを編集する
```

```env
# ファイルパス: backend/.env

# API ドキュメント(/docs)を非公開にし、デバッグ情報を隠す
DEBUG=false

# 32 文字以上のランダムな秘密鍵（漏洩するとなりすましが可能になる）
SECRET_KEY=ここに生成した文字列を貼り付ける

# アクセスを許可するオリジン（自分のドメインのみ指定）
CORS_ORIGINS=https://yourdomain.com

# CSV アップロードの最大サイズ（MB）
MAX_UPLOAD_SIZE_MB=10
```

### 環境変数一覧

| 変数 | デフォルト | 本番推奨値 | 説明 |
|------|-----------|-----------|------|
| `DEBUG` | `false` | `false` | `true` にすると `/docs`（API 仕様書）が誰でも閲覧可能になる |
| `SECRET_KEY` | *(内部デフォルト)* | **必ず変更** | JWT 署名用秘密鍵 |
| `CORS_ORIGINS` | *(同一オリジンのみ)* | `https://yourdomain.com` | 許可するオリジン（カンマ区切り複数指定可） |
| `MAX_UPLOAD_SIZE_MB` | `10` | `10` | CSV アップロードの上限サイズ |
| `DATABASE_URL` | `sqlite:///./sales.db` | *(任意)* | データベース接続 URL |

### SECRET_KEY 生成コマンド

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# 例: a3f8c2d1e4b5a6f7c8d9e0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1
```

> ⚠️ `backend/.env` は絶対に Git にコミットしないこと。`.gitignore` に追加してください。

---

## Docker での実行（オプション）

```bash
docker-compose up -d
```

アクセス: http://localhost:8000

停止:
```bash
docker-compose down
```

---

## トラブルシューティング

### ログインできない

- ブラウザの開発者ツール（F12）→ コンソールでエラーを確認
- `backend/.env` に `SECRET_KEY` が設定されているか確認
- サーバー起動ログに「Created default admin user」が表示されていることを確認し、そのパスワードを使用する

### 401 Unauthorized が返り続ける

- トークンの有効期限（8 時間）が切れていないか確認
- ログアウト後に再ログインしてトークンを再取得する

### CSV アップロードが失敗する

- エンコーディングが UTF-8 であることを確認
- ファイルの拡張子が `.csv` であることを確認
- ファイルサイズが `MAX_UPLOAD_SIZE_MB` 以下であることを確認
- 必須カラム（販売日時・店舗コード等）が全て含まれているか確認

### ポート 8000 が既に使用中

別のポートで起動：

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

その後、`http://localhost:8080` にアクセスしてください。

### フロントエンド画面が表示されない

- バックエンドが起動しているか確認（`http://localhost:8000/api/health` でレスポンスがあるか）
- ブラウザのコンソール（F12）でエラーログを確認

---

## セキュリティ機能

| 機能 | 詳細 |
|------|------|
| JWT 認証 | 全 API（公開エンドポイントを除く）に Bearer トークン必須 |
| セキュリティヘッダー | `X-Content-Type-Options` / `X-Frame-Options` / `X-XSS-Protection` / `Referrer-Policy` / `Strict-Transport-Security`（本番のみ） |
| CORS 制限 | `CORS_ORIGINS` 未設定時は同一オリジンのみ許可 |
| パスワード強度 | 8 文字以上・英字・数字を含む必要あり |
| パスワードハッシュ | bcrypt（passlib 経由） |
| CSV 検証 | 拡張子・Content-Type・ファイルサイズの多段検証 |
| レート制限 | ブルートフォース対策 |
| 監査ログ | ログイン・操作イベントを DB に記録 |
| API ドキュメント制御 | `DEBUG=false` 時は `/docs` / `/redoc` / `/openapi.json` を非公開 |

---

## サポート

問題が発生した場合は、GitHub Issues で報告してください。
