# 売上実績管理システム - 完全仕様書

**最終更新**: 2026年2月20日  
**バージョン**: 2.0.0

---

## 目次

1. [システム概要](#1-システム概要)
2. [システムアーキテクチャ](#2-システムアーキテクチャ)
3. [データベーススキーマ](#3-データベーススキーマ)
4. [ユーザーロールと権限](#4-ユーザーロールと権限)
5. [主要な処理フロー](#5-主要な処理フロー)
6. [API仕様](#6-api仕様)
7. [CSV処理仕様](#7-csv処理仕様)
8. [UI/UXフロー](#8-uiuxフロー)
9. [セキュリティとログ](#9-セキュリティとログ)

---

## 1. システム概要

### 1.1 目的

売上実績データをCSVファイルからアップロードし、複数の店舗・スタッフの成績を管理・分析するWebシステム。スマートフォン販売、au+1Collection加入、MNPなどの詳細なサービス別分析に対応。

### 1.2 特徴

- **マルチテナント対応**: 複数店舗のデータを一元管理
- **ロールベースアクセス制御**: 管理者、マネージャー、一般ユーザーで機能を制限
- **リアルタイム集計**: CSV アップロード後の自動集計・分析
- **監査ログ**: すべての重要操作を記録
- **CSVサポート**: CP932（Shift-JIS）エンコーディング対応

### 1.3 動作環境

| 項目 | 仕様 |
|-----|------|
| バックエンド | Python 3.10以上、FastAPI |
| フロントエンド | React 18以上、TypeScript |
| データベース | SQLite (sales.db) |
| Webサーバー | Uvicorn (非本番用) |
| 推奨ブラウザ | Chrome/Firefox/Safari (最新版) |
| ポート | 10168 |

---

## 2. システムアーキテクチャ

### 2.1 全体構成図

```
┌─────────────────────────────────────────┐
│  ブラウザ (React + TypeScript)          │
│  - Dashboard タブ                      │
│  - 個人別成績・グラフ タブ              │
│  - 分析・グラフ タブ                    │
│  - Admin パネル (管理者のみ)            │
└────────────────┬──────────────────────┘
                 │ HTTP/REST API
                 ↓
┌─────────────────────────────────────────┐
│ FastAPI バックエンド                    │
│ ├─ routes/                              │
│ │  ├─ main.py (CSV アップロード)       │
│ │  ├─ sales.py (売上API)               │
│ │  ├─ admin.py (管理者API)             │
│ │  ├─ health.py (ヘルスチェック)       │
│ │  └─ auth.py (認証・ユーザー管理)     │
│ ├─ services/                            │
│ │  ├─ csv_service.py (CSV処理)         │
│ │  └─ sales_service.py (売上計算)      │
│ ├─ models/ (SQLAlchemy ORM)             │
│ │  ├─ sales.py (トランザクション)      │
│ │  ├─ user.py (ユーザー)               │
│ │  ├─ store.py (店舗)                  │
│ │  ├─ admin.py (管理者ユーザー)        │
│ │  └─ audit_log.py (監査ログ)          │
│ └─ templates/                           │
│    └─ index.html (SPA)                  │
└────────────────┬──────────────────────┘
                 │ SQL
                 ↓
        ┌─────────────────┐
        │  SQLite DB      │
        │  (sales.db)     │
        └─────────────────┘
```

### 2.2 ディレクトリ構成

```
pj1/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI アプリケーション起動
│   │   ├── config.py                  # 設定情報
│   │   ├── database.py                # DB 接続管理
│   │   ├── schemas.py                 # Pydantic スキーマ
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── sales.py               # SalesTransaction モデル
│   │   │   ├── user.py                # User モデル
│   │   │   ├── store.py               # Store モデル
│   │   │   ├── admin.py               # AdminUser モデル
│   │   │   └── audit_log.py           # AuditLog モデル
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # POST /api/upload
│   │   │   ├── sales.py               # GET /api/summary/* など
│   │   │   ├── admin.py               # 管理者API
│   │   │   ├── auth.py                # 認証・ユーザー管理
│   │   │   └── health.py              # GET /api/health
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── csv_service.py         # CSV 解析・処理
│   │   │   └── sales_service.py       # 売上計算・集計
│   │   ├── static/                    # 静的ファイル
│   │   └── templates/
│   │       └── index.html             # React SPA
│   ├── requirements.txt
│   ├── Dockerfile
│   └── reset_db.py                    # DB リセットスクリプト
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # メインコンポーネント
│   │   ├── api.ts                     # API クライアント
│   │   ├── index.tsx                  # エントリーポイント
│   │   ├── components/
│   │   │   ├── Charts.tsx             # グラフコンポーネント
│   │   │   └── FileUpload.tsx         # ファイルアップロード
│   │   └── pages/
│   │       └── Dashboard.tsx          # ダッシュボード
│   ├── package.json
│   └── tsconfig.json
├── SPECIFICATION.md                   # 基本仕様書
├── TEST_GUIDE.md                      # テストガイド
├── SYSTEM_DOCUMENTATION.md            # このファイル
└── README.md
```

---

## 3. データベーススキーマ

### 3.1 SalesTransaction テーブル（売上トランザクション）

```sql
CREATE TABLE sales_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATE,              -- 売上日付
    transaction_time TIME,              -- 売上時刻
    store_code VARCHAR(20),             -- 統括拠点コード (店舗コード)
    product_code VARCHAR(50),           -- 商品コード
    product_name VARCHAR(255),          -- 商品名
    ticket_number VARCHAR(50),          -- 伝票番号
    quantity INTEGER,                   -- 販売数量
    unit_price DECIMAL(10, 2),          -- 販売単価
    total_price DECIMAL(10, 2),         -- 販売明細額
    gross_profit DECIMAL(10, 2),        -- 粗利
    staff_id VARCHAR(50),               -- 実績ユーザーID
    staff_name VARCHAR(100),            -- 実績担当者名
    large_category VARCHAR(100),        -- 大分類名
    small_category VARCHAR(100),        -- 中分類名
    procedure_name VARCHAR(100),        -- 手続区分名
    procedure_name_2 VARCHAR(100),      -- 手続区分2名
    service_category VARCHAR(60),       -- MNPJudge サービスカテゴリ判定結果
    customer_division VARCHAR(100),     -- 顧客契約区分名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_store_code ON sales_transactions(store_code);
CREATE INDEX idx_staff_id ON sales_transactions(staff_id);
CREATE INDEX idx_transaction_date ON sales_transactions(transaction_date);
CREATE INDEX idx_large_category ON sales_transactions(large_category);
CREATE INDEX idx_ticket_number ON sales_transactions(ticket_number);
```

### 3.2 User テーブル（一般ユーザー）

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,  -- ログインID
    password_hash VARCHAR(255) NOT NULL,   -- パスワードハッシュ
    staff_id VARCHAR(50),                  -- スタッフID
    staff_name VARCHAR(100),               -- スタッフ名
    store_code VARCHAR(20),                -- 割り当て店舗コード
    role VARCHAR(20),                      -- admin / manager / user
    is_active BOOLEAN DEFAULT TRUE,        -- アクティブ状態
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

**ロール説明**:
- **admin**: 全店舗データへのアクセス、ユーザー管理、データ削除可能
- **manager**: 全店舗データの閲覧、分析可能 (操作制限あり)
- **user**: 割り当てられた店舗のみデータ閲覧可能

### 3.3 Store テーブル（店舗情報）

```sql
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_code VARCHAR(20) UNIQUE NOT NULL,  -- 統括拠点コード
    store_name VARCHAR(100),                 -- 店舗名
    location VARCHAR(255),                   -- 所在地
    phone VARCHAR(20),                       -- 電話番号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 AdminUser テーブル（管理者）

```sql
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,  -- 通常 'admin'
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 3.5 AuditLog テーブル（監査ログ）

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(50),                -- login / logout / data_upload / data_delete / store_deleted など
    user_id INTEGER,
    username VARCHAR(50),
    ip_address VARCHAR(45),
    status VARCHAR(20),                    -- success / failure
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_event_type ON audit_logs(event_type);
CREATE INDEX idx_timestamp ON audit_logs(timestamp);
```

---

## 4. ユーザーロールと権限

### 4.1 権限マトリックス

| 機能 | 管理者 (admin) | マネージャー (manager) | 一般ユーザー (user) |
|-----|----------------|-----------------------|-------------------|
| CSV アップロード | ✅ | ❌ | ❌ |
| データ閲覧 (全店舗) | ✅ | ✅ | ❌ |
| データ閲覧 (割り当て店舗) | ✅ | ✅ | ✅ |
| ユーザー管理 | ✅ | ❌ | ❌ |
| パスワード変更 | ✅ | ✅ | ✅ |
| データ削除 | ✅ | ❌ | ❌ |
| 店舗管理 (追加/削除) | ✅ | ❌ | ❌ |
| 監査ログ表示 | ✅ | ❌ | ❌ |
| セキュリティ設定 | ✅ | ❌ | ❌ |

### 4.2 デフォルトアカウント

| ユーザー名 | パスワード | ロール |
|-----------|-----------|--------|
| admin | admin123 | 管理者 |

---

## 5. 主要な処理フロー

### 5.1 CSVアップロード処理フロー

```
ユーザー (フロントエンド)
    ↓
[CSV ファイル選択]
    ↓
fetch('/api/upload', FormData)
    ↓
バックエンド (POST /api/upload)
    ↓
[ファイル保存]
    ↓
csv_service.parse_csv()
    ├─ ファイルをバイナリで読み込み
    ├─ エンコーディング自動検出 (CP932/UTF-8)
    ├─ CSV 解析 (75カラム検証)
    └─ デフォルト値を補填
    ↓
[各行を処理]
    ├─ カラム値を抽出
    ├─ 日時フォーマット変換
    ├─ MNPJudge で service_category を判定
    └─ Store 自動作成 (未登録の場合)
    ↓
[重複チェック]
    ├─ MD5 ハッシュで完全重複判定
    ├─ 重複: スキップ
    └─ 新規: DB登録予定
    ↓
[トランザクション開始]
    ↓
sales_transactions テーブルに INSERT
    ↓
[トランザクション確定]
    ↓
audit_log に記録
    ↓
レスポンス: {新規件数, 重複件数}
    ↓
フロントエンド: ダッシュボード自動更新
```

### 5.2 データ表示・集計処理フロー

```
ユーザー (フロントエンド - Dashboard タブ)
    ↓
[店舗選択] (選択肢は getAllStores() で取得)
    ↓
fetch('/api/summary/daily?store_code=S002001')
    ↓
バックエンド (GET /api/summary/daily)
    ├─ store_code フィルタリング
    ├─ transaction_date でグループ化
    ├─ SUM(total_price), SUM(gross_profit) を集計
    └─ 日付でソート
    ↓
レスポンス: [{date, total_sales, gross_profit, transaction_count}, ...]
    ↓
フロントエンド: Chart.js でグラフ描画
    ↓
[スタッフ選択フィルタ]
    ↓
fetch('/api/summary/staff-list?store_code=S002001')
    ↓
バックエンド: スタッフ一覧取得・フィルタ
    ↓
更新されたデータでグラフ再描画
```

### 5.3 Admin パネル - 店舗管理フロー

```
ユーザー (管理者)
    ↓
【ログイン】
fetch('/api/admin/verify-password', {password})
    ↓
バックエンド: パスワード検証
    ├─ 正確: sessionStorage['adminAuthenticated'] = true
    ├─ 監査ログ記録: 'admin_login'
    └─ Admin パネル表示
    ↓
【店舗一覧表示】
fetch('/api/admin/stores')
    ↓
バックエンド: SELECT * FROM stores
    ↓
テーブル描画 (storeListTableBody)
    ↓
    ┌─────────────────────────────┐
    │ 🏢 店舗管理テーブル           │
    │ ┌───┬──────┬────┬──────┐    │
    │ │ID │店舗名│所在│操作  │    │
    │ ├───┼──────┼────┼──────┤    │
    │ │S001│店1  │東京│[削除]│    │
    │ │S002│店2  │愛知│[削除]│    │
    │ └───┴──────┴────┴──────┘    │
    └─────────────────────────────┘
    ↓
【削除ボタンクリック】
    ↓
confirm('本当に削除しますか?\nこの操作は取り消せません')
    ↓
[キャンセル] → 処理終了
[OK] → 続行
    ↓
fetch('/api/admin/delete-store', {method: DELETE, store_id})
    ↓
バックエンド (DELETE /api/admin/delete-store)
    ├─ Store 存在確認
    ├─ 関連トランザクション確認 (警告)
    ├─ Store 削除実行
    ├─ 監査ログ記録: 'store_deleted'
    └─ レスポンス: {success, message}
    ↓
フロントエンド: 成功メッセージ表示
    ↓
await loadAdminStoreList()  # 一覧再読み込み
```

### 5.4 ユーザーログインフロー

```
新規ユーザー訪問
    ↓
[ログイン画面表示]
    ↓
username / password 入力
    ↓
fetch('/api/auth/login', {username, password})
    ↓
バックエンド (POST /api/auth/login)
    ├─ 既存ユーザーか確認
    │  ├─ 存在: パスワード検証
    │  └─ 未存在: 新規作成 (デフォルトパスワード)
    ├─ role・store_code を返却
    └─ 監査ログ記録: 'user_login'
    ↓
フロントエンド: localStorage に保存
    ├─ userId
    ├─ username
    ├─ userRole
    └─ userStoreCode
    ↓
【ロール別表示制御】
    ├─ admin / manager: 全店舗データ表示
    └─ user: 割り当て店舗のみ表示
    ↓
ダッシュボード表示
```

### 5.5 MNPJudge サービスカテゴリ判定フロー

```
CSV : 伝票番号ごとに複数行
    ↓
[同じ伝票番号でグループ化]
    ↓
MNPJudge ロジック
    ↓
【判定ロジック】

1. au+1Collection チェック
   └─ 大分類 = "au+1 Collection" ? 
      ✅ → "au+1Collection" で決定

2. 手続区分チェック
   └─ procedure_name / procedure_name_2 に "MNP" が含まれる?
      ❌ → "その他" で決定
      ✅ → 次へ

3. MNP タイプ判定
   ├─ 顧客区分が "auMNP" ?
   │  ├─ au 端末 + au-SIM → "auMNP(端末あり)"
   │  └─ au-SIM のみ → "auMNP(SIM単体)"
   │
   └─ 顧客区分が "UQMNP" ?
      ├─ UQ 端末 + UQ-SIM → "UQMNP(端末あり)"
      └─ UQ-SIM のみ → "UQMNP(SIM単体)"

    ↓
結果を各トランザクション行に記録
```

---

## 6. API仕様

### 6.1 認証・ユーザー管理 API

#### ログイン
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "user001",
  "password": "password123"
}

レスポンス (200):
{
  "id": 1,
  "username": "user001",
  "staff_name": "山田太郎",
  "store_code": "S002001",
  "role": "user",
  "message": "ログインしました"
}

エラー (401):
{"detail": "ユーザー名またはパスワードが正しくありません"}
```

#### ユーザー一覧取得
```
GET /api/auth/users?admin_user_id=1

レスポンス (200):
{
  "data": [
    {
      "id": 1,
      "username": "user001",
      "staff_name": "山田太郎",
      "store_code": "S002001",
      "role": "user",
      "is_active": true
    },
    ...
  ]
}
```

### 6.2 CSV アップロード API

#### ファイルアップロード
```
POST /api/upload
Content-Type: multipart/form-data

Body:
file: [binary CSV file]

レスポンス (200):
{
  "message": "Successfully uploaded 585 new transactions (skipped 229 duplicates)",
  "count": 585,
  "duplicates": 229
}

エラー (400):
{"detail": "CSV解析失敗: invalid columns"}
```

### 6.3 売上データ API

#### 日次売上サマリー
```
GET /api/summary/daily?store_code=S002001&start_date=2026-02-01&end_date=2026-02-28

レスポンス (200):
[
  {
    "date": "2026-02-01",
    "total_sales": 1500000,
    "gross_profit": 450000,
    "transaction_count": 45
  },
  ...
]
```

#### au+1Collection 実績サマリー
```
GET /api/au1-collection/summary?store_code=S002001

レスポンス (200):
[
  {
    "staff_id": "ST001",
    "staff_name": "山田太郎",
    "transaction_count": 15,
    "total_sales": 450000,
    "gross_profit": 135000
  },
  ...
]
```

#### スマートフォン販売詳細
```
GET /api/smartphone/unit-price?store_code=S002001

レスポンス (200):
[
  {
    "staff_id": "ST001",
    "staff_name": "山田太郎",
    "au1_gross_profit": 45000,
    "smartphone_count": 5,
    "iphone_count": 3,
    "unit_price": 7500
  },
  ...
]
```

### 6.4 管理者 API

#### パスワード検証
```
POST /api/admin/verify-password
Content-Type: application/json

{
  "password": "admin123"
}

レスポンス (200):
{
  "success": true,
  "message": "ログインしました"
}

エラー (401):
{"detail": "パスワードが正しくありません"}
```

#### 店舗一覧取得
```
GET /api/admin/stores

レスポンス (200):
{
  "data": [
    {
      "id": 1,
      "store_code": "S002001",
      "store_name": "テスト店舗1",
      "location": "東京都",
      "phone": "090-xxxx-xxxx"
    },
    ...
  ],
  "count": 3
}
```

#### 店舗削除
```
DELETE /api/admin/delete-store?store_id=1&admin_user_id=1

レスポンス (200):
{
  "success": true,
  "message": "店舗「テスト店舗1」(コード: S002001)を削除しました"
}

エラー (404):
{"detail": "店舗が見つかりません"}
```

#### データクリア
```
POST /api/admin/clear-data

レスポンス (200):
{
  "success": true,
  "message": "すべての売上データを削除しました"
}
```

---

## 7. CSV処理仕様

### 7.1 CSVフォーマット

- **エンコーディング**: CP932 (Shift-JIS) / UTF-8 自動検出
- **カラム数**: 74カラム (1-74 インデックス)
- **区切り文字**: カンマ (,)
- **改行文字**: LF または CRLF

### 7.2 重要なカラムマッピング

| 位置 | カラム名 | DB フィールド | 備考 |
|------|---------|---------------|------|
| 1 | 統括拠点コード | store_code | 必須、店舗識別 |
| 4 | 売上日付 | transaction_date | 日付フォーマット: YYYY-MM-DD |
| 5 | 売上時刻 | transaction_time | 時刻フォーマット: HH:MM:SS |
| 7 | 売上伝票番号 | ticket_number | グループ化・重複排除用 |
| 16 | 商品コード | product_code | - |
| 17 | POS表示商品名 | product_name | - |
| 21 | 大分類名 | large_category | MNPJudge 判定に使用 |
| 23 | 中分類名 | small_category | au+1Collection 判定 |
| 30 | 数量 | quantity | 数値 |
| 31 | 販売単価（税込） | unit_price | decimal(10,2) |
| 32 | 販売明細額（税込） | total_price | decimal(10,2) |
| 48 | 手続区分名 | procedure_name | MNP 判定に使用 |
| 50 | 手続区分2名 | procedure_name_2 | MNP 判定に使用 |
| 57 | 実績ユーザーID | staff_id | **重要**: 売上者ID |
| 58 | 実績担当者姓 | staff_name (姓) | - |
| 59 | 実績担当者名 | staff_name (名) | 姓+名で連結 |
| 64 | お客様契約区分名 | customer_division | MNP 判定に使用 |
| 73 | 粗利 | gross_profit | decimal(10,2) |

### 7.3 データ検証ルール

```python
# 型チェック
- quantity: 整数 > 0
- unit_price: 数値 >= 0
- total_price: 数値 >= 0
- gross_profit: 数値 >= 0

# 必須フィールド
- store_code: 長さ 1-20
- ticket_number: 長さ 1-50
- staff_id: 長さ 1-50
- transaction_date: 有効な日付

# フォーマット
- transaction_date: YYYY-MM-DD
- transaction_time: HH:MM:SS (不正値は補填)
```

### 7.4 エラーハンドリング

| エラー | 処理 |
|--------|------|
| ファイルなし | エラーメッセージ返却 |
| 無効なエンコーディング | CP932 / UTF-8 自動判定 |
| カラム数不足 | エラーメッセージ返却 |
| 無効な日付 | デフォルト値を使用 |
| 重複行 | スキップ (カウントに含む) |
| DB エラー | トランザクション ロールバック |

---

## 8. UI/UXフロー

### 8.1 ログインから ダッシュボード表示まで

```
【1】ブラウザで localhost:10168 にアクセス
      ↓
【2】ログイン画面が表示
      ├─ ユーザー名入力フィールド
      ├─ パスワード入力フィールド
      └─ ログインボタン
      ↓
【3】ユーザー名 / パスワード入力
      ↓
【4】[ログイン] ボタンをクリック
      ├─ fetch('/api/auth/login')
      └─ 認証結果待機
      ↓
【5】認証成功の場合
      ├─ localStorage に userId, username, userRole, userStoreCode を保存
      ├─ sessionStorage に selectedStoreCode を設定 (admin/manager のみ)
      └─ ダッシュボードを表示
      ↓
【6】ダッシュボード初期表示
      ├─ 「全店舗」を選択状態に設定 (admin/manager)
      ├─ または割り当て店舗を選択 (user)
      └─ 各種データ読み込み開始

【成功】ダッシュボード表示完了
【失敗】エラーメッセージ表示 → ログイン画面に戻る
```

### 8.2 ダッシュボード - 店舗選択から グラフ表示まで

```
【1】店舗ドロップダウン表示
      ├─ 管理者 / マネージャー: 「--全店舗--」+ 全店舗リスト
      └─ 一般ユーザー: 割り当て店舗のみ (選択不可)
      ↓
【2】店舗を選択
      ├─ fetch('/api/summary/daily?store_code=S002001')
      ├─ fetch('/api/summary/product?store_code=S002001')
      ├─ fetch('/api/au1-collection/daily?store_code=S002001')
      └─ 3つの GET リクエストを並行実行
      ↓
【3】データ読み込み完了
      ├─ Chart.js インスタンス初期化
      ├─ X軸: 日付, Y軸: 売上 / 粗利
      └─ グラフ描画
      ↓
【4】グラフ下のテーブルに詳細データ表示
      ├─ スタッフ別実績
      ├─ 中分類別実績
      └─ スマートフォン単価
      ↓
【成功】ダッシュボード表示完了
```

### 8.3 CSVアップロード処理フロー (UI)

```
【1】ダッシュボード上部の「CSVをアップロード」セクション表示
      ├─ ドラッグ&ドロップエリア (淡青背景)
      └─ 「ファイルを選択」ボタン
      ↓
【2】ファイル選択
      ├─ ドラッグ&ドロップ: .csv ファイルをドロップ
      └─ または「ファイルを選択」で選択
      ↓
【3】ファイル選択完了
      ├─ ファイル名表示
      └─ 「アップロード」ボタン有効化
      ↓
【4】[アップロード] ボタンをクリック
      ├─ ローディングアイコン表示
      ├─ fetch('/api/upload', FormData)
      └─ バックエンド処理中...
      ↓
【5】アップロード完了
      ├─ ✅ "ファイルをアップロードしました"
      ├─ {新規件数} に新しいデータが追加
      └─ {重複件数} 件をスキップ
      ↓
【6】ダッシュボード自動更新
      ├─ グラフ再描画
      ├─ テーブルデータ更新
      └─ 統計情報更新
      ↓
【成功】新しいデータがダッシュボードに反映
【失敗】エラーメッセージ表示 → ユーザーに対応を通知
```

### 8.4 Admin パネル - ログインから店舗削除まで

```
【1】ダッシュボード上部ナビゲーションバーに「管理者」タブ表示

【2】「管理者」タブをクリック
      ├─ admin 権限確認
      └─ 未認証: ログインフォーム表示
      ↓
【3】管理者パスワード入力
      ├─ パスワード入力フィールド
      └─ 「ログイン」ボタン
      ↓
【4】[ログイン] ボタンをクリック
      ├─ fetch('/api/admin/verify-password')
      └─ パスワード検証中...
      ↓
【5】認証成功
      ├─ sessionStorage['adminAuthenticated'] = 'true'
      ├─ 管理者コンテンツ表示
      └─ await loadAdminStoreList()
      ↓
【6】管理者パネル表示開始
      ├─ 【CSVアップロード】セクション
      ├─ 【パスワード変更】セクション
      ├─ 【データ管理】セクション (データクリア)
      ├─ 🏢 【店舗管理】セクション
      │  ├─ 登録済み店舗テーブル
      │  │  ├─ 店舗コード
      │  │  ├─ 店舗名
      │  │  ├─ 所在地
      │  │  └─ [削除] ボタン
      │  ├─ [店舗一覧を更新] ボタン
      │  └─ メッセージ表示エリア
      ├─ 【ユーザー管理】セクション
      └─ ...その他管理機能
      ↓
【7】[店舗一覧を更新] ボタンをクリック
      ├─ fetch('/api/admin/stores')
      ├─ テーブルリロード
      └─ ✅ "N 件の店舗を読み込みました"
      ↓
【8】削除対象の店舗の [削除] ボタンをクリック
      ├─ 確認ダイアログ表示
      │  └─ "店舗「テスト店舗1」(S002001)を削除しますか?"
      │  └─ "⚠️ この操作は取り消せません"
      └─ [キャンセル] [削除]
      ↓
【9】[削除] ボタンをクリック (確認)
      ├─ fetch('/api/admin/delete-store?store_id=1')
      ├─ DELETE リクエスト実行
      └─ バックエンド削除処理中...
      ↓
【10】削除完了
      ├─ ✅ "店舗「テスト店舗1」を削除しました"
      ├─ await loadAdminStoreList()
      └─ テーブル自動更新 (削除済み店舗が消える)
      ↓
【成功】店舗が削除されてテーブルから消滅
【失敗】❌ エラーメッセージ表示
```

---

## 9. セキュリティとログ

### 9.1 パスワード管理

```python
# パスワードハッシング = bcrypt（OWASP推奨）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ハッシュ化例
hashed = pwd_context.hash("plain_password")

# 検証例
is_correct = pwd_context.verify("plain_password", hashed)
```

### 9.2 監査ログ記録対象

| イベント | event_type | 記録される情報 |
|---------|-----------|----------------|
| ユーザーログイン | user_login | username, ip_address, status |
| 管理者ログイン | admin_login | ip_address, status |
| CSV アップロード | csv_upload | filename, record_count, duplicates |
| データ削除 | data_deleted | record_count, timestamp |
| 店舗削除 | store_deleted | store_code, store_name |
| ユーザー作成 | user_created | new_username, role |
| パスワード変更 | password_changed | username |

### 9.3 セッション管理

**フロントエンド側**:
- `sessionStorage`: 管理者認証状態 ($adminAuthenticated)
- `localStorage`: ユーザー情報 (userId, username, userRole, userStoreCode)

**バックエンド側**:
- JWT или session cookies (今後実装予定)

### 9.4 アクセス制御

```python
# ユーザーロール別アクセス
- POST /api/upload: admin のみ
- GET /api/summary/*: 認証済みユーザー (ロール別フィルタ)
- DELETE /api/admin/*: admin のみ
- POST /api/admin/*: admin のみ
```

### 9.5 入力・出力検証

```python
# 入力検証
- ファイルサイズ: 10MB以下
- MIME type: text/csv のみ
- SQL injection 対策: SQLAlchemy ORM 使用
- XSS 対策: HTML エスケープ処理

# 出力検証
- JSON レスポンス: Pydantic スキーマで型安全
- CSV 出力: 特殊文字エスケープ
```

---

## 10. トラブルシューティング

### 10.1 よくあるエラー

| エラー | 原因 | 対策 |
|--------|------|------|
| CSV解析失敗: invalid columns | CSV カラム数が 74 でない | CSV ファイルフォーマットを確認 |
| ユーザー認証失敗 | パスワード誤り | パスワード再入力、または管理画面でリセット |
| ダッシュボード表示されない | JavaScript エラー | ブラウザコンソール確認 (F12) |
| グラフが表示されない | ブラウザキャッシュ問題 | ページ再読み込み (Ctrl+Shift+R) |
| 店舗データが表示されない | ロール権限不足 | 管理者に確認 |

### 10.2 デバッグモード

```bash
# バックエンド - デバッグモードで起動
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10168

# ブラウザ開発者ツール
F12 → Console タブでエラー確認
F12 → Network タブで API 呼び出し確認
```

---

## 11. 今後の拡張予定

- [ ] JWT ベースの認証 (セッション永続化)
- [ ] ユーザーロール細分化 (運営管理者、エリア管理者)
- [ ] Excel エクスポート機能
- [ ] 定期自動バックアップ
- [ ] メール通知機能
- [ ] 多言語対応 (英語、中国語)
- [ ] モバイル最適化 (レスポンシブ改善)
- [ ] API レート制限
- [ ] 高度な分析機能 (予測分析、異常検知)

---

**ドキュメント最終更新**: 2026年2月20日
**作成者**: システムドキュメント生成
**バージョン管理**: Git リポジトリで管理
