param(
    [ValidateSet('Release','Debug','RelWithDebInfo')][string]$Configuration = 'Release',
    [ValidateSet('Auto','vs2026-x64','vs2022-x64')][string]$Preset = 'Auto',
    [ValidateSet('PROXY','RESHADE','ASI','PLUGIN')][string]$Loader = 'PROXY',
    [switch]$SkipTests,
    [switch]$Package,
    [switch]$AsmTests
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) {
    throw 'Install Visual Studio 2022/2026 or Build Tools with Desktop development with C++, the x64 tools, and a Windows SDK.'
}
$instances = @(& $vswhere -all -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or -not $instances.Count) { throw 'No Visual Studio x64 C/C++ toolchain was found.' }
$cmakeCommand = Get-Command cmake.exe -ErrorAction SilentlyContinue
$cmakePath = if ($cmakeCommand) { $cmakeCommand.Source } else { $null }
if (-not $cmakePath) {
    foreach ($instance in $instances) {
        $candidate = Join-Path $instance.installationPath 'Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
        if (Test-Path -LiteralPath $candidate) { $cmakePath = $candidate; break }
    }
}
if (-not $cmakePath) { throw 'Install CMake 3.25+ (4.2+ for VS 2026), or the Visual Studio C++ CMake tools component.' }
$versionText = (& $cmakePath --version | Select-Object -First 1)
if ($versionText -notmatch '(\d+\.\d+\.\d+)') { throw 'Cannot read the CMake version.' }
$cmakeVersion = [version]$Matches[1]
if ($cmakeVersion -lt [version]'3.25.0') { throw 'CMake 3.25 or later is required.' }
$chosen = $null
foreach ($instance in ($instances | Sort-Object {[version]$_.installationVersion} -Descending)) {
    $major = ([version]$instance.installationVersion).Major
    if ($major -eq 18 -and $cmakeVersion -ge [version]'4.2.0' -and $Preset -in @('Auto','vs2026-x64')) {
        $chosen = $instance; $Preset = 'vs2026-x64'; break
    }
    if ($major -eq 17 -and $Preset -in @('Auto','vs2022-x64')) {
        $chosen = $instance; $Preset = 'vs2022-x64'; break
    }
}
if (-not $chosen) { throw 'No matching toolchain/preset. VS 2026 requires CMake 4.2+; VS 2022 requires CMake 3.25+.' }
$toolDirectory = Split-Path -Parent $cmakePath
$ctestPath = Join-Path $toolDirectory 'ctest.exe'
$cpackPath = Join-Path $toolDirectory 'cpack.exe'

function Invoke-BuildTool([string]$Tool, [string[]]$ToolArguments) {
    & $Tool @ToolArguments
    if ($LASTEXITCODE -ne 0) { throw "$([IO.Path]::GetFileName($Tool)) failed with exit code $LASTEXITCODE." }
}

Push-Location -LiteralPath $projectRoot
try {
    $configurePreset = if($Loader -eq 'PROXY'){$Preset}else{$Preset + '-' + $Loader.ToLowerInvariant()}
    $asmChoice = if ($AsmTests) { 'ON' } else { 'OFF' }
    Invoke-BuildTool $cmakePath @('--preset', $configurePreset, "-DCMAKE_GENERATOR_INSTANCE=$($chosen.installationPath)", '-DBUILD_TESTING=ON', "-DSSO_PROXY_ENABLE_ASM_TESTS=$asmChoice")
    $buildPath = Join-Path $projectRoot "out/build/$configurePreset"
    Invoke-BuildTool $cmakePath @('--build', $buildPath, '--config', $Configuration, '--parallel')
    & (Join-Path $PSScriptRoot 'verify_pe_metadata.ps1') -BuildDirectory (Join-Path $buildPath "bin/$Configuration") -OutputPath (Join-Path $buildPath "bin/$Configuration/validation/pe-metadata.json")
    if (-not $SkipTests) {
        $validationPath = Join-Path $buildPath "bin/$Configuration/validation"
        [IO.Directory]::CreateDirectory($validationPath) | Out-Null
        Invoke-BuildTool $ctestPath @('--test-dir', $buildPath, '-C', $Configuration, '--output-on-failure', '--output-junit', (Join-Path $validationPath 'ctest.xml'))
        Copy-Item -LiteralPath (Join-Path $buildPath 'Testing/Temporary/LastTest.log') -Destination (Join-Path $validationPath 'ctest.log')
    }
    if ($Package) {
        Invoke-BuildTool $cpackPath @('--config', (Join-Path $buildPath 'CPackConfig.cmake'), '-C', $Configuration, '-B', (Join-Path $projectRoot "out/packages/$Loader/$Configuration"))
    }
    $artifact = switch($Loader){'PROXY'{'opengl32.dll'} 'RESHADE'{'SSOVisibility.addon64'} 'ASI'{'SSOVisibility.asi'} default{'SSOVisibility.dll'}}
    Write-Host "Artifact: $(Join-Path $buildPath "bin/$Configuration/$artifact")"
} finally { Pop-Location }
