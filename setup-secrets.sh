#!/bin/bash

# セキュアな機密情報生成スクリプト

set -euo pipefail

SECRETS_DIR="./secrets"
ENV_FILE=".env"

echo "🔐 Devin AI Clone - セキュアな機密情報生成スクリプト"
echo "=================================================="

# secretsディレクトリを作成
mkdir -p "$SECRETS_DIR"

# 機密情報生成関数
generate_secret() {
    local name="$1"
    local length="${2:-32}"
    local file="$SECRETS_DIR/${name}.txt"
    
    if [[ -f "$file" ]]; then
        echo "⚠️  $name は既に存在します。スキップします。"
        return 0
    fi
    
    echo "🔑 $name を生成中..."
    python3 -c "import secrets; print(secrets.token_urlsafe($length))" > "$file"
    chmod 600 "$file"
    echo "✅ $name を生成しました: $file"
}

# パスワード生成関数
generate_password() {
    local name="$1"
    local length="${2:-16}"
    local file="$SECRETS_DIR/${name}.txt"
    
    if [[ -f "$file" ]]; then
        echo "⚠️  $name は既に存在します。スキップします。"
        return 0
    fi
    
    echo "🔑 $name を生成中..."
    python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range($length)))" > "$file"
    chmod 600 "$file"
    echo "✅ $name を生成しました: $file"
}

echo ""
echo "🔐 機密情報を生成しています..."
echo ""

# JWT秘密鍵
generate_secret "jwt_secret_key" 32

# データベースパスワード
generate_password "db_password" 20

# Redisパスワード
generate_password "redis_password" 16

# 暗号化キー
generate_secret "encryption_key" 32

echo ""
echo "📝 .envファイルを作成しています..."

# .envファイルが存在しない場合は.env.exampleからコピー
if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f ".env.example" ]]; then
        cp ".env.example" "$ENV_FILE"
        echo "✅ .env.exampleから.envファイルを作成しました"
    else
        echo "❌ .env.exampleファイルが見つかりません"
        exit 1
    fi
else
    echo "⚠️  .envファイルは既に存在します"
fi

echo ""
echo "🔒 ファイル権限を設定しています..."

# .envファイルの権限を制限
chmod 600 "$ENV_FILE"

# secretsディレクトリの権限を制限
chmod 700 "$SECRETS_DIR"

echo ""
echo "✅ セットアップが完了しました！"
echo ""
echo "📋 生成された機密情報:"
echo "  - JWT秘密鍵: $SECRETS_DIR/jwt_secret_key.txt"
echo "  - データベースパスワード: $SECRETS_DIR/db_password.txt"
echo "  - Redisパスワード: $SECRETS_DIR/redis_password.txt"
echo "  - 暗号化キー: $SECRETS_DIR/encryption_key.txt"
echo ""
echo "⚠️  重要な注意事項:"
echo "  1. secretsディレクトリをGitにコミットしないでください"
echo "  2. 本番環境では、これらのファイルを安全な場所にバックアップしてください"
echo "  3. 定期的にパスワードを変更してください"
echo ""
echo "🚀 次のステップ:"
echo "  1. .envファイルを確認し、必要に応じて設定を調整してください"
echo "  2. docker compose up -d でアプリケーションを起動してください"
echo ""

# 管理者パスワードを表示
echo "👤 デフォルト管理者アカウント:"
echo "  ユーザー名: admin"
echo "  パスワード: アプリケーション起動時にログに表示されます"
echo ""

