# Devin AI Clone - デプロイメントガイド

## 概要

このガイドでは、Devin AI Clone を様々な環境にデプロイする方法について説明します。開発環境から本番環境まで、段階的なデプロイメント手順を提供します。

## 前提条件

### システム要件

#### 最小要件
- **CPU**: 2コア以上
- **メモリ**: 4GB以上
- **ストレージ**: 20GB以上の空き容量
- **OS**: Linux (Ubuntu 18.04+), macOS 10.15+, Windows 10+

#### 推奨要件
- **CPU**: 4コア以上 (Intel i5/AMD Ryzen 5 相当)
- **メモリ**: 8GB以上
- **ストレージ**: 50GB以上の空き容量 (SSD推奨)
- **ネットワーク**: 安定したインターネット接続

#### GPU要件 (オプション)
- **NVIDIA GPU**: GTX 1060 / RTX 2060 以上
- **VRAM**: 6GB以上
- **CUDA**: 11.0以上
- **cuDNN**: 8.0以上

### ソフトウェア要件

#### 必須
- **Docker**: 20.10以上
- **Docker Compose**: 2.0以上
- **Git**: 2.20以上

#### オプション
- **NVIDIA Docker**: GPU使用時
- **Make**: 開発用コマンド実行
- **curl**: ヘルスチェック用

## ローカル開発環境

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/devin-ai-clone.git
cd devin-ai-clone
```

### 2. 環境設定

```bash
# 環境変数ファイルの作成
cp .env.example .env

# 環境変数の編集
nano .env
```

### 3. 必要な環境変数の設定

```bash
# GitHub Personal Access Token (必須)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# データベース設定
POSTGRES_PASSWORD=your_secure_password_here

# セキュリティ設定
SECRET_KEY=your_very_long_and_secure_secret_key_here

# 開発環境設定
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

### 4. 開発環境の起動

```bash
# 開発用セットアップ
make setup-dev

# 開発モードで起動
make dev

# または、直接Docker Composeを使用
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 5. 動作確認

```bash
# ヘルスチェック
curl http://localhost:5000/health

# フロントエンドアクセス
open http://localhost:8080
```

## ステージング環境

### 1. サーバー準備

```bash
# Ubuntu 20.04 LTSの場合
sudo apt update && sudo apt upgrade -y

# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Composeのインストール
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. アプリケーションのデプロイ

```bash
# アプリケーションディレクトリの作成
sudo mkdir -p /opt/devin-ai-clone
sudo chown $USER:$USER /opt/devin-ai-clone
cd /opt/devin-ai-clone

# リポジトリのクローン
git clone https://github.com/your-username/devin-ai-clone.git .

# 環境設定
cp .env.example .env
nano .env
```

### 3. ステージング用環境変数

```bash
# 環境設定
FLASK_ENV=staging
LOG_LEVEL=INFO

# データベース設定
POSTGRES_PASSWORD=staging_secure_password

# セキュリティ設定
SECRET_KEY=staging_very_long_and_secure_secret_key

# GitHub設定
GITHUB_TOKEN=your_github_token

# ドメイン設定
ALLOWED_ORIGINS=https://staging.your-domain.com
```

### 4. SSL証明書の設定

```bash
# Let's Encryptを使用する場合
sudo apt install certbot
sudo certbot certonly --standalone -d staging.your-domain.com

# 証明書をコピー
sudo cp /etc/letsencrypt/live/staging.your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/staging.your-domain.com/privkey.pem nginx/ssl/
sudo chown $USER:$USER nginx/ssl/*
```

### 5. ステージング環境の起動

```bash
# 本番用設定で起動
FLASK_ENV=staging docker-compose up -d

# 動作確認
./test.sh
```

## 本番環境

### 1. インフラストラクチャの準備

#### AWS EC2の場合

```bash
# インスタンス作成 (推奨: t3.large以上)
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx

# セキュリティグループの設定
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

#### Google Cloud Platformの場合

```bash
# インスタンス作成
gcloud compute instances create devin-ai-clone \
  --machine-type=n1-standard-2 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --tags=http-server,https-server

# ファイアウォールルールの作成
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server

gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags https-server
```

### 2. 本番環境のセットアップ

```bash
# サーバーにSSH接続
ssh -i your-key.pem ubuntu@your-server-ip

# システムの更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージのインストール
sudo apt install -y curl git make ufw

# ファイアウォールの設定
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable

# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Docker Composeのインストール
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 再ログイン（Dockerグループ反映のため）
exit
ssh -i your-key.pem ubuntu@your-server-ip
```

### 3. アプリケーションのデプロイ

```bash
# アプリケーションディレクトリの作成
sudo mkdir -p /opt/devin-ai-clone
sudo chown ubuntu:ubuntu /opt/devin-ai-clone
cd /opt/devin-ai-clone

# リポジトリのクローン
git clone https://github.com/your-username/devin-ai-clone.git .

# 本番用環境変数の設定
cp .env.example .env
nano .env
```

### 4. 本番用環境変数

```bash
# 環境設定
FLASK_ENV=production
LOG_LEVEL=WARNING

# データベース設定
POSTGRES_PASSWORD=production_very_secure_password_here
POSTGRES_DB=devin_ai_prod
POSTGRES_USER=devin_prod

# セキュリティ設定
SECRET_KEY=production_extremely_long_and_secure_secret_key_here

# GitHub設定
GITHUB_TOKEN=your_production_github_token

# ドメイン設定
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# パフォーマンス設定
CELERY_WORKER_CONCURRENCY=4
REDIS_MAXMEMORY=1gb
```

### 5. SSL証明書の設定

```bash
# Let's Encryptを使用
sudo apt install certbot

# 証明書の取得
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# 証明書のコピー
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
sudo chown ubuntu:ubuntu nginx/ssl/*

# 自動更新の設定
sudo crontab -e
# 以下を追加
# 0 12 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

### 6. 本番環境の起動

```bash
# 本番用設定で起動
FLASK_ENV=production docker-compose up -d

# 動作確認
./test.sh

# ログの確認
docker-compose logs -f
```

## 高可用性構成

### 1. ロードバランサーの設定

#### Nginx Proxy Manager使用

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  nginx-proxy-manager:
    image: 'jc21/nginx-proxy-manager:latest'
    restart: unless-stopped
    ports:
      - '80:80'
      - '81:81'
      - '443:443'
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
```

#### AWS Application Load Balancer使用

```bash
# ALBの作成
aws elbv2 create-load-balancer \
  --name devin-ai-clone-alb \
  --subnets subnet-xxxxxxxxx subnet-yyyyyyyyy \
  --security-groups sg-xxxxxxxxx

# ターゲットグループの作成
aws elbv2 create-target-group \
  --name devin-ai-clone-targets \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-xxxxxxxxx \
  --health-check-path /health
```

### 2. データベースクラスタリング

#### PostgreSQL Master-Slave構成

```yaml
# docker-compose.cluster.yml
version: '3.8'
services:
  postgres-master:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: replication_password
    volumes:
      - postgres_master_data:/var/lib/postgresql/data

  postgres-slave:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: replication_password
      POSTGRES_MASTER_HOST: postgres-master
    depends_on:
      - postgres-master
```

### 3. Redis Cluster

```yaml
# redis-cluster.yml
version: '3.8'
services:
  redis-node-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes

  redis-node-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes

  redis-node-3:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendonly yes
```

## 監視とログ

### 1. PrometheusとGrafanaの設定

```bash
# 監視スタックの起動
docker-compose --profile monitoring up -d

# Grafanaダッシュボードのインポート
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/dashboard.json
```

### 2. ログ集約

#### ELK Stack使用

```yaml
# elk-stack.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
```

### 3. アラート設定

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@your-domain.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@your-domain.com'
    subject: 'Devin AI Clone Alert'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## バックアップとリストア

### 1. データベースバックアップ

```bash
# 自動バックアップスクリプト
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
DB_NAME="devin_ai"

# バックアップディレクトリの作成
mkdir -p $BACKUP_DIR

# データベースバックアップ
docker-compose exec -T postgres pg_dump -U devin_user $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# 古いバックアップの削除（30日以上）
find $BACKUP_DIR -name "db_backup_*.sql" -mtime +30 -delete

# S3にアップロード（オプション）
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql s3://your-backup-bucket/database/
```

### 2. アプリケーションデータバックアップ

```bash
# アプリケーションデータのバックアップ
#!/bin/bash
# app-backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

# ワークスペースのバックアップ
tar -czf $BACKUP_DIR/workspace_backup_$DATE.tar.gz workspace/

# モデルキャッシュのバックアップ
tar -czf $BACKUP_DIR/models_backup_$DATE.tar.gz models/

# 設定ファイルのバックアップ
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz .env docker-compose.yml nginx/
```

### 3. リストア手順

```bash
# データベースリストア
docker-compose exec -T postgres psql -U devin_user -d devin_ai < backup_file.sql

# アプリケーションデータリストア
tar -xzf workspace_backup_20250613_120000.tar.gz
tar -xzf models_backup_20250613_120000.tar.gz

# サービス再起動
docker-compose restart
```

## パフォーマンス最適化

### 1. Docker最適化

```dockerfile
# 最適化されたDockerfile例
FROM python:3.11-slim as builder

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local

# アプリケーションコードのコピー
COPY . /app
WORKDIR /app

# 非rootユーザーで実行
RUN useradd --create-home --shell /bin/bash app
USER app

CMD ["python", "app.py"]
```

### 2. データベース最適化

```sql
-- PostgreSQL最適化設定
-- postgresql.conf

shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 3. Redis最適化

```conf
# redis.conf

maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
tcp-keepalive 300
timeout 0
```

## セキュリティ強化

### 1. ファイアウォール設定

```bash
# UFW設定
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# fail2banの設定
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Docker セキュリティ

```yaml
# セキュリティ強化されたdocker-compose.yml
version: '3.8'
services:
  backend:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

### 3. 環境変数の暗号化

```bash
# sopsを使用した環境変数の暗号化
sops -e .env > .env.encrypted

# 復号化
sops -d .env.encrypted > .env
```

## トラブルシューティング

### 1. 一般的な問題

#### メモリ不足
```bash
# メモリ使用量確認
docker stats

# スワップファイルの作成
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### ディスク容量不足
```bash
# ディスク使用量確認
df -h

# Dockerクリーンアップ
docker system prune -af
docker volume prune -f
```

#### ネットワーク問題
```bash
# ポート確認
netstat -tulpn | grep :8080

# ファイアウォール確認
sudo ufw status

# DNS確認
nslookup your-domain.com
```

### 2. ログ分析

```bash
# エラーログの確認
docker-compose logs backend | grep ERROR
docker-compose logs frontend | grep ERROR

# リアルタイムログ監視
docker-compose logs -f --tail=100

# 特定の時間範囲のログ
docker-compose logs --since="2025-06-13T10:00:00" --until="2025-06-13T11:00:00"
```

### 3. パフォーマンス問題

```bash
# CPU使用率確認
top
htop

# メモリ使用率確認
free -h

# ディスクI/O確認
iotop

# ネットワーク使用率確認
iftop
```

## 継続的デプロイメント

### 1. GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/devin-ai-clone
          git pull origin main
          docker-compose down
          docker-compose up -d --build
```

### 2. GitLab CI/CD

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  DOCKER_DRIVER: overlay2

build:
  stage: build
  script:
    - docker build -t devin-ai-clone .

test:
  stage: test
  script:
    - docker-compose -f docker-compose.test.yml up --abort-on-container-exit

deploy:
  stage: deploy
  script:
    - ssh user@server "cd /opt/devin-ai-clone && git pull && docker-compose up -d --build"
  only:
    - main
```

## まとめ

このデプロイメントガイドでは、Devin AI Clone を様々な環境にデプロイする方法を説明しました。環境に応じて適切な設定を選択し、セキュリティとパフォーマンスを考慮したデプロイメントを行ってください。

継続的な監視とメンテナンスにより、安定したサービス運用を実現できます。問題が発生した場合は、ログ分析とトラブルシューティング手順を参考に対処してください。

