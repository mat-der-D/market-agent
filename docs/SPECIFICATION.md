# market-agent 仕様書

## 1. 概要

ユーザーが指定した金額を USD↔JPY でリアルタイム換算する Discord BOT。

## 2. 機能要件

### 2.1 コマンド

| コマンド | 引数 | 説明 |
|---------|------|------|
| `/usd2jpy` | `amount` (数値) | 指定した USD 金額を JPY に換算して返す |
| `/jpy2usd` | `amount` (数値) | 指定した JPY 金額を USD に換算して返す |

### 2.2 レスポンス形式

換算結果に加え、以下の情報を付与して返す:

- 換算結果（小数点以下 2 桁）
- 使用した為替レート
- レート取得時刻（UTC）

例:
```
100 USD = 14,800.50 JPY
（レート: 148.005、取得時刻: 2024-01-15 09:00 UTC）
```

### 2.3 入力バリデーション

| 入力 | 結果 |
|------|------|
| 数値以外 | エラーメッセージを返す |
| 負の数値 | エラーメッセージを返す |
| 0 | `0` を返す（正常系） |

### 2.4 為替レート取得

- Yahoo! Finance から最新レートを取得する
- `yfinance` ライブラリを使用（API キー不要）
- ティッカーシンボル: `USDJPY=X`
- キャッシュなし（コマンド実行のたびに取得）

## 3. 非機能要件

### 3.1 技術スタック

| 層 | 技術 | 役割 |
|----|------|------|
| Discord 接続層 | discord.py (Python) | WebSocket 常駐、スラッシュコマンド受信 |
| ロジック層 | Cloud Run (GCP) | 為替レート取得・換算処理 |
| 市場データ取得 | yfinance (Python) | Yahoo! Finance から USD/JPY レート取得 |

※ データ永続化（Firestore 等）は不要（ステートレス）

### 3.2 デプロイ構成（VPS + Cloud Run の分離構成）

discord.py の WebSocket 常駐コストを既存 VPS のリソースで吸収し、
GCP 側はリクエスト単位の課金に抑えるアーキテクチャを採用する。

```
Discord
  │ スラッシュコマンド（WebSocket）
  ▼
XServer VPS（薄い常駐プロセス）
  │ HTTP POST /convert
  │ リクエストボディ: {from_currency, to_currency, amount}
  ▼
Cloud Run（換算 API、スケールゼロ対応）
  │
  └── Yahoo! Finance（yfinance 経由、リアルタイム取得）
  │
  └── レスポンス: {"result": 14800.50, "rate": 148.005, "fetched_at": "..."}
  ▼
XServer VPS がレスポンスを受けて Discord に返信
```

**VPS 側の責務（薄く保つ）:**

- Discord WebSocket 接続の維持
- スラッシュコマンドの受信と入力値の取得
- Cloud Run API への HTTP 呼び出し
- レスポンスに従い Discord へ返信

**Cloud Run 側の責務（ビジネスロジック全般）:**

- 入力値のバリデーション
- 外部 API から最新の為替レート取得
- 換算処理と結果の整形

**コスト面のメリット:**

- VPS: 既存契約のため追加コストなし
- Cloud Run: コマンド実行分だけリクエスト課金（無料枠 200 万リクエスト/月で実質ゼロ）
- Firestore 不使用のためデータ層のコストもゼロ

### 3.3 信頼性・可用性

- Cloud Run のスケールゼロによりアイドル時のコストを最小化
- 外部 API が利用不可の場合はエラーメッセージを返す
- Discord のスラッシュコマンドは 3 秒以内のレスポンスが必要なため、`defer` を使い応答を遅延させる

## 4. 環境変数

| 変数名 | 必須 | 説明 | デフォルト |
|--------|------|------|-----------|
| `DISCORD_TOKEN` | ✓ | Discord BOT トークン | - |
| `API_URL` | ✓ | Cloud Run API のエンドポイント URL | - |

## 5. API 仕様（Cloud Run）

### POST /convert

**リクエストボディ:**

```json
{
  "from_currency": "USD",
  "to_currency": "JPY",
  "amount": 100.0
}
```

**レスポンス（成功時）:**

```json
{
  "result": 14800.50,
  "rate": 148.005,
  "fetched_at": "2024-01-15T09:00:00Z"
}
```

**レスポンス（エラー時）:**

```json
{
  "error": "Invalid amount"
}
```

## 6. 処理フロー

```
スラッシュコマンド受信 (/usd2jpy or /jpy2usd)
    │
    ├─ Discord に defer 応答を送信（3 秒タイムアウト回避）
    │
    ├─ Cloud Run API に HTTP POST /convert を送信
    │
    │   Cloud Run 内処理:
    │   ├─ 入力値が数値か？ → No → {"error": "..."} を返す
    │   ├─ 入力値が正の数か？ → No → {"error": "..."} を返す
    │   ├─ Yahoo! Finance から USD/JPY レートを取得（yfinance: USDJPY=X）
    │   │       → 失敗時 → {"error": "為替レートの取得に失敗しました"} を返す
    │   └─ 換算処理（amount × rate または amount ÷ rate）
    │
    └─ レスポンスを Discord メッセージとしてフォローアップ返信
```

## 7. セキュリティ要件

- BOT トークンは環境変数 `DISCORD_TOKEN` で管理し、コードに直接記述しない

## 8. 開発・デプロイ構成（想定）

```
/
├── bot/                  # VPS にデプロイする Discord 接続層
│   ├── main.py           # discord.py エントリーポイント
│   └── requirements.txt
├── api/                  # Cloud Run にデプロイするロジック層
│   ├── main.py           # FastAPI エンドポイント
│   ├── converter.py      # 通貨換算ロジック
│   ├── rate_fetcher.py   # 為替レート取得
│   ├── requirements.txt
│   └── Dockerfile
└── docs/
    └── SPECIFICATION.md
```
