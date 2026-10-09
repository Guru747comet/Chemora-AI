$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $Root 'frontend')
if (-not (Test-Path 'node_modules')) {
  throw 'Frontend dependencies not found. Run .\setup_frontend.ps1 first.'
}
npm run dev
