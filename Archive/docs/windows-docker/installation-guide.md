# NeuroBridge EDU - Complete Windows Docker Installation Guide

This comprehensive guide will help you install and run NeuroBridge EDU using Docker Desktop on Windows systems. Follow these step-by-step instructions to set up a professional, production-ready environment.

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Docker Desktop Installation](#docker-desktop-installation)
4. [WSL2 Setup and Configuration](#wsl2-setup-and-configuration)
5. [NeuroBridge EDU Installation](#neurobridge-edu-installation)
6. [Configuration and Setup](#configuration-and-setup)
7. [Performance Optimization](#performance-optimization)
8. [Verification and Testing](#verification-and-testing)

## 🖥️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 Pro/Enterprise/Education (64-bit) version 1903 or later, or Windows 11
- **Processor**: Intel/AMD 64-bit processor with virtualization support
- **Memory**: 8 GB RAM minimum (16 GB recommended)
- **Storage**: 20 GB free disk space
- **Virtualization**: Hardware virtualization must be enabled in BIOS/UEFI

### Recommended Specifications
- **Operating System**: Windows 11 Pro or Windows 10 Pro (latest version)
- **Processor**: Intel Core i5 or AMD Ryzen 5 (or equivalent)
- **Memory**: 16 GB RAM or more
- **Storage**: 50 GB free SSD space
- **Network**: Stable internet connection for Docker image downloads

### Check Your System
Before proceeding, verify your system meets the requirements:

```powershell
# Check Windows version
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, WindowsBuildLabEx

# Check available RAM
Get-WmiObject -Class Win32_ComputerSystem | Select-Object TotalPhysicalMemory

# Check if Hyper-V is available
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All

# Check virtualization support
Get-ComputerInfo | Select-Object HyperVisorPresent, HyperVRequirementVirtualizationFirmwareEnabled
```

## ✅ Pre-Installation Checklist

### Step 1: Enable Virtualization in BIOS/UEFI
1. Restart your computer and enter BIOS/UEFI setup (usually F2, F12, Del, or Esc during boot)
2. Navigate to CPU or Advanced settings
3. Enable **Intel VT-x** (Intel) or **AMD-V** (AMD)
4. Enable **Intel VT-d** or **AMD IOMMU** if available
5. Save settings and exit BIOS/UEFI

### Step 2: Enable Windows Features
Run PowerShell as Administrator and execute:

```powershell
# Enable required Windows features
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All

# Restart required
Restart-Computer
```

### Step 3: Update Windows
1. Open **Settings** → **Update & Security** → **Windows Update**
2. Click **Check for updates**
3. Install all available updates
4. Restart if required

## 🐳 Docker Desktop Installation

### Method 1: Interactive Installation (Recommended for First-Time Users)

1. **Download Docker Desktop**
   - Visit [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - Click **Download for Windows**
   - Save `Docker Desktop Installer.exe` to your Downloads folder

2. **Run the Installer**
   ```cmd
   # Right-click "Docker Desktop Installer.exe" → "Run as administrator"
   ```
   
3. **Installation Options**
   - ✅ **Use WSL 2 instead of Hyper-V** (recommended)
   - ✅ **Add shortcut to desktop**
   - Click **OK** to start installation

4. **Complete Installation**
   - Wait for installation to complete (5-10 minutes)
   - Click **Close** when prompted
   - **Restart your computer** when requested

### Method 2: Command-Line Installation (For IT Professionals)

```powershell
# Download and install silently
$url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$output = "$env:TEMP\DockerDesktopInstaller.exe"

# Download installer
Invoke-WebRequest -Uri $url -OutFile $output

# Install with WSL2 backend
Start-Process $output -Wait -ArgumentList 'install', '--quiet', '--accept-license', '--backend=wsl-2'

# Add current user to docker-users group
net localgroup docker-users $env:USERNAME /add
```

### Method 3: Enterprise MSI Installation

For enterprise environments, use the MSI package:

```powershell
# Install MSI package silently
msiexec /i "DockerDesktop.msi" /quiet /norestart ALWAYSRUNSERVICE=1 ENGINE=wsl
```

## 🐧 WSL2 Setup and Configuration

### Step 1: Install/Update WSL2

```powershell
# Install or update WSL2
wsl --install

# Or update if already installed
wsl --update

# Set WSL2 as default version
wsl --set-default-version 2

# Verify WSL version
wsl --version
```

Expected output:
```
WSL version: 2.1.5.0
Kernel version: 5.15.146.1
WSLg version: 1.0.60
```

### Step 2: Install Ubuntu Distribution

```powershell
# Install Ubuntu (recommended distribution)
wsl --install -d Ubuntu

# Or install Ubuntu 22.04 LTS specifically
wsl --install -d Ubuntu-22.04
```

### Step 3: Configure WSL2 Settings

Create or edit `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
# Limit memory usage (adjust based on your system)
memory=8GB

# Limit CPU cores (adjust based on your system)
processors=4

# Set swap size
swap=2GB

# Disable swap file
# swap=0

# Enable nested virtualization (if needed)
nestedVirtualization=true

# Set custom kernel location (optional)
# kernel=C:\\path\\to\\custom\\kernel

# Additional performance settings
localhostForwarding=true
```

Restart WSL after making changes:
```powershell
wsl --shutdown
```

### Step 4: Configure Ubuntu Environment

Start Ubuntu and run initial setup:

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git unzip

# Install Docker CLI (for direct access)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

## 🧠 NeuroBridge EDU Installation

### Step 1: Start Docker Desktop

1. **Launch Docker Desktop**
   - Double-click the desktop shortcut, or
   - Search for "Docker Desktop" in Start Menu
   - Wait for Docker to start (whale icon in system tray turns blue)

2. **Verify Docker is Running**
   ```powershell
   # Check Docker status
   docker --version
   docker compose version
   
   # Test Docker installation
   docker run hello-world
   ```

### Step 2: Download NeuroBridge EDU

```powershell
# Create project directory
New-Item -ItemType Directory -Path "$env:USERPROFILE\NeuroBridge" -Force
Set-Location "$env:USERPROFILE\NeuroBridge"

# Clone the repository (replace with actual repository URL)
git clone https://github.com/your-org/neurobridge-edu.git
Set-Location neurobridge-edu
```

### Step 3: Configure Environment

```powershell
# Copy environment template
Copy-Item .env.example .env

# Edit configuration with your preferred editor
notepad .env
# OR
code .env
```

**Required Configuration in `.env`:**

```bash
# Essential settings - UPDATE THESE VALUES
OPENAI_API_KEY=sk-your-openai-api-key-here

# Application settings (defaults usually work)
HOST=0.0.0.0
PORT=3939
VITE_API_BASE_URL=http://localhost:3939
DATABASE_PATH=./data/neurobridge.db

# Security (change for production)
JWT_SECRET=your-secure-jwt-secret-change-in-production
CORS_ORIGINS=http://localhost:3131,http://localhost:3939
```

### Step 4: Deploy with Docker Compose

```powershell
# Build and start services
docker compose up -d --build

# View logs (optional)
docker compose logs -f

# Check service status
docker compose ps
```

Expected output:
```
NAME                   IMAGE              COMMAND                  SERVICE     STATUS
neurobridge-backend    neurobridge-backend   "python -m uvicorn m…"   backend     running
neurobridge-frontend   neurobridge-frontend  "serve -s dist -l 31…"   frontend    running
```

## ⚙️ Configuration and Setup

### Docker Desktop Settings

1. **Open Docker Desktop**
2. **Go to Settings** (gear icon)
3. **Configure Resources**:
   - **Memory**: 6-8 GB (adjust based on available RAM)
   - **CPUs**: 4-6 cores (adjust based on available cores)
   - **Disk Image Size**: 64 GB minimum

4. **Enable WSL Integration**:
   - Go to **Resources** → **WSL Integration**
   - Enable integration with Ubuntu distribution
   - Click **Apply & Restart**

### Windows Firewall Configuration

```powershell
# Allow Docker through Windows Firewall
New-NetFirewallRule -DisplayName "Docker Desktop" -Direction Inbound -Protocol TCP -LocalPort 3939,3131 -Action Allow
```

### Windows Defender Exclusions (Performance Optimization)

```powershell
# Add Windows Defender exclusions for better performance
Add-MpPreference -ExclusionPath "C:\Program Files\Docker"
Add-MpPreference -ExclusionPath "$env:USERPROFILE\.docker"
Add-MpPreference -ExclusionPath "$env:USERPROFILE\NeuroBridge"
Add-MpPreference -ExclusionProcess "dockerd.exe"
Add-MpPreference -ExclusionProcess "docker.exe"
```

## 🚀 Performance Optimization

### WSL2 Performance Tips

1. **Keep Files in WSL Filesystem**
   ```bash
   # Move project to WSL filesystem for better performance
   cd /home/$USER
   git clone https://github.com/your-org/neurobridge-edu.git
   cd neurobridge-edu
   ```

2. **Optimize WSL2 Settings**
   ```ini
   # In %USERPROFILE%\.wslconfig
   [wsl2]
   memory=12GB
   processors=6
   swap=4GB
   localhostForwarding=true
   # Disable GUI for better performance
   guiApplications=false
   ```

### Docker Performance Settings

1. **Enable BuildKit** (faster builds):
   ```powershell
   # Set environment variable
   $env:DOCKER_BUILDKIT = 1
   
   # Or add to system environment variables permanently
   [Environment]::SetEnvironmentVariable("DOCKER_BUILDKIT", "1", "User")
   ```

2. **Use Docker Compose Override** for development:
   ```yaml
   # docker-compose.override.yml
   version: '3.8'
   services:
     backend:
       volumes:
         - ./python_backend:/app
       command: python -m uvicorn main:app --host 0.0.0.0 --port 3939 --reload
     
     frontend:
       volumes:
         - ./src:/app/src
         - ./public:/app/public
       command: npm run dev -- --host 0.0.0.0 --port 3131
   ```

## ✅ Verification and Testing

### Step 1: Health Check

```powershell
# Check if services are running
docker compose ps

# Test backend API
Invoke-RestMethod -Uri "http://localhost:3939/health"

# Test frontend (should open in browser)
Start-Process "http://localhost:3131"
```

### Step 2: Functionality Test

1. **Open NeuroBridge EDU**: Navigate to `http://localhost:3131`
2. **Test Recording**: Click the record button (allow microphone access)
3. **Test Transcription**: Speak into the microphone and verify real-time transcription
4. **Test AI Summarization**: Stop recording and generate a summary
5. **Test Export**: Try exporting as PDF or Markdown

### Step 3: Performance Verification

```powershell
# Monitor resource usage
docker stats

# Check Docker system info
docker system info

# View disk usage
docker system df
```

## 🔧 Troubleshooting Common Issues

### Docker Won't Start
```powershell
# Check if Hyper-V is running
Get-Service -Name vmms

# Restart Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### WSL2 Issues
```powershell
# Reset WSL2
wsl --shutdown
wsl --unregister Ubuntu
wsl --install -d Ubuntu
```

### Permission Issues
```powershell
# Add user to docker-users group
net localgroup docker-users $env:USERNAME /add
# Log out and back in
```

## 📚 Next Steps

- **[Quick Start Guide](quick-start-guide.md)** - Get up and running in 5 minutes
- **[Troubleshooting FAQ](troubleshooting-faq.md)** - Solutions to common problems  
- **[Advanced Configuration](advanced-configuration.md)** - Custom domains, SSL, and more
- **[Desktop Integration](desktop-integration.md)** - Shortcuts and system integration

---

## 📞 Support

If you encounter issues:
1. Check the **[Troubleshooting FAQ](troubleshooting-faq.md)**
2. Review Docker Desktop logs: Settings → Troubleshoot → Show logs
3. Check the [GitHub Issues](https://github.com/your-org/neurobridge-edu/issues)
4. Contact support with detailed system information

---
**NeuroBridge EDU Team** | [Documentation](../README.md) | [GitHub](https://github.com/your-org/neurobridge-edu)