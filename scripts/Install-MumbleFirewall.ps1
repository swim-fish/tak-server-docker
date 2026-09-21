[CmdletBinding()]
param(
    [string]$LocalAddress = '192.168.137.1',
    [string]$RemoteAddress = '192.168.137.0/24',
    [ValidateRange(1, 65535)]
    [int]$Port = 64400
)

$ErrorActionPreference = 'Stop'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)) {
    throw 'Run this script from an elevated PowerShell session.'
}

$rules = @(
    @{
        Name = 'TAK-Local-Mumble-TCP-64400'
        DisplayName = 'TAK Local Mumble TCP 64400'
        Protocol = 'TCP'
    },
    @{
        Name = 'TAK-Local-Mumble-UDP-64400'
        DisplayName = 'TAK Local Mumble UDP 64400'
        Protocol = 'UDP'
    }
)

Get-NetFirewallRule `
    -Name 'TAK-Local-Mumble-TCP-64738','TAK-Local-Mumble-UDP-64738' `
    -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

foreach ($rule in $rules) {
    Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule

    New-NetFirewallRule `
        -Name $rule.Name `
        -DisplayName $rule.DisplayName `
        -Direction Inbound `
        -Action Allow `
        -Enabled True `
        -Profile Any `
        -Protocol $rule.Protocol `
        -LocalAddress $LocalAddress `
        -LocalPort $Port `
        -RemoteAddress $RemoteAddress | Out-Null
}

Get-NetFirewallRule -Name ($rules.Name) |
    Get-NetFirewallPortFilter |
    Select-Object InstanceID, Protocol, LocalPort
