[CmdletBinding()]
param(
    [string]$LocalAddress,
    [string]$RemoteAddress,
    [ValidateRange(1, 65535)]
    [int]$Port = 40000,
    [string]$ElevationRequestPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$networkConfig = & (Join-Path $PSScriptRoot 'Local-NetworkConfig.ps1')
if (-not $LocalAddress) { $LocalAddress = $networkConfig.Address }
if (-not $RemoteAddress) { $RemoteAddress = $networkConfig.Subnet }

function Get-MumbleLocalInterface {
    param([string]$Address)

    # The configured address belongs to the clients' local network.
    $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object { $_.IPAddress -eq $Address -and $_.AddressState -eq 'Preferred' })
    foreach ($item in $addresses) {
        $interfaces = @(Get-NetIPInterface -AddressFamily IPv4 -InterfaceIndex $item.InterfaceIndex -ErrorAction Stop |
            Where-Object { $_.ConnectionState -eq 'Connected' })
        if ($interfaces.Count -gt 0) { return $item }
    }
    return $null
}

function Invoke-MumbleFirewallSession {
    param(
        [string]$Address,
        [string]$Subnet,
        [int]$ListenPort,
        [string]$StopPath,
        [int]$OwnerProcessId = 0,
        [long]$OwnerStartTicks = 0
    )

    $createdRules = [Collections.Generic.List[string]]::new()
    $sessionId = [Guid]::NewGuid().ToString('N')
    try {
        $network = Get-MumbleLocalInterface -Address $Address
        if (-not $network) {
            throw "Local address $Address is not ready. Connect the target interface, then run this script again."
        }
        $existing = @(Get-NetFirewallRule -Name 'TAK-Local-Mumble-*' -ErrorAction SilentlyContinue)
        if ($existing.Count -gt 0) {
            Write-Warning 'Existing Mumble firewall rules will be preserved. They may continue allowing traffic after this session ends.'
        }

        foreach ($protocol in @('TCP', 'UDP')) {
            $name = "TAK-Local-Mumble-Session-$sessionId-$protocol-$ListenPort"
            # Register ownership before creation so a partial failure is also cleaned up.
            $createdRules.Add($name)
            New-NetFirewallRule -Name $name -DisplayName "TAK Local Mumble Session $protocol $ListenPort" `
                -Direction Inbound -Action Allow -Enabled True -Profile Any `
                -Protocol $protocol -LocalAddress $Address -LocalPort $ListenPort `
                -RemoteAddress $Subnet -InterfaceAlias $network.InterfaceAlias `
                -ErrorAction Stop | Out-Null
        }

        Write-Host "Mumble firewall active: ${Address}:$ListenPort TCP/UDP on '$($network.InterfaceAlias)' for $Subnet."
        Write-Host 'Keep this window open. Press Ctrl+C to remove this session firewall rules.'
        while ($true) {
            if ($StopPath -and (Test-Path -LiteralPath $StopPath)) { break }
            if ($OwnerProcessId -gt 0) {
                $owner = Get-Process -Id $OwnerProcessId -ErrorAction SilentlyContinue
                if (-not $owner -or $owner.StartTime.ToUniversalTime().Ticks -ne $OwnerStartTicks) {
                    Write-Host 'The launching shell has closed. Stopping the firewall session.'
                    break
                }
            }
            $current = Get-MumbleLocalInterface -Address $Address
            if (-not $current -or $current.InterfaceIndex -ne $network.InterfaceIndex) {
                Write-Warning "The interface for $Address is no longer ready. Stopping the firewall session."
                break
            }
            Start-Sleep -Seconds 1
        }
    } finally {
        $cleanupFailed = $false
        foreach ($name in $createdRules) {
            try {
                Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue |
                    Remove-NetFirewallRule -ErrorAction Stop
            } catch {
                $cleanupFailed = $true
                Write-Warning "Unable to remove firewall rule '$name': $_"
            }
        }
        if ($createdRules.Count -gt 0 -and -not $cleanupFailed) {
            Write-Host 'This session Mumble firewall rules have been removed.'
        }
        if ($cleanupFailed) { throw 'Firewall cleanup was incomplete. Remove the reported rules with administrator access.' }
    }
}

$stopRequestPath = ''
$ownerId = 0
$ownerTicks = 0L
if ($ElevationRequestPath) {
    $request = Import-Clixml -LiteralPath $ElevationRequestPath
    $LocalAddress = [string]$request.LocalAddress
    $RemoteAddress = [string]$request.RemoteAddress
    $Port = [int]$request.Port
    $stopRequestPath = "$ElevationRequestPath.stop"
    $ownerId = [int]$request.OwnerProcessId
    $ownerTicks = [long]$request.OwnerStartTicks
}

$parsedAddress = $null
if (-not [Net.IPAddress]::TryParse($LocalAddress, [ref]$parsedAddress) -or
    $parsedAddress.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
    $Port -lt 1 -or $Port -gt 65535) {
    throw 'LocalAddress must be an IPv4 address and Port must be between 1 and 65535.'
}

# Fail before requesting UAC or changing any firewall rules.
if (-not (Get-MumbleLocalInterface -Address $LocalAddress)) {
    throw "Local address $LocalAddress is not ready. Connect the target interface, then run this script again. No firewall rules were changed."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($ElevationRequestPath) { throw 'The elevated process did not receive administrator access.' }
    $requestFile = New-TemporaryFile
    $elevatedProcess = $null
    $stopFile = "$($requestFile.FullName).stop"
    try {
        [pscustomobject]@{
            LocalAddress = $LocalAddress
            RemoteAddress = $RemoteAddress
            Port = $Port
            OwnerProcessId = $PID
            OwnerStartTicks = (Get-Process -Id $PID).StartTime.ToUniversalTime().Ticks
        } | Export-Clixml -LiteralPath $requestFile.FullName

        $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
            Join-Path $PSHOME 'pwsh.exe'
        } else { Join-Path $PSHOME 'powershell.exe' }
        $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            ('"{0}"' -f $PSCommandPath), '-ElevationRequestPath',
            ('"{0}"' -f $requestFile.FullName))

        Write-Host 'Approve Windows UAC to open the firewall session window. Keep both shells open; Ctrl+C in either shell stops the session.'
        # This visible elevated console is the interactive session requested by the user.
        $elevatedProcess = Start-Process -FilePath $executable -Verb RunAs `
            -WindowStyle Normal -ArgumentList $arguments -PassThru
        while (-not $elevatedProcess.HasExited) { Start-Sleep -Milliseconds 250 }
        if ($elevatedProcess.ExitCode -ne 0 -and $elevatedProcess.ExitCode -ne -1073741510) {
            throw "The elevated Mumble firewall session failed with exit code $($elevatedProcess.ExitCode)."
        }
    } finally {
        if ($elevatedProcess -and -not $elevatedProcess.HasExited) {
            # Cooperatively stop the privileged child; killing it would skip cleanup.
            [IO.File]::WriteAllText($stopFile, 'stop')
            if (-not $elevatedProcess.WaitForExit(15000)) {
                Write-Warning 'The elevated window is still running. Press Ctrl+C there to complete cleanup.'
            }
        }
        if (-not $elevatedProcess -or $elevatedProcess.HasExited) {
            Remove-Item -LiteralPath $requestFile.FullName -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $stopFile -Force -ErrorAction SilentlyContinue
        }
    }
    return
}

Invoke-MumbleFirewallSession -Address $LocalAddress -Subnet $RemoteAddress -ListenPort $Port `
    -StopPath $stopRequestPath -OwnerProcessId $ownerId -OwnerStartTicks $ownerTicks
