[CmdletBinding()]
param(
    [string]$LocalAddress = '192.168.137.1',
    [string]$RemoteAddress = '192.168.137.0/24'
)

$ErrorActionPreference = 'Stop'
$ruleNames = @('TAK-Local-CoT-8089', 'TAK-Local-Admin-8443')
foreach ($name in $ruleNames) {
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
}

New-NetFirewallRule -DisplayName $ruleNames[0] -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress $LocalAddress -LocalPort 8089 -RemoteAddress $RemoteAddress -Profile Any | Out-Null
New-NetFirewallRule -DisplayName $ruleNames[1] -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress $LocalAddress -LocalPort 8443 -RemoteAddress $RemoteAddress -Profile Any | Out-Null

Write-Host "Installed TAK firewall rules for $RemoteAddress."
