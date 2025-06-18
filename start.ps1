# start.ps1
# Description: Main startup script for the autoai project on Windows.

# --- Prerequisite Check ---
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker is not installed or not in your PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows and ensure it's running."
    exit 1
}

if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "Error: docker-compose is not installed or not in your PATH." -ForegroundColor Red
    Write-Host "Please ensure Docker Desktop is configured to use docker-compose."
    exit 1
}

# --- Check Docker Status ---
try {
    $dockerInfo = docker info
    if ($LASTEXITCODE -ne 0) {
        throw "Docker daemon is not running."
    }
}
catch {
    Write-Host "Error: Docker daemon is not running." -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}


Write-Host "Starting AutoAI Project Setup for Windows..."

# --- Step 1: Setup secrets and .env file ---
$setupScript = ".\setup-secrets.ps1"
if (-not (Test-Path $setupScript)) {
    Write-Host "Error: setup-secrets.ps1 not found. Please ensure the file exists in the project root." -ForegroundColor Red
    exit 1
}

# Execute the secrets setup script
& $setupScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error during secrets setup. Please check the output above." -ForegroundColor Red
    exit 1
}


# --- Step 2: Start Docker containers ---
Write-Host "Starting Docker containers with docker-compose..."
docker-compose up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: docker-compose up failed." -ForegroundColor Red
    Write-Host "Please check the container logs for more details using 'docker-compose logs -f'"
    exit 1
}

Write-Host "AutoAI services are starting up." -ForegroundColor Green
Write-Host "You can monitor the logs with: docker-compose logs -f"
Write-Host "Frontend will be available at http://localhost:5173"
Write-Host "Backend API is at http://localhost:5000"
