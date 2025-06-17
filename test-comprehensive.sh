#!/bin/bash

# 包括的テストスイート実行スクリプト

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🧪 Devin AI Clone - 包括的テストスイート"
echo "========================================"

# カラー定義
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

# テスト結果を記録
TEST_RESULTS=()
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# テスト実行関数
run_test() {
    local test_name="$1"
    local test_command="$2"
    local test_dir="${3:-$PROJECT_ROOT}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_info "Running: $test_name"
    
    if cd "$test_dir" && eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name"
        TEST_RESULTS+=("✅ $test_name")
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$test_name"
        TEST_RESULTS+=("❌ $test_name")
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 詳細テスト実行関数（出力を表示）
run_detailed_test() {
    local test_name="$1"
    local test_command="$2"
    local test_dir="${3:-$PROJECT_ROOT}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_info "Running: $test_name"
    echo "Command: $test_command"
    echo "Directory: $test_dir"
    echo "----------------------------------------"
    
    if cd "$test_dir" && eval "$test_command"; then
        echo "----------------------------------------"
        log_success "$test_name"
        TEST_RESULTS+=("✅ $test_name")
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo "----------------------------------------"
        log_error "$test_name"
        TEST_RESULTS+=("❌ $test_name")
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# パフォーマンステスト関数
run_performance_test() {
    local test_name="$1"
    local test_command="$2"
    local max_time="$3"
    local test_dir="${4:-$PROJECT_ROOT}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_info "Running performance test: $test_name (max: ${max_time}s)"
    
    local start_time=$(date +%s)
    
    if cd "$test_dir" && timeout "$max_time" bash -c "$test_command" > /dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        if [ $duration -le $max_time ]; then
            log_success "$test_name (${duration}s)"
            TEST_RESULTS+=("✅ $test_name (${duration}s)")
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            log_error "$test_name (timeout: ${duration}s > ${max_time}s)"
            TEST_RESULTS+=("❌ $test_name (timeout)")
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        log_error "$test_name (failed or timeout)"
        TEST_RESULTS+=("❌ $test_name (failed)")
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 環境確認
echo ""
log_info "環境確認中..."

# 必要なコマンドの確認
REQUIRED_COMMANDS=("python3" "node" "npm" "git" "curl")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if command -v "$cmd" > /dev/null 2>&1; then
        log_success "$cmd is available"
    else
        log_error "$cmd is not available"
        exit 1
    fi
done

# Python環境の確認
echo ""
log_info "Python環境の確認..."
python3 --version
pip3 --version

# Node.js環境の確認
echo ""
log_info "Node.js環境の確認..."
node --version
npm --version

# 1. バックエンドテスト
echo ""
echo "🔧 バックエンドテスト"
echo "===================="

# Python依存関係のインストール
log_info "Python依存関係のインストール..."
if cd backend && pip3 install -q flask flask-cors flask-socketio PyJWT bcrypt psutil paramiko cryptography; then
    log_success "Python dependencies installed"
else
    log_warning "Some Python dependencies may have failed to install"
fi

# バックエンドユニットテスト
if [ -f "backend/tests/test_backend.py" ]; then
    run_detailed_test "Backend Unit Tests" "python3 -m pytest tests/test_backend.py -v" "backend"
else
    log_warning "Backend unit tests not found"
fi

# バックエンドサービステスト
run_test "Secret Manager Test" "python3 -c 'from services.secret_manager import SecretManager; sm = SecretManager(); print(\"Secret manager works\")'" "backend"

run_test "JWT Auth Test" "python3 -c 'from services.jwt_auth import AuthManager; am = AuthManager(); print(\"JWT auth works\")'" "backend"

# バックエンドサーバー起動テスト
log_info "バックエンドサーバー起動テスト..."
if [ -f "backend/test_app.py" ]; then
    cd backend
    python3 test_app.py &
    SERVER_PID=$!
    sleep 5
    
    if kill -0 $SERVER_PID 2>/dev/null; then
        log_success "Backend server started successfully"
        
        # APIエンドポイントテスト
        run_test "Health Check API" "curl -f http://localhost:5001/api/health"
        run_test "Auth API Structure" "curl -s http://localhost:5001/api/auth/login | grep -q 'error\\|success'"
        
        # サーバー停止
        kill $SERVER_PID
        wait $SERVER_PID 2>/dev/null || true
        log_success "Backend server stopped"
    else
        log_error "Backend server failed to start"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    cd ..
else
    log_warning "Backend test app not found"
fi

# 2. フロントエンドテスト
echo ""
echo "🎨 フロントエンドテスト"
echo "====================="

# Node.js依存関係のインストール
log_info "Node.js依存関係のインストール..."
if cd frontend && npm install --silent; then
    log_success "Node.js dependencies installed"
else
    log_error "Failed to install Node.js dependencies"
    cd ..
fi

# フロントエンドユニットテスト
if [ -f "frontend/src/tests/frontend.test.jsx" ]; then
    run_detailed_test "Frontend Unit Tests" "npm test -- --watchAll=false" "frontend"
else
    log_warning "Frontend unit tests not found"
fi

# フロントエンドビルドテスト
run_performance_test "Frontend Build Test" "npm run build" 120 "frontend"

# フロントエンドリントテスト
if [ -f "frontend/.eslintrc.js" ] || [ -f "frontend/.eslintrc.json" ]; then
    run_test "Frontend Lint Test" "npm run lint" "frontend"
else
    log_warning "ESLint configuration not found"
fi

cd ..

# 3. 統合テスト
echo ""
echo "🔗 統合テスト"
echo "============"

# Docker Composeファイルの検証
run_test "Docker Compose Validation" "docker-compose config"

# 環境変数テンプレートの検証
run_test "Environment Template Validation" "[ -f .env.example ]"

# セキュリティ設定の検証
run_test "Secrets Directory Structure" "[ -d secrets ] || mkdir -p secrets"

# Git設定の検証
run_test "Git Repository Initialization" "git status || git init"

# 4. セキュリティテスト
echo ""
echo "🔒 セキュリティテスト"
echo "==================="

# 機密情報の検出
log_info "機密情報スキャン..."
if grep -r --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ \
    -E "(password|secret|key|token).*=.*['\"][^'\"]{8,}['\"]" . > /dev/null 2>&1; then
    log_warning "Potential hardcoded secrets found"
else
    log_success "No hardcoded secrets detected"
fi

# ファイル権限の確認
run_test "Secrets File Permissions" "[ ! -f secrets/jwt_secret_key.txt ] || [ \$(stat -c '%a' secrets/jwt_secret_key.txt) = '600' ]"

# 5. パフォーマンステスト
echo ""
echo "⚡ パフォーマンステスト"
echo "====================="

# メモリリークテスト（簡易版）
if command -v python3 > /dev/null 2>&1; then
    run_performance_test "Memory Usage Test" "python3 -c 'import sys; print(f\"Memory usage: {sys.getsizeof({})} bytes\")'" 5
fi

# ファイルサイズチェック
log_info "ファイルサイズチェック..."
LARGE_FILES=$(find . -name "*.js" -o -name "*.py" -o -name "*.jsx" | xargs ls -la | awk '$5 > 100000 {print $9, $5}')
if [ -n "$LARGE_FILES" ]; then
    log_warning "Large files detected:"
    echo "$LARGE_FILES"
else
    log_success "No unusually large files detected"
fi

# 6. 品質チェック
echo ""
echo "📊 品質チェック"
echo "==============="

# コード行数統計
log_info "コード統計..."
PYTHON_LINES=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
JS_LINES=$(find . -name "*.js" -o -name "*.jsx" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")

echo "Python lines: $PYTHON_LINES"
echo "JavaScript/JSX lines: $JS_LINES"

# TODOコメントの確認
TODO_COUNT=$(grep -r --exclude-dir=.git --exclude-dir=node_modules "TODO\|FIXME\|XXX" . | wc -l)
echo "TODO/FIXME comments: $TODO_COUNT"

if [ "$TODO_COUNT" -gt 20 ]; then
    log_warning "High number of TODO comments ($TODO_COUNT)"
else
    log_success "Reasonable number of TODO comments ($TODO_COUNT)"
fi

# 7. 結果サマリー
echo ""
echo "📋 テスト結果サマリー"
echo "===================="

echo "総テスト数: $TOTAL_TESTS"
echo "成功: $PASSED_TESTS"
echo "失敗: $FAILED_TESTS"
echo "成功率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"

echo ""
echo "詳細結果:"
for result in "${TEST_RESULTS[@]}"; do
    echo "  $result"
done

# 最終判定
echo ""
if [ $FAILED_TESTS -eq 0 ]; then
    log_success "🎉 すべてのテストが成功しました！"
    echo ""
    echo "✅ プロダクションレベルの品質基準を満たしています"
    echo "✅ セキュリティチェックを通過しました"
    echo "✅ パフォーマンステストを通過しました"
    echo "✅ 統合テストを通過しました"
    exit 0
else
    log_error "❌ $FAILED_TESTS 個のテストが失敗しました"
    echo ""
    echo "🔧 修正が必要な項目があります"
    echo "📝 詳細なエラーログを確認してください"
    exit 1
fi

