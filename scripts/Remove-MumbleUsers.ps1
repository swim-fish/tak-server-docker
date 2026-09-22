[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$ServerName = 'takbox.local',
    [switch]$ListOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Select-MumbleUsers {
    param(
        [object[]]$Users,
        [scriptblock]$ReadKey = { [Console]::ReadKey($true) },
        [scriptblock]$Render = {
            param($Rows, $Selected, $Cursor)
            Clear-Host
            Write-Host 'Remove Mumble registrations (SuperUser is excluded)'
            Write-Host 'Up/Down: move | Space: toggle | A: all | N: none | Enter: review | Q/Esc: cancel'
            Write-Host "Selected: $($Selected.Count) / $($Rows.Count)"
            $pageSize = [Math]::Max(1, [Math]::Min(12, [Console]::WindowHeight - 7))
            $start = [int][Math]::Floor($Cursor / $pageSize) * $pageSize
            $end = [Math]::Min($Rows.Count, $start + $pageSize)
            for ($i = $start; $i -lt $end; $i++) {
                $row = $Rows[$i]
                $pointer = if ($i -eq $Cursor) { '>' } else { ' ' }
                $mark = if ($Selected.Contains([int]$row.id)) { 'x' } else { ' ' }
                $name = Get-MumbleDisplayName ([string]$row.name)
                Write-Host "$pointer [$mark] ID=$($row.id)  $name  (online sessions: $($row.sessions))"
            }
            Write-Host "Rows $($start + 1)-$end / $($Rows.Count)"
        }
    )
    $rows = @($Users | Where-Object { $_.id -gt 0 } | Sort-Object id)
    if ($rows.Count -eq 0) { return }
    $selected = [Collections.Generic.HashSet[int]]::new()
    $cursor = 0
    while ($true) {
        & $Render $rows $selected $cursor
        $key = & $ReadKey
        switch ([string]$key.Key) {
            'UpArrow' { $cursor = ($cursor + $rows.Count - 1) % $rows.Count }
            'DownArrow' { $cursor = ($cursor + 1) % $rows.Count }
            'Spacebar' {
                $id = [int]$rows[$cursor].id
                if (-not $selected.Add($id)) { [void]$selected.Remove($id) }
            }
            'A' { foreach ($row in $rows) { [void]$selected.Add([int]$row.id) } }
            'N' { $selected.Clear() }
            'Enter' { return @($rows | Where-Object { $selected.Contains([int]$_.id) }) }
            'Escape' { return }
            'Q' { return }
            'C' { if ($key.Modifiers -band [ConsoleModifiers]::Control) { return } }
        }
    }
}

function Get-MumbleDisplayName {
    param([string]$Name)
    # Avoid terminal control characters in remote user names.
    $safe = [regex]::Replace($Name, '[\p{Cc}\p{Cf}]', '?')
    if ($safe.Length -gt 64) { return $safe.Substring(0, 61) + '...' }
    return $safe
}

function Invoke-MumbleUserRemoval {
    if (-not $ListOnly -and ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected)) {
        throw 'Interactive selection requires a terminal. Use Windows Terminal/PowerShell, or -ListOnly for inspection.'
    }
    $project = Split-Path $PSScriptRoot -Parent
    $helper = Join-Path $PSScriptRoot 'manage_mumble_users.py'
    $directory = Join-Path $project 'runtime\mumble-admin'
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $snapshot = Join-Path $directory ('selection-' + [Guid]::NewGuid().ToString('N') + '.json')
    & $Python $helper list --snapshot $snapshot --server-name $ServerName
    if ($LASTEXITCODE -ne 0) { throw 'Unable to load registered users. No users were removed.' }
    $data = Get-Content -LiteralPath $snapshot -Raw -Encoding utf8 | ConvertFrom-Json
    $users = @($data.users)
    if ($ListOnly) {
        $users | Select-Object id, @{Name='Name'; Expression={ Get-MumbleDisplayName $_.name }}, sessions | Format-Table
        return
    }
    if ($users.Count -eq 0) { Write-Host 'No registered users other than SuperUser.'; return }
    $chosen = @(Select-MumbleUsers -Users $users)
    if ($chosen.Count -eq 0) { Write-Host 'Cancelled or no users selected. No users were removed.'; return }
    Write-Host "`nSelected registrations:"
    foreach ($user in $chosen) { Write-Host "  ID=$($user.id)  $(Get-MumbleDisplayName $user.name)" }
    Write-Host 'A verified database backup will be created before removal. Selected online users will be disconnected.'
    Write-Host 'Client settings, server certificates, channels and SuperUser will be preserved.'
    if ((Read-Host 'Type DELETE to confirm, or anything else to cancel') -cne 'DELETE') {
        Write-Host 'Cancelled. No users were removed.'
        return
    }
    $arguments = @($helper, 'apply', '--snapshot', $snapshot, '--server-name', $ServerName, '--ids')
    $arguments += @($chosen | ForEach-Object { [string]$_.id })
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Removal did not complete. Review the reported backup/journal before retrying.' }
}

# Dot-sourcing exposes the selector for deterministic tests without connecting.
if ($MyInvocation.InvocationName -ne '.') { Invoke-MumbleUserRemoval }
