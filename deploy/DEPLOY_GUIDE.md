# A2A SNS System - EC2 Deploy Guide

## Prerequisites

- AWS アカウント
- Claude Code サブスクリプション（Max または Pro）
- SSH キーペア

---

## Step 1: EC2 インスタンス作成

### AWS Console から作成

1. **EC2 Dashboard** > **Launch Instance**

2. **設定**:
   | 項目 | 推奨値 |
   |------|--------|
   | Name | `a2a-sns-server` |
   | AMI | Amazon Linux 2023 または Ubuntu 22.04 |
   | Instance Type | `t3.medium`（4GB RAM） |
   | Key Pair | 既存のものを選択 or 新規作成 |
   | Storage | 20GB gp3 |

3. **Security Group** 設定:
   ```
   Inbound Rules:
   - SSH (22)        : Your IP のみ
   - HTTP (80)       : Anywhere (API公開する場合)
   - Custom TCP 8080-8084 : Your IP (開発用)
   ```

4. **Launch**

### AWS CLI で作成（オプション）

```bash
# セキュリティグループ作成
aws ec2 create-security-group \
  --group-name a2a-sns-sg \
  --description "A2A SNS System Security Group"

# SSH許可
aws ec2 authorize-security-group-ingress \
  --group-name a2a-sns-sg \
  --protocol tcp \
  --port 22 \
  --cidr $(curl -s ifconfig.me)/32

# インスタンス起動
aws ec2 run-instances \
  --image-id ami-0599b6e53ca798bb2 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-groups a2a-sns-sg \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=a2a-sns-server}]'
```

---

## Step 2: SSH 接続

```bash
# EC2のパブリックIPを取得
EC2_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=a2a-sns-server" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

# SSH接続
ssh -i ~/.ssh/your-key.pem ec2-user@$EC2_IP
# Ubuntu の場合: ssh -i ~/.ssh/your-key.pem ubuntu@$EC2_IP
```

---

## Step 3: 環境セットアップ

### セットアップスクリプト実行

```bash
# スクリプトをダウンロードして実行
curl -sSL https://raw.githubusercontent.com/YOUR_REPO/deploy/ec2-setup.sh | bash

# または、ローカルからコピー
scp -i ~/.ssh/your-key.pem deploy/ec2-setup.sh ec2-user@$EC2_IP:~
ssh -i ~/.ssh/your-key.pem ec2-user@$EC2_IP "bash ~/ec2-setup.sh"
```

### 再ログイン（Docker グループ適用）

```bash
exit
ssh -i ~/.ssh/your-key.pem ec2-user@$EC2_IP
```

---

## Step 4: Claude Code 認証

```bash
# Claude Code にログイン
claude login

# ブラウザが開けない環境では、表示されるURLを手動でブラウザで開く
# 認証コードをターミナルに貼り付け
```

**認証情報の保存場所**: `~/.claude/`

---

## Step 5: A2A システムデプロイ

### プロジェクトをデプロイ

```bash
cd /opt/a2a-sns

# Git clone（プライベートリポジトリの場合）
git clone https://github.com/YOUR_REPO/A2A-SNS.git .

# または SCP で直接コピー（ローカルから）
# scp -r -i ~/.ssh/your-key.pem ./* ec2-user@$EC2_IP:/opt/a2a-sns/
```

### 依存関係インストール

```bash
pip3 install -r _shared/requirements.txt
```

### 🔒 セキュリティ設定（重要）

```bash
# 1. APIキーを生成
export A2A_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Your API Key: $A2A_API_KEY"
echo "export A2A_API_KEY=$A2A_API_KEY" >> ~/.bashrc

# 2. 環境変数を設定
cp .env.example .env
nano .env  # 実際の値を設定

# 必須設定:
# - A2A_API_KEY=<生成したキー>
# - GOOGLE_API_KEY=<YouTube API キー>
```

### システム起動

```bash
# Docker Compose で全エージェント起動（EC2用設定）
docker-compose -f docker-compose.ec2.yml up -d

# ログ確認
docker-compose -f docker-compose.ec2.yml logs -f

# 状態確認
docker-compose -f docker-compose.ec2.yml ps
```

---

## Step 6: HTTPS 設定（本番環境必須）

### 自己署名証明書（開発用）

```bash
cd deploy/nginx
./generate-ssl.sh
```

### Let's Encrypt（本番用）

```bash
# ドメインのDNSをEC2のIPに向けてから実行
sudo ./setup-letsencrypt.sh your-domain.com your-email@example.com
```

### nginx + HTTPS で起動

```bash
docker-compose -f docker-compose.ec2.yml up -d
```

---

## Step 7: 動作確認

### Agent Card 取得（認証不要）

```bash
# HTTP（開発用）
curl http://localhost:8099/.well-known/agent.json | jq

# HTTPS（本番用）
curl https://your-domain.com/.well-known/agent.json | jq
```

### タスク送信テスト（認証必須）

```bash
# APIキーをヘッダーに付与
curl -X POST http://localhost:8099/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $A2A_API_KEY" \
  -d '{
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "テスト: Hello World"}]
    }
  }' | jq
```

### HTTPS経由（本番用）

```bash
curl -X POST https://your-domain.com/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $A2A_API_KEY" \
  -d '{
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "バズ動画をチェック"}]
    }
  }' | jq
```

### ヘルスチェック

```bash
curl https://your-domain.com/health
# {"status": "healthy"}
```

---

## 運用コマンド

### サービス管理

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再起動
docker-compose restart

# ログ確認
docker-compose logs -f sns-orchestrator

# 個別サービスログ
docker-compose logs -f youtube-script-writer
```

### systemd で自動起動設定

```bash
# 有効化
sudo systemctl enable a2a-sns
sudo systemctl start a2a-sns

# ステータス確認
sudo systemctl status a2a-sns

# 停止
sudo systemctl stop a2a-sns
```

---

## コスト試算

### EC2 インスタンス（東京リージョン、オンデマンド）

| インスタンス | vCPU | RAM | 月額 | 用途 |
|-------------|------|-----|------|------|
| t3.micro | 1 | 1GB | ~$12 | Claude Code単体のみ |
| t3.small | 2 | 2GB | ~$24 | 最小構成（メモリ注意） |
| **t3.medium** | 2 | 4GB | **~$47** | **推奨**（Docker + 5サービス） |
| t3.large | 2 | 8GB | ~$95 | 余裕あり |

### 追加コスト

| 項目 | コスト |
|------|--------|
| EBS (20GB gp3) | ~$2/月 |
| データ転送（OUT） | $0.114/GB |
| Elastic IP | $3.65/月（停止時） |

### 節約オプション

1. **Reserved Instance (1年)**: 約30%オフ
2. **Spot Instance**: 約70%オフ（中断リスクあり）
3. **Savings Plans**: 柔軟な割引

---

## トラブルシューティング

### Claude Code 認証エラー

```bash
# 認証情報削除して再ログイン
rm -rf ~/.claude
claude login
```

### Docker メモリ不足

```bash
# メモリ確認
free -h

# スワップ追加（t3.small以下の場合）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### ポート競合

```bash
# 使用中のポート確認
sudo netstat -tlnp | grep -E '808[0-4]'

# プロセス強制終了
sudo kill -9 $(sudo lsof -t -i:8080)
```

---

## セキュリティ推奨事項

### 必須事項

1. **API認証キー設定**: `A2A_API_KEY` 環境変数を必ず設定
2. **HTTPS有効化**: Let's Encrypt で無料SSL証明書を取得
3. **SSH キーのみ許可**（パスワード認証無効化）
4. **Security Group**: 80/443 のみ公開、SSHは自分のIPのみ

### 推奨事項

5. **Claude 認証情報**: EC2 外には持ち出さない
6. **定期的なアップデート**: `sudo dnf update -y`
7. **ログ監視**: CloudWatch Logs 連携推奨
8. **APIキーローテーション**: 定期的に新しいキーに変更

### セキュリティチェックリスト

```bash
# 1. APIキーが設定されているか確認
echo $A2A_API_KEY

# 2. HTTPS証明書の有効期限確認
openssl x509 -enddate -noout -in deploy/nginx/ssl/cert.pem

# 3. 外部からのアクセステスト（認証なしは拒否されるべき）
curl -X POST https://your-domain.com/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"type":"text","text":"test"}]}}'
# Expected: 401 Unauthorized

# 4. 認証ありでアクセス成功
curl -X POST https://your-domain.com/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $A2A_API_KEY" \
  -d '{"message":{"role":"user","parts":[{"type":"text","text":"test"}]}}'
# Expected: 200 OK
```

---

## 次のステップ

- [x] HTTPS 対応（Let's Encrypt）
- [x] API認証（X-API-Key）
- [x] レート制限（nginx + アプリ層）
- [ ] ドメイン設定（Route 53）
- [ ] Auto Scaling 設定
- [ ] CloudWatch アラーム設定
- [ ] バックアップ自動化
