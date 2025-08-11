# NeuroBridge EDU - Windows Docker Troubleshooting FAQ 🔧

This comprehensive troubleshooting guide addresses common Windows-specific Docker issues when running NeuroBridge EDU. Each solution includes both quick fixes and detailed explanations.

## 📋 Table of Contents

1. [Docker Desktop Issues](#docker-desktop-issues)
2. [WSL2 Problems](#wsl2-problems)
3. [Container and Service Issues](#container-and-service-issues)
4. [Network and Port Problems](#network-and-port-problems)
5. [Performance Issues](#performance-issues)
6. [Permission and Access Problems](#permission-and-access-problems)
7. [Audio and Microphone Issues](#audio-and-microphone-issues)
8. [Environment and Configuration Issues](#environment-and-configuration-issues)

---

## 🐳 Docker Desktop Issues

### ❌ Docker Desktop Won't Start

**Symptoms**: Docker Desktop hangs on startup, whale icon stays gray, or error messages appear.

#### **Quick Fix**:
```powershell
# Restart Docker Desktop service
taskkill /f /im "Docker Desktop.exe"
Start-Service docker
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

#### **Detailed Solutions**:

1. **Check Virtualization Support**:
   ```powershell
   # Verify hardware virtualization is enabled
   Get-ComputerInfo | Select-Object HyperVisorPresent, HyperVRequirementVirtualizationFirmwareEnabled
   ```
   If `False`, enable virtualization in BIOS/UEFI.

2. **Enable Hyper-V Feature**:
   ```powershell
   # Enable Hyper-V (run as admin)
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All
   Restart-Computer
   ```

3. **Fix Hypervisor Launch Type**:
   ```cmd
   # Run in Command Prompt as Admin
   bcdedit /set hypervisorlaunchtype auto
   ```

4. **Clear Docker Data** (last resort):
   ```powershell
   # Stop Docker
   taskkill /f /im "Docker Desktop.exe"
   
   # Clear Docker data (WARNING: This removes all containers and images)
   Remove-Item -Recurse -Force "$env:APPDATA\Docker"
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Docker"
   
   # Restart Docker Desktop
   Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
   ```

### ❌ "Docker Desktop requires a newer WSL kernel version"

#### **Quick Fix**:
```powershell
# Update WSL kernel
wsl --update
wsl --shutdown
```

#### **If Update Fails**:
```powershell
# Manual kernel update
$url = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$output = "$env:TEMP\wsl_update_x64.msi"
Invoke-WebRequest -Uri $url -OutFile $output
Start-Process msiexec -Wait -ArgumentList "/i", $output, "/quiet"
```

### ❌ "Hardware assisted virtualization and data execution protection must be enabled in the BIOS"

#### **Solution**:
1. Restart computer and enter BIOS/UEFI
2. Find CPU or Advanced settings
3. Enable **Intel VT-x** or **AMD-V**
4. Enable **Intel VT-d** or **AMD IOMMU**
5. Save and restart

### ❌ Docker Desktop Installation Fails

#### **Common Solutions**:

1. **Run as Administrator**:
   ```powershell
   # Ensure installer runs with admin privileges
   Start-Process "Docker Desktop Installer.exe" -Verb RunAs -ArgumentList "install"
   ```

2. **Clean Previous Installation**:
   ```powershell
   # Remove existing Docker installations
   Get-AppxPackage *docker* | Remove-AppxPackage
   Remove-Item -Recurse -Force "C:\Program Files\Docker" -ErrorAction SilentlyContinue
   ```

3. **Disable Antivirus Temporarily**:
   - Temporarily disable Windows Defender real-time protection
   - Add Docker installation directory to antivirus exclusions

---

## 🐧 WSL2 Problems

### ❌ WSL2 Not Starting or Crashes

#### **Quick Diagnosis**:
```powershell
# Check WSL status
wsl --status
wsl --list --verbose

# Check for running WSL processes
Get-Process | Where-Object {$_.ProcessName -like "*wsl*"}
```

#### **Solutions**:

1. **Restart WSL Service**:
   ```powershell
   # Restart WSL
   wsl --shutdown
   Start-Sleep -Seconds 5
   wsl --distribution Ubuntu
   ```

2. **Reset WSL Configuration**:
   ```powershell
   # Reset WSL settings
   wsl --shutdown
   Remove-Item "$env:USERPROFILE\.wslconfig" -Force -ErrorAction SilentlyContinue
   wsl --distribution Ubuntu
   ```

3. **Reinstall WSL Distribution**:
   ```powershell
   # Remove and reinstall Ubuntu
   wsl --unregister Ubuntu
   wsl --install -d Ubuntu
   ```

### ❌ "WSL 2 requires an update to its kernel component"

#### **Solution**:
```powershell
# Download and install WSL2 kernel update
$kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$kernelPath = "$env:TEMP\wsl_update_x64.msi"
Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath
Start-Process msiexec -Wait -ArgumentList "/i", $kernelPath, "/quiet"
wsl --set-default-version 2
```

### ❌ WSL2 High Memory Usage

#### **Solution - Configure WSL2 Memory Limits**:
Create `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
# Limit memory to 50% of total RAM (adjust as needed)
memory=8GB

# Limit swap usage
swap=2GB

# Limit processors
processors=4

# Reclaim memory aggressively
vmIdleTimeout=60000
```

Then restart WSL:
```powershell
wsl --shutdown
```

### ❌ Docker Desktop Can't Access WSL2 Distribution

#### **Solution**:
```powershell
# Enable WSL integration in Docker Desktop settings
# Or via command line:
wsl --set-default Ubuntu
wsl --set-version Ubuntu 2

# Verify integration
wsl -l -v
```

---

## 📦 Container and Service Issues

### ❌ "docker compose up" Fails with Build Errors

#### **Quick Fix**:
```powershell
# Clear Docker cache and rebuild
docker system prune -a
docker compose build --no-cache
docker compose up -d
```

#### **Common Build Issues**:

1. **Node.js Build Failures**:
   ```powershell
   # Clear npm cache
   docker compose exec frontend npm cache clean --force
   docker compose restart frontend
   ```

2. **Python Package Installation Fails**:
   ```powershell
   # Check Python backend logs
   docker compose logs backend
   
   # Rebuild with verbose output
   docker compose build --no-cache backend
   ```

3. **Insufficient Disk Space**:
   ```powershell
   # Clean Docker system
   docker system prune -a --volumes
   docker builder prune -a
   ```

### ❌ Containers Keep Restarting

#### **Diagnosis**:
```powershell
# Check container status
docker compose ps

# View container logs
docker compose logs backend
docker compose logs frontend

# Check resource usage
docker stats
```

#### **Solutions**:

1. **Memory Issues**:
   ```powershell
   # Increase Docker Desktop memory allocation
   # Settings → Resources → Memory → Increase to 6-8GB
   ```

2. **Environment Variable Problems**:
   ```powershell
   # Verify .env file exists and has correct values
   Get-Content .env | Where-Object {$_ -match "OPENAI_API_KEY"}
   
   # Recreate containers with new environment
   docker compose down
   docker compose up -d
   ```

3. **Port Conflicts**:
   ```powershell
   # Check what's using the ports
   netstat -ano | findstr ":3939"
   netstat -ano | findstr ":3131"
   
   # Kill processes using the ports if needed
   taskkill /PID [PID_NUMBER] /F
   ```

### ❌ "Container failed to start" with Exit Code 125

#### **Solution**:
```powershell
# Check Docker daemon status
docker info

# Restart Docker daemon
Restart-Service docker

# If that fails, restart Docker Desktop
taskkill /f /im "Docker Desktop.exe"
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

---

## 🌐 Network and Port Problems

### ❌ Cannot Access Application at localhost:3131

#### **Quick Diagnosis**:
```powershell
# Test if ports are accessible
Test-NetConnection -ComputerName localhost -Port 3131
Test-NetConnection -ComputerName localhost -Port 3939

# Check if containers are running and ports are mapped
docker compose ps
```

#### **Solutions**:

1. **Windows Firewall Blocking Ports**:
   ```powershell
   # Add firewall rules
   New-NetFirewallRule -DisplayName "NeuroBridge Frontend" -Direction Inbound -Protocol TCP -LocalPort 3131 -Action Allow
   New-NetFirewallRule -DisplayName "NeuroBridge Backend" -Direction Inbound -Protocol TCP -LocalPort 3939 -Action Allow
   ```

2. **Ports Already in Use**:
   ```powershell
   # Find what's using the port
   netstat -ano | findstr ":3131"
   
   # Stop the conflicting process
   taskkill /PID [PID] /F
   
   # Or change ports in docker-compose.yml
   ```

3. **Docker Network Issues**:
   ```powershell
   # Reset Docker networks
   docker network prune
   docker compose down
   docker compose up -d
   ```

### ❌ Backend API Not Reachable from Frontend

#### **Solution**:
```powershell
# Check if backend is healthy
Invoke-RestMethod -Uri "http://localhost:3939/health"

# Check Docker network connectivity
docker compose exec frontend curl http://backend:3939/health

# Verify environment variables
docker compose exec frontend env | grep VITE_API_BASE_URL
```

### ❌ CORS Errors in Browser Console

#### **Solution**:
Check the backend CORS configuration in `.env`:
```bash
CORS_ORIGINS=http://localhost:3131,http://localhost:3939
```

If accessing from a different domain, add it to CORS_ORIGINS.

---

## ⚡ Performance Issues

### ❌ Slow Application Performance

#### **Quick Optimization**:
```powershell
# Add Windows Defender exclusions
Add-MpPreference -ExclusionPath "C:\Program Files\Docker"
Add-MpPreference -ExclusionPath "$env:USERPROFILE\.docker"
Add-MpPreference -ExclusionProcess "dockerd.exe"
```

#### **Detailed Performance Tuning**:

1. **Allocate More Resources to Docker**:
   - Docker Desktop → Settings → Resources
   - Increase Memory to 6-8GB
   - Increase CPUs to 4-6 cores

2. **Optimize WSL2 Configuration**:
   ```ini
   # %USERPROFILE%\.wslconfig
   [wsl2]
   memory=8GB
   processors=4
   swap=2GB
   localhostForwarding=true
   ```

3. **Move Project to WSL2 Filesystem**:
   ```bash
   # From within WSL2/Ubuntu
   cd /home/$USER
   git clone https://github.com/your-org/neurobridge-edu.git
   cd neurobridge-edu
   ```

4. **Use Docker BuildKit**:
   ```powershell
   $env:DOCKER_BUILDKIT = 1
   docker compose build --parallel
   ```

### ❌ High CPU/Memory Usage

#### **Diagnosis**:
```powershell
# Monitor Docker resource usage
docker stats

# Check Windows Task Manager
# Look for high CPU/Memory usage by:
# - Docker Desktop
# - Vmmem (WSL2)
# - com.docker.backend
```

#### **Solutions**:

1. **Limit Container Resources**:
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '2'
   ```

2. **Optimize Node.js Memory**:
   ```yaml
   # In docker-compose.yml for frontend
   environment:
     - NODE_OPTIONS=--max-old-space-size=2048
   ```

3. **Configure WSL2 Limits**:
   ```ini
   # %USERPROFILE%\.wslconfig
   [wsl2]
   memory=6GB
   processors=4
   ```

---

## 🔐 Permission and Access Problems

### ❌ "Docker daemon is not running" or Permission Denied

#### **Quick Fix**:
```powershell
# Add current user to docker-users group
net localgroup docker-users $env:USERNAME /add

# Log out and back in for changes to take effect
# Or restart computer
```

#### **If Issue Persists**:
```powershell
# Check if Docker service is running
Get-Service docker

# Start Docker service manually
Start-Service docker

# Check Docker Desktop process
Get-Process | Where-Object {$_.ProcessName -like "*docker*"}
```

### ❌ File Permission Issues in WSL2

#### **Solution**:
```bash
# From within WSL2
sudo chown -R $USER:$USER /path/to/project
chmod -R 755 /path/to/project
```

### ❌ Cannot Create/Write Files in Mounted Volumes

#### **Solution**:
```powershell
# Check volume mounts in docker-compose.yml
# Ensure paths are correct and accessible

# For WSL2 paths, use Linux-style paths:
# ./data:/app/data

# For Windows paths, use absolute paths:
# C:\Users\YourName\NeuroBridge\data:/app/data
```

---

## 🎙️ Audio and Microphone Issues

### ❌ Microphone Not Working in Browser

#### **Solutions**:

1. **Check Browser Permissions**:
   - Click the lock icon in the address bar
   - Ensure microphone is set to "Allow"

2. **HTTPS Requirement**:
   ```powershell
   # For local development, some browsers require HTTPS for microphone access
   # Use Chrome with --unsafely-treat-insecure-origin-as-secure flag:
   chrome.exe --unsafely-treat-insecure-origin-as-secure=http://localhost:3131
   ```

3. **Windows Microphone Privacy Settings**:
   - Settings → Privacy → Microphone
   - Ensure "Allow apps to access your microphone" is ON
   - Ensure browser is allowed to access microphone

### ❌ Audio Quality Issues or Dropouts

#### **Solutions**:

1. **Check Microphone Settings**:
   - Right-click speaker icon → Recording devices
   - Set correct default microphone
   - Adjust microphone levels

2. **Browser Audio Settings**:
   - Check browser's audio input settings
   - Try different audio input devices

---

## ⚙️ Environment and Configuration Issues

### ❌ OpenAI API Key Not Working

#### **Verification**:
```powershell
# Test API key directly
$headers = @{
    "Authorization" = "Bearer YOUR_API_KEY_HERE"
    "Content-Type" = "application/json"
}
Invoke-RestMethod -Uri "https://api.openai.com/v1/models" -Headers $headers
```

#### **Solutions**:

1. **Check API Key Format**:
   - Must start with `sk-`
   - Should be 51 characters long
   - No extra spaces or quotes

2. **Verify Environment Variable Loading**:
   ```powershell
   # Check if .env file is correctly formatted
   Get-Content .env | Where-Object {$_ -match "OPENAI_API_KEY"}
   
   # Check if containers see the environment variable
   docker compose exec backend env | grep OPENAI_API_KEY
   ```

3. **API Key Permissions**:
   - Ensure API key has sufficient permissions
   - Check OpenAI account billing and limits

### ❌ Database Connection Issues

#### **Solutions**:

1. **Check Database Volume**:
   ```powershell
   # Verify database volume exists
   docker volume ls
   
   # Check database file permissions
   docker compose exec backend ls -la /app/data/
   ```

2. **Recreate Database**:
   ```powershell
   # Remove existing database and recreate
   docker compose down -v
   docker compose up -d
   ```

---

## 🆘 Emergency Recovery Procedures

### 🚨 Complete Reset (Nuclear Option)

When everything fails, here's how to completely reset your Docker environment:

```powershell
# WARNING: This will remove ALL Docker data, containers, and images

# 1. Stop all Docker processes
taskkill /f /im "Docker Desktop.exe"
Stop-Service docker -Force

# 2. Remove Docker data
Remove-Item -Recurse -Force "$env:APPDATA\Docker" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Docker" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:PROGRAMDATA\Docker" -ErrorAction SilentlyContinue

# 3. Reset WSL2
wsl --shutdown
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data

# 4. Restart Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 5. Wait for Docker to initialize, then redeploy
Start-Sleep -Seconds 60
docker compose up -d --build
```

### 🔄 Quick Health Check Script

Save this as `health-check.ps1`:

```powershell
Write-Host "🏥 NeuroBridge EDU Health Check" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check Docker
try {
    docker --version
    Write-Host "✅ Docker CLI: OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker CLI: Failed" -ForegroundColor Red
}

# Check containers
try {
    $containers = docker compose ps --format json | ConvertFrom-Json
    foreach ($container in $containers) {
        if ($container.State -eq "running") {
            Write-Host "✅ $($container.Service): Running" -ForegroundColor Green
        } else {
            Write-Host "❌ $($container.Service): $($container.State)" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "❌ Container check: Failed" -ForegroundColor Red
}

# Test endpoints
try {
    Invoke-RestMethod -Uri "http://localhost:3939/health" -TimeoutSec 5 | Out-Null
    Write-Host "✅ Backend API: OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend API: Failed" -ForegroundColor Red
}

try {
    Invoke-WebRequest -Uri "http://localhost:3131" -TimeoutSec 5 | Out-Null
    Write-Host "✅ Frontend: OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend: Failed" -ForegroundColor Red
}

# Check system resources
$memory = Get-WmiObject -Class Win32_OperatingSystem
$memoryUsed = ($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize * 100
Write-Host "📊 Memory Usage: $([math]::Round($memoryUsed, 1))%" -ForegroundColor $(if ($memoryUsed -gt 80) { "Red" } else { "Green" })

Write-Host ""
Write-Host "🌐 Access URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3131" -ForegroundColor White
Write-Host "  Backend:  http://localhost:3939" -ForegroundColor White
Write-Host "  API Docs: http://localhost:3939/docs" -ForegroundColor White
```

---

## 📞 Getting Additional Help

### Log Collection for Support

When reporting issues, collect these logs:

```powershell
# Create support bundle
$supportDir = "$env:USERPROFILE\NeuroBridge-Support-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $supportDir

# Collect system info
Get-ComputerInfo > "$supportDir\system-info.txt"
docker --version > "$supportDir\docker-version.txt"
docker compose ps > "$supportDir\container-status.txt"
docker system info > "$supportDir\docker-info.txt"

# Collect logs
docker compose logs > "$supportDir\application-logs.txt"
Get-EventLog -LogName System -Newest 100 | Where-Object {$_.Source -like "*docker*"} > "$supportDir\windows-events.txt"

Write-Host "Support bundle created at: $supportDir"
```

### Resources for Further Help

- **Documentation**: [Installation Guide](installation-guide.md) | [Advanced Configuration](advanced-configuration.md)
- **GitHub Issues**: https://github.com/your-org/neurobridge-edu/issues
- **Docker Documentation**: https://docs.docker.com/desktop/windows/
- **WSL2 Documentation**: https://docs.microsoft.com/en-us/windows/wsl/

---

**💡 Pro Tip**: Most Windows Docker issues are related to WSL2 configuration, resource allocation, or Windows Defender interference. Always check these first!

---
**NeuroBridge EDU Team** | [Back to Docs](../README.md) | [Installation Guide](installation-guide.md)