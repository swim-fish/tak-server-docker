$address = '192.168.137.1'
$subnet = '192.168.137.0/24'
    $dotenv = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
    if (Test-Path -LiteralPath $dotenv) {
        foreach ($line in Get-Content -LiteralPath $dotenv) {
            if ($line -match '^\s*TAK_BIND_IP\s*=\s*["'']?([^\s"'']+)["'']?\s*$') {
                $address = $Matches[1]
            } elseif ($line -match '^\s*TAK_ALLOWED_SUBNET\s*=\s*["'']?([^\s"'']+)["'']?\s*$') {
                $subnet = $Matches[1]
            }
        }
    }
    if ($env:TAK_BIND_IP) { $address = $env:TAK_BIND_IP }
    if ($env:TAK_ALLOWED_SUBNET) { $subnet = $env:TAK_ALLOWED_SUBNET }
    $parsed = $null
    if (-not [Net.IPAddress]::TryParse($address, [ref]$parsed) -or
        $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        $address -eq '0.0.0.0' -or $address.StartsWith('127.')) {
        throw 'TAK_BIND_IP must be a local IPv4 address.'
    }
    $parts = $subnet.Split('/')
    $network = $null
    if ($parts.Count -ne 2 -or -not [Net.IPAddress]::TryParse($parts[0], [ref]$network) -or
        $network.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        $parts[1] -notmatch '^\d{1,2}$' -or [int]$parts[1] -gt 32) {
        throw 'TAK_ALLOWED_SUBNET must be an IPv4 CIDR.'
    }
    $prefix = [int]$parts[1]
    $addressBytes = $parsed.GetAddressBytes()
    $networkBytes = $network.GetAddressBytes()
    for ($index = 0; $index -lt 4; $index++) {
        $bits = [Math]::Min(8, [Math]::Max(0, $prefix - 8 * $index))
        $mask = if ($bits -eq 0) { 0 } else { (255 -shl (8 - $bits)) -band 255 }
        if (($addressBytes[$index] -band $mask) -ne ($networkBytes[$index] -band $mask)) {
            throw 'TAK_BIND_IP must be inside TAK_ALLOWED_SUBNET.'
        }
    }
[pscustomobject]@{ Address = $address; Subnet = $subnet }
