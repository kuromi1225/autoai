@echo off
REM Devin AI Clone Startup Script for Windows
REM Command Prompt batch file with proper encoding

setlocal enabledelayedexpansion

echo === Devin AI Clone - Windows Startup ===
echo.

REM Check if Docker is installed
echo [INFO] Checking Docker installation...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not accessible
    echo [ERROR] Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [SUCCESS] Docker found

REM Check Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker Compose v2 not found, trying docker-compose...
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose not found
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker-compose
) else (
    set COMPOSE_CMD=docker compose
)

echo [SUCCESS] Docker Compose found

REM Create secrets directory if it doesn't exist
if not exist "secrets" (
    echo [INFO] Creating secrets directory...
    mkdir secrets
)

REM Generate secrets if they don't exist
echo [INFO] Initializing secrets...

if not exist "secrets\jwt_secret_key.txt" (
    echo [INFO] Generating JWT Secret Key...
    echo %RANDOM%%RANDOM%%RANDOM%%RANDOM% > secrets\jwt_secret_key.txt
)

if not exist "secrets\db_password.txt" (
    echo [INFO] Generating Database Password...
    echo %RANDOM%%RANDOM%%RANDOM%%RANDOM% > secrets\db_password.txt
)

if not exist "secrets\redis_password.txt" (
    echo [INFO] Generating Redis Password...
    echo %RANDOM%%RANDOM%%RANDOM%%RANDOM% > secrets\redis_password.txt
)

if not exist "secrets\encryption_key.txt" (
    echo [INFO] Generating Encryption Key...
    echo %RANDOM%%RANDOM%%RANDOM%%RANDOM% > secrets\encryption_key.txt
)

REM Clean up existing containers and networks
echo [INFO] Cleaning up existing containers and networks...
%COMPOSE_CMD% down --volumes --remove-orphans >nul 2>&1

REM Remove conflicting networks
docker network rm devin-ai-clone_devin-network >nul 2>&1
docker network rm devin-ai-network >nul 2>&1
docker network rm devin_network >nul 2>&1

REM Check port availability
echo [INFO] Checking port availability...
netstat -an | findstr ":8765 " >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8765 is in use
)

netstat -an | findstr ":8766 " >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8766 is in use
)

netstat -an | findstr ":8767 " >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8767 is in use
)

netstat -an | findstr ":8768 " >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8768 is in use
)

REM Start services
echo [INFO] Starting Devin AI Clone services...
%COMPOSE_CMD% up -d

if errorlevel 1 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

echo [SUCCESS] Services started successfully!

REM Wait for services to be ready
echo [INFO] Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Health check
echo [INFO] Performing health check...
curl -s http://localhost:8765/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Health check failed. Services may still be starting.
) else (
    echo [SUCCESS] All services are healthy!
)

echo.
echo === Access Information ===
echo Main Application:  http://localhost:8765
echo ChromaDB Admin:    http://localhost:8767
echo Prometheus:        http://localhost:8768
echo.
echo Demo Accounts:
echo   admin / admin123 (Administrator)
echo   user / user123 (Regular User)
echo   demo / demo123 (Demo User)
echo.
echo [INFO] To view logs, run: %COMPOSE_CMD% logs -f
echo [INFO] To stop services, run: %COMPOSE_CMD% down
echo.

pause

