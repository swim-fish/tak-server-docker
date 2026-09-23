[CmdletBinding()]
param(
    [string]$LocalAddress = '192.168.137.1',
    [string]$RemoteAddress = '192.168.137.0/24',
    [ValidateRange(1, 65535)]
    [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$parsedAddress = $null
if (-not [Net.IPAddress]::TryParse($LocalAddress, [ref]$parsedAddress) -or
    $parsedAddress.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'LocalAddress must be an IPv4 address.'
}

$interfaces = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object { $_.IPAddress -eq $LocalAddress -and $_.AddressState -eq 'Preferred' })
if ($interfaces.Count -ne 1) {
    throw "Local address $LocalAddress is not ready. Enable the target interface first."
}
$network = $interfaces[0]
$connected = @(Get-NetIPInterface -AddressFamily IPv4 -InterfaceIndex $network.InterfaceIndex |
    Where-Object ConnectionState -eq 'Connected')
if ($connected.Count -eq 0) {
    throw "Interface '$($network.InterfaceAlias)' is not connected."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
        Join-Path $PSHOME 'pwsh.exe'
    } else { Join-Path $PSHOME 'powershell.exe' }
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        ('"{0}"' -f $PSCommandPath), '-LocalAddress', ('"{0}"' -f $LocalAddress),
        '-RemoteAddress', ('"{0}"' -f $RemoteAddress), '-Port', "$Port")
    Write-Host 'Approve Windows UAC to open the temporary share portal firewall window.'
    $child = Start-Process -FilePath $executable -Verb RunAs -WindowStyle Normal `
        -ArgumentList $arguments -PassThru -Wait
    if ($child.ExitCode -ne 0 -and $child.ExitCode -ne -1073741510) {
        throw "Share portal firewall session failed: exit $($child.ExitCode)"
    }
    return
}

$name = 'TAK-Local-Share-Portal-' + [Guid]::NewGuid().ToString('N')
try {
    New-NetFirewallRule -Name $name -DisplayName 'TAK Local Share Portal Session' `
        -Direction Inbound -Action Allow -Enabled True -Profile Any -Protocol TCP `
        -LocalAddress $LocalAddress -LocalPort $Port -RemoteAddress $RemoteAddress `
        -InterfaceAlias $network.InterfaceAlias -ErrorAction Stop | Out-Null
    Write-Host "Share portal firewall active: ${LocalAddress}:$Port TCP on '$($network.InterfaceAlias)' for $RemoteAddress."
    Write-Host 'Keep this elevated window open. Press Ctrl+C to remove this session firewall rule.'
    while ($true) {
        $current = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LocalAddress -ErrorAction SilentlyContinue |
            Where-Object { $_.AddressState -eq 'Preferred' -and $_.InterfaceIndex -eq $network.InterfaceIndex })
        if ($current.Count -eq 0) {
            Write-Warning 'The target interface is no longer ready; removing the firewall rule.'
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction Stop
    Write-Host 'This session share portal firewall rule has been removed.'
}
