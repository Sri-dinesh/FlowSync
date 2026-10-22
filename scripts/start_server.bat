@echo off
:: FlowSync backend start script — always uses the project venv
:: Run this from the FlowSync root directory: scripts\start_server.bat

cd /d "%~dp0\.."
echo [FlowSync] Starting backend with project venv...
set "FLOWSYNC_PYTHON=server\.venv\Scripts\python.exe"
if not exist "%FLOWSYNC_PYTHON%" set "FLOWSYNC_PYTHON=server\venv\Scripts\python.exe"
if not exist "%FLOWSYNC_PYTHON%" (
    echo Create server/.venv first; see docs/setup.md.
    exit /b 1
)
echo [FlowSync] Python: %FLOWSYNC_PYTHON%
"%FLOWSYNC_PYTHON%" -m uvicorn app.main:app --reload --port 8000 --app-dir server
