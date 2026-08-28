$ErrorActionPreference = 'Stop'

$composeFile = Join-Path $PSScriptRoot '..\docker-compose.dev.yml'
$composeFile = [System.IO.Path]::GetFullPath($composeFile)

Write-Host 'Checking Compose configuration...'
docker compose -f $composeFile config --quiet

Write-Host 'Checking service health...'
$services = docker compose -f $composeFile ps --format json | ConvertFrom-Json
$required = @('backend', 'frontend', 'ml-engine', 'postgresql', 'redis')
foreach ($service in $required) {
    $container = $services | Where-Object { $_.Service -eq $service }
    if ($null -eq $container -or $container.State -ne 'running' -or $container.Health -notmatch 'healthy') {
        throw "Service '$service' is not healthy."
    }
}

Write-Host 'Compiling backend...'
docker compose -f $composeFile exec -T backend python -m compileall -q /app/app
Write-Host 'Compiling ML engine...'
docker compose -f $composeFile exec -T ml-engine python -m compileall -q /app/src

Write-Host 'Checking backend endpoints...'
$health = Invoke-RestMethod http://localhost:8000/health
if ($health.status -ne 'ok') { throw 'Backend health check failed.' }
$status = Invoke-RestMethod http://localhost:8000/api/status
if ($status.api -ne 'connected') { throw 'Backend status check failed.' }
if ($status.trading_mode -ne 'paper') { throw "Expected paper mode, got '$($status.trading_mode)'." }

Write-Host 'Checking frontend...'
$frontend = Invoke-WebRequest -UseBasicParsing http://localhost:3000/
if ($frontend.StatusCode -ne 200) { throw 'Frontend check failed.' }

Write-Host 'Checking ML startup logs...'
$savedErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$mlLogs = docker logs --since 10m aiz-trading-ml-engine-1 2>&1 | Out-String
$ErrorActionPreference = $savedErrorActionPreference
if ($mlLogs -match 'Permission denied|Traceback|Retraining failed') {
    throw 'ML engine logs contain a startup or retraining failure.'
}

Write-Host 'Offline smoke checks: PASS' -ForegroundColor Green
