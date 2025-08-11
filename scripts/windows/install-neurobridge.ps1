# NeuroBridge EDU Automated Installation Script for Windows
# This script automates the complete installation and setup process

param(
    [Parameter(Mandatory=$false)]
    [string]$OpenAIKey,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDocker,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipWSL,
    
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "$env:USERPROFILE\NeuroBridge",
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Colors for output
$Colors = @{
    Header = "Cyan"
    Success = "Green" 
    Warning = "Yellow"
    Error = "Red"
    Info = "White"
}

# Display header
function Write-Header {
    param([string]$Message)
    Write-Host "`n" -NoNewline
    Write-Host "=" * 60 -ForegroundColor $Colors.Header
    Write-Host "  $Message" -ForegroundColor $Colors.Header
    Write-Host "=" * 60 -ForegroundColor $Colors.Header
    Write-Host ""
}

# Display step
function Write-Step {
    param([string]$Message)
    Write-Host "🔄 $Message" -ForegroundColor $Colors.Info
}

# Display success
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Success
}

# Display warning
function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Colors.Warning
}

# Display error
function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Error
}

# Check if running as administrator
function Test-IsAdmin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Download file with progress
function Download-File {
    param(
        [string]$Url,
        [string]$Path
    )
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Path -UseBasicParsing
        return $true
    }
    catch {
        Write-Warning "Download failed: $($_.Exception.Message)"
        return $false
    }
}

# Test internet connectivity
function Test-InternetConnection {
    try {
        $null = Test-NetConnection -ComputerName "google.com" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        return $true
    }
    catch {
        return $false
    }
}

# Check system requirements
function Test-SystemRequirements {
    Write-Step "Checking system requirements..."
    
    $issues = @()
    
    # Check Windows version
    $winVersion = [System.Environment]::OSVersion.Version
    if ($winVersion.Major -lt 10) {
        $issues += "Windows 10 or later required (current: Windows $($winVersion.Major).$($winVersion.Minor))"
    }
    
    # Check RAM
    $totalRAM = (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory / 1GB
    if ($totalRAM -lt 8) {
        $issues += "Insufficient RAM: ${totalRAM}GB available, 8GB minimum required"
    }
    
    # Check disk space
    $diskSpace = (Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB
    if ($diskSpace -lt 20) {
        $issues += "Insufficient disk space: ${diskSpace}GB available, 20GB minimum required"
    }
    
    # Check virtualization
    $hvFeatures = Get-ComputerInfo | Select-Object HyperVisorPresent, HyperVRequirementVirtualizationFirmwareEnabled
    if (-not $hvFeatures.HyperVRequirementVirtualizationFirmwareEnabled) {
        $issues += "Hardware virtualization not enabled in BIOS/UEFI"
    }
    
    if ($issues.Count -gt 0) {
        Write-Error "System requirements not met:"
        foreach ($issue in $issues) {
            Write-Host "  • $issue" -ForegroundColor $Colors.Error
        }
        throw "System requirements check failed"
    }
    
    Write-Success "System requirements check passed"
}

# Install Windows features
function Install-WindowsFeatures {
    Write-Step "Enabling required Windows features..."
    
    $features = @(
        "Microsoft-Hyper-V-All",
        "VirtualMachinePlatform",
        "Microsoft-Windows-Subsystem-Linux"
    )
    
    $rebootRequired = $false
    
    foreach ($feature in $features) {
        try {
            $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart
            if ($result.RestartNeeded) {
                $rebootRequired = $true
            }
            Write-Success "Enabled feature: $feature"
        }
        catch {
            Write-Warning "Failed to enable feature $feature: $($_.Exception.Message)"
        }
    }
    
    return $rebootRequired
}

# Install WSL2
function Install-WSL2 {
    if ($SkipWSL) {
        Write-Warning "Skipping WSL2 installation (--SkipWSL specified)"
        return $false
    }
    
    Write-Step "Installing WSL2..."
    
    try {
        # Check if WSL is already installed
        $wslVersion = wsl --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "WSL2 already installed"
            return $false
        }
    }
    catch {
        # WSL not installed, continue with installation
    }
    
    try {
        # Install WSL2 with Ubuntu
        wsl --install -d Ubuntu
        wsl --set-default-version 2
        
        Write-Success "WSL2 installation completed"
        return $true
    }
    catch {
        Write-Error "WSL2 installation failed: $($_.Exception.Message)"
        throw
    }
}

# Install Docker Desktop
function Install-DockerDesktop {
    if ($SkipDocker) {
        Write-Warning "Skipping Docker Desktop installation (--SkipDocker specified)"
        return $false
    }
    
    Write-Step "Installing Docker Desktop..."
    
    # Check if Docker is already installed
    try {
        $null = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker Desktop already installed"
            return $false
        }
    }
    catch {
        # Docker not installed, continue
    }
    
    # Download Docker Desktop installer
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
    
    Write-Step "Downloading Docker Desktop installer..."
    if (-not (Download-File -Url $dockerUrl -Path $dockerInstaller)) {
        throw "Failed to download Docker Desktop installer"
    }
    
    # Install Docker Desktop
    Write-Step "Installing Docker Desktop (this may take several minutes)..."
    try {
        Start-Process $dockerInstaller -Wait -ArgumentList 'install', '--quiet', '--accept-license', '--backend=wsl-2'
        
        # Add user to docker-users group
        net localgroup docker-users $env:USERNAME /add 2>$null
        
        Write-Success "Docker Desktop installation completed"
        return $true
    }
    catch {
        Write-Error "Docker Desktop installation failed: $($_.Exception.Message)"
        throw
    }
    finally {
        # Cleanup installer
        if (Test-Path $dockerInstaller) {
            Remove-Item $dockerInstaller -Force
        }
    }
}

# Setup project
function Setup-Project {
    Write-Step "Setting up NeuroBridge EDU project..."
    
    # Create installation directory
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        Write-Success "Created installation directory: $InstallPath"
    }
    
    # Change to installation directory
    Push-Location $InstallPath
    
    try {
        # Check if project already exists
        $projectPath = Join-Path $InstallPath "neurobridge-edu"
        if (Test-Path $projectPath) {
            Write-Warning "Project directory already exists, updating..."
            Set-Location $projectPath
            git pull origin main
        }
        else {
            # Clone repository
            Write-Step "Cloning NeuroBridge EDU repository..."
            git clone https://github.com/your-org/neurobridge-edu.git
            Set-Location neurobridge-edu
        }
        
        # Setup environment file
        if (-not (Test-Path ".env")) {
            Copy-Item ".env.example" ".env"
            Write-Success "Created .env file from template"
            
            # Configure OpenAI API key if provided
            if ($OpenAIKey) {
                (Get-Content ".env") -replace 'sk-your-openai-api-key-here', $OpenAIKey | Set-Content ".env"
                Write-Success "Configured OpenAI API key"
            }
            else {
                Write-Warning "OpenAI API key not provided. Please edit .env file manually."
            }
        }
        
        Write-Success "Project setup completed"
    }
    finally {
        Pop-Location
    }
}

# Configure Windows Defender exclusions
function Configure-DefenderExclusions {
    Write-Step "Configuring Windows Defender exclusions for better performance..."
    
    $exclusions = @(
        "C:\Program Files\Docker",
        "$env:USERPROFILE\.docker",
        $InstallPath
    )
    
    foreach ($exclusion in $exclusions) {
        try {
            Add-MpPreference -ExclusionPath $exclusion -ErrorAction Stop
            Write-Success "Added Defender exclusion: $exclusion"
        }
        catch {
            Write-Warning "Failed to add Defender exclusion for $exclusion"
        }
    }
    
    # Process exclusions
    $processes = @("dockerd.exe", "docker.exe", "wsl.exe")
    foreach ($process in $processes) {
        try {
            Add-MpPreference -ExclusionProcess $process -ErrorAction Stop
            Write-Success "Added process exclusion: $process"
        }
        catch {
            Write-Warning "Failed to add process exclusion for $process"
        }
    }
}

# Create desktop shortcuts
function Create-Shortcuts {
    Write-Step "Creating desktop shortcuts..."
    
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    
    # NeuroBridge EDU shortcut
    $shortcutPath = Join-Path $desktopPath "NeuroBridge EDU.lnk"
    $targetPath = "http://localhost:3131"
    
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "cmd.exe"
        $shortcut.Arguments = "/c start `"NeuroBridge EDU`" `"$targetPath`""
        $shortcut.WorkingDirectory = Join-Path $InstallPath "neurobridge-edu"
        $shortcut.IconLocation = "shell32.dll,13"
        $shortcut.Description = "Open NeuroBridge EDU in browser"
        $shortcut.Save()
        
        Write-Success "Created desktop shortcut: NeuroBridge EDU"
    }
    catch {
        Write-Warning "Failed to create desktop shortcut: $($_.Exception.Message)"
    }
}

# Wait for Docker to be ready
function Wait-ForDocker {
    Write-Step "Waiting for Docker Desktop to start..."
    
    $timeout = 120 # 2 minutes timeout
    $elapsed = 0
    
    while ($elapsed -lt $timeout) {
        try {
            $null = docker version 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker Desktop is ready"
                return $true
            }
        }
        catch {
            # Continue waiting
        }
        
        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "." -NoNewline -ForegroundColor $Colors.Info
    }
    
    Write-Host ""
    Write-Warning "Docker Desktop startup timeout (${timeout}s)"
    return $false
}

# Deploy application
function Deploy-Application {
    Write-Step "Deploying NeuroBridge EDU..."
    
    $projectPath = Join-Path $InstallPath "neurobridge-edu"
    Push-Location $projectPath
    
    try {
        # Build and start services
        docker compose up -d --build
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Application deployed successfully"
            
            # Show status
            Write-Host "`nContainer Status:" -ForegroundColor $Colors.Info
            docker compose ps
            
            return $true
        }
        else {
            Write-Error "Application deployment failed"
            return $false
        }
    }
    finally {
        Pop-Location
    }
}

# Verify installation
function Test-Installation {
    Write-Step "Verifying installation..."
    
    Start-Sleep -Seconds 10 # Wait for services to start
    
    $success = $true
    
    # Test backend API
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:3939/health" -TimeoutSec 10
        Write-Success "Backend API: OK"
    }
    catch {
        Write-Error "Backend API: Failed"
        $success = $false
    }
    
    # Test frontend
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:3131" -TimeoutSec 10
        Write-Success "Frontend: OK"
    }
    catch {
        Write-Error "Frontend: Failed"
        $success = $false
    }
    
    return $success
}

# Main installation flow
function Start-Installation {
    Write-Header "NeuroBridge EDU Automated Installation"
    
    # Pre-flight checks
    if (-not (Test-IsAdmin)) {
        Write-Error "This script requires administrator privileges. Please run as Administrator."
        exit 1
    }
    
    if (-not (Test-InternetConnection)) {
        Write-Error "Internet connection required for installation."
        exit 1
    }
    
    # System requirements check
    Test-SystemRequirements
    
    $rebootRequired = $false
    
    # Install Windows features
    Write-Header "Installing Windows Features"
    if (Install-WindowsFeatures) {
        $rebootRequired = $true
    }
    
    # Install WSL2
    Write-Header "Installing WSL2"
    if (Install-WSL2) {
        $rebootRequired = $true
    }
    
    # Check if reboot is required
    if ($rebootRequired) {
        Write-Warning "System restart required to complete Windows feature installation."
        Write-Host "Please restart your computer and run this script again with the same parameters." -ForegroundColor $Colors.Warning
        Write-Host "`nTo continue after restart, run:" -ForegroundColor $Colors.Info
        Write-Host "  PowerShell -ExecutionPolicy Bypass -File '$PSCommandPath'" -ForegroundColor $Colors.Info
        if ($OpenAIKey) {
            Write-Host "  -OpenAIKey '$OpenAIKey'" -ForegroundColor $Colors.Info -NoNewline
        }
        Write-Host ""
        return
    }
    
    # Install Docker Desktop
    Write-Header "Installing Docker Desktop"
    if (Install-DockerDesktop) {
        Write-Warning "Please restart your computer to complete Docker Desktop installation."
        Write-Host "After restart, run this script again to continue setup." -ForegroundColor $Colors.Warning
        return
    }
    
    # Configure system
    Write-Header "Configuring System"
    Configure-DefenderExclusions
    
    # Setup project
    Write-Header "Setting Up Project"
    Setup-Project
    
    # Wait for Docker to be ready
    Write-Header "Starting Docker Desktop"
    if (-not (Wait-ForDocker)) {
        Write-Error "Docker Desktop failed to start. Please check the installation and try again."
        return
    }
    
    # Deploy application
    Write-Header "Deploying Application"
    if (-not (Deploy-Application)) {
        Write-Error "Application deployment failed. Check the logs for details."
        return
    }
    
    # Create shortcuts
    Write-Header "Creating Shortcuts"
    Create-Shortcuts
    
    # Verify installation
    Write-Header "Verifying Installation"
    if (Test-Installation) {
        Write-Header "Installation Complete!"
        Write-Success "NeuroBridge EDU has been successfully installed and deployed!"
        Write-Host "`n🌐 Access your application at:" -ForegroundColor $Colors.Info
        Write-Host "   Frontend:  http://localhost:3131" -ForegroundColor $Colors.Success
        Write-Host "   Backend:   http://localhost:3939" -ForegroundColor $Colors.Success
        Write-Host "   API Docs:  http://localhost:3939/docs" -ForegroundColor $Colors.Success
        
        if (-not $OpenAIKey) {
            Write-Host "`n⚠️  Don't forget to:" -ForegroundColor $Colors.Warning
            Write-Host "   1. Edit the .env file with your OpenAI API key" -ForegroundColor $Colors.Warning
            Write-Host "   2. Restart the application: docker compose restart" -ForegroundColor $Colors.Warning
        }
        
        Write-Host "`n🚀 Opening NeuroBridge EDU in your browser..." -ForegroundColor $Colors.Info
        Start-Process "http://localhost:3131"
    }
    else {
        Write-Error "Installation verification failed. Please check the logs and troubleshoot."
    }
}

# Script entry point
try {
    Start-Installation
}
catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    Write-Host "`nFor troubleshooting help, see: docs/windows-docker/troubleshooting-faq.md" -ForegroundColor $Colors.Warning
    exit 1
}