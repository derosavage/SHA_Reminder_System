# Danvas1 - Supervisor Launch Script
# Launches bot with automatic restart on failure

param(
    [int]$MaxRestartAttempts = 10,
    [int]$RestartDelaySeconds = 30,
    [switch]$NoRestart
)

$ErrorActionPreference = "Continue"

# Configuration
$BOT_NAME = "Danvas1"
$SCRIPT_DIR = $PSScriptRoot

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  $BOT_NAME Supervisor" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$Script:RestartCount = 0
$Script:Running = $true

function Write-SupervisorLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    switch ($Level) {
        "INFO" { Write-Host "[$Timestamp] $Message" -ForegroundColor Gray }
        "OK" { Write-Host "[$Timestamp] $Message" -ForegroundColor Green }
        "WARN" { Write-Host "[$Timestamp] $Message" -ForegroundColor Yellow }
        "ERROR" { Write-Host "[$Timestamp] $Message" -ForegroundColor Red }
    }
}

function Start-BotProcess {
    $RunScript = Join-Path $SCRIPT_DIR "run.ps1"

    if (Test-Path $RunScript) {
        $Process = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $RunScript -PassThru -WindowStyle Normal

        Write-SupervisorLog "Bot process started (PID: $($Process.Id))" -Level "OK"

        return $Process
    } else {
        Write-SupervisorLog "run.ps1 not found" -Level "ERROR"
        return $null
    }
}

function Stop-BotProcess {
    $Processes = Get-Process python* -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

    if ($Processes) {
        Write-SupervisorLog "Stopping bot processes..." -Level "WARN"
        $Processes | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
}

function Get-BotStatus {
    $Processes = Get-Process python* -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*Danvas1*" -or $_.CommandLine -like "*bot.py*" }

    return ($null -ne $Processes)
}

# Main supervisor loop
Write-SupervisorLog "Starting supervisor..."
Write-SupervisorLog "Max restart attempts: $MaxRestartAttempts"
Write-SupervisorLog "Restart delay: $RestartDelaySeconds seconds"
Write-SupervisorLog "Auto-restart: $(-not $NoRestart)"
Write-Host ""

$BotProcess = Start-BotProcess

while ($Script:Running) {
    if ($NoRestart) {
        # Just wait for bot to exit
        if ($BotProcess) {
            $BotProcess.WaitForExit()
            Write-SupervisorLog "Bot exited with code: $($BotProcess.ExitCode)" -Level "INFO"
        }
        break
    }

    # Check if bot is still running
    if (-not (Get-BotStatus)) {
        Write-SupervisorLog "Bot process not detected" -Level "WARN"

        if ($Script:RestartCount -ge $MaxRestartAttempts) {
            Write-SupervisorLog "Max restart attempts reached. Supervisor stopping." -Level "ERROR"
            break
        }

        $Script:RestartCount++
        Write-SupervisorLog "Restart attempt $Script:RestartCount/$MaxRestartAttempts" -Level "WARN"
        Write-SupervisorLog "Waiting $RestartDelaySeconds seconds before restart..." -Level "INFO"

        Start-Sleep -Seconds $RestartDelaySeconds

        $BotProcess = Start-BotProcess
    }

    # Check every 10 seconds
    Start-Sleep -Seconds 10
}

Write-Host ""
Write-SupervisorLog "Supervisor stopped" -Level "INFO"

# Cleanup
Stop-BotProcess

Write-Host ""
Write-Host "Press any key to close..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")