@echo off
setlocal
cd /d "%~dp0\..\.."

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run: python -m venv .venv
  exit /b 1
)

if not exist ".env" (
  echo .env is missing. Create it from .env.production.example before live trading.
  exit /b 1
)

set DRY_RUN=false
".venv\Scripts\python.exe" ".\main.py"
