# NeuroBridge EDU Desktop Integration Script
# Creates desktop shortcuts and Start Menu entries for easy access

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "$env:USERPROFILE\NeuroBridge\neurobridge-edu",
    
    [Parameter(Mandatory=$false)]
    [switch]$RemoveShortcuts
)

# Configuration
$AppName = "NeuroBridge EDU"
$AppVersion = "2.0.0"
$AppDescription = "AI-powered lecture transcription and summarization"
$AppIcon = "shell32.dll,13"  # Globe icon from Windows
$PowerShellIcon = "powershell.exe"

# Paths
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$StartMenuPath = [Environment]::GetFolderPath("StartMenu")
$ProgramsPath = Join-Path $StartMenuPath "Programs"
$AppFolderPath = Join-Path $ProgramsPath $AppName

# Shortcuts configuration
$Shortcuts = @(
    @{
        Name = "$AppName"
        Description = "Open NeuroBridge EDU in browser"
        Target = "cmd.exe"
        Arguments = "/c start `"$AppName`" `"http://localhost:3131`""
        Icon = $AppIcon
        Location = "Desktop"
    },
    @{
        Name = "$AppName - Start"
        Description = "Start NeuroBridge EDU services"
        Target = "powershell.exe"
        Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\manage-neurobridge.ps1`" start"
        Icon = $PowerShellIcon
        Location = "StartMenu"
    },
    @{
        Name = "$AppName - Stop"
        Description = "Stop NeuroBridge EDU services"
        Target = "powershell.exe"
        Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\manage-neurobridge.ps1`" stop"
        Icon = $PowerShellIcon
        Location = "StartMenu"
    },
    @{
        Name = "$AppName - Status"
        Description = "Show NeuroBridge EDU status"
        Target = "powershell.exe"
        Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\manage-neurobridge.ps1`" status"
        Icon = $PowerShellIcon
        Location = "StartMenu"
    },
    @{
        Name = "$AppName - Logs"
        Description = "View NeuroBridge EDU logs"
        Target = "powershell.exe"
        Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\manage-neurobridge.ps1`" logs -Follow"
        Icon = $PowerShellIcon
        Location = "StartMenu"
    },
    @{
        Name = "Backend API"
        Description = "Open NeuroBridge EDU API documentation"
        Target = "cmd.exe"
        Arguments = "/c start `"$AppName API`" `"http://localhost:3939/docs`""
        Icon = $AppIcon
        Location = "StartMenu"
    }
)

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    $Colors = @{
        Success = "Green"
        Warning = "Yellow"
        Error = "Red"
        Info = "Cyan"
    }
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Create-Shortcut {
    param(
        [string]$Name,
        [string]$Description,
        [string]$Target,
        [string]$Arguments,
        [string]$Icon,
        [string]$WorkingDirectory,
        [string]$Path
    )
    
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($Path)
        $shortcut.TargetPath = $Target
        $shortcut.Arguments = $Arguments
        $shortcut.Description = $Description
        $shortcut.WorkingDirectory = $WorkingDirectory
        
        # Set icon if specified
        if ($Icon -and (Test-Path $Icon)) {
            $shortcut.IconLocation = $Icon
        }
        elseif ($Icon -and $Icon.Contains(",")) {
            $shortcut.IconLocation = $Icon
        }
        
        $shortcut.Save()
        return $true
    }
    catch {
        Write-ColorOutput "Failed to create shortcut: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Remove-Shortcut {
    param([string]$Path)
    
    if (Test-Path $Path) {
        Remove-Item $Path -Force
        return $true
    }
    return $false
}

function Create-StartMenuFolder {
    if (-not (Test-Path $AppFolderPath)) {
        New-Item -ItemType Directory -Path $AppFolderPath -Force | Out-Null
        Write-ColorOutput "Created Start Menu folder: $AppFolderPath" "Info"
    }
}

function Remove-StartMenuFolder {
    if (Test-Path $AppFolderPath) {
        Remove-Item $AppFolderPath -Recurse -Force
        Write-ColorOutput "Removed Start Menu folder: $AppFolderPath" "Info"
    }
}

function Create-AllShortcuts {
    Write-ColorOutput "Creating desktop shortcuts and Start Menu entries..." "Info"
    
    # Create Start Menu folder
    Create-StartMenuFolder
    
    $successCount = 0
    $totalCount = $Shortcuts.Count
    
    foreach ($shortcut in $Shortcuts) {
        if ($shortcut.Location -eq "Desktop") {
            $shortcutPath = Join-Path $DesktopPath "$($shortcut.Name).lnk"
        }
        else {
            $shortcutPath = Join-Path $AppFolderPath "$($shortcut.Name).lnk"
        }
        
        if (Create-Shortcut -Name $shortcut.Name -Description $shortcut.Description -Target $shortcut.Target -Arguments $shortcut.Arguments -Icon $shortcut.Icon -WorkingDirectory $InstallPath -Path $shortcutPath) {
            Write-ColorOutput "✅ Created: $($shortcut.Name)" "Success"
            $successCount++
        }
        else {
            Write-ColorOutput "❌ Failed: $($shortcut.Name)" "Error"
        }
    }
    
    # Create uninstall shortcut
    $uninstallPath = Join-Path $AppFolderPath "Uninstall $AppName.lnk"
    if (Create-Shortcut -Name "Uninstall $AppName" -Description "Remove NeuroBridge EDU shortcuts and configuration" -Target "powershell.exe" -Arguments "-ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\create-desktop-shortcuts.ps1`" -RemoveShortcuts" -Icon "shell32.dll,31" -WorkingDirectory $InstallPath -Path $uninstallPath) {
        Write-ColorOutput "✅ Created: Uninstall shortcut" "Success"
        $successCount++
        $totalCount++
    }
    
    Write-ColorOutput "`nShortcut creation completed: $successCount/$totalCount successful" "Info"
    
    if ($successCount -eq $totalCount) {
        Write-ColorOutput "🎉 All shortcuts created successfully!" "Success"
        
        # Show instructions
        Write-ColorOutput "`n📍 Shortcuts created:" "Info"
        Write-Host "  Desktop: $AppName.lnk" -ForegroundColor White
        Write-Host "  Start Menu: $AppName folder with management shortcuts" -ForegroundColor White
        
        Write-ColorOutput "`n🚀 Quick access:" "Info"
        Write-Host "  • Double-click the desktop icon to open NeuroBridge EDU" -ForegroundColor White
        Write-Host "  • Use Start Menu shortcuts to manage the application" -ForegroundColor White
        Write-Host "  • Right-click desktop icon → Properties to customize" -ForegroundColor White
    }
}

function Remove-AllShortcuts {
    Write-ColorOutput "Removing all shortcuts..." "Warning"
    
    $removedCount = 0
    
    # Remove desktop shortcuts
    foreach ($shortcut in $Shortcuts) {
        if ($shortcut.Location -eq "Desktop") {
            $shortcutPath = Join-Path $DesktopPath "$($shortcut.Name).lnk"
            if (Remove-Shortcut $shortcutPath) {
                Write-ColorOutput "✅ Removed: $($shortcut.Name)" "Success"
                $removedCount++
            }
        }
    }
    
    # Remove Start Menu folder
    Remove-StartMenuFolder
    $removedCount += $Shortcuts.Where({$_.Location -eq "StartMenu"}).Count + 1 # +1 for uninstall
    
    Write-ColorOutput "Removed $removedCount shortcuts" "Info"
}

function Create-RegistryEntries {
    Write-ColorOutput "Creating Windows registry entries..." "Info"
    
    try {
        # Create application registry key
        $regPath = "HKCU:\Software\NeuroBridge\NeuroBridge EDU"
        if (-not (Test-Path $regPath)) {
            New-Item -Path $regPath -Force | Out-Null
        }
        
        # Set application information
        Set-ItemProperty -Path $regPath -Name "InstallPath" -Value $InstallPath
        Set-ItemProperty -Path $regPath -Name "Version" -Value $AppVersion
        Set-ItemProperty -Path $regPath -Name "InstallDate" -Value (Get-Date -Format "yyyy-MM-dd")
        
        # Create URL protocol handler (optional)
        $protocolPath = "HKCU:\Software\Classes\neurobridge"
        if (-not (Test-Path $protocolPath)) {
            New-Item -Path $protocolPath -Force | Out-Null
            Set-ItemProperty -Path $protocolPath -Name "(Default)" -Value "NeuroBridge EDU Protocol"
            Set-ItemProperty -Path $protocolPath -Name "URL Protocol" -Value ""
            
            $commandPath = "$protocolPath\shell\open\command"
            New-Item -Path $commandPath -Force | Out-Null
            Set-ItemProperty -Path $commandPath -Name "(Default)" -Value "`"cmd.exe`" /c start `"NeuroBridge EDU`" `"http://localhost:3131`""
        }
        
        Write-ColorOutput "✅ Registry entries created" "Success"
    }
    catch {
        Write-ColorOutput "⚠️  Failed to create registry entries: $($_.Exception.Message)" "Warning"
    }
}

function Remove-RegistryEntries {
    Write-ColorOutput "Removing registry entries..." "Info"
    
    try {
        $regPath = "HKCU:\Software\NeuroBridge"
        if (Test-Path $regPath) {
            Remove-Item -Path $regPath -Recurse -Force
            Write-ColorOutput "✅ Removed application registry entries" "Success"
        }
        
        $protocolPath = "HKCU:\Software\Classes\neurobridge"
        if (Test-Path $protocolPath) {
            Remove-Item -Path $protocolPath -Recurse -Force
            Write-ColorOutput "✅ Removed protocol registry entries" "Success"
        }
    }
    catch {
        Write-ColorOutput "⚠️  Failed to remove registry entries: $($_.Exception.Message)" "Warning"
    }
}

function Create-SystemIntegration {
    Write-ColorOutput "Creating system integration..." "Info"
    
    # Create Windows service file (for reference, not actual service)
    $serviceScript = @"
# NeuroBridge EDU Service Management
# This script can be used to create a Windows service for NeuroBridge EDU

# To create a service:
# 1. Install NSSM (Non-Sucking Service Manager)
# 2. Run: nssm install "NeuroBridge EDU"
# 3. Set Application Path: powershell.exe
# 4. Set Arguments: -ExecutionPolicy Bypass -File "$InstallPath\scripts\windows\manage-neurobridge.ps1" start
# 5. Configure service settings as needed

# Example NSSM commands:
# nssm install "NeuroBridge EDU" powershell.exe "-ExecutionPolicy Bypass -File `"$InstallPath\scripts\windows\manage-neurobridge.ps1`" start"
# nssm set "NeuroBridge EDU" DisplayName "NeuroBridge EDU Service"
# nssm set "NeuroBridge EDU" Description "$AppDescription"
# nssm set "NeuroBridge EDU" Start SERVICE_AUTO_START
"@
    
    $serviceScriptPath = Join-Path $InstallPath "scripts\windows\service-setup.txt"
    $serviceScript | Out-File -FilePath $serviceScriptPath -Encoding UTF8
    
    Write-ColorOutput "✅ Created service setup reference at: $serviceScriptPath" "Success"
}

function Test-Prerequisites {
    # Check if install path exists
    if (-not (Test-Path $InstallPath)) {
        Write-ColorOutput "❌ Installation path not found: $InstallPath" "Error"
        Write-ColorOutput "Please run the installation script first." "Warning"
        return $false
    }
    
    # Check if management script exists
    $managementScript = Join-Path $InstallPath "scripts\windows\manage-neurobridge.ps1"
    if (-not (Test-Path $managementScript)) {
        Write-ColorOutput "❌ Management script not found: $managementScript" "Error"
        return $false
    }
    
    return $true
}

# Main script logic
Write-ColorOutput "🖥️  NeuroBridge EDU Desktop Integration" "Info"
Write-ColorOutput "=================================" "Info"

if ($RemoveShortcuts) {
    Remove-AllShortcuts
    Remove-RegistryEntries
    Write-ColorOutput "🧹 Cleanup completed!" "Success"
}
else {
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    Create-AllShortcuts
    Create-RegistryEntries
    Create-SystemIntegration
    
    Write-ColorOutput "`n🎉 Desktop integration completed!" "Success"
    Write-ColorOutput "NeuroBridge EDU is now integrated with your Windows desktop." "Info"
    
    # Offer to create taskbar pin
    Write-ColorOutput "`n📌 Optional: Pin to Taskbar" "Info"
    Write-Host "To pin NeuroBridge EDU to your taskbar:"
    Write-Host "1. Right-click the desktop shortcut"
    Write-Host "2. Select 'Pin to taskbar'"
    Write-Host "Or drag the shortcut to your taskbar"
}

Write-ColorOutput "`nDesktop integration script completed!" "Success"