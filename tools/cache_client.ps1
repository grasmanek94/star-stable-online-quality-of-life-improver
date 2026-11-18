# Local, versioned analysis backup. Never runs, patches or uploads the client.
param(
    [Parameter(Mandatory=$true)][string]$ClientPath,
    [string]$CacheRoot=(Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Codex/cache/SSO-FPS/clients')
)
$ErrorActionPreference='Stop'
$resolved=(Resolve-Path -LiteralPath $ClientPath).ProviderPath
if([IO.Path]::GetFileName($resolved) -ine 'SSOClient.exe'){throw 'Select the actual SSOClient.exe file.'}
$cache=[IO.Path]::GetFullPath($CacheRoot)
$repo=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\','/')
if($cache -eq $repo -or $cache.StartsWith($repo+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Keep client backups outside the source repository.'
}
# Deny writers/deletion during hashing and copying so an updater cannot race us.
$inputStream=[IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
try{
    if($inputStream.Length -lt 4096){throw 'Client file is too short.'}
    $reader=[IO.BinaryReader]::new($inputStream,[Text.Encoding]::ASCII,$true)
    try{
        if($reader.ReadUInt16() -ne 0x5A4D){throw 'Expected a Windows executable.'}
        $inputStream.Position=0x3C;$pe=$reader.ReadInt32()
        if($pe -lt 0x40 -or $pe -gt $inputStream.Length-264){throw 'Invalid PE header offset.'}
        $inputStream.Position=$pe
        if($reader.ReadUInt32() -ne 0x4550 -or $reader.ReadUInt16() -ne 0x8664){throw 'Expected a Windows x64 PE image.'}
        $inputStream.Position=$pe+8;$stamp=$reader.ReadUInt32()
        $inputStream.Position=$pe+24
        if($reader.ReadUInt16() -ne 0x20B){throw 'Expected a PE32+ optional header.'}
        $inputStream.Position=$pe+24+56;$imageSize=$reader.ReadUInt32()
    }finally{$reader.Dispose()}
    $info=[Diagnostics.FileVersionInfo]::GetVersionInfo($resolved)
    $version=if($info.FileVersion){$info.FileVersion}else{'unversioned'}
    $folder=([regex]::Replace($version,'[^A-Za-z0-9._-]','_'))
    if($folder.Length -gt 80){$folder=$folder.Substring(0,80)}
    $hasher=[Security.Cryptography.SHA256]::Create()
    try{
        $inputStream.Position=0
        $digest=([BitConverter]::ToString($hasher.ComputeHash($inputStream))).Replace('-','').ToLowerInvariant()
        $targetDir=Join-Path (Join-Path $cache $folder) $digest
        [IO.Directory]::CreateDirectory($targetDir) | Out-Null
        $target=Join-Path $targetDir 'SSOClient.exe'
        $created=$false
        if(Test-Path -LiteralPath $target){
            $existing=[IO.File]::OpenRead($target)
            try{$existingHash=([BitConverter]::ToString($hasher.ComputeHash($existing))).Replace('-','').ToLowerInvariant()}
            finally{$existing.Dispose()}
            if($existingHash -ne $digest){throw 'Existing archive is damaged; refusing to overwrite it.'}
        }else{
            $output=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try{$inputStream.Position=0;$inputStream.CopyTo($output)}finally{$output.Dispose()}
            $verify=[IO.File]::OpenRead($target)
            try{$copiedHash=([BitConverter]::ToString($hasher.ComputeHash($verify))).Replace('-','').ToLowerInvariant()}
            finally{$verify.Dispose()}
            if($copiedHash -ne $digest){throw 'Backup hash verification failed.'}
            $created=$true
        }
    }finally{$hasher.Dispose()}
    $utf8=[Text.UTF8Encoding]::new($false)
    $manifest=Join-Path $targetDir 'manifest.json'
    if(-not(Test-Path -LiteralPath $manifest)){
        $record=[ordered]@{schema=1;file='SSOClient.exe';file_version=$version;product_version=$info.ProductVersion;
            sha256=$digest;file_size=$inputStream.Length;pe_timestamp=('0x{0:X8}' -f $stamp);
            image_size=('0x{0:X}' -f $imageSize);source_path=$resolved;archived_utc=[DateTime]::UtcNow.ToString('o');
            purpose='Local offline update comparison; never execute or redistribute this cached client'}
        [IO.File]::WriteAllText($manifest,($record | ConvertTo-Json -Depth 4)+[Environment]::NewLine,$utf8)
    }
    $ignore=Join-Path $cache '.gitignore'
    if(-not(Test-Path -LiteralPath $ignore)){[IO.File]::WriteAllText($ignore,"*`n!.gitignore`n",$utf8)}
    [ordered]@{created=$created;version=$version;sha256=$digest;backup=$target;manifest=$manifest} | ConvertTo-Json
}finally{$inputStream.Dispose()}
