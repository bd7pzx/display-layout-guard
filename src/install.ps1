<#
.SYNOPSIS
    Install or repair the Display Layout Guard for the current user.

.DESCRIPTION
    Copies the guard into %LOCALAPPDATA%\DisplayLayoutGuard, registers a per-user
    autostart entry under HKCU\Software\Microsoft\Windows\CurrentVersion\Run, and
    starts it if it is not already running. Idempotent.

.PARAMETER Verify
    Only report the current installation state; change nothing.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File src\install.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File src\install.ps1 -Verify
#>
[CmdletBinding()]
param(
    [switch]$Verify
)

$ErrorActionPreference = 'Stop'

$InstallDir = Join-Path $env:LOCALAPPDATA 'DisplayLayoutGuard'
$ScriptName = 'display_guard.py'
$SourceFile = Join-Path $PSScriptRoot $ScriptName
$TargetFile = Join-Path $InstallDir $ScriptName
$LogFile    = Join-Path $InstallDir 'display_guard.log'
$RunKey     = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$RunName    = 'DisplayLayoutGuard'

function Find-Pythonw {
    $candidates = @()
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += (Join-Path (Split-Path $cmd.Source) 'pythonw.exe') }
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }
    return $null
}

function Get-GuardProcesses {
    Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*$ScriptName*" }
}

function Get-RunEntry {
    (Get-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue).$RunName
}

function Report-State {
    $pythonw = Find-Pythonw
    $procs = @(Get-GuardProcesses)
    [pscustomobject]@{
        InstallDir    = $InstallDir
        ScriptPresent = (Test-Path $TargetFile)
        RunEntry      = if (Get-RunEntry) { 'present' } else { 'missing' }
        Pythonw       = if ($pythonw) { $pythonw } else { 'not found' }
        Processes     = $procs.Count
        LogFile       = (Test-Path $LogFile)
    }
}

if ($Verify) {
    Report-State | Format-List
    return
}

if (-not (Test-Path $SourceFile)) {
    throw "Source file not found: $SourceFile"
}

$pythonw = Find-Pythonw
if (-not $pythonw) {
    throw 'pythonw.exe not found. Install CPython 3.9+ and ensure it is on PATH.'
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $SourceFile $TargetFile -Force

$command = '"{0}" "{1}"' -f $pythonw, $TargetFile
New-Item -Path $RunKey -Force | Out-Null
New-ItemProperty -Path $RunKey -Name $RunName -Value $command -PropertyType String -Force | Out-Null

if (-not (Get-GuardProcesses)) {
    Start-Process -FilePath $pythonw -ArgumentList ('"' + $TargetFile + '"') -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

Report-State | Format-List
