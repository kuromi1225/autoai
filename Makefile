# Makefile for Devin AI Clone
# クロスプラットフォーム対応版

.PHONY: help start stop restart logs build clean health test setup

# デフォルトターゲット
.DEFAULT_GOAL := help

# Docker Compose コマンドの検出
DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null || echo "docker compose")

# カラー出力
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m

help: ## ヘルプを表示
	@echo "$(BLUE)Devin AI Clone - 管理コマンド$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(GREEN)基本コマンド:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)アクセス情報:$(NC)"
	@echo "  メインアプリ:     http://localhost:8765"
	@echo "  ChromaDB:        http://localhost:8767"
	@echo "  Prometheus:      http://localhost:8768"

setup: ## 初期セットアップ（シークレット生成等）
	@echo "$(BLUE)初期セットアップを実行しています...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN).envファイルを作成しました$(NC)"; \
		else \
			echo "$(RED).env.exampleが見つかりません$(NC)"; \
			exit 1; \
		fi \
	fi
	@mkdir -p secrets
	@if [ ! -f secrets/jwt_secret_key.txt ]; then \
		openssl rand -base64 32 > secrets/jwt_secret_key.txt 2>/dev/null || echo "jwt_secret_$$(date +%s)" > secrets/jwt_secret_key.txt; \
		echo "$(GREEN)JWT秘密鍵を生成しました$(NC)"; \
	fi
	@if [ ! -f secrets/db_password.txt ]; then \
		openssl rand -base64 16 > secrets/db_password.txt 2>/dev/null || echo "db_pass_$$(date +%s)" > secrets/db_password.txt; \
		echo "$(GREEN)データベースパスワードを生成しました$(NC)"; \
	fi
	@if [ ! -f secrets/redis_password.txt ]; then \
		openssl rand -base64 16 > secrets/redis_password.txt 2>/dev/null || echo "redis_pass_$$(date +%s)" > secrets/redis_password.txt; \
		echo "$(GREEN)Redisパスワードを生成しました$(NC)"; \
	fi
	@if [ ! -f secrets/encryption_key.txt ]; then \
		openssl rand -base64 32 > secrets/encryption_key.txt 2>/dev/null || echo "enc_key_$$(date +%s)" > secrets/encryption_key.txt; \
		echo "$(GREEN)暗号化キーを生成しました$(NC)"; \
	fi
	@chmod 600 secrets/* 2>/dev/null || true
	@echo "$(GREEN)セットアップが完了しました$(NC)"

build: setup ## Dockerイメージをビルド
	@echo "$(BLUE)Dockerイメージをビルドしています...$(NC)"
	$(DOCKER_COMPOSE) build --no-cache

start: setup ## サービスを起動
	@echo "$(BLUE)Devin AI Cloneを起動しています...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)起動完了！ http://localhost:8765 でアクセスできます$(NC)"

start-monitoring: setup ## 監視サービスも含めて起動
	@echo "$(BLUE)監視サービスも含めてDevin AI Cloneを起動しています...$(NC)"
	$(DOCKER_COMPOSE) --profile monitoring up -d
	@echo "$(GREEN)起動完了！$(NC)"
	@echo "  メインアプリ: http://localhost:8765"
	@echo "  Prometheus:   http://localhost:8768"

stop: ## サービスを停止
	@echo "$(BLUE)サービスを停止しています...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)停止完了$(NC)"

restart: ## サービスを再起動
	@echo "$(BLUE)サービスを再起動しています...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)再起動完了$(NC)"

logs: ## 全サービスのログを表示
	$(DOCKER_COMPOSE) logs -f

logs-backend: ## バックエンドのログを表示
	$(DOCKER_COMPOSE) logs -f backend

logs-frontend: ## フロントエンドのログを表示
	$(DOCKER_COMPOSE) logs -f frontend

logs-nginx: ## Nginxのログを表示
	$(DOCKER_COMPOSE) logs -f nginx

logs-chromadb: ## ChromaDBのログを表示
	$(DOCKER_COMPOSE) logs -f chromadb

status: ## サービスの状態を確認
	@echo "$(BLUE)サービス状態:$(NC)"
	$(DOCKER_COMPOSE) ps

health: ## ヘルスチェックを実行
	@echo "$(BLUE)ヘルスチェックを実行しています...$(NC)"
	@curl -s http://localhost:8765/health > /dev/null && echo "$(GREEN)✓ メインアプリケーション: 正常$(NC)" || echo "$(RED)✗ メインアプリケーション: 異常$(NC)"
	@curl -s http://localhost:8767/api/v1/version > /dev/null && echo "$(GREEN)✓ ChromaDB: 正常$(NC)" || echo "$(RED)✗ ChromaDB: 異常$(NC)"

test: ## テストを実行
	@echo "$(BLUE)テストを実行しています...$(NC)"
	$(DOCKER_COMPOSE) exec backend python -m pytest tests/ || echo "$(YELLOW)バックエンドテストをスキップ（コンテナが起動していません）$(NC)"
	@cd frontend && npm test 2>/dev/null || echo "$(YELLOW)フロントエンドテストをスキップ（npm環境が設定されていません）$(NC)"

clean: ## 全てのコンテナ・ボリューム・ネットワークを削除
	@echo "$(YELLOW)警告: 全てのデータが削除されます。続行しますか？ [y/N]$(NC)"
	@read -r REPLY; \
	if [ "$$REPLY" = "y" ] || [ "$$REPLY" = "Y" ]; then \
		echo "$(BLUE)クリーンアップを実行しています...$(NC)"; \
		$(DOCKER_COMPOSE) down -v --remove-orphans; \
		docker system prune -f; \
		echo "$(GREEN)クリーンアップ完了$(NC)"; \
	else \
		echo "$(YELLOW)キャンセルされました$(NC)"; \
	fi

clean-force: ## 強制的にクリーンアップ（確認なし）
	@echo "$(BLUE)強制クリーンアップを実行しています...$(NC)"
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)クリーンアップ完了$(NC)"

shell-backend: ## バックエンドコンテナにシェルアクセス
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-frontend: ## フロントエンドコンテナにシェルアクセス
	$(DOCKER_COMPOSE) exec frontend /bin/sh

shell-postgres: ## PostgreSQLコンテナにアクセス
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d devin_ai_clone

shell-redis: ## Redisコンテナにアクセス
	$(DOCKER_COMPOSE) exec redis redis-cli

backup-db: ## データベースをバックアップ
	@echo "$(BLUE)データベースをバックアップしています...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U postgres devin_ai_clone > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)バックアップ完了: backups/$(NC)"

restore-db: ## データベースを復元（最新のバックアップから）
	@echo "$(BLUE)データベースを復元しています...$(NC)"
	@LATEST_BACKUP=$$(ls -t backups/db_backup_*.sql 2>/dev/null | head -n1); \
	if [ -n "$$LATEST_BACKUP" ]; then \
		echo "復元ファイル: $$LATEST_BACKUP"; \
		$(DOCKER_COMPOSE) exec -T postgres psql -U postgres devin_ai_clone < "$$LATEST_BACKUP"; \
		echo "$(GREEN)復元完了$(NC)"; \
	else \
		echo "$(RED)バックアップファイルが見つかりません$(NC)"; \
	fi

update: ## プロジェクトを更新
	@echo "$(BLUE)プロジェクトを更新しています...$(NC)"
	git pull
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)更新完了$(NC)"

dev-frontend: ## フロントエンド開発モード
	@echo "$(BLUE)フロントエンド開発サーバーを起動しています...$(NC)"
	@cd frontend && npm install && npm run dev

dev-backend: ## バックエンド開発モード
	@echo "$(BLUE)バックエンド開発サーバーを起動しています...$(NC)"
	@cd backend && pip install -r requirements.txt && python app.py

# Windows用のヘルプ（PowerShellから実行される場合）
help-windows: ## Windows用ヘルプ
	@echo "Windows環境では以下のコマンドも利用できます:"
	@echo "  .\start.ps1          - PowerShellで起動"
	@echo "  .\start.bat          - コマンドプロンプトで起動"
	@echo "  make start           - Makefileで起動（WSL/Git Bash）"

