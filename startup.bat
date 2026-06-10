@echo off
setlocal

echo ============================================================
echo   NIFTY Trading System - Startup
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11+ is required but not found in PATH.
    echo       Install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Checking Python...
python --version

echo.
echo [2/3] Installing dependencies...
if not exist ".venv\" (
    echo       Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
:: FIXED: Changed Activate.ps1 to activate.bat so the batch script can read it natively
call .\.venv\Scripts\activate.bat

echo Installing dependencies...
:: FIXED: Kept one clean, quiet installation call
call pip install -q fastapi uvicorn websockets requests python-dotenv pytest pytest-cov pandas upstox-python-sdk
call pip install --upgrade upstox-python-sdk
echo.
echo [3/3] Starting FastAPI server...
echo       Dashboard  : http://localhost:8000/
echo       API docs   : http://localhost:8000/docs
echo       WebSocket  : ws://localhost:8000/ws
echo.
echo       Press Ctrl+C to stop the server.
echo       Or open a new terminal to run tests or curl commands.
echo.
echo ============================================================

:: FIXED: Added call to ensure uvicorn runs reliably and stays in bounds of the script setup
call uvicorn app:app --host 0.0.0.0 --port 8000 --reload

endlocal
