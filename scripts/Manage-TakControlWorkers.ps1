[CmdletBinding()]
param(
    [ValidateSet('Install', 'Start', 'Stop', 'Status', 'Uninstall')]
    [string]$Action = 'Status'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSEdition -ne 'Desktop') {
    $windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Action $Action
    exit $LASTEXITCODE
}
Import-Module ScheduledTasks -ErrorAction Stop

$projectRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot 'run_host_worker.py'
$workers = @(
    @{ Name = 'certificate'; Task = 'TAK-Certificate-Worker'; Control = 'runtime\tak-cert-control' },
    @{ Name = 'mumble'; Task = 'TAK-Mumble-Worker'; Control = 'runtime\share-control' }
)

function Get-WorkerTask([string]$taskName) {
    Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
}

function Wait-WorkerHeartbeat([string]$controlPath, [string]$taskName) {
    $heartbeat = Join-Path $projectRoot (Join-Path $controlPath 'heartbeat')
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-Path -LiteralPath $heartbeat) {
            $age = ((Get-Date) - (Get-Item -LiteralPath $heartbeat).LastWriteTime).TotalSeconds
            if ($age -lt 5 -and (Get-WorkerTask $taskName).State -eq 'Running') { return }
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Worker heartbeat did not start: $heartbeat"
}

if ($Action -eq 'Install') {
    $python = (& python -c 'import sys; print(sys.executable)').Trim()
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python)) {
        throw 'Python is unavailable. Install the host worker requirements first.'
    }
    $pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) {
        throw "pythonw.exe was not found next to $python"
    }
    & $python -c 'import cryptography'
    if ($LASTEXITCODE -ne 0) {
        throw 'Python host worker dependencies are missing.'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    foreach ($worker in $workers) {
        $arguments = '"{0}" {1}' -f $runner, $worker.Name
        $taskAction = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments `
            -WorkingDirectory $projectRoot
        Register-ScheduledTask -TaskName $worker.Task -Action $taskAction `
            -Principal $principal -Trigger $trigger -Settings $settings `
            -Description "Starts the TAK $($worker.Name) management worker after Windows logon." `
            -Force | Out-Null
        Write-Output "Installed $($worker.Task) for $identity."
    }
    $Action = 'Start'
}

if ($Action -eq 'Start') {
    foreach ($worker in $workers) {
        if (-not (Get-WorkerTask $worker.Task)) {
            throw "$($worker.Task) is not installed. Run -Action Install first."
        }
        Start-ScheduledTask -TaskName $worker.Task
        Wait-WorkerHeartbeat $worker.Control $worker.Task
        Write-Output "$($worker.Task) is responding."
    }
} elseif ($Action -eq 'Stop' -or $Action -eq 'Uninstall') {
    foreach ($worker in $workers) {
        if (Get-WorkerTask $worker.Task) {
            Stop-ScheduledTask -TaskName $worker.Task -ErrorAction SilentlyContinue
            if ($Action -eq 'Uninstall') {
                Unregister-ScheduledTask -TaskName $worker.Task -Confirm:$false
            }
        }
        Write-Output "$($worker.Task): $Action complete."
    }
} elseif ($Action -eq 'Status') {
    foreach ($worker in $workers) {
        $task = Get-WorkerTask $worker.Task
        $heartbeat = Join-Path $projectRoot (Join-Path $worker.Control 'heartbeat')
        $fresh = (Test-Path -LiteralPath $heartbeat) -and
            (((Get-Date) - (Get-Item -LiteralPath $heartbeat).LastWriteTime).TotalSeconds -lt 5)
        [pscustomobject]@{
            Worker = $worker.Name
            Task = $worker.Task
            TaskState = if ($task) { $task.State } else { 'NotInstalled' }
            Responding = $fresh
        }
    }
}
