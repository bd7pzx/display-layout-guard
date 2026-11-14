<#
.SYNOPSIS
    Remove the Display Layout Guard for the current user.

.PARAMETER Purge
    Also delete configuration and logs from %LOCALAPPDATA%\DisplayLayoutGuard.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File src\uninstall.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File src\uninstall.ps1 -Purge
#>
[CmdletBinding()]
param(
    [switch]$Purge
)

$ErrorActionPreference = 'Stop'

$InstallDir = Join-Path $env:LOCALAPPDATA 'DisplayLayoutGuard'
$StartupDir = [Environment]::GetFolderPath('Startup')
$Launcher   = Join-Path $StartupDir 'DisplayLayoutGuard.vbs'
$ScriptName = 'display_guard.py'

if (Test-Path $Launcher) {
    Remove-Item $Launcher -Force
    Write-Host "Removed launcher: $Launcher"
}

Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$ScriptName*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped guard process: $($_.ProcessId)"
    }

if ($Purge -and (Test-Path $InstallDir)) {
    Remove-Item $InstallDir -Recurse -Force
    Write-Host "Removed data directory: $InstallDir"
} else {
    Write-Host "Kept data directory: $InstallDir"
}
