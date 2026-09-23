[CmdletBinding()]
param(
    [string]$LocalAddress = '192.168.137.1',
    [string]$RemoteAddress = '192.168.137.0/24'
)

$ErrorActionPreference = 'Stop'

$address = $null
if (-not [Net.IPAddress]::TryParse($LocalAddress, [ref]$address) -or
    $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'LocalAddress must be an IPv4 address.'
}
$network = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LocalAddress -ErrorAction SilentlyContinue |
    Where-Object { $_.AddressState -eq 'Preferred' })
if ($network.Count -ne 1) {
    throw "Local address $LocalAddress is not ready. Enable the target interface first."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
        Join-Path $PSHOME 'pwsh.exe'
    } else { Join-Path $PSHOME 'powershell.exe' }
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        ('"{0}"' -f $PSCommandPath), '-LocalAddress', ('"{0}"' -f $LocalAddress),
        '-RemoteAddress', ('"{0}"' -f $RemoteAddress))
    Write-Host 'Approve Windows UAC to install MediaMTX firewall rules.'
    $child = Start-Process -FilePath $executable -Verb RunAs -WindowStyle Hidden `
        -ArgumentList $arguments -PassThru -Wait
    if ($child.ExitCode -ne 0) { throw "MediaMTX firewall setup failed: exit $($child.ExitCode)" }
    return
}

$interfaceAlias = $network[0].InterfaceAlias
$rules = @(
    @{ Name = 'TAK-Local-MediaMTX-TCP'; Protocol = 'TCP'; Ports = @('8554', '8322') },
    @{ Name = 'TAK-Local-MediaMTX-UDP'; Protocol = 'UDP'; Ports = @('8000', '8001', '8004', '8005') }
)
foreach ($rule in $rules) {
    Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction Stop
    New-NetFirewallRule -Name $rule.Name -DisplayName $rule.Name -Direction Inbound `
        -Action Allow -Enabled True -Profile Any -Protocol $rule.Protocol `
        -LocalAddress $LocalAddress -LocalPort $rule.Ports -RemoteAddress $RemoteAddress `
        -InterfaceAlias $interfaceAlias -ErrorAction Stop | Out-Null
}

Write-Host "Installed MediaMTX firewall rules for $LocalAddress on '$interfaceAlias' from $RemoteAddress."
