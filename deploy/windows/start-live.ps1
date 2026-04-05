$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Create it first with:" -ForegroundColor Yellow
    Write-Host "python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".\.env")) {
    Write-Host ".env is missing. Create it from .env.production.example before live trading." -ForegroundColor Red
    exit 1
}

$env:DRY_RUN = "false"
& ".\.venv\Scripts\python.exe" ".\main.py"
