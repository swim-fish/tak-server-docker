[CmdletBinding()]
param(
    [string]$LocalAddress = '192.168.137.1',
    [string]$RemoteAddress = '192.168.137.0/24',
    [ValidateRange(1, 65535)]
    [int]$Port = 40000,
    [string]$ElevationRequestPath
)

$ErrorActionPreference = 'Stop'

if ($ElevationRequestPath) {
    if (-not (Test-Path -LiteralPath $ElevationRequestPath)) {
        throw "The elevation request file was not found: $ElevationRequestPath"
    }

    $elevationRequest = Import-Clixml -LiteralPath $ElevationRequestPath
    Remove-Item -LiteralPath $ElevationRequestPath -Force -ErrorAction SilentlyContinue
    $LocalAddress = [string]$elevationRequest.LocalAddress
    $RemoteAddress = [string]$elevationRequest.RemoteAddress
    $Port = [int]$elevationRequest.Port
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if (-not $PSCommandPath) {
        throw 'This script must be executed from a .ps1 file before it can request administrator access.'
    }

    $requestFile = New-TemporaryFile
    [pscustomobject]@{
        LocalAddress = $LocalAddress
        RemoteAddress = $RemoteAddress
        Port = $Port
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
        throw "The elevated Mumble firewall installation failed with exit code $($elevatedProcess.ExitCode)."
    }

    Write-Output 'The elevated Mumble firewall installation completed successfully.'
    return
}

$rules = @(
    @{
        Name = "TAK-Local-Mumble-TCP-$Port"
        DisplayName = "TAK Local Mumble TCP $Port"
        Protocol = 'TCP'
    },
    @{
        Name = "TAK-Local-Mumble-UDP-$Port"
        DisplayName = "TAK Local Mumble UDP $Port"
        Protocol = 'UDP'
    }
)

Get-NetFirewallRule `
    -Name 'TAK-Local-Mumble-TCP-64738', `
        'TAK-Local-Mumble-UDP-64738', `
        'TAK-Local-Mumble-TCP-64400', `
        'TAK-Local-Mumble-UDP-64400' `
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
