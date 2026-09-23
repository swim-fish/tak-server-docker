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

& $venvPython -c 'import ifaddr, zeroconf' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'The mDNS Python environment is incomplete. Run Manage-WindowsMdns.ps1 -Action Install and approve the Windows UAC prompt.'
}

$taskStatusNote = $null
$scheduledTasks = Join-Path $env:SystemRoot 'System32\schtasks.exe'
if (-not (Test-Path -LiteralPath $scheduledTasks)) {
    $taskStatusNote = "schtasks.exe was not found at $scheduledTasks."
} else {
    $taskStatus = & $scheduledTasks /Query /TN $TaskName /FO LIST 2>&1
    if ($LASTEXITCODE -eq 0) {
        $taskStatus | Write-Output
    } else {
        $taskStatusNote = "Scheduled task '$TaskName' was not found or cannot be queried: $taskStatus"
    }
}

& $venvPython $query --config $configPath --timeout-ms 5000
if ($LASTEXITCODE -ne 0) {
    if ($taskStatusNote) {
        Write-Warning $taskStatusNote
    }
    throw 'The expected mDNS records were not found.'
}

if ($taskStatusNote) {
    Write-Output "mDNS records are responding. Task Scheduler status is unavailable in this session: $taskStatusNote"
}
