# SHA Reminder System - Local Test Script (Windows PowerShell)
# Tests the penalty calculator without any dependencies

Write-Host "========================================" -ForegroundColor Green
Write-Host "SHA Reminder System - Local Test Suite" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Step 1: Create a virtual environment
Write-Host "[1/4] Setting up Python virtual environment..." -ForegroundColor Cyan
$venvPath = Join-Path $PSScriptRoot "..\backend\.venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "  ✔ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  ✔ Virtual environment already exists" -ForegroundColor Yellow
}

# Step 2: Activate and install dependencies
Write-Host "[2/4] Installing dependencies..." -ForegroundColor Cyan
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
& $activateScript
pip install -r (Join-Path $PSScriptRoot "..\backend\requirements.txt") 2>&1 | Out-Null
Write-Host "  ✔ Dependencies installed" -ForegroundColor Green

# Step 3: Run the penalty calculator tests
Write-Host "[3/4] Running Penalty Calculator Tests..." -ForegroundColor Cyan
Set-Location (Join-Path $PSScriptRoot "..\backend")
python -m pytest tests/test_penalty.py -v 2>&1 | ForEach-Object { Write-Host $_ }

# Step 4: Start the API server (optional - requires user input)
Write-Host ""
Write-Host "[4/4] Starting API server for manual testing..." -ForegroundColor Cyan
Write-Host ""
Write-Host "The API will be available at: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Swagger docs at: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "NOTE: Full functionality requires PostgreSQL and Redis." -ForegroundColor Magenta
Write-Host "The server will start but DB-dependent features will be limited." -ForegroundColor Magenta
Write-Host ""
Write-Host "Testing endpoints you can hit immediately WITHOUT a database:" -ForegroundColor Green
Write-Host "  • GET  /                    - Root info" 
Write-Host "  • GET  /api/v1/health       - Health check"
Write-Host "  • GET  /api/v1/penalty/formula - Get penalty formula"
Write-Host "  • POST /api/v1/penalty/calculate - Calculate penalty (no auth needed)"
Write-Host "  • GET  /api/v1/payments/paybill  - Get paybill info"
Write-Host ""

# Start the server
Write-Host "Starting Uvicorn server..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server when done." -ForegroundColor Yellow
Write-Host ""
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload