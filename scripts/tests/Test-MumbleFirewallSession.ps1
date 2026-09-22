# Tests use mocked Windows networking/firewall commands; no system rules are changed.
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot '..\Install-MumbleFirewall.ps1'
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$definitions = ($ast.FindAll({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst]
}, $false) | ForEach-Object { $_.Extent.Text }) -join "`n"
$mocks = @'
function Get-NetIPAddress {
    param($AddressFamily, $ErrorAction)
    $state.Checks++
    if ($state.Missing -or ($state.DropAfter -gt 0 -and $state.Checks -gt $state.DropAfter)) { return }
    [pscustomobject]@{ IPAddress = '192.0.2.1'; AddressState = $state.AddressState; InterfaceIndex = 42; InterfaceAlias = 'Test Hotspot' }
}
function Get-NetIPInterface {
    param($AddressFamily, $InterfaceIndex, $ErrorAction)
    [pscustomobject]@{ ConnectionState = $state.ConnectionState }
}
function Get-NetFirewallRule {
    param($Name, $ErrorAction)
    foreach ($key in @($state.Rules.Keys)) {
        if ($key -like $Name) { [pscustomobject]@{ Name = $key } }
    }
}
function New-NetFirewallRule {
    param($Name, $DisplayName, $Direction, $Action, $Enabled, $Profile, $Protocol,
        $LocalAddress, $LocalPort, $RemoteAddress, $InterfaceAlias, $ErrorAction)
    if ($state.FailUdp -and $Protocol -eq 'UDP') { throw 'Simulated UDP creation failure' }
    if ($LocalAddress -ne '192.0.2.1' -or $RemoteAddress -ne '192.0.2.0/24' -or
        $LocalPort -ne 40000 -or $InterfaceAlias -ne 'Test Hotspot') { throw 'Incorrect rule scope' }
    $state.Rules[$Name] = $true
    $state.Created++
}
function Remove-NetFirewallRule {
    param([Parameter(ValueFromPipeline)]$InputObject)
    process { $state.Rules.Remove($InputObject.Name); $state.Removed++ }
}
'@
. ([scriptblock]::Create($definitions))
. ([scriptblock]::Create($mocks))
function New-TestState {
    [hashtable]::Synchronized(@{
        Rules = [hashtable]::Synchronized(@{ 'TAK-Local-Mumble-TCP-40000' = $true; 'Unrelated' = $true })
        Created = 0; Removed = 0; Checks = 0; DropAfter = 0; Missing = $false; FailUdp = $false
        AddressState = 'Preferred'; ConnectionState = 'Connected'
    })
}
function Assert-Cleaned {
    param($State, [int]$ExpectedCreated)
    if ($State.Created -ne $ExpectedCreated -or $State.Removed -ne $ExpectedCreated -or
        $State.Rules.Count -ne 2 -or -not $State.Rules.ContainsKey('Unrelated') -or
        -not $State.Rules.ContainsKey('TAK-Local-Mumble-TCP-40000')) {
        throw 'Session cleanup or pre-existing rule preservation failed'
    }
}

foreach ($scenario in @('Missing', 'Disconnected', 'Tentative')) {
    $state = New-TestState
    switch ($scenario) {
        Missing { $state.Missing = $true }
        Disconnected { $state.ConnectionState = 'Disconnected' }
        Tentative { $state.AddressState = 'Tentative' }
    }
    $failed = $false
    try { Invoke-MumbleFirewallSession -Address '192.0.2.1' -Subnet '192.0.2.0/24' -ListenPort 40000 }
    catch { $failed = $_.ToString() -like '*not ready*' }
    if (-not $failed) { throw "Expected preflight failure: $scenario" }
    Assert-Cleaned $state 0
    Write-Output "PASS: $scenario interface rejected before rule creation"
}

$state = New-TestState
$state.FailUdp = $true
$failed = $false
try { Invoke-MumbleFirewallSession -Address '192.0.2.1' -Subnet '192.0.2.0/24' -ListenPort 40000 }
catch { $failed = $_.ToString() -like '*Simulated UDP*' }
if (-not $failed) { throw 'Expected simulated creation failure' }
Assert-Cleaned $state 1
Write-Output 'PASS: partial creation rolls back TCP and preserves existing rules'

$state = New-TestState
$state.DropAfter = 1
Invoke-MumbleFirewallSession -Address '192.0.2.1' -Subnet '192.0.2.0/24' -ListenPort 40000
Assert-Cleaned $state 2
Write-Output 'PASS: hotspot loss cleans up both rules'

$state = New-TestState
# An existing file is sufficient to test the cooperative stop signal.
Invoke-MumbleFirewallSession -Address '192.0.2.1' -Subnet '192.0.2.0/24' -ListenPort 40000 -StopPath $PSCommandPath
Assert-Cleaned $state 2
Write-Output 'PASS: parent stop signal cleans up both rules'

$state = New-TestState
$worker = [PowerShell]::Create()
try {
    $body = 'param($state)' + "`n" + $definitions + "`n" + $mocks + "`n" +
        "Invoke-MumbleFirewallSession -Address '192.0.2.1' -Subnet '192.0.2.0/24' -ListenPort 40000"
    $null = $worker.AddScript($body).AddArgument($state)
    $pending = $worker.BeginInvoke()
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ($state.Created -lt 2 -and -not $pending.IsCompleted -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 50
    }
    if ($state.Created -ne 2) { throw "Worker did not start: $($worker.Streams.Error | Out-String)" }
    # Ctrl+C stops a PowerShell pipeline; exercise that cancellation and its finally block.
    $worker.Stop()
    Assert-Cleaned $state 2
    Write-Output 'PASS: pipeline cancellation runs cleanup and preserves existing rules'
} finally { $worker.Dispose() }
