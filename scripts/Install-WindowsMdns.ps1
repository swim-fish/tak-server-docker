[CmdletBinding()]
param(
    [string]$Address = '192.168.137.1',
    [string]$Hostname = 'takbox.local',
    [int]$MumblePort = 40000,
    [int]$TakPort = 8089,
    [string]$RemoteSubnet = '192.168.137.0/24',
    [string]$TaskName = 'TAK-mDNS-Responder',
    [string]$ElevationRequestPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $projectRoot 'mdns\requirements.txt'
$responder = Join-Path $projectRoot 'mdns\responder.py'
$query = Join-Path $projectRoot 'mdns\query.py'
$runtimeDir = Join-Path $projectRoot 'runtime\mdns'
$venvDir = Join-Path $runtimeDir '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$configPath = Join-Path $runtimeDir 'config.json'
$logPath = Join-Path $runtimeDir 'responder.log'
$installErrorPath = Join-Path $runtimeDir 'install-error.log'
$firewallInName = 'TAK-mDNS-Responder-In'
$firewallOutName = 'TAK-mDNS-Responder-Out'

trap {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    ($_ | Out-String) | Set-Content -LiteralPath $installErrorPath -Encoding UTF8
    Write-Error $_
    exit 1
}

if ($ElevationRequestPath) {
    if (-not (Test-Path -LiteralPath $ElevationRequestPath)) {
        throw "The elevation request file was not found: $ElevationRequestPath"
    }

    $elevationRequest = Import-Clixml -LiteralPath $ElevationRequestPath
    Remove-Item -LiteralPath $ElevationRequestPath -Force -ErrorAction SilentlyContinue
    $Address = [string]$elevationRequest.Address
    $Hostname = [string]$elevationRequest.Hostname
    $MumblePort = [int]$elevationRequest.MumblePort
    $TakPort = [int]$elevationRequest.TakPort
    $RemoteSubnet = [string]$elevationRequest.RemoteSubnet
    $TaskName = [string]$elevationRequest.TaskName
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if (-not $PSCommandPath) {
        throw 'This script must be executed from a .ps1 file before it can request administrator access.'
    }

    $requestFile = New-TemporaryFile
    [pscustomobject]@{
        Address      = $Address
        Hostname     = $Hostname
        MumblePort   = $MumblePort
        TakPort      = $TakPort
        RemoteSubnet = $RemoteSubnet
        TaskName     = $TaskName
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
        throw "The elevated mDNS installation failed with exit code $($elevatedProcess.ExitCode)."
    }

    Write-Output 'The elevated mDNS installation completed successfully.'
    return
}

if ($Hostname -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,62}\.local\.?$') {
    throw 'Hostname must be a single valid mDNS label ending in .local.'
}

if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction SilentlyContinue)) {
    throw "Address $Address is not assigned to this Windows host."
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$pythonInterpreter = 'C:\Python314\python.exe'
if (-not (Test-Path -LiteralPath $pythonInterpreter)) {
    throw "Python 3.14 was not found at $pythonInterpreter."
}

$venvNeedsRebuild = -not (Test-Path -LiteralPath $venvPython)
if (-not $venvNeedsRebuild) {
    & $venvPython -c 'import pip' *> $null
    $venvNeedsRebuild = $LASTEXITCODE -ne 0
}

if ($venvNeedsRebuild) {
    $runtimeFullPath = [IO.Path]::GetFullPath($runtimeDir)
    $venvFullPath = [IO.Path]::GetFullPath($venvDir)
    if ((Split-Path -Parent $venvFullPath) -ne $runtimeFullPath) {
        throw "Refusing to rebuild an unexpected virtual environment path: $venvFullPath"
    }

    & $pythonInterpreter -m venv --clear $venvFullPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create or repair the Python virtual environment.'
    }
}

& $venvPython -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to bootstrap pip in the mDNS virtual environment.'
}

& $venvPython -m pip install --disable-pip-version-check --requirement $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install the mDNS responder dependencies.'
}

& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) {
    throw 'The mDNS responder dependency check failed.'
}

& $venvPython -c 'import ifaddr, zeroconf'
if ($LASTEXITCODE -ne 0) {
    throw 'The mDNS responder dependencies could not be imported.'
}

$config = [ordered]@{
    address  = $Address
    hostname = $Hostname.TrimEnd('.').ToLowerInvariant()
    services = @(
        [ordered]@{
            type       = '_mumble._tcp.local.'
            name       = 'ATAK Voice'
            port       = $MumblePort
            properties = [ordered]@{ tls = 'true' }
        },
        [ordered]@{
            type       = '_tak-cot._tcp.local.'
            name       = 'TAK CoT TLS'
            port       = $TakPort
            properties = [ordered]@{ tls = 'true' }
        }
    )
}

$utf8WithoutBom = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText(
    $configPath,
    ($config | ConvertTo-Json -Depth 8),
    $utf8WithoutBom
)

Get-NetFirewallRule -Name $firewallInName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
Get-NetFirewallRule -Name $firewallOutName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

New-NetFirewallRule `
    -Name $firewallInName `
    -DisplayName 'TAK mDNS Responder (Inbound)' `
    -Direction Inbound `
    -Action Allow `
    -Protocol UDP `
    -LocalAddress $Address `
    -LocalPort 5353 `
    -RemoteAddress $RemoteSubnet `
    -Program $venvPython `
    -Profile Any | Out-Null

New-NetFirewallRule `
    -Name $firewallOutName `
    -DisplayName 'TAK mDNS Responder (Outbound)' `
    -Direction Outbound `
    -Action Allow `
    -Protocol UDP `
    -LocalAddress $Address `
    -LocalPort 5353 `
    -RemoteAddress $RemoteSubnet, '224.0.0.251' `
    -Program $venvPython `
    -Profile Any | Out-Null

$arguments = '"{0}" --config "{1}" --log-file "{2}"' -f `
    $responder, $configPath, $logPath
$action = New-ScheduledTaskAction `
    -Execute $venvPython `
    -Argument $arguments `
    -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $identity.Name `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Stop-ScheduledTask -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $taskPrincipal `
    -Settings $settings `
    -Description 'Publishes takbox.local and TAK service records on the Windows hotspot interface.' `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

& $venvPython $query --config $configPath --timeout-ms 5000
if ($LASTEXITCODE -ne 0) {
    throw "The responder was installed, but its service records could not be verified. Review $logPath."
}

Remove-Item -LiteralPath $installErrorPath -Force -ErrorAction SilentlyContinue

Write-Output "Installed $TaskName."
Write-Output "Published $Hostname -> $Address."
Write-Output "Runtime configuration: $configPath"
Write-Output "Responder log: $logPath"
