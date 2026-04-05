$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Create it first with:" -ForegroundColor Yellow
    Write-Host "python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".\.env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review it before continuing." -ForegroundColor Yellow
}

$env:DRY_RUN = "true"
& ".\.venv\Scripts\python.exe" ".\main.py"
