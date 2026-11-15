# Read version resources without loading or executing the inspected binaries.
param(
    [Parameter(Mandatory=$true)][string]$BuildDirectory,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
if (-not ('SsoPeVersionStrings' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class SsoPeVersionStrings {
    [DllImport("version.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern uint GetFileVersionInfoSizeW(string path, out uint unused);
    [DllImport("version.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool GetFileVersionInfoW(string path, uint unused, uint size, IntPtr data);
    [DllImport("version.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern bool VerQueryValueW(IntPtr data, string key, out IntPtr value, out uint length);
    public static string Read(string path, string key) {
        uint unused; uint size=GetFileVersionInfoSizeW(path,out unused);
        if(size==0)throw new Win32Exception(Marshal.GetLastWin32Error());
        IntPtr data=Marshal.AllocHGlobal(checked((int)size));
        try {
            if(!GetFileVersionInfoW(path,0,size,data))throw new Win32Exception(Marshal.GetLastWin32Error());
            IntPtr value; uint length;
            if(!VerQueryValueW(data,@"\StringFileInfo\040904b0\"+key,out value,out length))return null;
            return Marshal.PtrToStringUni(value);
        } finally { Marshal.FreeHGlobal(data); }
    }
}
'@
}
$product = 'Star Stable Online Frame Rate / Performance Fixer'
$repository = 'https://github.com/grasmanek94/star-stable-online-quality-of-life-improver'
$author = 'grasmanek94'
$year = [Math]::Max(2026,[DateTime]::UtcNow.Year)
$projectRoot = Split-Path -Parent $PSScriptRoot
$cmake = [IO.File]::ReadAllText((Join-Path $projectRoot 'CMakeLists.txt'))
$match = [regex]::Match($cmake,'project\(SSOVisibility\s+VERSION\s+(\d+\.\d+\.\d+(?:\.\d+)?)')
if (-not $match.Success) { throw 'Cannot determine project version for PE verification.' }
$version = [version]$match.Groups[1].Value
$revision = [Math]::Max(0,$version.Revision)
$expectedVersion = '{0}.{1}.{2}.{3}' -f $version.Major,$version.Minor,$version.Build,$revision
$folder = [IO.Path]::GetFullPath($BuildDirectory)
$images = @(Get-ChildItem -LiteralPath $folder -File | Where-Object {$_.Extension -in '.exe','.dll','.asi','.addon64'})
if (-not $images.Count) { throw "No PE outputs found in $folder" }
$records = @()
foreach ($file in $images) {
    $info = [Diagnostics.FileVersionInfo]::GetVersionInfo($file.FullName)
    $values = [ordered]@{
        FileDescription=$info.FileDescription; ProductName=$info.ProductName; CompanyName=$info.CompanyName
        Author=[SsoPeVersionStrings]::Read($file.FullName,'Author')
        Authors=[SsoPeVersionStrings]::Read($file.FullName,'Authors')
        RepositoryURL=[SsoPeVersionStrings]::Read($file.FullName,'RepositoryURL')
        LegalCopyright=$info.LegalCopyright; OriginalFilename=$info.OriginalFilename
        InternalName=$info.InternalName; FileVersion=$info.FileVersion; ProductVersion=$info.ProductVersion
    }
    $expected = [ordered]@{
        FileDescription="$product - $repository"; ProductName=$product; CompanyName=$author
        Author=$author; Authors=$author; RepositoryURL=$repository
        LegalCopyright="Copyright (c) 2026-$year $author"; OriginalFilename=$file.Name
        InternalName=$file.BaseName; FileVersion=$expectedVersion; ProductVersion=$expectedVersion
    }
    foreach ($key in $expected.Keys) {
        if ($values[$key] -cne $expected[$key]) { throw "PE metadata mismatch in $($file.Name): $key" }
    }
    $debugExpected = (Split-Path -Leaf $folder) -eq 'Debug'
    if ($info.IsDebug -ne $debugExpected) { throw "PE debug flag mismatch in $($file.Name)" }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $digest = ([BitConverter]::ToString($hasher.ComputeHash([IO.File]::ReadAllBytes($file.FullName)))).Replace('-','').ToLowerInvariant() }
    finally { $hasher.Dispose() }
    $records += [ordered]@{File=$file.Name;Sha256=$digest;Debug=$info.IsDebug;VersionInfo=$values}
}
$result = [ordered]@{CheckedImages=$records.Count;BuildYear=$year;Files=$records}
if ($OutputPath) {
    $destination = [IO.Path]::GetFullPath($OutputPath)
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
    [IO.File]::WriteAllText($destination,($result | ConvertTo-Json -Depth 6)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
} else { $result | ConvertTo-Json -Depth 6 }
Write-Host "PE_METADATA_PASS $($records.Count) images; version $expectedVersion; copyright 2026-$year."
