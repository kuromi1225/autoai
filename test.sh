#!/bin/bash

# Devin AI Clone - Integration Test Script

set -e

echo "🧪 Running Devin AI Clone Integration Tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((TESTS_FAILED++))
    fi
}

# Function to test HTTP endpoint
test_http() {
    local url="$1"
    local expected_status="${2:-200}"
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    [ "$status" = "$expected_status" ]
}

# Function to test service health
test_service_health() {
    local service="$1"
    docker-compose ps "$service" | grep -q "Up"
}

echo "🔍 Checking if services are running..."

# Test Docker services
run_test "PostgreSQL service" "test_service_health postgres"
run_test "Redis service" "test_service_health redis"
run_test "Backend service" "test_service_health backend"
run_test "Frontend service" "test_service_health frontend"
run_test "Nginx service" "test_service_health nginx"

echo ""
echo "🌐 Testing HTTP endpoints..."

# Test HTTP endpoints
run_test "Frontend accessibility" "test_http http://localhost:8080"
run_test "Backend health endpoint" "test_http http://localhost:5000/health"
run_test "Backend API root" "test_http http://localhost:5000/api/"

echo ""
echo "🗄️ Testing database connectivity..."

# Test database
run_test "Database connection" "docker-compose exec -T postgres pg_isready -U devin_user -d devin_ai"
run_test "Database tables exist" "docker-compose exec -T postgres psql -U devin_user -d devin_ai -c '\dt' | grep -q users"

echo ""
echo "📦 Testing Redis connectivity..."

# Test Redis
run_test "Redis ping" "docker-compose exec -T redis redis-cli ping | grep -q PONG"

echo ""
echo "🔧 Testing API functionality..."

# Test API endpoints
run_test "API status endpoint" "test_http http://localhost:5000/api/status"
run_test "API projects endpoint" "test_http http://localhost:5000/api/projects"

echo ""
echo "🎯 Testing WebSocket connectivity..."

# Test WebSocket (basic check)
run_test "WebSocket endpoint accessible" "curl -s -I http://localhost:5000/ws | grep -q 'HTTP/1.1'"

echo ""
echo "📊 Testing monitoring endpoints..."

# Test monitoring (if enabled)
if docker-compose ps prometheus | grep -q "Up"; then
    run_test "Prometheus accessibility" "test_http http://localhost:9090"
    run_test "Prometheus targets" "curl -s http://localhost:9090/api/v1/targets | grep -q 'devin-backend'"
else
    echo "⏭️  Skipping Prometheus tests (not running)"
fi

echo ""
echo "🧪 Running unit tests..."

# Run backend unit tests
if docker-compose exec -T backend python -c "import pytest" > /dev/null 2>&1; then
    run_test "Backend unit tests" "docker-compose exec -T backend python -m pytest tests/ -v"
else
    echo "⏭️  Skipping backend unit tests (pytest not available)"
fi

# Run frontend tests
if docker-compose exec -T frontend npm list jest > /dev/null 2>&1; then
    run_test "Frontend unit tests" "docker-compose exec -T frontend npm test -- --watchAll=false"
else
    echo "⏭️  Skipping frontend unit tests (jest not available)"
fi

echo ""
echo "🔐 Testing security configurations..."

# Test security headers
run_test "Security headers present" "curl -s -I http://localhost:8080 | grep -q 'X-Frame-Options'"
run_test "CORS headers present" "curl -s -I http://localhost:5000/api/ | grep -q 'Access-Control-Allow-Origin'"

echo ""
echo "📈 Testing performance..."

# Basic performance tests
run_test "Frontend load time < 3s" "timeout 3s curl -s http://localhost:8080 > /dev/null"
run_test "Backend response time < 1s" "timeout 1s curl -s http://localhost:5000/health > /dev/null"

echo ""
echo "🔄 Testing container restart resilience..."

# Test container restart
echo "Restarting backend container..."
docker-compose restart backend
sleep 10

run_test "Backend recovery after restart" "test_http http://localhost:5000/health"

echo ""
echo "📋 Test Summary:"
echo "=================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed! Devin AI Clone is working correctly.${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Please check the logs and fix the issues.${NC}"
    echo ""
    echo "🔍 Debugging commands:"
    echo "  docker-compose logs backend"
    echo "  docker-compose logs frontend"
    echo "  docker-compose logs nginx"
    echo "  docker-compose ps"
    exit 1
fi

