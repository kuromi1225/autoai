#!/bin/bash

# Devin AI Clone 起動スクリプト
# Windows (Git Bash/WSL), macOS, Linux 対応

set -e

# カラー出力の設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# OS検出
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS=Linux;;
        Darwin*)    OS=Mac;;
        CYGWIN*)    OS=Windows;;
        MINGW*)     OS=Windows;;
        MSYS*)      OS=Windows;;
        *)          OS="Unknown";;
    esac
    log_info "検出されたOS: $OS"
}

# Docker と Docker Compose の確認
check_docker() {
    log_info "Docker環境を確認しています..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Dockerがインストールされていません"
        log_info "Dockerをインストールしてください: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Dockerデーモンが起動していません"
        log_info "Dockerを起動してください"
        exit 1
    fi
    
    # Docker Compose の確認（v2とv1の両方をサポート）
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        log_info "Docker Compose v1を使用します"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
        log_info "Docker Compose v2を使用します"
    else
        log_error "Docker Composeが見つかりません"
        exit 1
    fi
    
    log_success "Docker環境の確認が完了しました"
}

# 環境設定ファイルの確認
check_env_file() {
    log_info "環境設定ファイルを確認しています..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".envファイルが見つかりません。.env.exampleからコピーします"
            cp .env.example .env
            log_info ".envファイルを編集して必要な設定を行ってください"
        else
            log_error ".env.exampleファイルが見つかりません"
            exit 1
        fi
    fi
    
    log_success "環境設定ファイルの確認が完了しました"
}

# シークレットファイルの確認と生成
setup_secrets() {
    log_info "シークレットファイルを確認しています..."
    
    if [ ! -d "secrets" ]; then
        mkdir -p secrets
        log_info "secretsディレクトリを作成しました"
    fi
    
    # シークレットファイルの生成
    if [ ! -f "secrets/jwt_secret_key.txt" ]; then
        openssl rand -base64 32 > secrets/jwt_secret_key.txt 2>/dev/null || echo "$(date +%s)_jwt_secret_$(openssl rand -hex 16)" > secrets/jwt_secret_key.txt
        log_info "JWT秘密鍵を生成しました"
    fi
    
    if [ ! -f "secrets/db_password.txt" ]; then
        openssl rand -base64 16 > secrets/db_password.txt 2>/dev/null || echo "devin_db_$(openssl rand -hex 8)" > secrets/db_password.txt
        log_info "データベースパスワードを生成しました"
    fi
    
    if [ ! -f "secrets/redis_password.txt" ]; then
        openssl rand -base64 16 > secrets/redis_password.txt 2>/dev/null || echo "devin_redis_$(openssl rand -hex 8)" > secrets/redis_password.txt
        log_info "Redisパスワードを生成しました"
    fi
    
    if [ ! -f "secrets/encryption_key.txt" ]; then
        openssl rand -base64 32 > secrets/encryption_key.txt 2>/dev/null || echo "$(date +%s)_encryption_$(openssl rand -hex 16)" > secrets/encryption_key.txt
        log_info "暗号化キーを生成しました"
    fi
    
    # Windows環境での権限設定
    if [ "$OS" = "Windows" ]; then
        log_info "Windows環境でのファイル権限を設定しています..."
        chmod 600 secrets/* 2>/dev/null || true
    else
        chmod 600 secrets/*
    fi
    
    log_success "シークレットファイルの設定が完了しました"
}

# ネットワーク競合の確認
check_network_conflicts() {
    log_info "ネットワーク競合を確認しています..."
    
    # 既存のネットワークをクリーンアップ
    if docker network ls | grep -q "devin-network"; then
        log_warning "既存のdevin-networkを削除します"
        docker network rm devin-network 2>/dev/null || true
    fi
    
    if docker network ls | grep -q "devin-ai-clone_devin-network"; then
        log_warning "既存のdevin-ai-clone_devin-networkを削除します"
        docker network rm devin-ai-clone_devin-network 2>/dev/null || true
    fi
    
    log_success "ネットワーク競合の確認が完了しました"
}

# ポート競合の確認
check_port_conflicts() {
    log_info "ポート競合を確認しています..."
    
    PORTS=(8765 8766 8767 8768)
    
    for port in "${PORTS[@]}"; do
        if command -v netstat &> /dev/null; then
            if netstat -tuln 2>/dev/null | grep -q ":$port "; then
                log_warning "ポート $port が使用中です"
            fi
        elif command -v ss &> /dev/null; then
            if ss -tuln 2>/dev/null | grep -q ":$port "; then
                log_warning "ポート $port が使用中です"
            fi
        fi
    done
    
    log_success "ポート競合の確認が完了しました"
}

# Docker Composeサービスの起動
start_services() {
    log_info "Devin AI Cloneサービスを起動しています..."
    
    # 既存のコンテナを停止・削除
    $DOCKER_COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    
    # イメージのビルドと起動
    log_info "Dockerイメージをビルドしています..."
    $DOCKER_COMPOSE_CMD build --no-cache
    
    log_info "サービスを起動しています..."
    $DOCKER_COMPOSE_CMD up -d
    
    log_success "サービスの起動が完了しました"
}

# ヘルスチェック
health_check() {
    log_info "サービスのヘルスチェックを実行しています..."
    
    # 最大待機時間（秒）
    MAX_WAIT=300
    WAIT_TIME=0
    
    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if curl -s http://localhost:8765/health > /dev/null 2>&1; then
            log_success "アプリケーションが正常に起動しました！"
            break
        fi
        
        log_info "起動を待機中... ($WAIT_TIME/$MAX_WAIT秒)"
        sleep 10
        WAIT_TIME=$((WAIT_TIME + 10))
    done
    
    if [ $WAIT_TIME -ge $MAX_WAIT ]; then
        log_warning "ヘルスチェックがタイムアウトしました"
        log_info "サービスの状態を確認してください: $DOCKER_COMPOSE_CMD logs"
    fi
}

# アクセス情報の表示
show_access_info() {
    echo ""
    log_success "🎉 Devin AI Clone が起動しました！"
    echo ""
    echo "📱 アクセス情報:"
    echo "   メインアプリケーション: http://localhost:8765"
    echo "   ChromaDB管理画面:      http://localhost:8767"
    echo "   Prometheus監視:        http://localhost:8768 (monitoring profile使用時)"
    echo ""
    echo "🔧 管理コマンド:"
    echo "   ログ確認:    $DOCKER_COMPOSE_CMD logs -f"
    echo "   停止:        $DOCKER_COMPOSE_CMD down"
    echo "   再起動:      $DOCKER_COMPOSE_CMD restart"
    echo "   状態確認:    $DOCKER_COMPOSE_CMD ps"
    echo ""
    echo "📚 ドキュメント:"
    echo "   README.md を参照してください"
    echo ""
}

# メイン実行
main() {
    echo "🚀 Devin AI Clone 起動スクリプト"
    echo "=================================="
    
    detect_os
    check_docker
    check_env_file
    setup_secrets
    check_network_conflicts
    check_port_conflicts
    start_services
    health_check
    show_access_info
}

# スクリプト実行
main "$@"

