#Requires -Version 5.1
<#
.SYNOPSIS
  Host-side checks for the Compose stack (expects .env and running containers).

.EXAMPLE
  .\scripts\verify_docker.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root ".env"))) {
    Write-Error "Missing .env - copy .env.example to .env first."
}
Set-Location $Root

Write-Host "== docker compose ps ==" -ForegroundColor Cyan
docker compose ps

Write-Host "`n== postgres (pg_isready) ==" -ForegroundColor Cyan
docker compose exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== redis (PING) ==" -ForegroundColor Cyan
docker compose exec -T redis redis-cli ping

Write-Host "`n== backend: in-container stack script ==" -ForegroundColor Cyan
docker compose exec -T backend python scripts/verify_stack.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$publishPort = "8000"
$envPath = Join-Path $Root ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*APP_PUBLISH_PORT\s*=\s*(.+)\s*$') {
            $publishPort = $matches[1].Trim().Trim('"').Trim([char]39)
        }
    }
}
$health = "http://127.0.0.1:$publishPort/api/v1/health"
Write-Host "`n== API health ($health) ==" -ForegroundColor Cyan
$r = Invoke-RestMethod -Uri $health -Method Get -TimeoutSec 10
if ($r.status -ne "ok") { throw "Unexpected health payload: $($r | ConvertTo-Json)" }
Write-Host "api_health: ok"

Write-Host "`nAll checks passed." -ForegroundColor Green
