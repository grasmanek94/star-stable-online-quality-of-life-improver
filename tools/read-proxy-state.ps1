# Read-only: no activation, code writes, DLL injection or process suspension.
param([string]$MetadataPath)
$ErrorActionPreference='Stop'
if([IntPtr]::Size -ne 8){throw 'Use 64-bit PowerShell for the x64 client.'}
if(-not $MetadataPath){
 $MetadataPath=Join-Path $PSScriptRoot 'validation/proxy-symbols.json'
 if(-not(Test-Path -LiteralPath $MetadataPath)){$MetadataPath=Join-Path $PSScriptRoot 'build/proxy-symbols.json'}
}
$meta=Get-Content -Raw -LiteralPath $MetadataPath | ConvertFrom-Json
$game=Get-Process -Name SSOClient | Select-Object -First 1
$clientPath=$game.MainModule.FileName
$expected=Join-Path ([IO.Path]::GetDirectoryName($clientPath)) 'opengl32.dll'
$proxy=@($game.Modules | Where-Object {$_.FileName -ieq $expected})
if($proxy.Count -ne 1){throw 'The application-directory OpenGL proxy is not loaded in this SSOClient process.'}
if((Get-FileHash -LiteralPath $expected -Algorithm SHA256).Hash -ine $meta.dll_sha256){throw 'DLL hash differs from this metadata; regenerate symbols before reading private offsets.'}
if(-not('SsoProxyStateRead' -as [type])){
 Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class SsoProxyStateRead {
 [DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr OpenProcess(uint rights,bool inherit,uint pid);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr h,IntPtr a,byte[] b,UIntPtr n,out UIntPtr got);
 public static byte[] Read(IntPtr h,long a,int n){var b=new byte[n];UIntPtr got;if(!ReadProcessMemory(h,new IntPtr(a),b,new UIntPtr((uint)n),out got)||got.ToUInt64()!=(ulong)n)throw new Exception("ReadProcessMemory failed");return b;}
}
'@
}
$handle=[SsoProxyStateRead]::OpenProcess(0x410,$false,[uint32]$game.Id)
if($handle -eq [IntPtr]::Zero){throw 'Cannot open process with query/read rights.'}
try{
 function ReadProxyBytes([long]$at,[int]$n){return [SsoProxyStateRead]::Read($handle,$at,$n)}
 function ParseProxyHex([string]$s){return [Convert]::ToInt64($s.Substring(2),16)}
 function ReadProxyUInt32([long]$at){return [BitConverter]::ToUInt32((ReadProxyBytes $at 4),0)}
 $base=$game.MainModule.BaseAddress.ToInt64();$dllBase=$proxy[0].BaseAddress.ToInt64()
 $nt=$dllBase+(ReadProxyUInt32 ($dllBase+0x3C))
 if((ReadProxyUInt32 ($nt+8)) -ne (ParseProxyHex $meta.dll_pe_timestamp) -or (ReadProxyUInt32 ($nt+24+56)) -ne (ParseProxyHex $meta.dll_image_size)){throw 'Loaded DLL headers do not match the symbol metadata.'}
 $cfgAddress=$dllBase+(ParseProxyHex $meta.symbols.g_config.rva);$cfg=ReadProxyBytes $cfgAddress 344
 $prepared=[BitConverter]::ToInt64($cfg,64)
 if($prepared -ne 0 -and $prepared -ne $base){throw 'Config image pointer does not match the running client.'}
 $categories=@();for($i=0;$i -lt 11;$i++){$categories+=[ordered]@{Name=$meta.categories[$i];Hide=[int]$cfg[16+$i];NativeHideCalls=[BitConverter]::ToUInt64($cfg,256+8*$i)}}
 $gameNt=$base+(ReadProxyUInt32 ($base+0x3C));$known=(ReadProxyUInt32 ($gameNt+8)) -eq 0x6AEB5BD3 -and (ReadProxyUInt32 ($gameNt+24+56)) -eq 0x014AF000
 $hooks=@()
 if($known){foreach($spec in $meta.hooks){
  $at=$base+(ParseProxyHex $spec.patch_rva);$b=ReadProxyBytes $at 5;$target=if($b[0] -eq 0xE8){$at+5+[BitConverter]::ToInt32($b,1)}else{[long]0}
  $owned=$false
  if($target -gt 0x10000 -and $target -ne ($base+(ParseProxyHex $spec.target_rva))){
   try{$t=ReadProxyBytes $target 14;$owned=$t[0] -eq 0xFF -and $t[1] -eq 0x25 -and [BitConverter]::ToUInt32($t,2) -eq 0 -and [BitConverter]::ToInt64($t,6) -eq ($dllBase+(ParseProxyHex $spec.wrapper_rva))}catch{}
  }
  $window=ReadProxyBytes ($base+(ParseProxyHex $spec.match_rva)) $spec.original_window.Length;$context=$true
  for($j=0;$j -lt $window.Length;$j++){if($j -ge $spec.patch_offset -and $j -lt ($spec.patch_offset+5)){continue};if($window[$j] -ne $spec.original_window[$j]){$context=$false}}
  $hooks+=[ordered]@{Name=$spec.name;OwnedByProxy=$owned;NativeOriginalTarget=($target -eq ($base+(ParseProxyHex $spec.target_rva)));SurroundingContextMatches=$context;Target=('0x{0:X}'-f $target)}
 }}
 [ordered]@{CapturedUtc=(Get-Date).ToUniversalTime().ToString('o');Pid=$game.Id;ProxyPath=$expected;ProxyBase=('0x{0:X}'-f $dllBase);ConfigAddress=('0x{0:X}'-f $cfgAddress);Prepared=($prepared -ne 0);Active=[int]$cfg[0];CacheCapacity=[BitConverter]::ToUInt32($cfg,96);Epoch=[BitConverter]::ToUInt32($cfg,100);KnownGameLayout=$known;Categories=$categories;Hooks=$hooks} | ConvertTo-Json -Depth 8
}finally{[void][SsoProxyStateRead]::CloseHandle($handle)}
