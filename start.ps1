# Q-GREEN CORRIDOR — one-command startup for Windows PowerShell
# Usage: right-click -> Run with PowerShell, or:  .\start.ps1

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "=============================================="
Write-Host " Q-GREEN CORRIDOR - starting local prototype"
Write-Host "=============================================="

# ---- backend ----
$VenvDir = Join-Path $BackendDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "[backend] creating virtual environment..."
    python -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "[backend] installing Python dependencies..."
& $VenvPython -m pip install -q -r (Join-Path $RootDir "requirements.txt")

$CityFile = Join-Path $BackendDir "data\city_network.json"
if (-not (Test-Path $CityFile)) {
    Write-Host "[backend] generating simulated city network..."
    Push-Location (Join-Path $BackendDir "data")
    & $VenvPython generate_city.py
    Pop-Location
}

Write-Host "[backend] starting FastAPI server on http://localhost:8000 ..."
$BackendProc = Start-Process -PassThru -NoNewWindow -WorkingDirectory $BackendDir `
    -FilePath $VenvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"

# ---- frontend ----
Write-Host "[frontend] installing npm dependencies (first run only)..."
Push-Location $FrontendDir
npm install --silent
Write-Host "[frontend] starting Vite dev server on http://localhost:5173 ..."
$FrontendProc = Start-Process -PassThru -NoNewWindow -WorkingDirectory $FrontendDir `
    -FilePath "npm" -ArgumentList "run", "dev", "--", "--host"
Pop-Location

Write-Host ""
Write-Host "=============================================="
Write-Host " Backend:  http://localhost:8000/docs"
Write-Host " Frontend: http://localhost:5173"
Write-Host "=============================================="
Write-Host " Press Ctrl+C to stop both servers."
Write-Host ""

try {
    Wait-Process -Id $BackendProc.Id
} finally {
    Stop-Process -Id $BackendProc.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $FrontendProc.Id -ErrorAction SilentlyContinue
}
