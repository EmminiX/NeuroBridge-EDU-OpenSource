# NeuroBridge EDU - Windows Docker Quick Start Guide ⚡

Get NeuroBridge EDU running on Windows in under 10 minutes with Docker Desktop!

## 🚀 Quick Overview

This guide assumes you have:
- Windows 10 Pro/Enterprise or Windows 11
- 8GB+ RAM and 20GB+ free disk space
- Internet connection for downloads

**Total Time**: 5-10 minutes ⏱️

## 📦 Step 1: Install Docker Desktop (3 minutes)

### Option A: Automated PowerShell Installation
Run this in **PowerShell as Administrator**:

```powershell
# Quick install script
$url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installer = "$env:TEMP\DockerDesktop.exe"

Write-Host "🔄 Downloading Docker Desktop..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $url -OutFile $installer

Write-Host "🚀 Installing Docker Desktop..." -ForegroundColor Yellow
Start-Process $installer -Wait -ArgumentList 'install', '--quiet', '--accept-license'

Write-Host "👤 Adding user to docker-users group..." -ForegroundColor Yellow
net localgroup docker-users $env:USERNAME /add

Write-Host "✅ Installation complete! Please restart your computer." -ForegroundColor Green
```

### Option B: Manual Installation
1. Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Run installer as Administrator
3. Check "Use WSL 2 instead of Hyper-V"
4. Restart when prompted

## 🐧 Step 2: Setup WSL2 (2 minutes)

```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu

# Wait for completion, then restart computer
```

After restart, complete Ubuntu setup:
- Create username and password when prompted
- WSL2 will automatically integrate with Docker Desktop

## 🧠 Step 3: Deploy NeuroBridge EDU (2 minutes)

### Download and Setup
```powershell
# Create project directory
mkdir "$env:USERPROFILE\NeuroBridge"
cd "$env:USERPROFILE\NeuroBridge"

# Download NeuroBridge EDU (replace with actual repo URL)
git clone https://github.com/your-org/neurobridge-edu.git
cd neurobridge-edu
```

### Configure Environment
```powershell
# Copy environment template
copy .env.example .env

# Edit with your OpenAI API key
notepad .env
```

**⚠️ IMPORTANT**: Replace `sk-your-openai-api-key-here` with your actual OpenAI API key in the `.env` file.

### Launch Application
```powershell
# Start Docker Desktop (if not already running)
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait 30 seconds for Docker to start, then deploy
Start-Sleep -Seconds 30
docker compose up -d --build
```

## 🎯 Step 4: Access Your Application (30 seconds)

```powershell
# Open NeuroBridge EDU in your default browser
Start-Process "http://localhost:3131"
```

**That's it!** 🎉 NeuroBridge EDU should now be running at:
- **Frontend**: http://localhost:3131
- **Backend API**: http://localhost:3939
- **API Documentation**: http://localhost:3939/docs

## ✅ Quick Test

1. **Open** http://localhost:3131 in your browser
2. **Click** the microphone button
3. **Allow** microphone access when prompted
4. **Speak** a few words to test transcription
5. **Generate** an AI summary

## 🛠️ One-Liner Setup Script

For the ultimate quick start, save this as `install-neurobridge.ps1` and run it:

```powershell
# NeuroBridge EDU Quick Install Script for Windows
param(
    [Parameter(Mandatory=$true)]
    [string]$OpenAIKey
)

Write-Host "🚀 NeuroBridge EDU Quick Installer" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check if running as admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ Please run as Administrator" -ForegroundColor Red
    exit 1
}

# Install WSL2
Write-Host "🐧 Setting up WSL2..." -ForegroundColor Yellow
wsl --install -d Ubuntu

# Install Docker Desktop
Write-Host "🐳 Installing Docker Desktop..." -ForegroundColor Yellow
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktop.exe"
Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller
Start-Process $dockerInstaller -Wait -ArgumentList 'install', '--quiet', '--accept-license'
net localgroup docker-users $env:USERNAME /add

# Setup project
Write-Host "📁 Setting up project..." -ForegroundColor Yellow
$projectDir = "$env:USERPROFILE\NeuroBridge\neurobridge-edu"
New-Item -ItemType Directory -Path "$env:USERPROFILE\NeuroBridge" -Force
Set-Location "$env:USERPROFILE\NeuroBridge"
git clone https://github.com/your-org/neurobridge-edu.git
Set-Location neurobridge-edu

# Configure environment
Write-Host "⚙️ Configuring environment..." -ForegroundColor Yellow
Copy-Item .env.example .env
(Get-Content .env) -replace 'sk-your-openai-api-key-here', $OpenAIKey | Set-Content .env

Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Restart your computer" -ForegroundColor White
Write-Host "2. Run: cd $projectDir" -ForegroundColor White
Write-Host "3. Run: docker compose up -d --build" -ForegroundColor White
Write-Host "4. Open: http://localhost:3131" -ForegroundColor White
```

Usage:
```powershell
.\install-neurobridge.ps1 -OpenAIKey "sk-your-actual-openai-key-here"
```

## 🔧 Common Quick Fixes

### Docker Desktop Won't Start
```powershell
# Restart Docker service
Restart-Service docker
# OR restart Docker Desktop
taskkill /f /im "Docker Desktop.exe"
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### Application Won't Load
```powershell
# Check if containers are running
docker compose ps

# Restart containers
docker compose restart

# View logs for debugging
docker compose logs -f
```

### WSL2 Issues
```powershell
# Update WSL2
wsl --update
wsl --shutdown
```

## 📋 Quick Commands Reference

```powershell
# Start application
docker compose up -d

# Stop application  
docker compose down

# View logs
docker compose logs -f

# Restart services
docker compose restart

# Update containers
docker compose pull && docker compose up -d

# Remove everything (fresh start)
docker compose down -v
docker system prune -a
```

## 🆘 Need Help?

- **Detailed Guide**: See [Full Installation Guide](installation-guide.md)
- **Troubleshooting**: Check [FAQ](troubleshooting-faq.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/neurobridge-edu/issues)

---

## ⚡ Success Checklist

- [ ] Docker Desktop installed and running
- [ ] WSL2 configured with Ubuntu
- [ ] OpenAI API key configured in `.env`
- [ ] Application accessible at http://localhost:3131
- [ ] Microphone recording works
- [ ] AI summarization works

**🎉 You're all set! Welcome to NeuroBridge EDU!**

---
**NeuroBridge EDU Team** | [Back to Docs](../README.md)