param(
    [Parameter(Mandatory=$true)][string]$DllPath,
    [Parameter(Mandatory=$true)][string]$MapPath,
    [Parameter(Mandatory=$true)][string]$SitesPath,
    [Parameter(Mandatory=$true)][string]$LayoutPath,
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
$layout=Get-Content -Raw -LiteralPath $LayoutPath | ConvertFrom-Json
$selected = @('g_config','g_originals','g_patchSites','ProxyHideActor','ProxyHideVisual','ProxyHideFlag','ProxyHideParticles','g_particleChildren')
$selected += @(0..($layout.hook_count-1) | ForEach-Object { 'HideHook_' + $_ })
foreach($optional in @('g_glFunctions','ProxyInitialize','ProxyResolve','g_currentPreset')){if($symbols.ContainsKey($optional)){$selected+=$optional}}
$symbolInfo = [ordered]@{}
foreach ($name in $selected) {
    if (-not $symbols.ContainsKey($name) -or $symbols[$name] -ge $imageSize) { throw "Missing/out-of-range link-map symbol: $name" }
    $symbolInfo[$name] = [ordered]@{rva=('0x{0:x}' -f $symbols[$name]); preferred_va=('0x{0:x}' -f ($base + $symbols[$name]))}
}
if ($symbols['g_config'] -gt $imageSize - $layout.config_size) { throw 'Config extends outside the image.' }
$sites = Get-Content -Raw -LiteralPath $SitesPath | ConvertFrom-Json
$hooks = @(); $index = 0
foreach ($property in $sites.PSObject.Properties) {
    $site = $property.Value
    $window = @($site.window.Split(' ', [StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { [Convert]::ToInt32($_, 16) })
    $patternMask=@($site.pattern.Split(' ',[StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object {if($_ -eq '??'){0}else{255}})
    $hooks += [ordered]@{name=$property.Name; match_rva=$site.rva; patch_rva=$site.patch_rva; patch_offset=$site.patch_offset; target_rva=$site.target_rva; wrapper_rva=('0x{0:x}' -f $symbols['HideHook_' + $index]); kind=$(if($site.kind){$site.kind}else{'call'}); original_window=$window; pattern_mask=$patternMask}
    $index++
}
if ($hooks.Count -ne $layout.hook_count) { throw 'Hook count drift: update metadata and runtime together.' }
$hasher = [Security.Cryptography.SHA256]::Create()
try { $digest = ([BitConverter]::ToString($hasher.ComputeHash($raw))).Replace('-', '').ToLowerInvariant() }
finally { $hasher.Dispose() }
$metadata = [ordered]@{
    dll_sha256=$digest
    preferred_base=('0x{0:x}' -f $base)
    dll_pe_timestamp=('0x{0:x}' -f [BitConverter]::ToUInt32($raw, $nt + 8))
    dll_image_size=('0x{0:x}' -f $imageSize)
    config_size=$layout.config_size
    module_name=[IO.Path]::GetFileName($DllPath)
    protect_gameplay_offset=$layout.protect_gameplay_offset
    symbols=$symbolInfo
    categories=@($layout.categories)
    hooks=$hooks
}
$destination = [IO.Path]::GetFullPath($OutputPath)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($destination, ($metadata | ConvertTo-Json -Depth 12) + [Environment]::NewLine, $utf8)
Write-Host "Metadata: $destination"
