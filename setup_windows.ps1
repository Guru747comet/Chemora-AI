$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path 'backend\.venv\Scripts\python.exe')) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv 'backend\.venv'
  } elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv 'backend\.venv'
  } else {
    throw 'Python was not found. Install Python 3.10 or newer from python.org, enable the launcher, then retry.'
  }
}
& 'backend\.venv\Scripts\python.exe' -m pip install --upgrade pip
& 'backend\.venv\Scripts\python.exe' -m pip install -r 'backend\requirements.txt'
Write-Host ''
Write-Host 'Backend setup complete. Run .\start_backend.ps1 and open http://127.0.0.1:8000/.' -ForegroundColor Green
Write-Host 'Optional: run .\setup_frontend.ps1 for the separate React/Vite frontend.' -ForegroundColor Cyan
