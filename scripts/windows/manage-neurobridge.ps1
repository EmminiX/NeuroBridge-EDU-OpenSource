# NeuroBridge EDU Management Script for Windows
# Provides easy commands to start, stop, update, and manage the application

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "update", "reset", "backup", "health")]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [switch]$Follow,
    
    [Parameter(Mandatory=$false)]
    [string]$Service = ""
)

# Configuration
$ProjectPath = "$env:USERPROFILE\NeuroBridge\neurobridge-edu"
$BackupPath = "$env:USERPROFILE\NeuroBridge\backups"

# Colors for output
$Colors = @{
    Header = "Cyan"
    Success = "Green"
    Warning = "Yellow" 
    Error = "Red"
    Info = "White"
}

# Utility functions
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Test-ProjectExists {
    if (-not (Test-Path $ProjectPath)) {
        Write-ColorOutput "❌ Project not found at: $ProjectPath" "Error"
        Write-ColorOutput "Please run the installation script first." "Warning"
        exit 1
    }
}

function Test-DockerRunning {
    try {
        $null = docker version 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Wait-ForDockerDesktop {
    Write-ColorOutput "🔄 Waiting for Docker Desktop to start..." "Info"
    
    $timeout = 120
    $elapsed = 0
    
    while ($elapsed -lt $timeout) {
        if (Test-DockerRunning) {
            Write-ColorOutput "✅ Docker Desktop is ready" "Success"
            return $true
        }
        
        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "." -NoNewline
    }
    
    Write-Host ""
    Write-ColorOutput "❌ Docker Desktop startup timeout" "Error"
    return $false
}

# Action functions
function Start-Application {
    Write-ColorOutput "`n🚀 Starting NeuroBridge EDU..." "Header"
    
    Test-ProjectExists
    
    if (-not (Test-DockerRunning)) {
        Write-ColorOutput "Starting Docker Desktop..." "Info"
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        
        if (-not (Wait-ForDockerDesktop)) {
            Write-ColorOutput "Failed to start Docker Desktop" "Error"
            return
        }
    }
    
    Push-Location $ProjectPath
    try {
        # Start services
        docker compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ NeuroBridge EDU started successfully!" "Success"
            Show-Status
            Show-URLs
        }
        else {
            Write-ColorOutput "❌ Failed to start application" "Error"
        }
    }
    finally {
        Pop-Location
    }
}

function Stop-Application {
    Write-ColorOutput "`n🛑 Stopping NeuroBridge EDU..." "Header"
    
    Test-ProjectExists
    
    Push-Location $ProjectPath
    try {
        docker compose down
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ NeuroBridge EDU stopped successfully!" "Success"
        }
        else {
            Write-ColorOutput "❌ Failed to stop application" "Error"
        }
    }
    finally {
        Pop-Location
    }
}

function Restart-Application {
    Write-ColorOutput "`n🔄 Restarting NeuroBridge EDU..." "Header"
    
    Test-ProjectExists
    
    Push-Location $ProjectPath
    try {
        if ($Service) {
            Write-ColorOutput "Restarting service: $Service" "Info"
            docker compose restart $Service
        }
        else {
            docker compose restart
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ NeuroBridge EDU restarted successfully!" "Success"
            Show-Status
        }
        else {
            Write-ColorOutput "❌ Failed to restart application" "Error"
        }
    }
    finally {
        Pop-Location
    }
}

function Show-Status {
    Write-ColorOutput "`n📊 NeuroBridge EDU Status" "Header"
    
    Test-ProjectExists
    
    if (-not (Test-DockerRunning)) {
        Write-ColorOutput "❌ Docker Desktop is not running" "Error"
        return
    }
    
    Push-Location $ProjectPath
    try {
        # Show container status
        Write-ColorOutput "Container Status:" "Info"
        docker compose ps
        
        Write-Host ""
        
        # Show resource usage
        Write-ColorOutput "Resource Usage:" "Info"
        docker stats --no-stream
        
        Write-Host ""
        
        # Test endpoints
        Test-Endpoints
        
    }
    finally {
        Pop-Location
    }
}

function Show-Logs {
    Write-ColorOutput "`n📋 NeuroBridge EDU Logs" "Header"
    
    Test-ProjectExists
    
    Push-Location $ProjectPath
    try {
        if ($Service) {
            Write-ColorOutput "Showing logs for service: $Service" "Info"
            if ($Follow) {
                docker compose logs -f $Service
            }
            else {
                docker compose logs $Service
            }
        }
        else {
            Write-ColorOutput "Showing logs for all services" "Info"
            if ($Follow) {
                docker compose logs -f
            }
            else {
                docker compose logs
            }
        }
    }
    finally {
        Pop-Location
    }
}

function Update-Application {
    Write-ColorOutput "`n🔄 Updating NeuroBridge EDU..." "Header"
    
    Test-ProjectExists
    
    Push-Location $ProjectPath
    try {
        # Pull latest code
        Write-ColorOutput "Pulling latest code..." "Info"
        git pull origin main
        
        # Pull latest Docker images
        Write-ColorOutput "Pulling latest Docker images..." "Info"
        docker compose pull
        
        # Rebuild and restart
        Write-ColorOutput "Rebuilding containers..." "Info"
        docker compose up -d --build
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Update completed successfully!" "Success"
            Show-Status
        }
        else {
            Write-ColorOutput "❌ Update failed" "Error"
        }
    }
    finally {
        Pop-Location
    }
}

function Reset-Application {
    Write-ColorOutput "`n🔥 Resetting NeuroBridge EDU..." "Warning"
    Write-ColorOutput "This will remove all containers, images, and volumes!" "Warning"
    
    $confirmation = Read-Host "Are you sure? Type 'yes' to continue"
    if ($confirmation -ne 'yes') {
        Write-ColorOutput "Reset cancelled" "Info"
        return
    }
    
    Test-ProjectExists
    
    Push-Location $ProjectPath
    try {
        # Stop and remove everything
        docker compose down -v --remove-orphans
        docker system prune -a --volumes -f
        
        # Rebuild from scratch
        Write-ColorOutput "Rebuilding from scratch..." "Info"
        docker compose up -d --build
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Reset completed successfully!" "Success"
            Show-Status
        }
        else {
            Write-ColorOutput "❌ Reset failed" "Error"
        }
    }
    finally {
        Pop-Location
    }
}

function Backup-Application {
    Write-ColorOutput "`n💾 Creating backup..." "Header"
    
    Test-ProjectExists
    
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupName = "neurobridge-backup-$timestamp"
    
    # Create backup directory
    if (-not (Test-Path $BackupPath)) {
        New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    }
    
    $fullBackupPath = Join-Path $BackupPath $backupName
    New-Item -ItemType Directory -Path $fullBackupPath -Force | Out-Null
    
    Push-Location $ProjectPath
    try {
        # Backup configuration files
        Copy-Item ".env" (Join-Path $fullBackupPath ".env") -ErrorAction SilentlyContinue
        Copy-Item "docker-compose.yml" (Join-Path $fullBackupPath "docker-compose.yml") -ErrorAction SilentlyContinue
        
        # Backup database (if exists)
        if (Test-Path "data") {
            Copy-Item "data" (Join-Path $fullBackupPath "data") -Recurse -Force
        }
        
        # Export Docker volumes
        Write-ColorOutput "Exporting Docker volumes..." "Info"
        $volumes = docker volume ls --filter "name=neurobridge" --format "{{.Name}}"
        foreach ($volume in $volumes) {
            if ($volume) {
                $volumeBackup = Join-Path $fullBackupPath "volume-$volume.tar"
                docker run --rm -v ${volume}:/data -v ${fullBackupPath}:/backup alpine tar czf /backup/volume-$volume.tar -C /data .
            }
        }
        
        Write-ColorOutput "✅ Backup created at: $fullBackupPath" "Success"
    }
    catch {
        Write-ColorOutput "❌ Backup failed: $($_.Exception.Message)" "Error"
    }
    finally {
        Pop-Location
    }
}

function Test-Health {
    Write-ColorOutput "`n🏥 Health Check" "Header"
    
    Test-ProjectExists
    
    $healthStatus = @{
        Docker = $false
        Backend = $false
        Frontend = $false
        Database = $false
    }
    
    # Check Docker
    if (Test-DockerRunning) {
        $healthStatus.Docker = $true
        Write-ColorOutput "✅ Docker: Running" "Success"
    }
    else {
        Write-ColorOutput "❌ Docker: Not running" "Error"
    }
    
    # Check containers
    Push-Location $ProjectPath -ErrorAction SilentlyContinue
    try {
        $containers = docker compose ps --format json 2>$null | ConvertFrom-Json
        foreach ($container in $containers) {
            if ($container.Service -eq "backend" -and $container.State -eq "running") {
                $healthStatus.Backend = $true
            }
            elseif ($container.Service -eq "frontend" -and $container.State -eq "running") {
                $healthStatus.Frontend = $true
            }
        }
    }
    catch {
        # Ignore errors if not in project directory
    }
    finally {
        Pop-Location -ErrorAction SilentlyContinue
    }
    
    # Test endpoints
    if ($healthStatus.Backend) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:3939/health" -TimeoutSec 5
            Write-ColorOutput "✅ Backend API: Healthy" "Success"
        }
        catch {
            Write-ColorOutput "❌ Backend API: Unhealthy" "Error"
            $healthStatus.Backend = $false
        }
    }
    else {
        Write-ColorOutput "❌ Backend: Not running" "Error"
    }
    
    if ($healthStatus.Frontend) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:3131" -TimeoutSec 5
            Write-ColorOutput "✅ Frontend: Accessible" "Success"
        }
        catch {
            Write-ColorOutput "❌ Frontend: Inaccessible" "Error"
            $healthStatus.Frontend = $false
        }
    }
    else {
        Write-ColorOutput "❌ Frontend: Not running" "Error"
    }
    
    # Overall health
    $overallHealthy = $healthStatus.Docker -and $healthStatus.Backend -and $healthStatus.Frontend
    
    Write-Host ""
    if ($overallHealthy) {
        Write-ColorOutput "🎉 Overall Status: Healthy" "Success"
        Show-URLs
    }
    else {
        Write-ColorOutput "⚠️  Overall Status: Unhealthy" "Warning"
        Write-ColorOutput "Run 'manage-neurobridge.ps1 logs' to check for errors" "Info"
    }
}

function Test-Endpoints {
    Write-ColorOutput "Endpoint Health:" "Info"
    
    # Test backend
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:3939/health" -TimeoutSec 5
        Write-ColorOutput "  ✅ Backend API: OK" "Success"
    }
    catch {
        Write-ColorOutput "  ❌ Backend API: Failed" "Error"
    }
    
    # Test frontend
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:3131" -TimeoutSec 5
        Write-ColorOutput "  ✅ Frontend: OK" "Success"
    }
    catch {
        Write-ColorOutput "  ❌ Frontend: Failed" "Error"
    }
}

function Show-URLs {
    Write-ColorOutput "`n🌐 Access URLs:" "Info"
    Write-Host "  Frontend:  http://localhost:3131" -ForegroundColor $Colors.Success
    Write-Host "  Backend:   http://localhost:3939" -ForegroundColor $Colors.Success  
    Write-Host "  API Docs:  http://localhost:3939/docs" -ForegroundColor $Colors.Success
}

function Show-Help {
    Write-ColorOutput "`n📖 NeuroBridge EDU Management Script" "Header"
    Write-Host "Usage: .\manage-neurobridge.ps1 <action> [options]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  start    - Start the application"
    Write-Host "  stop     - Stop the application"  
    Write-Host "  restart  - Restart the application or specific service"
    Write-Host "  status   - Show application status"
    Write-Host "  logs     - Show application logs"
    Write-Host "  update   - Update application to latest version"
    Write-Host "  reset    - Reset application (removes all data)"
    Write-Host "  backup   - Create a backup of application data"
    Write-Host "  health   - Run comprehensive health check"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Follow      - Follow logs (use with 'logs' action)"
    Write-Host "  -Service <name> - Target specific service (use with 'restart' or 'logs')"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\manage-neurobridge.ps1 start"
    Write-Host "  .\manage-neurobridge.ps1 logs -Follow"
    Write-Host "  .\manage-neurobridge.ps1 restart -Service backend"
    Write-Host "  .\manage-neurobridge.ps1 health"
}

# Main script logic
switch ($Action) {
    "start" { Start-Application }
    "stop" { Stop-Application }
    "restart" { Restart-Application }
    "status" { Show-Status }
    "logs" { Show-Logs }
    "update" { Update-Application }
    "reset" { Reset-Application }
    "backup" { Backup-Application }
    "health" { Test-Health }
    default { Show-Help }
}