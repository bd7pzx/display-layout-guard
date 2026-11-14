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
$ScriptName = 'display_guard.py'
$RunKey     = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$RunName    = 'DisplayLayoutGuard'

if (Get-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue) {
    Remove-ItemProperty -Path $RunKey -Name $RunName -Force
    Write-Host "Removed autostart entry: $RunName"
}

$legacy = Join-Path ([Environment]::GetFolderPath('Startup')) 'DisplayLayoutGuard.vbs'
if (Test-Path $legacy) {
    Remove-Item $legacy -Force -ErrorAction SilentlyContinue
    Write-Host "Removed legacy launcher: $legacy"
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
