[CmdletBinding()]
param(
    [string]$TaskName = 'TAK-mDNS-Responder',
    [switch]$RemoveRuntime,
    [string]$ElevationRequestPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($ElevationRequestPath) {
    if (-not (Test-Path -LiteralPath $ElevationRequestPath)) {
        throw "The elevation request file was not found: $ElevationRequestPath"
    }

    $elevationRequest = Import-Clixml -LiteralPath $ElevationRequestPath
    Remove-Item -LiteralPath $ElevationRequestPath -Force -ErrorAction SilentlyContinue
    $TaskName = [string]$elevationRequest.TaskName
    $RemoveRuntime = [bool]$elevationRequest.RemoveRuntime
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if (-not $PSCommandPath) {
        throw 'This script must be executed from a .ps1 file before it can request administrator access.'
    }

    $requestFile = New-TemporaryFile
    [pscustomobject]@{
        TaskName = $TaskName
        RemoveRuntime = [bool]$RemoveRuntime
    } | Export-Clixml -LiteralPath $requestFile.FullName

    $powerShellExecutable = if ($PSVersionTable.PSEdition -eq 'Core') {
        Join-Path $PSHOME 'pwsh.exe'
    } else {
        Join-Path $PSHOME 'powershell.exe'
    }
    $elevatedArguments = @(
        '-NoProfile'
        '-ExecutionPolicy'
        'Bypass'
        '-File'
        ('"{0}"' -f $PSCommandPath)
        '-ElevationRequestPath'
        ('"{0}"' -f $requestFile.FullName)
    )

    Write-Output 'Administrator access is required. Approve the Windows UAC prompt to continue.'
    try {
        $elevatedProcess = Start-Process `
            -FilePath $powerShellExecutable `
            -Verb RunAs `
            -ArgumentList $elevatedArguments `
            -Wait `
            -PassThru
    } catch {
        throw 'Administrator approval was cancelled or the elevated process could not be started.'
    } finally {
        Remove-Item -LiteralPath $requestFile.FullName -Force -ErrorAction SilentlyContinue
    }

    if ($elevatedProcess.ExitCode -ne 0) {
        throw "The elevated mDNS removal failed with exit code $($elevatedProcess.ExitCode)."
    }

    Write-Output 'The elevated mDNS removal completed successfully.'
    return
}

$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$runtimeDir = [IO.Path]::GetFullPath((Join-Path $projectRoot 'runtime\mdns'))

Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Stop-ScheduledTask -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false

Get-NetFirewallRule -Name 'TAK-mDNS-Responder-In' -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
Get-NetFirewallRule -Name 'TAK-mDNS-Responder-Out' -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

if ($RemoveRuntime -and (Test-Path -LiteralPath $runtimeDir)) {
    $expected = [IO.Path]::GetFullPath((Join-Path $projectRoot 'runtime\mdns'))
    if ($runtimeDir -ne $expected -or -not $runtimeDir.StartsWith($projectRoot)) {
        throw "Unexpected runtime path: $runtimeDir"
    }
    Remove-Item -LiteralPath $runtimeDir -Recurse -Force
}

Write-Output "Removed $TaskName and its firewall rules."
