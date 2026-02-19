# 売上実績管理Webアプリケーション

CSVファイルからの実績データアップロード・分析・ダッシュボード表示システムです。

## 技術スタック

- **バックエンド**: Python + FastAPI + SQLAlchemy
- **フロントエンド**: HTML5 + Vanilla JavaScript + Chart.js
- **データベース**: SQLite（デフォルト）/ PostgreSQL（本番環境）
- **その他**: Python依存ライブラリ

## 機能

- 📥 **CSVアップロード**: 売上明細データをCSVで一括登録
- 📊 **ダッシュボード**: 店舗別・日別・商品別の売上サマリー表示
- 📈 **グラフ分析**: 日別売上推移、商品別売上TOP10表示
- � **個人別成績**: スタッフ別のサービス成績集計表示（サービスごとのカウント数・粗利）
- 🔍 **データフィルタ**: 店舗・期間・スタッフ別で売上データを集計

## プロジェクト構成

```
.
├── backend/
│   ├── app/
│   │   ├── models/         # SQLAlchemyモデル定義
│   │   ├── routes/         # APIエンドポイント
│   │   ├── services/       # ビジネスロジック
│   │   ├── templates/      # HTMLテンプレート
│   │   ├── static/         # 静的ファイル（CSS/JS）
│   │   ├── config.py       # 設定管理
│   │   ├── database.py     # DB接続設定
│   │   ├── schemas.py      # Pydanticスキーマ
│   │   └── main.py         # FastAPIメインファイル
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # (オプション) React TS版
├── setup.bat / setup.sh    # セットアップスクリプト
├── run.bat / run.sh        # 実行スクリプト
├── docker-compose.yml      # Docker 構成（オプション）
└── README.md
```

## オンプレミスセットアップ（推奨）

### 前提条件

- **Windows**: Python 3.8+
- **Linux/Mac**: Python 3.8+, pip

### セットアップ手順

#### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd sales-performance
```

#### 2. セットアップスクリプトを実行

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

セットアップスクリプトが以下を自動実行します：
- Python のインストール確認
- `.env` ファイルの作成
- Python依存パッケージのインストール

#### 3. 環境変数設定（必要に応じて）

`backend/.env` を編集してカスタマイズできます：

```env
# デフォルト（SQLite）
DATABASE_URL=sqlite:///./sales.db

# PostgreSQL の場合
# DATABASE_URL=postgresql://user:password@localhost:5432/sales_db

DEBUG=True
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

### 起動

**Windows:**
```bash
run.bat
```

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

または直接実行：
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**ブラウザで以下にアクセス:**
```
http://localhost:8000
```

## 使用方法

### 各タブの機能

1. **ダッシュボード**
   - 店舗別の売上サマリーを表示
   - 合計売上、合計粗利、粗利率を表示

2. **ファイルアップロード**
   - CSVファイルをドラッグ&ドロップでアップロード
   - または「ファイルを選択」ボタンからファイルを選択
   - アップロード後のトランザクション件数を表示

3. **個人別成績**
   - スタッフを選択して成績を表示
   - 日付範囲でフィルター
   - サービス別の成績を集計表示
     - **auMNP, UQMNP, 店頭設定サポート, 機種変更, クレジットカード, ゴールドランクアップ, 新規ゴールド, auひかり, 固定事業者トスアップ**: 件数を表示
     - **au+1Collection**: 粗利額を表示

4. **分析・グラフ**
   - 日別売上推移（折れ線グラフ）
   - 商品別売上TOP10（棒グラフ）

## API エンドポイント

### 認証なし

- `GET /` - フロントエンド（ダッシュボード）
- `GET /api/health` - ヘルスチェック

### CSV アップロード

- `POST /api/upload` - CSVファイルをアップロードして登録

### データ取得

- `GET /api/transactions` - 売上トランザクション一覧
- `GET /api/summary/daily` - 日別売上サマリー
- `GET /api/summary/product` - 商品別売上サマリー
- `GET /api/summary/store` - 店舗別売上サマリー

### スタッフ別実績

- `GET /api/summary/staff-list` - スタッフ一覧取得
- `GET /api/summary/staff-performance` - スタッフ別成績（詳細）
- `GET /api/summary/staff-aggregated` - スタッフ別成績（集計済み）

**クエリパラメータ:**
- `store_code` (string) - 店舗コード
- `start_date` (ISO 8601) - 開始日
- `end_date` (ISO 8601) - 終了日
- `staff_id` (string) - スタッフID

## CSVフォーマット

アップロードするCSVは以下のカラムを含む必要があります：

```
販売日時,店舗コード,商品コード,商品名,数量,単価,合計金額,粗利,スタッフID,スタッフ名
2026-02-18 10:00:00,S001,P001,商品1,1,1000,1000,200,U001,田中太郎
```

## Docker での実行（オプション）

### 前提条件

- Docker & Docker Compose がインストールされていること

### 起動

```bash
docker-compose up -d
```

アクセス: http://localhost:8000

### 停止

```bash
docker-compose down
```

## トラブルシューティング

### SQLite 関連エラー

デフォルトではローカルの SQLite を使用します。別のディレクトリで実行する場合、`backend/.env` の `DATABASE_URL` を調整してください：

```env
DATABASE_URL=sqlite:///./sales.db
```

### ポート 8000 が既に使用中

別のポートで起動：

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

その後、http://localhost:8080 にアクセスしてください

### CSVアップロード失敗

- CSVのエンコーディングが UTF-8 であること確認
- 必須カラムが全て含まれているか確認
- ファイルサイズが極端に大きくない確認

### フロントエンド画面が表示されない

- バックエンドが起動しているか確認
- ブラウザのコンソール（F12キー）でエラーログを確認

## 開発環境設定

### Linux/Mac での実行権限

スクリプトに実行権限を付与：

```bash
chmod +x setup.sh run.sh
```

### 環境変数カスタマイズ

`backend/.env` で以下をカスタマイズ可能：

| 変数 | デフォルト | 説明 |
|-----|----------|------|
| DATABASE_URL | sqlite:///./sales.db | データベース接続URL |
| DEBUG | True | デバッグモード |
| CORS_ORIGINS | http://localhost:8000 | CORS許可オリジン |

## ライセンス

MIT

## サポート

問題が発生した場合は、GitHub Issues で報告してください。
