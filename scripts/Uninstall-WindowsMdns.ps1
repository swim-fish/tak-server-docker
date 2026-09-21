[CmdletBinding()]
param(
    [string]$TaskName = 'TAK-mDNS-Responder',
    [switch]$RemoveRuntime
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated Windows PowerShell session.'
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
