# デプロイ手順

## 前提条件

- GCP プロジェクトが作成済みであること
- `gcloud` CLI がインストール済みであること
- XServer VPS に SSH でアクセスできること
- Discord Developer Portal で BOT が作成済みで、**Applications Commands** スコープが有効であること

---

## 1. API のデプロイ（GCP Cloud Run）

### 1.1 GCP の準備

```bash
# プロジェクトを設定
gcloud config set project YOUR_PROJECT_ID

# 必要な API を有効化
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 1.2 Cloud Run へデプロイ

```bash
# api/ ディレクトリに移動
cd api/

# Cloud Run にデプロイ（Dockerfile を使ったソースデプロイ）
gcloud run deploy market-agent-api \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### 1.3 サービス URL の確認

デプロイ完了後に表示される URL（例: `https://market-agent-api-xxxx-an.a.run.app`）を控えておきます。
後述の VPS 側設定で `API_URL` に使用します。

### 1.4 動作確認

```bash
curl https://market-agent-api-xxxx-an.a.run.app/health
# {"status":"ok"} が返れば OK

curl -X POST https://market-agent-api-xxxx-an.a.run.app/convert \
  -H "Content-Type: application/json" \
  -d '{"from_currency":"USD","to_currency":"JPY","amount":100}'
# {"result":...,"rate":...,"fetched_at":"..."} が返れば OK
```

---

## 2. BOT のデプロイ（XServer VPS）

### 2.1 VPS へ SSH 接続

```bash
ssh USERNAME@YOUR_VPS_IP
```

### 2.2 リポジトリのクローン

```bash
git clone https://github.com/YOUR_ORG/market-agent.git
cd market-agent
```

### 2.3 Python 環境のセットアップ

```bash
cd bot/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.4 環境変数ファイルの作成

```bash
cat > .env << 'EOF'
DISCORD_TOKEN=your_discord_bot_token_here
API_URL=https://market-agent-api-xxxx-an.a.run.app
EOF
chmod 600 .env
```

### 2.5 動作確認（手動起動）

```bash
source .venv/bin/activate
export $(cat .env | xargs)
python main.py
```

ログに `Logged in as ... (ID: ...)` が表示されれば正常起動しています。
スラッシュコマンド `/usd2jpy` と `/jpy2usd` が Discord で使えることを確認します。
`Ctrl+C` で停止します。

### 2.6 systemd サービスとして登録（常駐化）

```bash
# サービスファイルを作成
sudo tee /etc/systemd/system/market-agent-bot.service << EOF
[Unit]
Description=market-agent Discord Bot
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/market-agent/bot
EnvironmentFile=$HOME/market-agent/bot/.env
ExecStart=$HOME/market-agent/bot/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# サービスを有効化・起動
sudo systemctl daemon-reload
sudo systemctl enable market-agent-bot
sudo systemctl start market-agent-bot
```

### 2.7 サービス状態の確認

```bash
sudo systemctl status market-agent-bot
sudo journalctl -u market-agent-bot -f  # ログをリアルタイム確認
```

---

## 3. 更新手順

### API を更新する場合

```bash
cd api/
gcloud run deploy market-agent-api --source . --region asia-northeast1
```

### BOT を更新する場合

```bash
# VPS 上で
cd market-agent/
git pull
sudo systemctl restart market-agent-bot
```

---

## 4. 環境変数リファレンス

| 変数名 | コンポーネント | 必須 | 説明 |
|--------|--------------|------|------|
| `DISCORD_TOKEN` | bot | ✓ | Discord BOT トークン |
| `API_URL` | bot | ✓ | Cloud Run サービスの URL |
