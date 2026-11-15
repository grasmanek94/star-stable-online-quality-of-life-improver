param(
    [Parameter(Mandatory=$true)][string]$DllPath,
    [Parameter(Mandatory=$true)][string]$MapPath,
    [Parameter(Mandatory=$true)][string]$SitesPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$raw = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $DllPath).Path)
$nt = [BitConverter]::ToInt32($raw, 60)
if ([BitConverter]::ToUInt16($raw, $nt + 4) -ne 0x8664) { throw 'Expected an x64 PE image.' }
$opt = $nt + 24
$base = [BitConverter]::ToUInt64($raw, $opt + 24)
$imageSize = [BitConverter]::ToUInt32($raw, $opt + 56)
$symbols = @{}
$map = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $MapPath).Path)
foreach ($match in [regex]::Matches($map, '(?m)^\s+[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+(\S+)\s+([0-9A-Fa-f]{16})\s')) {
    $symbols[$match.Groups[1].Value] = [Convert]::ToUInt64($match.Groups[2].Value, 16) - $base
}
$selected = @('g_config','g_originals','g_glFunctions','ProxyInitialize','ProxyResolve','ProxyHideActor','ProxyHideVisual','ProxyHideFlag')
$selected += @(0..17 | ForEach-Object { 'HideHook_' + $_ })
$symbolInfo = [ordered]@{}
foreach ($name in $selected) {
    if (-not $symbols.ContainsKey($name) -or $symbols[$name] -ge $imageSize) { throw "Missing/out-of-range link-map symbol: $name" }
    $symbolInfo[$name] = [ordered]@{rva=('0x{0:x}' -f $symbols[$name]); preferred_va=('0x{0:x}' -f ($base + $symbols[$name]))}
}
if ($symbols['g_config'] -gt $imageSize - 344) { throw 'Config extends outside the image.' }
$sites = Get-Content -Raw -LiteralPath $SitesPath | ConvertFrom-Json
$hooks = @(); $index = 0
foreach ($property in $sites.PSObject.Properties) {
    $site = $property.Value
    $window = @($site.window.Split(' ', [StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { [Convert]::ToInt32($_, 16) })
    $hooks += [ordered]@{name=$property.Name; match_rva=$site.rva; patch_rva=$site.patch_rva; patch_offset=$site.patch_offset; target_rva=$site.target_rva; wrapper_rva=('0x{0:x}' -f $symbols['HideHook_' + $index]); original_window=$window}
    $index++
}
if ($hooks.Count -ne 18) { throw 'Hook count drift: update metadata and runtime together.' }
$hasher = [Security.Cryptography.SHA256]::Create()
try { $digest = ([BitConverter]::ToString($hasher.ComputeHash($raw))).Replace('-', '').ToLowerInvariant() }
finally { $hasher.Dispose() }
$metadata = [ordered]@{
    dll_sha256=$digest
    preferred_base=('0x{0:x}' -f $base)
    dll_pe_timestamp=('0x{0:x}' -f [BitConverter]::ToUInt32($raw, $nt + 8))
    dll_image_size=('0x{0:x}' -f $imageSize)
    config_size=344
    symbols=$symbolInfo
    categories=@('Player horses','Player characters','Player pets','NPC animals','NPC actors / fallback','NPC horses','Standalone riderless horses','Sale / display horses','Coins / collectibles','Quest markers','NPC floating text')
    hooks=$hooks
}
$destination = [IO.Path]::GetFullPath($OutputPath)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($destination, ($metadata | ConvertTo-Json -Depth 12) + [Environment]::NewLine, $utf8)
Write-Host "Metadata: $destination"
