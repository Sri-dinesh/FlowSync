@echo off
:: FlowSync backend start script — always uses the project venv
:: Run this from the FlowSync root directory: scripts\start_server.bat

cd /d "%~dp0\.."
echo [FlowSync] Starting backend with project venv...
echo [FlowSync] Python: server\venv\Scripts\python.exe

server\venv\Scripts\uvicorn app.main:app --reload --port 8000 --app-dir server
