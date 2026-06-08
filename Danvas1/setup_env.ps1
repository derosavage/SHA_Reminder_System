# Danvas1 Environment Setup
# Run this ONCE to set up the shared Python environment

# Step 1: Create the shared virtual environment (run once)
python -m venv C:\TradingBots\_shared_venv

# Step 2: Install all dependencies
C:\TradingBots\_shared_venv\Scripts\pip.exe install -r C:\TradingBots\Danvas1\requirements.txt

# Alternative: If upgrading existing environment
C:\TradingBots\_shared_venv\Scripts\pip.exe install --upgrade pybit pandas numpy python-dotenv requests websocket-client scipy scikit-learn matplotlib ta openpyxl xlsxwriter python-dateutil coloredlogs aiohttp pytest pytest-asyncio

# Verify installation
C:\TradingBots\_shared_venv\Scripts\python.exe -c "import pybit; print(f'pybit version: {pybit.__version__}')"