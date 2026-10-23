# FlowSync backend start script — always uses the project venv
# Run from the FlowSync root: .\scripts\start_server.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$Python = Join-Path $RootDir "server\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $RootDir "server\venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    throw "Create server/.venv first; see docs/setup.md."
}

Write-Host "[FlowSync] Starting backend with project venv..." -ForegroundColor Cyan
Write-Host "[FlowSync] Python: $Python" -ForegroundColor DarkGray

Set-Location (Join-Path $RootDir "server")
& $Python -m uvicorn app.main:app --reload --port 8000
