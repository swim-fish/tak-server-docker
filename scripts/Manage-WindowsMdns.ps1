[CmdletBinding()]
param(
    [ValidateSet('Menu', 'Install', 'Start', 'Stop', 'Test', 'Uninstall')]
    [string]$Action = 'Menu',
    [string]$Address = '192.168.137.1',
    [string]$Hostname = 'takbox.local',
    [int]$MumblePort = 40000,
    [int]$TakPort = 8089,
    [string]$RemoteSubnet = '192.168.137.0/24',
    [string]$TaskName = 'TAK-mDNS-Responder',
    [switch]$RemoveRuntime,
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
    if ($Action -eq 'Install') {
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
        ($_ | Out-String) | Add-Content -LiteralPath $installErrorPath -Encoding UTF8
    }
    Write-Error $_
    exit 1
}

if ($ElevationRequestPath) {
    if (-not (Test-Path -LiteralPath $ElevationRequestPath)) {
        throw "The elevation request file was not found: $ElevationRequestPath"
    }

    $elevationRequest = Import-Clixml -LiteralPath $ElevationRequestPath
    Remove-Item -LiteralPath $ElevationRequestPath -Force -ErrorAction SilentlyContinue
    $Action = [string]$elevationRequest.Action
    $Address = [string]$elevationRequest.Address
    $Hostname = [string]$elevationRequest.Hostname
    $MumblePort = [int]$elevationRequest.MumblePort
    $TakPort = [int]$elevationRequest.TakPort
    $RemoteSubnet = [string]$elevationRequest.RemoteSubnet
    $TaskName = [string]$elevationRequest.TaskName
    $RemoveRuntime = [bool]$elevationRequest.RemoveRuntime
}

if ($Action -eq 'Menu') {
    while ($true) {
        Write-Host ''
        Write-Host 'Windows mDNS 管理'
        Write-Host '1. 安裝／修復並啟動'
        Write-Host '2. 啟動公告'
        Write-Host '3. 停止公告'
        Write-Host '4. 測試公告'
        Write-Host '5. 移除設定與防火牆規則'
        Write-Host '0. 結束'
        $choice = Read-Host '請選擇'
        if ($choice -eq '0') { return }
        $selectedAction = switch ($choice) {
            '1' { 'Install' }
            '2' { 'Start' }
            '3' { 'Stop' }
            '4' { 'Test' }
            '5' { 'Uninstall' }
            default { Write-Warning '無效選項。'; $null }
        }
        if (-not $selectedAction) { continue }
        $removeSelectedRuntime = $false
        if ($selectedAction -eq 'Uninstall') {
            if ((Read-Host '確認停止並移除 mDNS 排程與防火牆規則？輸入 REMOVE') -cne 'REMOVE') {
                Write-Output 'Cancelled.'
                continue
            }
            $removeSelectedRuntime = (Read-Host '同時刪除 runtime/mdns 與紀錄？輸入 Y 確認') -match '^[Yy]$'
        }
        & $PSCommandPath -Action $selectedAction -Address $Address -Hostname $Hostname `
            -MumblePort $MumblePort -TakPort $TakPort -RemoteSubnet $RemoteSubnet `
            -TaskName $TaskName -RemoveRuntime:$removeSelectedRuntime
    }
}

$scheduledTasks = Join-Path $env:SystemRoot 'System32\schtasks.exe'
if ($Action -eq 'Start') {
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw 'mDNS is not installed. Select Install first.'
    }
    & $scheduledTasks /Run /TN $TaskName
    if ($LASTEXITCODE -ne 0) { throw "Could not start scheduled task $TaskName." }
    Start-Sleep -Seconds 3
    & $venvPython $query --config $configPath --timeout-ms 5000
    if ($LASTEXITCODE -ne 0) { throw 'mDNS records did not respond after starting the task.' }
    return
}
if ($Action -eq 'Stop') {
    & $scheduledTasks /End /TN $TaskName
    if ($LASTEXITCODE -ne 0) { throw "Could not stop scheduled task $TaskName." }
    return
}
if ($Action -eq 'Test') {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw 'The mDNS runtime is not installed.'
    }
    & $venvPython -c 'import ifaddr, zeroconf'
    if ($LASTEXITCODE -ne 0) { throw 'The mDNS Python environment is incomplete.' }
    & $venvPython $query --config $configPath --timeout-ms 5000
    if ($LASTEXITCODE -ne 0) { throw 'The expected mDNS records were not found.' }
    return
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if (-not $PSCommandPath) {
        throw 'This script must be executed from a .ps1 file before it can request administrator access.'
    }

    $requestFile = New-TemporaryFile
    [pscustomobject]@{
        Action       = $Action
        Address      = $Address
        Hostname     = $Hostname
        MumblePort   = $MumblePort
        TakPort      = $TakPort
        RemoteSubnet = $RemoteSubnet
        TaskName     = $TaskName
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
        throw "The elevated mDNS $Action failed with exit code $($elevatedProcess.ExitCode)."
    }

    Write-Output "The elevated mDNS $Action completed successfully."
    return
}

if ($Action -eq 'Uninstall') {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
        Stop-ScheduledTask -ErrorAction SilentlyContinue
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
        Unregister-ScheduledTask -Confirm:$false
    Get-NetFirewallRule -Name $firewallInName, $firewallOutName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
    if ($RemoveRuntime -and (Test-Path -LiteralPath $runtimeDir)) {
        $runtimeRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'runtime'))
        $runtimeTarget = [IO.Path]::GetFullPath($runtimeDir)
        if (-not $runtimeTarget.StartsWith($runtimeRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
            $runtimeTarget -ne [IO.Path]::GetFullPath((Join-Path $runtimeRoot 'mdns'))) {
            throw "Unexpected runtime path: $runtimeTarget"
        }
        Remove-Item -LiteralPath $runtimeTarget -Recurse -Force
    }
    Write-Output "Removed $TaskName and its firewall rules."
    return
}

if ($Hostname -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,62}\.local\.?$') {
    throw 'Hostname must be a single valid mDNS label ending in .local.'
}

if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction SilentlyContinue)) {
    throw "Address $Address is not assigned to this Windows host."
}

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    $existingTask | Stop-ScheduledTask -ErrorAction SilentlyContinue
    $existingTask | Unregister-ScheduledTask -Confirm:$false
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
$taskAction = New-ScheduledTaskAction `
    -Execute $venvPython `
    -Argument $arguments `
    -WorkingDirectory $projectRoot
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $identity.Name `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $taskAction `
    -Principal $taskPrincipal `
    -Settings $settings `
    -Description 'Publishes takbox.local and TAK service records on the Windows hotspot interface.' `
    -Force | Out-Null

$registeredTask = Get-ScheduledTask -TaskName $TaskName
if (@($registeredTask.Triggers | Where-Object { $_ }).Count -ne 0) {
    throw 'The mDNS task unexpectedly has an automatic trigger.'
}

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

& $venvPython $query --config $configPath --timeout-ms 5000
if ($LASTEXITCODE -ne 0) {
    throw "The responder was installed, but its service records could not be verified. Review $logPath."
}

Remove-Item -LiteralPath $installErrorPath -Force -ErrorAction SilentlyContinue

Write-Output "Installed $TaskName."
Write-Output 'This task has no automatic trigger. Run -Action Start after reboot.'
Write-Output "Published $Hostname -> $Address."
Write-Output "Runtime configuration: $configPath"
Write-Output "Responder log: $logPath"
