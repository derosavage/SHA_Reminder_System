# Danvas1 - Restart Script
# Safely restarts the trading bot

param(
    [switch]$Force,
    [int]$WaitSeconds = 5
)

$ErrorActionPreference = "Stop"

$BOT_NAME = "Danvas1"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  $BOT_NAME Restart Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Find running bot processes
$PythonProcesses = Get-Process python* -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

if ($PythonProcesses) {
    Write-Host "Found running bot processes:" -ForegroundColor Yellow
    $PythonProcesses | Format-Table Id, ProcessName, StartTime -AutoSize
    Write-Host ""

    if (-not $Force) {
        $Response = Read-Host "Stop these processes and restart? (y/n)"
        if ($Response -ne 'y') {
            Write-Host "Restart cancelled." -ForegroundColor Cyan
            exit 0
        }
    }

    Write-Host "Stopping bot processes..." -ForegroundColor Yellow

    $PythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue

    Write-Host "Waiting $WaitSeconds seconds for cleanup..." -ForegroundColor Gray
    Start-Sleep -Seconds $WaitSeconds

} else {
    Write-Host "No running bot processes found." -ForegroundColor Gray
}

Write-Host "Starting bot..." -ForegroundColor Green
Write-Host ""

# Start new instance
$RunScript = Join-Path $PSScriptRoot "run.ps1"

if (Test-Path $RunScript) {
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $RunScript

    Write-Host "Bot started successfully!" -ForegroundColor Green
} else {
    Write-Host "ERROR: run.ps1 not found in script directory" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Use healthcheck.ps1 to monitor the bot." -ForegroundColor Gray