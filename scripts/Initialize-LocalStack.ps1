[CmdletBinding()]
param(
    [string]$ZipPath,
    [string]$ClientName = 'atak-client',
    [string]$ExpectedZipSha256,
    [switch]$CheckOnly,
    [switch]$SkipNetworkSetup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$vendorRoot = Join-Path $projectRoot 'vendor'
$upstreamName = 'takserver-docker-hardened-5.8-RELEASE-84'
$upstreamRoot = Join-Path $vendorRoot $upstreamName
$runtimeRoot = Join-Path $projectRoot 'runtime'
$hotspotAddress = '192.168.137.1'
$hotspotSubnet = '192.168.137.0/24'
$dnsName = 'takbox.local'

function Invoke-Checked {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

function Assert-UpstreamPackage {
    param([string]$Directory)
    foreach ($relative in @(
        'tak/CoreConfig.example.xml',
        'tak/takserver.war',
        'tak/utils/UserManager.jar',
        'docker/Dockerfile.hardened-takserver',
        'docker/Dockerfile.hardened-takserver-db'
    )) {
        $path = Join-Path $Directory $relative
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "The official package is missing $relative at $Directory."
        }
    }
}

function Assert-FreshDeployment {
    if ((Test-Path -LiteralPath $runtimeRoot) -and
        @(Get-ChildItem -LiteralPath $runtimeRoot -Force | Select-Object -First 1).Count -gt 0) {
        throw "Existing runtime data found at $runtimeRoot. This script never resets it."
    }
    foreach ($relative in @(
        'runtime/tak', 'runtime/pki', 'runtime/secrets', 'runtime/mediamtx',
        'runtime/packages', 'runtime/tak-cert-control', 'runtime/share-control'
    )) {
        $path = Join-Path $projectRoot $relative
        if (Test-Path -LiteralPath $path) {
            throw "Existing deployment data found at $path. Use the operations guide; this script never resets it."
        }
    }
    $containers = @(& docker compose ps -a -q 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect existing Compose containers.' }
    if ($containers.Count -gt 0) {
        throw 'Existing Compose containers found. This script is for a new deployment only.'
    }
    $volumes = @(& docker volume ls --quiet --filter 'label=com.docker.compose.project=tak-local' 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect existing Docker volumes.' }
    if ($volumes.Count -gt 0) {
        throw 'Existing tak-local Docker volumes found. This script will not reuse or delete them.'
    }
}

function Assert-Zip {
    param([string]$Path)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $prefix = "$upstreamName/"
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName
            if (-not $name.StartsWith($prefix, [StringComparison]::Ordinal) -or
                $name.Contains('\') -or $name.Contains(':') -or
                @($name.Split('/') | Where-Object { $_ -eq '.' -or $_ -eq '..' }).Count -gt 0) {
                throw "The ZIP contains an unexpected entry: $name"
            }
        }
        if ($archive.Entries.Count -eq 0) { throw 'The official ZIP is empty.' }
    } finally {
        $archive.Dispose()
    }
}

function Wait-ServiceState {
    param([string]$Service, [string]$Expected, [int]$TimeoutSeconds = 600)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $container = (& docker compose ps -q $Service 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $container) {
            $format = if ($Expected -eq 'running') { '{{.State.Status}}' } else {
                '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'
            }
            $state = (& docker inspect --format $format $container 2>$null | Select-Object -First 1)
            if ($LASTEXITCODE -eq 0 -and $state -eq $Expected) { return }
            if ($state -eq 'exited' -or $state -eq 'dead') {
                throw "$Service entered $state. Check docker compose logs $Service."
            }
        }
        Start-Sleep -Seconds 5
    }
    throw "Timed out waiting for $Service to become $Expected. Check docker compose ps and logs."
}

function Install-TakFirewall {
    $script = Join-Path $PSScriptRoot 'Install-TakFirewall.ps1'
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        & $script -LocalAddress $hotspotAddress -RemoteAddress $hotspotSubnet
        return
    }
    $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
        Join-Path $PSHOME 'pwsh.exe'
    } else { Join-Path $PSHOME 'powershell.exe' }
    Write-Output 'Approve Windows UAC to install the TAK firewall rules.'
    $process = Start-Process -FilePath $executable -Verb RunAs -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            ('"{0}"' -f $script), '-LocalAddress', $hotspotAddress,
            '-RemoteAddress', $hotspotSubnet)
    if ($process.ExitCode -ne 0) { throw "TAK firewall setup failed: exit $($process.ExitCode)." }
}

Push-Location $projectRoot
try {
    if ($ClientName -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$') {
        throw 'ClientName must be 2-63 ASCII letters, digits, dots, underscores, or hyphens.'
    }
    foreach ($command in @('docker', 'python', 'openssl', 'keytool')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            throw "$command is not available on PATH. See docs/getting-started.md."
        }
    }
    Invoke-Checked docker @('version', '--format', '{{.Server.Version}}')
    Invoke-Checked docker @('compose', 'version')
    Invoke-Checked python @('-c', 'import cryptography')
    if (-not $SkipNetworkSetup -and -not (Test-Path -LiteralPath 'C:\Python314\python.exe')) {
        throw 'mDNS installation requires C:\Python314\python.exe.'
    }
    $address = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $hotspotAddress -ErrorAction SilentlyContinue |
        Where-Object { $_.AddressState -eq 'Preferred' })
    if ($address.Count -ne 1) {
        throw "Enable the Windows Mobile hotspot first; $hotspotAddress must be assigned to this host."
    }
    $envFile = Join-Path $projectRoot '.env'
    if (Test-Path -LiteralPath $envFile -PathType Leaf) {
        $httpsPort = Get-Content -LiteralPath $envFile | Where-Object {
            $_ -match '^\s*TAK_HTTPS_HOST_PORT\s*='
        } | Select-Object -Last 1
        if ($httpsPort -and ($httpsPort -split '=', 2)[1].Trim().Trim('"', "'") -ne '8443') {
            throw 'The first-time ATAK package requires TAK_HTTPS_HOST_PORT=8443 in .env.'
        }
    }

    Assert-FreshDeployment
    $upstreamReady = Test-Path -LiteralPath $upstreamRoot -PathType Container
    if ($upstreamReady) { Assert-UpstreamPackage $upstreamRoot }
    if ($ZipPath) {
        $ZipPath = (Resolve-Path -LiteralPath $ZipPath -ErrorAction Stop).Path
        if (-not $ZipPath.EndsWith('.zip', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'ZipPath must identify the official .zip file.'
        }
        if ($ExpectedZipSha256) {
            if ($ExpectedZipSha256 -notmatch '^[0-9a-fA-F]{64}$') {
                throw 'ExpectedZipSha256 must contain 64 hexadecimal characters.'
            }
            $actualHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash
            if ($actualHash -ine $ExpectedZipSha256) { throw 'The official ZIP SHA-256 does not match.' }
        }
        Assert-Zip $ZipPath
    } elseif ($ExpectedZipSha256) {
        throw 'ExpectedZipSha256 requires ZipPath.'
    } elseif (-not $upstreamReady) {
        if ($CheckOnly) { throw 'Specify -ZipPath for a new deployment.' }
        $entered = Read-Host 'Official takserver-docker-hardened-5.8-RELEASE-84.zip path'
        if (-not $entered) { throw 'ZipPath is required when vendor is empty.' }
        $ZipPath = (Resolve-Path -LiteralPath $entered -ErrorAction Stop).Path
        Assert-Zip $ZipPath
    }

    if ($CheckOnly) {
        Write-Output 'Preflight passed. No files, containers, firewall rules, or certificates were changed.'
        return
    }

    if (-not $upstreamReady) {
        New-Item -ItemType Directory -Path $vendorRoot -Force | Out-Null
        $stage = Join-Path $vendorRoot ('.extract-' + [Guid]::NewGuid().ToString('N'))
        $vendorFull = [IO.Path]::GetFullPath($vendorRoot)
        $stageFull = [IO.Path]::GetFullPath($stage)
        if ((Split-Path -Parent $stageFull) -ne $vendorFull) {
            throw "Unexpected extraction path: $stageFull"
        }
        try {
            Expand-Archive -LiteralPath $ZipPath -DestinationPath $stageFull -ErrorAction Stop
            $extractedRoot = Join-Path $stageFull $upstreamName
            Assert-UpstreamPackage $extractedRoot
            Move-Item -LiteralPath $extractedRoot -Destination $upstreamRoot -ErrorAction Stop
        } finally {
            if (Test-Path -LiteralPath $stageFull) {
                Remove-Item -LiteralPath $stageFull -Recurse -Force
            }
        }
    }

    Invoke-Checked python @('.\scripts\bootstrap_local.py', '--host', $dnsName,
        '--client-name', $ClientName)
    Invoke-Checked python @('.\scripts\provision_mediamtx.py', '--dns', $dnsName)
    foreach ($relative in @(
        'runtime/tak/CoreConfig.xml', 'runtime/tak/UserAuthenticationFile.xml',
        'runtime/pki/mumble-fullchain.pem', 'runtime/pki/mediamtx-fullchain.pem',
        'runtime/mediamtx/mediamtx.yml', 'runtime/packages/atak/atak-local-test.dpk',
        'runtime/secrets/tak_store_password', 'runtime/secrets/mumble_server_password',
        'runtime/secrets/mumble_superuser_password', 'runtime/secrets/leaf_key_password',
        'runtime/secrets/share_admin_password', 'runtime/secrets/mediamtx_publish_password',
        'runtime/secrets/mediamtx_read_password', 'runtime/secrets/mediamtx_api_password'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relative) -PathType Leaf)) {
            throw "Bootstrap output is missing: $relative"
        }
    }
    Invoke-Checked docker @('compose', 'config', '--quiet')

    if (-not $SkipNetworkSetup) {
        & (Join-Path $PSScriptRoot 'Manage-WindowsMdns.ps1') -Action Install `
            -Address $hotspotAddress -Hostname $dnsName -RemoteSubnet $hotspotSubnet
        Install-TakFirewall
        & (Join-Path $PSScriptRoot 'Install-MediaMtxFirewall.ps1') `
            -LocalAddress $hotspotAddress -RemoteAddress $hotspotSubnet
        $firewallScript = Join-Path $PSScriptRoot 'Install-MumbleFirewall.ps1'
        $executable = if ($PSVersionTable.PSEdition -eq 'Core') {
            Join-Path $PSHOME 'pwsh.exe'
        } else { Join-Path $PSHOME 'powershell.exe' }
        Write-Output 'Opening an interactive Mumble firewall window. Keep it open while Android clients connect.'
        Start-Process -FilePath $executable -WindowStyle Normal -WorkingDirectory $projectRoot `
            -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-File',
                ('"{0}"' -f $firewallScript)) | Out-Null
        $firewallDeadline = (Get-Date).AddSeconds(90)
        while ((Get-Date) -lt $firewallDeadline) {
            if (Get-NetFirewallRule -Name 'TAK-Local-Mumble-Session-*-40000' -ErrorAction SilentlyContinue) {
                break
            }
            Start-Sleep -Seconds 2
        }
        if (-not (Get-NetFirewallRule -Name 'TAK-Local-Mumble-Session-*-40000' -ErrorAction SilentlyContinue)) {
            throw 'Mumble firewall did not become active. Check the interactive window and UAC prompt.'
        }
    }

    Invoke-Checked docker @('compose', 'up', '-d', '--build')
    Wait-ServiceState -Service 'tak-server' -Expected 'running' -TimeoutSeconds 300
    $adminGranted = $false
    for ($attempt = 1; $attempt -le 12; $attempt++) {
        & docker compose exec -T -w /opt/tak tak-server java -jar utils/UserManager.jar `
            certmod -A certs/files/admin.pem
        if ($LASTEXITCODE -eq 0) {
            $adminGranted = $true
            break
        }
        Start-Sleep -Seconds 10
    }
    if (-not $adminGranted) {
        throw 'Could not grant the TAK administrator certificate. Check docker compose logs tak-server.'
    }
    Invoke-Checked docker @('compose', 'restart', 'tak-server')
    Wait-ServiceState -Service 'tak-server' -Expected 'healthy' -TimeoutSeconds 600
    Wait-ServiceState -Service 'mumble' -Expected 'healthy' -TimeoutSeconds 180
    Invoke-Checked python @('.\scripts\provision_mumble_channel.py')

    & (Join-Path $PSScriptRoot 'Manage-TakControlWorkers.ps1') -Action Install
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw 'Windows management workers did not install successfully.'
    }

    Write-Output 'First-time setup completed. Review docker compose ps and import the device-specific ATAK DPK.'
    Write-Output 'The public QR download service is optional: docker compose --profile sharing up -d share-public'
} finally {
    Pop-Location
}
