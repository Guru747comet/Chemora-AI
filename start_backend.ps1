$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $Root 'backend')
if (-not (Test-Path '.venv\Scripts\python.exe')) {
  throw 'Backend environment not found. Run .\setup_windows.ps1 first.'
}
& '.venv\Scripts\python.exe' -m uvicorn app.main:app --reload
