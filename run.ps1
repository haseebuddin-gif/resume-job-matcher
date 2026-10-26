# One-command start on Windows: sets up the environment on first run, builds the
# Angular frontend if needed, then serves app + API at http://localhost:8000
#   powershell -ExecutionPolicy Bypass -File run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python environment (first run only)..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m spacy download en_core_web_sm
}

if (-not (Test-Path "frontend\dist\frontend\browser\index.html")) {
    Write-Host "Building the Angular frontend (first run only)..."
    Push-Location frontend
    if (-not (Test-Path "node_modules")) { npm install }
    npx ng build
    Pop-Location
}

Write-Host "Starting SkillMatch at http://localhost:8000"
Start-Process "http://localhost:8000"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
