$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw 'npm was not found. Install Node.js LTS from nodejs.org and reopen PowerShell.'
}
Set-Location (Join-Path $Root 'frontend')
npm install
Write-Host 'React frontend setup complete. Run .\start_frontend.ps1 in a separate PowerShell window.' -ForegroundColor Green
