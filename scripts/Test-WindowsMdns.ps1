[CmdletBinding()]
param(
    [string]$TaskName = 'TAK-mDNS-Responder'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot 'runtime\mdns'
$venvPython = Join-Path $runtimeDir '.venv\Scripts\python.exe'
$configPath = Join-Path $runtimeDir 'config.json'
$query = Join-Path $projectRoot 'mdns\query.py'

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'The mDNS runtime is not installed.'
}

$taskStatus = & schtasks.exe /Query /TN $TaskName /FO LIST 2>&1
if ($LASTEXITCODE -eq 0) {
    $taskStatus | Write-Output
} else {
    Write-Warning "Scheduled task status is unavailable in this session: $taskStatus"
}

& $venvPython $query --config $configPath --timeout-ms 5000
if ($LASTEXITCODE -ne 0) {
    throw 'The expected mDNS records were not found.'
}
