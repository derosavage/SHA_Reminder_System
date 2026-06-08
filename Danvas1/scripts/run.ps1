# Danvas1 - Run Script
# Starts the trading bot

param(
    [switch]$Backtest,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Bot Configuration
$BOT_NAME = "Danvas1"
$BOT_VERSION = "v1.0.0"
$PYTHON_PATH = "C:\TradingBots\_shared_venv\Scripts\python.exe"
$SCRIPT_DIR = $PSScriptRoot
$PROJECT_ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  $BOT_NAME Trading Bot $BOT_VERSION" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "ERROR: Python virtual environment not found at:" -ForegroundColor Red
    Write-Host "  $PYTHON_PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run setup_env.ps1 first to create the environment." -ForegroundColor Yellow
    exit 1
}

# Check for .env file in project root
$ENV_FILE = Join-Path $PROJECT_ROOT ".env"
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "WARNING: .env file not found in project root. Copying from .env.example..." -ForegroundColor Yellow
    $ENV_EXAMPLE = Join-Path $PROJECT_ROOT ".env.example"
    if (Test-Path $ENV_EXAMPLE) {
        Copy-Item $ENV_EXAMPLE $ENV_FILE
        Write-Host "Created .env file. Please edit it with your API credentials." -ForegroundColor Yellow
    }
}

# Set environment variables
$env:PYTHONUNBUFFERED = "1"
$env:DANVAS1_HOME = $PROJECT_ROOT

# Switch to project root so relative imports work correctly
Set-Location $PROJECT_ROOT

# Build command
$BOT_SCRIPT = Join-Path $PROJECT_ROOT "bot.py"
$LOG_DIR = Join-Path $PROJECT_ROOT "logs"
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

$LOG_FILE = Join-Path $LOG_DIR "bot.log"
$LOG_OUTPUT_FILE = Join-Path $LOG_DIR "bot_console.log"
try {
    $stream = [System.IO.File]::Open($LOG_OUTPUT_FILE, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::ReadWrite)
    $stream.Close()
} catch {
    $fallbackName = "bot_console_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date)
    $LOG_OUTPUT_FILE = Join-Path $LOG_DIR $fallbackName
    Write-Host "WARNING: Console log file locked; using fallback console log: $LOG_OUTPUT_FILE" -ForegroundColor Yellow
}

Write-Host "Starting $BOT_NAME..." -ForegroundColor Green
Write-Host "Bot log file: $LOG_FILE" -ForegroundColor Gray
Write-Host "Console output capture: $LOG_OUTPUT_FILE" -ForegroundColor Gray
Write-Host ""

# Determine execution mode
$Arguments = @($BOT_SCRIPT)

if ($Backtest) {
    $Arguments += "--backtest"
    Write-Host "Mode: BACKTEST" -ForegroundColor Yellow
} else {
    Write-Host "Mode: LIVE TRADING" -ForegroundColor Green
}

if ($Debug) {
    $Arguments += "--debug"
    $env:PYTHON_VERBOSE = "1"
    Write-Host "Debug mode enabled" -ForegroundColor Gray
}

Write-Host ""

# Run the bot
try {
    & $PYTHON_PATH @Arguments 2>&1 | Tee-Object -FilePath $LOG_OUTPUT_FILE
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start bot" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Keep window open if script exits
Write-Host ""
Write-Host "Bot has stopped. Press any key to close..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")