# Devin AI Clone Startup Script (PowerShell)
# Windows environment startup script with proper UTF-8 encoding

param(
    [switch]$Help,
    [switch]$Clean,
    [switch]$Logs,
    [switch]$Stop
)

# Script configuration
$script:dockerCommand = "docker"
$script:composeCommand = "compose"

# Color output functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Cyan
}

# Help function
function Show-Help {
    Write-Host "Devin AI Clone - Windows Startup Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\start.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help     Show this help message"
    Write-Host "  -Clean    Clean up containers and volumes before starting"
    Write-Host "  -Logs     Show service logs after startup"
    Write-Host "  -Stop     Stop all services"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\start.ps1                 # Start all services"
    Write-Host "  .\start.ps1 -Clean          # Clean and start"
    Write-Host "  .\start.ps1 -Logs           # Start and show logs"
    Write-Host "  .\start.ps1 -Stop           # Stop all services"
}

# Check Docker installation
function Test-DockerInstallation {
    Write-Info "Checking Docker installation..."
    
    try {
        $dockerVersion = & $script:dockerCommand --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker command failed"
        }
        Write-Success "Docker found: $dockerVersion"
        
        $composeVersion = & $script:dockerCommand $script:composeCommand version 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Docker Compose v2 not found, trying docker-compose..."
            $script:composeCommand = "docker-compose"
            $composeVersion = & $script:composeCommand --version 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw "Docker Compose not found"
            }
        }
        Write-Success "Docker Compose found: $composeVersion"
        return $true
    }
    catch {
        Write-Error "Docker is not installed or not accessible"
        Write-Error "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        return $false
    }
}

# Generate secrets
function Initialize-Secrets {
    Write-Info "Initializing secrets..."
    
    if (-not (Test-Path "secrets")) {
        New-Item -ItemType Directory -Path "secrets" -Force | Out-Null
    }
    
    $secrets = @{
        "jwt_secret_key.txt" = "JWT Secret Key"
        "db_password.txt" = "Database Password"
        "redis_password.txt" = "Redis Password"
        "encryption_key.txt" = "Encryption Key"
    }
    
    foreach ($file in $secrets.Keys) {
        $filePath = "secrets\$file"
        if (-not (Test-Path $filePath)) {
            $randomValue = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            $randomValue | Out-File -FilePath $filePath -Encoding utf8 -NoNewline
            Write-Info "Generated $($secrets[$file])"
        }
    }
}

# Clean up function
function Invoke-Cleanup {
    Write-Info "Cleaning up existing containers and networks..."
    
    try {
        # Stop and remove containers
        & $script:dockerCommand $script:composeCommand down --volumes --remove-orphans 2>$null
        
        # Remove conflicting networks
        $networks = @("devin-ai-clone_devin-network", "devin-ai-network", "devin_network")
        foreach ($network in $networks) {
            try {
                & $script:dockerCommand network rm $network 2>$null
            }
            catch {
                # Ignore errors for non-existent networks
            }
        }
        
        Write-Success "Cleanup completed"
    }
    catch {
        Write-Warning "Some cleanup operations failed, but continuing..."
    }
}

# Check port availability
function Test-PortAvailability {
    $ports = @(8765, 8766, 8767, 8768)
    $busyPorts = @()
    
    foreach ($port in $ports) {
        $connection = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($connection) {
            $busyPorts += $port
        }
    }
    
    if ($busyPorts.Count -gt 0) {
        Write-Warning "The following ports are in use: $($busyPorts -join ', ')"
        Write-Warning "Please stop services using these ports or the application may not work correctly"
        return $false
    }
    
    Write-Success "All required ports are available"
    return $true
}

# Health check function
function Test-ServiceHealth {
    Write-Info "Performing health check..."
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8765/health" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "All services are healthy!"
                return $true
            }
        }
        catch {
            if ($attempt -eq 1) {
                Write-Info "Waiting for services to start..."
            }
            Start-Sleep -Seconds 2
        }
    } while ($attempt -lt $maxAttempts)
    
    Write-Warning "Health check timeout. Services may still be starting."
    return $false
}

# Main execution
function Start-Application {
    Write-Host "=== Devin AI Clone - Windows Startup ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Check Docker
    if (-not (Test-DockerInstallation)) {
        exit 1
    }
    
    # Initialize secrets
    Initialize-Secrets
    
    # Clean up if requested
    if ($Clean) {
        Invoke-Cleanup
    }
    
    # Check ports
    Test-PortAvailability
    
    # Start services
    Write-Info "Starting Devin AI Clone services..."
    
    try {
        if ($script:composeCommand -eq "docker-compose") {
            & $script:composeCommand up -d
        } else {
            & $script:dockerCommand $script:composeCommand up -d
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose failed to start services"
        }
        
        Write-Success "Services started successfully!"
        
        # Health check
        $healthy = Test-ServiceHealth
        
        # Show access information
        Write-Host ""
        Write-Host "=== Access Information ===" -ForegroundColor Cyan
        Write-Host "Main Application:  http://localhost:8765" -ForegroundColor Green
        Write-Host "ChromaDB Admin:    http://localhost:8767" -ForegroundColor Green
        Write-Host "Prometheus:        http://localhost:8768" -ForegroundColor Green
        Write-Host ""
        
        if ($healthy) {
            Write-Host "Demo Accounts:" -ForegroundColor Yellow
            Write-Host "  admin / admin123 (Administrator)" -ForegroundColor White
            Write-Host "  user / user123 (Regular User)" -ForegroundColor White
            Write-Host "  demo / demo123 (Demo User)" -ForegroundColor White
            Write-Host ""
        }
        
        if ($Logs) {
            Write-Info "Showing service logs. Press Ctrl+C to exit log view."
            if ($script:composeCommand -eq "docker-compose") {
                & $script:composeCommand logs -f
            } else {
                & $script:dockerCommand $script:composeCommand logs -f
            }
        } else {
            Write-Info "To view logs, run: .\start.ps1 -Logs"
        }
        
    }
    catch {
        Write-Error "An error occurred during script execution: $($_.Exception.Message)"
        Write-Error "Please check the logs for more details"
        exit 1
    }
}

function Stop-Application {
    Write-Info "Stopping Devin AI Clone services..."
    
    try {
        if ($script:composeCommand -eq "docker-compose") {
            & $script:composeCommand down
        } else {
            & $script:dockerCommand $script:composeCommand down
        }
        
        Write-Success "Services stopped successfully!"
    }
    catch {
        Write-Error "Failed to stop services: $($_.Exception.Message)"
        exit 1
    }
}

# Script entry point
if ($Help) {
    Show-Help
    exit 0
}

if ($Stop) {
    Stop-Application
    exit 0
}

Start-Application

