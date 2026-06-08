# Danvas1 - Healthcheck Script
# Monitors bot health and alerts on issues

param(
    [int]$IntervalSeconds = 60,
    [int]$MaxRestartAttempts = 3,
    [switch]$AutoRestart
)

$ErrorActionPreference = "Continue"

# Configuration
$BOT_NAME = "Danvas1"
$CHECK_INTERVAL = $IntervalSeconds
$MAX_RESTARTS = $MaxRestartAttempts

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  $BOT_NAME Health Monitor" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# State tracking
$Script:RestartCount = 0
$Script:LastHealthCheck = $null

function Write-StatusLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    switch ($Level) {
        "OK" { Write-Host "[$Timestamp] [OK]   $Message" -ForegroundColor Green }
        "WARN" { Write-Host "[$Timestamp] [WARN] $Message" -ForegroundColor Yellow }
        "ERROR" { Write-Host "[$Timestamp] [ERR]  $Message" -ForegroundColor Red }
        "INFO" { Write-Host "[$Timestamp] [INFO] $Message" -ForegroundColor Gray }
    }
}

function Test-ProcessRunning {
    param([string]$ProcessName)

    $Processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue

    if ($Processes) {
        return $true
    }

    return $false
}

function Test-LogFreshness {
    param([string]$LogFile)

    if (-not (Test-Path $LogFile)) {
        return $false, "Log file not found"
    }

    $LastWrite = (Get-Item $LogFile).LastWriteTime
    $Age = (Get-Date) - $LastWrite

    if ($Age.TotalMinutes -gt 5) {
        return $false, "Log file is stale (${$Age.TotalMinutes} minutes old)"
    }

    return $true, "Log file is fresh"
}

function Test-ApiConnection {
    try {
        $PythonPath = "C:\TradingBots\_shared_venv\Scripts\python.exe"
        $TestScript = @"
import sys
sys.path.insert(0, r'$($PSScriptRoot -replace "\\", "\\\\")')
from exchange.bybit_client import BybitClient
from dotenv import load_dotenv
import os
load_dotenv()
client = BybitClient(os.getenv('BYBIT_API_KEY',''), os.getenv('BYBIT_API_SECRET',''))
print('connected' if client.test_connection() else 'failed')
"@

        $Result = & $PythonPath -c $TestScript 2>&1

        if ($Result -match "connected") {
            return $true, "API connection OK"
        } else {
            return $false, "API connection failed"
        }
    } catch {
        return $false, "API test error: $_"
    }
}

function Get-BotStatus {
    # Check for health file
    $HealthFile = Join-Path $PSScriptRoot "logs" "state.json"

    if (Test-Path $HealthFile) {
        try {
            $Content = Get-Content $HealthFile -Raw | ConvertFrom-Json
            return @{
                "Running" = $true
                "Equity" = $Content.equity
                "OpenPositions" = $Content.open_positions.Count
                "DailyPnL" = $Content.daily_pnl
            }
        } catch {
            return @{ "Running" = $false }
        }
    }

    return @{ "Running" = $false }
}

function Restart-Bot {
    Write-StatusLog "Attempting to restart bot..." -Level "WARN"

    # Find and stop existing process
    $PythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
    if ($PythonProcesses) {
        $PythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    # Start new instance
    $RunScript = Join-Path $PSScriptRoot "run.ps1"
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $RunScript

    $Script:RestartCount++
    Write-StatusLog "Restart initiated (attempt $Script:RestartCount/$MAX_RESTARTS)" -Level "WARN"
}

# Main monitoring loop
Write-StatusLog "Starting health monitor..."
Write-StatusLog "Check interval: $CHECK_INTERVAL seconds"
Write-StatusLog "Auto-restart: $($AutoRestart ? 'Enabled' : 'Disabled')"
Write-Host ""

while ($true) {
    try {
        # Check bot status
        $Status = Get-BotStatus

        if ($Status.Running) {
            Write-StatusLog "Bot status: RUNNING" -Level "OK"

            # Check API connection
            $ApiOK, $ApiMsg = Test-ApiConnection
            if ($ApiOK) {
                Write-StatusLog "API connection: OK" -Level "OK"
            } else {
                Write-StatusLog "API connection: $ApiMsg" -Level "WARN"
            }

            # Check log file freshness
            $LogFile = Join-Path $PSScriptRoot "logs" "bot.log"
            $LogOK, $LogMsg = Test-LogFreshness $LogFile

            if ($LogOK) {
                Write-StatusLog "Log file: Fresh" -Level "OK"
            } else {
                Write-StatusLog "Log file: $LogMsg" -Level "WARN"
            }

            # Display key metrics
            Write-StatusLog "Equity: $($Status.Equity ?? 'N/A')" -Level "INFO"
            Write-StatusLog "Open Positions: $($Status.OpenPositions ?? 0)" -Level "INFO"
            Write-StatusLog "Daily PnL: $($Status.DailyPnL ?? 0)" -Level "INFO"

        } else {
            Write-StatusLog "Bot status: NOT RUNNING" -Level "ERROR"

            if ($AutoRestart -and $Script:RestartCount -lt $MAX_RESTARTS) {
                Restart-Bot
            } elseif ($Script:RestartCount -ge $MAX_RESTARTS) {
                Write-StatusLog "Max restart attempts reached. Manual intervention required." -Level "ERROR"
            }
        }

        $Script:LastHealthCheck = Get-Date

    } catch {
        Write-StatusLog "Health check error: $_" -Level "ERROR"
    }

    Write-Host ""
    Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor DarkGray
    Write-Host ""

    Start-Sleep -Seconds $CHECK_INTERVAL
}