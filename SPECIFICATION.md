# 売上実績管理システム - 仕様書

**作成日**: 2026年2月19日  
**バージョン**: 1.0.0

---

## 1. システム概要

売上実績データを CSV ファイルからアップロードし、スタッフ別・サービス別に集計・分析するウェブシステム。
実績担当者ごとの成績管理と、スマートフォン販売の詳細分析に対応。

### 対応環境
- **バックエンド**: Python 3.10以上、FastAPI
- **フロントエンド**: React 18以上、TypeScript
- **データベース**: SQLite
- **ネットワーク**: ローカルネットワーク対応（0.0.0.0 バインド）
- **ポート**: 10168

---

## 2. 機能要件

### 2.1 CSV アップロード機能

#### 対応フォーマット
- **エンコーディング**: CP932（Shift-JIS）自動検出対応
- **カラム数**: 75 カラム
- **ファイル形式**: CSV

#### 主なカラムマッピング
| # | カラム名 | 説明 | 使用用途 |
|---|---------|------|---------|
| 1 | 統括拠点コード | 店舗コード | 店舗別集計 |
| 4 | 売上日付 | トランザクション日付 | 日時情報 |
| 5 | 売上時刻 | トランザクション時刻 | 日時情報 |
| 7 | 売上伝票番号 | 伝票番号 | 重複排除、グループ化 |
| 16 | 商品コード | 商品 ID | 商品別集計 |
| 17 | POS表示商品名 | 商品名 | 商品情報 |
| 21 | 大分類名 | カテゴリ大分類 | サービス種別判定 |
| 23 | 中分類名 | カテゴリ中分類 | サービス種別判定 |
| 30 | 数量 | 販売台数 | 数量集計 |
| 31 | 販売単価（税込） | 単価 | 売上計算 |
| 32 | 販売明細額（税込） | 売上金額 | 売上集計 |
| 48 | 手続区分名 | 手続種別 | MNP 判定 |
| 50 | 手続区分２名 | 手続種別２ | MNP 判定 |
| 57 | 実績ユーザーID | スタッフ ID | **実績者集計** |
| 58 | 実績担当者姓 | スタッフ姓 | **実績者集計** |
| 59 | 実績担当者名 | スタッフ名 | **実績者集計** |
| 64 | お客様契約区分名 | 契約種別 | MNP 判定 |
| 73 | 粗利 | 利益額 | **粗利集計** |

### 2.2 データ処理

#### 重複排除ルール
- **判定方法**: 各トランザクション全体のハッシュ値（MD5）で完全重複を検出
- **対象項目**: transaction_date, ticket_number, staff_id, product_code, quantity, total_price
- **処理**: 完全に同じデータは 1 件のみ登録、重複は スキップ

#### サービスカテゴリ判定（MNPJudge ロジック）
同一伝票内の複数行から以下を判定：
- **au+1Collection**: 大分類が「au+1 Collection」
- **auMNP(端末あり)**: MNP + au 契約 + au 端末 + au-SIM
- **auMNP(SIM単体)**: MNP + au 契約 + au-SIM のみ
- **UQMNP(端末あり)**: MNP + UQ 契約 + UQ 端末 + UQ-SIM
- **UQMNP(SIM単体)**: MNP + UQ 契約 + UQ-SIM のみ
- **その他**: デフォルト値

### 2.3 API エンドポイント

#### アップロード
```
POST /api/upload
```
- **入力**: マルチパートフォーム、ファイル: file (CSV)
- **出力**: 
```json
{
  "message": "Successfully uploaded 585 new transactions (skipped 229 duplicates)",
  "count": 585,
  "duplicates": 229
}
```

#### 店舗別サマリー
```
GET /api/summary/store?start_date=2026-02-01&end_date=2026-02-28
```
- **レスポンス**: 店舗コード、売上、粗利、トランザクション数

#### au+1 Collection 実績サマリー
```
GET /api/au1-collection/summary?start_date=2026-02-01&end_date=2026-02-28
```
- **レスポンス**: スタッフ別に件数、売上、粗利を集計

#### スマートフォン販売サマリー
```
GET /api/smartphone/summary?start_date=2026-02-01&end_date=2026-02-28
```
- **条件**: 大分類「移動機」かつ中分類「iPhone」または「スマートフォン」
- **レスポンス**:
```json
[
  {
    "staff_id": "AUS39254",
    "staff_name": "石井楓斗",
    "total_quantity": 17,
    "total_gross_profit": 0,           // スマートフォン分は常に 0
    "gross_profit_per_unit": 0,        // 台当たり単価/粗利は常に 0
    "total_sales": 1966101.0
  }
]
```

#### その他エンドポイント
- `GET /api/transactions?limit=100&skip=0` - トランザクション一覧
- `GET /api/summary/daily` - 日別サマリー
- `GET /api/summary/product` - 商品別サマリー
- `GET /api/au1-collection/detail` - au+1Collection 詳細（商品別）
- `GET /api/au1-collection/category` - au+1Collection 中分類別
- `GET /api/au1-collection/daily` - au+1Collection 日別推移

---

## 3. フロントエンド仕様

### 3.1 ページ構成

#### 1. ダッシュボード
- **表示内容**:
  - 合計売上（全店舗）
  - 合計粗利（全店舗）
  - 粗利率（%）
  - 店舗別売上テーブル

#### 2. 個人別実績（新規）
- **左パネル**: スタッフ一覧（名前順ソート）
- **右パネル**: 選択したスタッフの詳細
  - **スマートフォン販売**:
    - 販売台数
    - 台当たり単価（常に ¥0）
    - 粗利（常に ¥0）
    - 総売上
  - **au+1 Collection**:
    - 実績件数
    - 粗利
    - 総売上
- **日付フィルター**: 開始日、終了日で期間指定可能

#### 3. ファイルアップロード
- CSV ファイル選択とアップロード
- アップロード完了後、ダッシュボードに遷移

#### 4. 分析・グラフ
- 日別売上チャート
- 商品別売上チャート

### 3.2 API 接続

フロントエンド API ベースURL:
```typescript
const API_BASE_URL = `http://${window.location.hostname}:10168/api`;
```

- 動的にホスト名を取得
- ローカルPC: `http://localhost:10168/api`
- 別 PC: `http://<サーバーIP>:10168/api`

---

## 4. データベーススキーマ

### 4.1 sales_transactions テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER PRIMARY KEY | レコード ID |
| transaction_date | DATETIME | トランザクション日時 |
| store_code | VARCHAR | 店舗コード |
| product_code | VARCHAR | 商品コード |
| product_name | VARCHAR | 商品名 |
| quantity | INTEGER | 数量 |
| unit_price | FLOAT | 単価（税込） |
| total_price | FLOAT | 売上金額（税込） |
| gross_profit | FLOAT | 粗利 |
| staff_id | VARCHAR | **実績ユーザー ID** |
| staff_name | VARCHAR | **実績担当者名** |
| created_at | DATETIME | 登録日時 |
| ticket_number | VARCHAR | 伝票番号 |
| large_category | VARCHAR | 大分類 |
| small_category | VARCHAR | 中分類 |
| procedure_name | VARCHAR | 手続区分 |
| procedure_name_2 | VARCHAR | 手続区分２ |
| service_category | VARCHAR | サービスカテゴリ |

### 4.2 users テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER PRIMARY KEY | レコード ID |
| staff_id | VARCHAR | スタッフ ID |
| staff_name | VARCHAR | スタッフ名 |
| store_code | VARCHAR | 店舗コード |
| created_at | DATETIME | 登録日時 |

### 4.3 admin_users テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER PRIMARY KEY | レコード ID |
| username | VARCHAR | ユーザー名 |
| password | VARCHAR | パスワード（ハッシュ） |
| created_at | DATETIME | 登録日時 |

---

## 5. ビジネスルール

### 5.1 実績集計ルール

#### au+1 Collection
- **対象**: 大分類 = 「au+1 Collection」のすべてのトランザクション
- **集計項目**: 件数、売上、粗利
- **集計単位**: スタッフ別（実績ユーザー）

#### スマートフォン販売
- **条件**: 大分類 = 「移動機」 かつ 中分類 ∈ [「iPhone」, 「スマートフォン」]
- **集計項目**: 販売台数、売上、粗利（常に 0）
- **集計単位**: スタッフ別（実績ユーザー）
- **特記**: 粗利は表示上常に ¥0 で計算

#### MNP 判定
- **対象**: 同一伝票内の複数行をグループ化して判定
- **情報源**: 手続区分名、商品名、契約種別
- **結果**: service_category に割り当て

### 5.2 データ制約

- 実績集計は「実績ユーザーID」（column 57）で行う
- 粗利の出所は column 73
- 日付フォーマット: YYYY/MM/DD, YYYY/MM/DD HH:MM:SS
- 数値フォーマット: float（小数点対応）

---

## 6. ネットワーク設定

### 6.1 バインド設定

```bat
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10168
```

- **host 0.0.0.0**: すべてのネットワークインターフェースでリッスン
- **port 10168**: ポート番号は固定

### 6.2 CORS 設定

```python
CORS_ORIGINS = ["*"]  # 全オリジン許可
```

- クライアント PC からの API リクエストを許可
- フロントエンドはどの PC からでもアクセス可能

---

## 7. 暫定仕様・制限事項

### 7.1 既知の制限
1. **認証機能**: 未実装（ローカルネットワーク前提）
2. **ユーザー管理**: admin_users テーブル作成のみ、UI 未実装
3. **パフォーマンス**: SQLite 使用、大規模データ対応未検証
4. **エラーハンドリング**: 基本的なバリデーションのみ

### 7.2 将来対応予定
- ユーザー認証・ロールベースアクセス制御
- PostgreSQL への移行
- データエクスポート機能（PDF/Excel）
- より詳細なグラフ分析
- 前月比較機能

---

## 8. デプロイ・運用

### 8.1 起動方法

```bash
cd c:\Users\Rec\Desktop\pj1
.\run.bat
```

自動で以下が実行される：
1. バックエンド（FastAPI）起動 → http://0.0.0.0:10168
2. フロントエンド側は別途ブラウザでアクセス

### 8.2 初期化

```bash
# データベースをクリア
if (Test-Path app.db) { Remove-Item app.db -Force }
# サーバー再起動で新しい DB を作成
.\run.bat
```

### 8.3 ファイル構成

```
pj1/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI アプリケーション
│   │   ├── config.py        # 設定（CORS, DB）
│   │   ├── database.py      # SQLAlchemy 設定
│   │   ├── schemas.py       # Pydantic スキーマ
│   │   ├── models/          # ORM モデル
│   │   ├── routes/          # API ルート定義
│   │   ├── services/        # ビジネスロジック（CSV, 集計）
│   │   └── templates/       # フロントエンド HTML
│   ├── requirements.txt     # Python 依存パッケージ
│   └── Dockerfile          # コンテナ設定
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # ルートコンポーネント
│   │   ├── api.ts           # API 呼び出し
│   │   ├── pages/           # ページコンポーネント
│   │   │   ├── Dashboard.tsx        # ダッシュボード
│   │   │   └── StaffPerformance.tsx # 個人別実績
│   │   └── components/      # UI コンポーネント
│   └── package.json         # Node.js 依存パッケージ
├── app.db                   # SQLite データベース（自動生成）
├── run.bat                  # 起動スクリプト
└── README.md               # ドキュメント
```

---

## 9. 用語集

| 用語 | 説明 |
|-----|------|
| **実績ユーザー** | CSV の column 57 に記載されるスタッフ ID（実績担当者） |
| **粗利** | 売上から商品原価を差し引いた利益額（column 73） |
| **au+1 Collection** | 大分類コードで識別される特定のサービスカテゴリ |
| **MNP** | 携帯電話番号ポータビリティ（転出・転入） |
| **伝票番号** | 1 つの取引の複数商品をグループ化する票番号 |
| **台当たり単価** | スマートフォン販売数あたりの粗利（常に 0） |

---

**最終更新**: 2026年2月19日  
**メンテナー**: システム管理者
