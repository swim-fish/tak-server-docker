$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Remove-MumbleUsers.ps1')
$users = @(
    [pscustomobject]@{ id=0; name='SuperUser'; sessions=1 }
    [pscustomobject]@{ id=1; name='First'; sessions=0 }
    [pscustomobject]@{ id=2; name='Second'; sessions=1 }
    [pscustomobject]@{ id=3; name='Third'; sessions=0 }
)
function Assert-Selection {
    param([string[]]$Keys, [string]$Expected)
    $queue = [Collections.Generic.Queue[string]]::new()
    foreach ($key in $Keys) { $queue.Enqueue($key) }
    $read = {
        if ($queue.Count -eq 0) { throw 'Selector requested an unexpected extra key.' }
        [pscustomobject]@{ Key=$queue.Dequeue(); Modifiers=[ConsoleModifiers]::Control }
    }.GetNewClosure()
    $result = @(Select-MumbleUsers -Users $users -ReadKey $read -Render {})
    $actual = ($result | ForEach-Object { $_.id }) -join ','
    if ($actual -ne $Expected) { throw "Selection mismatch: expected '$Expected', got '$actual'." }
}
Assert-Selection -Keys @('Spacebar','DownArrow','DownArrow','Spacebar','Enter') -Expected '1,3'
Assert-Selection -Keys @('A','Enter') -Expected '1,2,3'
Assert-Selection -Keys @('A','N','Enter') -Expected ''
Assert-Selection -Keys @('Spacebar','Spacebar','Enter') -Expected ''
Assert-Selection -Keys @('UpArrow','Spacebar','Enter') -Expected '3'
Assert-Selection -Keys @('UpArrow','DownArrow','Spacebar','Enter') -Expected '1'
foreach ($cancel in @('Escape','Q','C')) { Assert-Selection -Keys @('A',$cancel) -Expected '' }
$empty = @(Select-MumbleUsers -Users @($users[0]) -ReadKey { throw 'Must not read keys for an empty list.' } -Render {})
if ($empty.Count) { throw 'SuperUser must never be selectable.' }
if ((Get-MumbleDisplayName "Name$([char]27)[31m") -match [char]27) { throw 'Terminal escape was not sanitized.' }
Write-Host 'Passed: multi-select, all, none, toggle, navigation, cancellation, empty list, SuperUser exclusion and display sanitization.'
