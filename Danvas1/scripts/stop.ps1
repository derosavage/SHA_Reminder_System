# Danvas1 - Stop Script
# Safely stops the trading bot

param(
    [switch]$Force,
    [int]$GracePeriodSeconds = 30
)

$ErrorActionPreference = "Stop"

$BOT_NAME = "Danvas1"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  $BOT_NAME Stop Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Find running bot processes
$PythonProcesses = Get-Process python* -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

if (-not $PythonProcesses) {
    Write-Host "No running bot processes found." -ForegroundColor Cyan
    exit 0
}

Write-Host "Found running bot processes:" -ForegroundColor Yellow
$PythonProcesses | Format-Table Id, ProcessName, StartTime -AutoSize
Write-Host ""

if (-not $Force) {
    Write-Host "This will close all open positions!" -ForegroundColor Red
    Write-Host ""

    $Response = Read-Host "Stop the bot? (y/n)"
    if ($Response -ne 'y') {
        Write-Host "Stop cancelled." -ForegroundColor Cyan
        exit 0
    }
}

Write-Host "Stopping bot gracefully..." -ForegroundColor Yellow
Write-Host "Grace period: $GracePeriodSeconds seconds" -ForegroundColor Gray

# Try graceful shutdown first
foreach ($Process in $PythonProcesses) {
    try {
        # Send interrupt signal
        $Process.CloseMainWindow() | Out-Null
    } catch {}
}

# Wait for graceful shutdown
$Waited = 0
$AllStopped = $false

while ($Waited -lt $GracePeriodSeconds) {
    Start-Sleep -Seconds 1
    $Waited++

    $Remaining = Get-Process python* -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

    if (-not $Remaining) {
        $AllStopped = $true
        break
    }

    if ($Waited % 5 -eq 0) {
        Write-Host "Waiting for graceful shutdown... ($Waited/$GracePeriodSeconds)" -ForegroundColor Gray
    }
}

# Force kill if needed
if (-not $AllStopped) {
    Write-Host ""
    Write-Host "Graceful shutdown timed out. Forcing stop..." -ForegroundColor Yellow

    $PythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue

    Start-Sleep -Seconds 2
}

# Verify stopped
$StillRunning = Get-Process python* -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

if ($StillRunning) {
    Write-Host ""
    Write-Host "WARNING: Some processes may still be running." -ForegroundColor Yellow
    $StillRunning | Format-Table Id, ProcessName -AutoSize
} else {
    Write-Host ""
    Write-Host "Bot stopped successfully." -ForegroundColor Green
}

Write-Host ""
Write-Host "Logs are available in the logs directory." -ForegroundColor Gray