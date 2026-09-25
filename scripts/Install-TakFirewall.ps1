[CmdletBinding()]
param(
    [string]$LocalAddress,
    [string]$RemoteAddress,
    [ValidateRange(1, 65535)]
    [int]$AdminPort = 8443
)

$ErrorActionPreference = 'Stop'
$networkConfig = & (Join-Path $PSScriptRoot 'Local-NetworkConfig.ps1')
if (-not $LocalAddress) { $LocalAddress = $networkConfig.Address }
if (-not $RemoteAddress) { $RemoteAddress = $networkConfig.Subnet }
$network = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LocalAddress -ErrorAction SilentlyContinue |
    Where-Object { $_.AddressState -eq 'Preferred' })
if ($network.Count -ne 1) {
    throw "Local address $LocalAddress is not assigned to an active Windows interface."
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
        Join-Path $PSHOME 'pwsh.exe'
    } else { Join-Path $PSHOME 'powershell.exe' }
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        ('"{0}"' -f $PSCommandPath), '-LocalAddress', ('"{0}"' -f $LocalAddress),
        '-RemoteAddress', ('"{0}"' -f $RemoteAddress), '-AdminPort', "$AdminPort")
    Write-Host 'Approve Windows UAC to install TAK firewall rules.'
    $child = Start-Process -FilePath $executable -Verb RunAs -WindowStyle Hidden `
        -ArgumentList $arguments -PassThru -Wait
    if ($child.ExitCode -ne 0) { throw "TAK firewall setup failed: exit $($child.ExitCode)" }
    return
}
$ruleNames = @('TAK-Local-CoT-8089', 'TAK-Local-Admin-8443')
foreach ($name in $ruleNames) {
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
}

New-NetFirewallRule -DisplayName $ruleNames[0] -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress $LocalAddress -LocalPort 8089 -RemoteAddress $RemoteAddress -Profile Any | Out-Null
New-NetFirewallRule -DisplayName $ruleNames[1] -Direction Inbound -Action Allow -Protocol TCP `
    -LocalAddress $LocalAddress -LocalPort $AdminPort -RemoteAddress $RemoteAddress -Profile Any | Out-Null

Write-Host "Installed TAK firewall rules for $RemoteAddress."
