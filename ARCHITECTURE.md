# 売上実績管理システム - ファイル構成・処理フロー

**作成日**: 2026年2月19日  
**バージョン**: 1.0.0

---

## 目次
1. [全体アーキテクチャ](#全体アーキテクチャ)
2. [バックエンド構成](#バックエンド構成)
3. [フロントエンド構成](#フロントエンド構成)
4. [データフロー](#データフロー)
5. [各ファイルの詳細](#各ファイルの詳細)

---

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                      ブラウザ (ユーザー)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/CORS
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌──────────────────────┐         ┌──────────────────────┐
│   フロントエンド      │         │   バックエンド       │
│   (React/TypeScript) │◄────────►│  (FastAPI/Python)   │
│   port: ?            │         │   port: 10168       │
└──────────────────────┘         └──────────────────────┘
         │                                   │
         │ 静的ファイル配信                 │ SQLiter操作
         │                                   ▼
         │                        ┌──────────────────┐
         │                        │   SQLite DB      │
         │                        │  (app.db)        │
         │                        └──────────────────┘
         │
         └─────────────────────────────────┐
                                            │ CSV読み込み
                                            ▼
                                  ┌──────────────────┐
                                  │  sales_data.csv  │
                                  │   (アップロード)  │
                                  └──────────────────┘
```

---

## バックエンド構成

```
backend/
├── app/
│   ├── __init__.py                 # Pythonパッケージ初期化
│   ├── main.py                     # ★ FastAPI 統合エントリーポイント
│   ├── config.py                   # ★ 設定（CORS, DB, 環境変数）
│   ├── database.py                 # ★ SQLAlchemy 初期化、Sessions
│   ├── schemas.py                  # ★ Pydantic スキーマ（入出力検証）
│   ├── models/                     # ORM モデル定義
│   │   ├── __init__.py
│   │   ├── sales.py                # SalesTransaction ORM モデル
│   │   ├── user.py                 # User ORM モデル
│   │   └── admin.py                # AdminUser ORM モデル
│   ├── routes/                     # API ルーター（エンドポイント定義）
│   │   ├── __init__.py
│   │   ├── sales.py                # ★★ 売上データ API ルート
│   │   ├── health.py               # ヘルスチェック
│   │   └── admin.py                # 管理者 API
│   ├── services/                   # ビジネスロジック（集計、変換）
│   │   ├── __init__.py
│   │   ├── csv_service.py          # ★★★ CSV パース、変換
│   │   └── sales_service.py        # ★★★ 売上集計ロジック
│   ├── templates/                  # フロントエンド配信
│   │   └── index.html              # React SPA HTML
│   ├── static/                     # 静的ファイル（CSS等）
│   ├── __pycache__/                # キャッシュ
│   └── Dockerfile                  # コンテナイメージ定義
├── requirements.txt                # Python 依存パッケージ
└── (その他の設定ファイル)
```

### バックエンド処理フロー

```
# CSV アップロード フロー
POST /api/upload
  │
  ├─► routes/sales.py::upload_csv()
  │   │
  │   ├─► services/csv_service.py::parse_sales_csv(file_bytes)
  │   │   │
  │   │   ├─► detect_encoding()        # CP932 検出
  │   │   ├─► pd.read_csv()            # CSV 読み込み
  │   │   ├─► column_index_map へマッピング
  │   │   ├─► grouped_by_ticket        # 伝票番号でグループ化
  │   │   ├─► MNPJudge.judge_service_category()
  │   │   │   └─ MNP と au/UQ SIM を組み合わせ判定
  │   │   └─► SalesTransactionCreate[] をリターン
  │   │
  │   ├─► 重複排除 (MD5 ハッシュ)
  │   ├─► DB に 保存
  │   └─► JSON レスポンス
  │
  └─► ブラウザに返却


# データ集計 フロー
GET /api/au1-collection/summary
  │
  ├─► routes/sales.py::get_au1_collection_summary()
  │   │
  │   ├─► services/sales_service.py::get_au_plus_one_collection_summary()
  │   │   │
  │   │   └─► SQLAlchemy Query
  │   │       ├─► フィルター: large_category = 'au+1 Collection'
  │   │       ├─► GROUP BY: staff_id, staff_name
  │   │       └─► SELECT: COUNT(*), SUM(total_price), SUM(gross_profit)
  │   │
  │   ├─► レスポンス整形 (float 変換等)
  │   └─► JSON リターン
  │
  └─► ブラウザに返却
```

---

## フロントエンド構成

```
frontend/
├── src/
│   ├── index.tsx                   # React エントリーポイント
│   ├── App.tsx                     # ★ ルートコンポーネント（ナビゲーション）
│   ├── api.ts                      # ★ API 呼び出し関数（axios ラッパー）
│   ├── pages/
│   │   ├── Dashboard.tsx           # ★ 店舗別ダッシュボード
│   │   └── StaffPerformance.tsx    # ★★ 個人別実績ページ
│   ├── components/
│   │   ├── FileUpload.tsx          # CSV アップロードコンポーネント
│   │   └── Charts.tsx              # グラフ表示コンポーネント
│   └── (React キャッシュ等)
├── public/
│   └── index.html                  # HTML テンプレート
├── package.json                    # npm 依存パッケージ
├── tsconfig.json                   # TypeScript 設定
└── Dockerfile.dev                  # 開発用コンテナ設定
```

### フロントエンド処理フロー

```
# ページ読み込み フロー
ユーザー がブラウザで http://localhost:10168 にアクセス
  │
  ├─► main.py::root() 
  │   └─ index.html を配信
  │
  ├─► React::App.tsx が render
  │   │
  │   ├─► ナビゲーション作成
  │   │   ├─ ダッシュボード
  │   │   ├─ 個人別実績 (new)
  │   │   ├─ ファイルアップロード
  │   │   └─ 分析・グラフ
  │   │
  │   └─► 初期ページ: Dashboard 表示
  │
  └─► 準備完了


# 個人別実績ページ フロー
ユーザー が 「個人別実績」タブをクリック
  │
  ├─► App.tsx::setActiveTab('staff')
  │
  ├─► StaffPerformance.tsx が render
  │   │
  │   ├─► useEffect() で fetchStaffData() 実行
  │   │   │
  │   │   ├─► axios.get('/api/smartphone/summary')
  │   │   │   └─ staffList に スマートフォン販売データを統合
  │   │   │
  │   │   └─► axios.get('/api/au1-collection/summary')
  │   │       └─ staffList に au+1 Collection データを統合
  │   │
  │   ├─► 左パネル: スタッフ名でリスト表示
  │   │   (クリックで selectedStaff を更新)
  │   │
  │   └─► 右パネル: 選択したスタッフの詳細表示
  │       ├─ スマートフォン販売
  │       │  ├─ 販売台数
  │       │  ├─ 台当たり単価 (¥0)
  │       │  ├─ 粗利 (¥0)
  │       │  └─ 総売上
  │       └─ au+1 Collection
  │          ├─ 実績件数
  │          ├─ 粗利
  │          └─ 総売上
  │
  └─► 画面表示完了
```

---

## データフロー

### 1. CSV アップロード → DB 保存

```
CSV ファイル (814行)
  │
  ├─► エンコーディング自動検出 (CP932)
  │
  ├─► 75 カラムを column_index_map でマッピング
  │   ├─ col 57-59: 実績ユーザー情報
  │   ├─ col 73: 粗利額
  │   ├─ col 21, 23: カテゴリ情報
  │   └─ col 4-5: 日時情報
  │
  ├─► 伝票番号でグループ化 (157 グループ)
  │
  ├─► MNP 判定 (同一伝票内で複数行を解析)
  │   ├─ 手続区分確認
  │   ├─ SIM/端末情報確認
  │   └─ au/UQ 判定
  │
  ├─► MD5 ハッシュで重複排除
  │   ├─ 新規 585 件をデータベース挿入
  │   └─ 重複 229 件をスキップ
  │
  └─► app.db (SQLite) へ保存


# 結果: 742 件のトランザクション登録
```

### 2. au+1 Collection 集計

```
app.db (SalesTransaction テーブル)
  │
  ├─► フィルター: large_category = 'au+1 Collection'
  │   └─ 55 件絞り込み
  │
  ├─► GROUP BY: staff_id, staff_name
  │
  ├─► 集計
  │   ├─ COUNT(*) → transaction_count
  │   ├─ SUM(total_price) → total_sales
  │   └─ SUM(gross_profit) → gross_profit
  │
  └─► JSONレスポンス
      ├─ スタッフ A: 14件, ¥343,275売上, ¥40,600粗利
      ├─ スタッフ B: 13件, ¥345,995売上, ¥40,600粗利
      └─ ... (計7名)
```

### 3. スマートフォン販売集計

```
app.db (SalesTransaction テーブル)
  │
  ├─► フィルター: large_category = '移動機'
  │   AND small_category IN ('iPhone', 'スマートフォン')
  │   └─ 67 件絞り込み
  │
  ├─► GROUP BY: staff_id, staff_name
  │
  ├─► 集計
  │   ├─ SUM(quantity) → total_quantity (17台)
  │   ├─ SUM(gross_profit) → 実データから取得
  │   │   └─ BUT: API レスポンスでは常に 0
  │   ├─ SUM(total_price) → total_sales
  │   └─ gross_profit_per_unit = 0 (常に0)
  │
  └─► JSONレスポンス
      ├─ スタッフ A: 17台, 総売上 ¥1,966,101, 粗利 ¥0
      ├─ スタッフ B: 12台, 総売上 ¥1,165,302, 粗利 ¥0
      └─ ... (計8名)
```

---

## 各ファイルの詳細

### ★ main.py - FastAPI アプリケーション

**役割**: 
- FastAPI インスタンスの初期化
- ルーター登録（API エンドポイント）
- CORS ミドルウェア設定
- 静的ファイル配信（フロントエンド HTML）
- ORM テーブルの自動生成

**主な処理**:
```python
1. FastAPI() インスタンス作成
2. CORSMiddleware 追加 (allow_origins: "*")
3. Router 登録
   - health.router (ヘルスチェック)
   - sales.router (★★ メイン機能)
   - admin.router (管理者)
4. GET "/" で index.html を配信
5. Base.metadata.create_all() で DB テーブル自動作成
```

**依存関係**:
- config.py (CORS_ORIGINS)
- database.py (engine, Base)
- models/* (SalesTransaction, User, AdminUser)
- routes/* (sales, admin, health)

---

### ★ config.py - 設定管理

**役割**:
- 環境変数の読み込み
- CORS オリジンの設定
- データベース URL の設定
- デバッグモード の設定

**主な処理**:
```python
1. .env ファイル読み込み (load_dotenv)
2. DATABASE_URL 設定
   - デフォルト: "postgresql://..."
3. DEBUG モード設定
   - デフォルト: True
4. CORS_ORIGINS 設定
   - 環境変数なし → "*" (全許可)
   - 環境変数あり → 指定オリジン
```

**重要な値**:
- `CORS_ORIGINS = ["*"]` - 全オリジン許可
- `DATABASE_URL` - SQLite または PostgreSQL

---

### ★ database.py - SQLAlchemy 初期化

**役割**:
- SQLAlchemy エンジン初期化
- Declarative Base 定義
- Session 管理

**主な処理**:
```python
1. SQLite エンジン初期化
   - DATABASE_URL = "sqlite:///./app.db"
2. Declarative Base 作成
   - すべてのモデルが Base を継承
3. SessionLocal クラス定義
   - 各リクエストで DB セッション生成
4. get_db() ジェネレーター
   - FastAPI Depends で使用
   - 自動トランザクション管理
```

**データフロー**:
```
Request → get_db() → SessionLocal() → Query 実行 → commit/rollback → Response
```

---

### ★ schemas.py - Pydantic スキーマ

**役割**:
- API リクエスト・レスポンスのデータ検証
- 型チェック
- JSON シリアライズ

**主なスキーマ**:
```python
SalesTransactionCreate
  ├─ transaction_date: datetime
  ├─ store_code: str
  ├─ product_code: str
  ├─ product_name: str
  ├─ quantity: int
  ├─ unit_price: float
  ├─ total_price: float
  ├─ gross_profit: float
  ├─ staff_id: str
  ├─ staff_name: str
  ├─ ticket_number: str
  ├─ large_category: str
  ├─ small_category: str
  ├─ procedure_name: str
  ├─ procedure_name_2: str
  └─ service_category: str

SalesTransactionRead
  └─ 上記 + id, created_at
```

---

### ★ models/sales.py - SalesTransaction ORM

**役割**:
- 売上トランザクションテーブル定義
- ORM マッピング

**主なカラム**:
```python
class SalesTransaction(Base):
    __tablename__ = "sales_transactions"
    
    id: 主キー
    transaction_date: トランザクション日時
    store_code: 店舗コード
    product_code: 商品コード
    product_name: 商品名
    quantity: 数量
    unit_price: 単価
    total_price: 売上額
    gross_profit: 粗利
    staff_id: 実績ユーザー ID
    staff_name: 実績担当者名
    created_at: 登録日時
    ticket_number: 伝票番号
    large_category: 大分類
    small_category: 中分類
    procedure_name: 手続区分
    service_category: サービスカテゴリ
```

---

### ★★ routes/sales.py - API エンドポイント

**役割**:
- API ルート定義
- リクエスト受け取り
- ビジネスロジック呼び出し
- レスポンス整形

**主なエンドポイント**:

| パス | メソッド | 説明 | 実装担当 |
|-----|---------|------|--------|
| `/upload` | POST | CSV アップロード | csv_service.parse_sales_csv() |
| `/au1-collection/summary` | GET | au+1 実績集計 | sales_service.get_au_plus_one_collection_summary() |
| `/smartphone/summary` | GET | スマートフォン販売集計 | sales_service.get_smartphone_sales_summary() |
| `/summary/store` | GET | 店舗別集計 | sales_service.get_store_summary() |
| `/summary/daily` | GET | 日別集計 | sales_service.get_daily_summary() |
| `/transactions` | GET | トランザクション一覧 | DB Query |
| `/au1-collection/daily` | GET | au+1 日別推移 | sales_service.get_au_plus_one_collection_daily() |

**処理フロー (upload 例)**:
```python
@router.post("/upload")
async def upload_csv(file: UploadFile, db: Session):
    # 1. ファイル読み込み
    content = await file.read()
    
    # 2. CSV パース (csv_service)
    transactions = CSVService.parse_sales_csv(content)
    
    # 3. 重複排除 (ハッシュ値比較)
    new_transactions = 重複チェック(transactions)
    
    # 4. DB 保存
    for tx in new_transactions:
        db.add(SalesTransaction(**tx.dict()))
    db.commit()
    
    # 5. レスポンス
    return {"count": len(new_transactions), ...}
```

---

### ★★★ services/csv_service.py - CSV パース・変換

**役割**:
- CSV ファイルのパース
- エンコーディング自動検出
- カラムマッピング
- MNP 判定
- SalesTransactionCreate スキーマへの変換

**主なクラス**:

#### MNPJudge
```python
@staticmethod
judge_service_category(ticket_data: List[Dict]) -> Dict[str, str]:
    """
    同一伝票内の複数行からサービスカテゴリを判定
    
    流れ:
    1. 伝票内の全行をスキャン
    2. 手続区分、SIM、端末を検出
    3. au/UQ MNP の判定
    4. 各行に service_category を割り当て
    """
```

#### CSVService
```python
@staticmethod
detect_encoding(file_bytes: bytes) -> str:
    """
    chardet で自動エンコーディング検出
    CP932 → cp932, SHIFT_JIS → shift_jis に正規化
    """

@staticmethod
parse_sales_csv(file_bytes: bytes) -> List[SalesTransactionCreate]:
    """
    CSV パース主処理
    
    1. エンコーディング検出
    2. pd.read_csv()
    3. カラムマッピング
    4. 伝票番号でグループ化
    5. MNP 判定
    6. SalesTransactionCreate[] 作成
    """
```

**処理フロー (詳細)**:
```
file_bytes
  │
  ├─► detect_encoding()
  │   └─ chardet.detect() → CP932
  │
  ├─► file_bytes.decode(cp932) → content_str
  │
  ├─► pd.read_csv(StringIO(content_str)) → DataFrame (814行)
  │
  ├─► column_index_map でカラムマッピング
  │   column 57 (実績ユーザーID)
  │   column 73 (粗利)
  │   etc.
  │
  ├─► 伝票番号でグループ化
  │   {"P00010003": [row1, row2, row3]}
  │
  ├─► MNPJudge.judge_service_category() で各行に service_category 付与
  │
  ├─► 各行を SalesTransactionCreate に変換
  │   ├─ 日付パース: row.iloc[4] + row.iloc[5]
  │   ├─ 数値変換: float(row.iloc[73])
  │   ├─ 文字列: str(row.iloc[51]).strip()
  │   └─ サービスカテゴリ割り当て
  │
  └─► List[SalesTransactionCreate] 返却
      (814件全て)
```

---

### ★★★ services/sales_service.py - 売上集計ロジック

**役割**:
- SQL クエリの構築と実行
- 売上データの集計
- 日別・商品別・スタッフ別集計

**主なメソッド**:

```python
@staticmethod
get_au_plus_one_collection_summary(
    db: Session,
    staff_id: str = None,
    store_code: str = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[au+1CollectionResult]:
    """
    au+1 Collection を実績ユーザー別に集計
    
    SQL:
    SELECT 
        staff_id, staff_name,
        COUNT(*) as transaction_count,
        SUM(total_price) as total_sales,
        SUM(gross_profit) as gross_profit
    FROM sales_transactions
    WHERE large_category = 'au+1 Collection'
        AND transaction_date BETWEEN start_date AND end_date
    GROUP BY staff_id, staff_name
    """

@staticmethod
get_smartphone_sales_summary(
    db: Session,
    staff_id: str = None,
    store_code: str = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[SmartphoneSalesResult]:
    """
    スマートフォン販売を実績ユーザー別に集計
    
    SQL:
    SELECT 
        staff_id, staff_name,
        SUM(quantity) as total_quantity,
        SUM(gross_profit) as total_gross_profit,
        SUM(total_price) as total_sales
    FROM sales_transactions
    WHERE large_category = '移動機'
        AND small_category IN ('iPhone', 'スマートフォン')
    GROUP BY staff_id, staff_name
    """

@staticmethod
get_store_summary(
    db: Session,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[StoreSummaryResult]:
    """店舗別に集計"""

@staticmethod
get_daily_summary(
    db: Session,
    store_code: str = None,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[DailySummaryResult]:
    """日別に集計"""
```

---

### ★ App.tsx - フロントエンド ルートコンポーネント

**役割**:
- ページナビゲーション
- タブ切り替え
- 子コンポーネント管理
- グローバルな状態管理

**状態管理**:
```tsx
const [activeTab, setActiveTab] = useState<'dashboard' | 'upload' | 'analysis' | 'staff'>('dashboard');
const [dailyData, setDailyData] = useState<DailySummaryData[]>([]);
const [productData, setProductData] = useState<ProductSummaryData[]>([]);
```

**ナビゲーション**:
```
┌─ ダッシュボード
│  └─ Dashboard.tsx
├─ 個人別実績 (NEW)
│  └─ StaffPerformance.tsx
├─ ファイルアップロード
│  └─ FileUpload.tsx
└─ 分析・グラフ
   └─ Charts.tsx (DailySalesChart + ProductSalesChart)
```

---

### ★ api.ts - API クライアント

**役割**:
- axios インスタンス生成
- API URL ベースの設定
- HTTP ヘッダー設定
- API 呼び出し関数

**コード**:
```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'multipart/form-data' }
});

export const uploadCSV = (file: File) => api.post('/upload', formData);
export const getDailySummary = (storeCode?, startDate?, endDate?) => 
  api.get('/summary/daily', { params: {...} });
// ... その他の関数
```

---

### ★ Dashboard.tsx - 店舗別ダッシュボード

**役割**:
- 店舗別売上サマリーの表示
- KPI 表示（合計売上、粗利、粗利率）
- テーブル形式での売上一覧

**構成**:
```tsx
useEffect(() => {
  fetchStoreSummary();
}, []);

UI:
├─ KPI カード (3個)
│  ├─ 合計売上
│  ├─ 合計粗利
│  └─ 粗利率
└─ テーブル (店舗ごと)
   ├─ 店舗コード
   ├─ 売上
   ├─ 粗利
   ├─ トランザクション数
   └─ 粗利率
```

---

### ★★ StaffPerformance.tsx - 個人別実績ページ

**役割**:
- スタッフ別の詳細実績表示
- au+1 Collection とスマートフォン販売を統合表示
- 日付フィルター機能

**処理フロー**:
```tsx
1. useEffect(() => {
     fetchStaffData();
   }, [startDate, endDate])

2. fetchStaffData():
   ├─ GET /api/smartphone/summary (67条件)
   ├─ GET /api/au1-collection/summary (55件)
   └─ Map で統合 (staffMap)

3. UI 構成:
   ├─ 左: スタッフリスト (クリックで選択)
   └─ 右: 選択スタッフの詳細
       ├─ スマートフォン販売
       │  ├─ 販売台数: 17
       │  ├─ 台当たり単価: ¥0
       │  ├─ 粗利: ¥0
       │  └─ 総売上: ¥1,966,101
       └─ au+1 Collection
          ├─ 実績件数: 14
          ├─ 粗利: ¥40,600
          └─ 総売上: ¥343,275
```

**重要な実装**:
```typescript
// API ベース URL を動的に（別 PC 対応）
const API_BASE_URL = `http://${window.location.hostname}:10168/api`;

// スマートフォン販売データとau+1データを Map で統合
const staffMap = new Map<string, StaffData>();
```

---

## 処理フロー サマリー

### エンドツーエンド フロー: CSV アップロード→表示

```
1. ユーザーがブラウザで http://localhost:10168 にアクセス
   └─► main.py::root() → index.html 配信
       └─► App.tsx render
           └─► Dashboard 初期表示

2. ユーザーが「ファイルアップロード」タブをクリック
   └─► FileUpload.tsx 表示

3. ユーザーが CSV ファイルをドラッグ&ドロップ
   └─► FileUpload.tsx::handleUpload()
       └─► api.uploadCSV(file)
           └─► POST /api/upload → routes/sales.py

4. routes/sales.py::upload_csv()
   ├─► await file.read() → file_bytes
   ├─► CSVService.parse_sales_csv(file_bytes)
   │   ├─► CP932 検出
   │   ├─► 75 カラムを column_index_map マッピング
   │   ├─► 伝票でグループ化 (157 グループ)
   │   ├─► MNP 判定
   │   └─► List[SalesTransactionCreate] (814件)
   ├─► MD5 ハッシュで重複排除
   │   └─► 585 件新規, 229 件重複
   ├─► db.add() & db.commit()
   │   └─► app.db に 585 件挿入
   └─► JSON レスポンス {"count": 585, ...}

5. ブラウザが レスポンス受け取り
   └─► ファイルアップロード成功 & ダッシュボードに遷移

6. ユーザーが「個人別実績」タブをクリック
   └─► StaffPerformance.tsx render

7. StaffPerformance.tsx::fetchStaffData()
   ├─► GET /api/smartphone/summary
   │   └─► services/sales_service.py::get_smartphone_sales_summary()
   │       └─► SQL: WHERE large_category='移動機' AND small_category IN (...)
   │           └─► GROUP BY staff_id, staff_name
   │               └─► 8 名のスマートフォン販売集計結果
   └─► GET /api/au1-collection/summary
       └─► services/sales_service.py::get_au_plus_one_collection_summary()
           └─► SQL: WHERE large_category='au+1 Collection'
               └─► GROUP BY staff_id, staff_name
                   └─► 7 名の au+1 Collection 集計結果

8. レスポンスを受け取り、Map で統合
   └─► staffMap に 7 名のスタッフデータを格納

9. UI 表示
   ├─ 左: スタッフリスト (7名表示)
   └─ 右: 選択スタッフの詳細
       ├─ スマートフォン販売 (あれば)
       └─ au+1 Collection (あれば)
```

---

## まとめ

### バックエンド責務分離

| 層 | ファイル | 責務 |
|----|--------|------|
| **プレゼンテーション** | routes/ | リクエスト/レスポンス処理 |
| **ビジネスロジック** | services/ | CSV 解析、集計、MNP 判定 |
| **データアクセス** | database.py, models/ | ORM, SQL 実行 |
| **構成** | config.py, main.py | 初期化、ミドルウェア |

### フロントエンド責務分離

| 層 | ファイル | 責務 |
|----|--------|------|
| **ルーティング** | App.tsx | ナビゲーション、タブ切り替え |
| **ページ** | pages/*.tsx | 画面表示、状態管理 |
| **UI** | components/*.tsx | 再利用可能なコンポーネント |
| **API** | api.ts | バックエンド通信 |

---

**最終更新**: 2026年2月19日  
**メンテナー**: システム管理者
