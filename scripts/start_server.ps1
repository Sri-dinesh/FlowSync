# FlowSync backend start script — always uses the project venv
# Run from the FlowSync root: .\scripts\start_server.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$Uvicorn   = Join-Path $RootDir "server\venv\Scripts\uvicorn.exe"

Write-Host "[FlowSync] Starting backend with project venv..." -ForegroundColor Cyan
Write-Host "[FlowSync] Uvicorn: $Uvicorn" -ForegroundColor DarkGray

Set-Location (Join-Path $RootDir "server")
& $Uvicorn app.main:app --reload --port 8000
