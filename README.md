# SSO Visibility Proxy

A Windows x64 `opengl32.dll` proxy written in C17 and MASM. It forwards the Windows OpenGL exports and supplies the existing F5/F6/category visibility controls for the analyzed Star Stable client **645.348067**.

This is the maintained standalone CMake project. The visibility decisions and native call wrappers come from the previous proxy; the build system, source layout, tests and packaging have been reorganized. Build outputs belong in `out/` and are ignored by Git.

## Build on Windows

Install either **Visual Studio 2022 / Build Tools** or **Visual Studio 2026 / Build Tools**, with:

- **Desktop development with C++**, including the MSVC x64 tools and MASM.
- A Windows 10 or 11 SDK.
- **CMake 3.25+** for VS 2022, or **CMake 4.2+** for VS 2026. CMake can be on PATH or supplied by the Visual Studio C++ CMake tools component.

Open a terminal in this directory and run:

```powershell
.\build.cmd
```

The wrapper discovers Visual Studio through `vswhere`, configures x64, builds Release, and runs the available tests. No hardcoded compiler installation path, game executable, IDA database, Cheat Engine installation, network connection, or Python package is required to build the DLL. Standard Windows PowerShell writes the diagnostic metadata. The C runtime is statically linked.

On VS 2026 the result is:

```text
out/build/vs2026-x64/bin/Release/opengl32.dll
```

For VS 2022, replace `vs2026-x64` with `vs2022-x64`.

Other common commands:

```powershell
.\build.cmd -Configuration Debug
.\build.cmd -Configuration RelWithDebInfo
.\build.cmd -Package
.\build.cmd -Preset vs2022-x64
```

`-Package` creates a runtime ZIP in `out/packages/<configuration>/` after the tests pass. `-SkipTests` is available for a local iteration. Nothing automatically copies a DLL to the game or starts/stops a game process.

### Direct CMake / IDE use

The wrapper is optional. For Visual Studio 2026:

```powershell
cmake --preset vs2026-x64
cmake --build --preset vs2026-release
ctest --preset vs2026-release
```

For Visual Studio 2022, use `vs2022-x64` / `vs2022-release`. Debug and RelWithDebInfo build/test presets are also included. Use **Open Folder** in Visual Studio and select a preset to work with the project directly.

Ninja is supported from an **x64 Native Tools Command Prompt** with Ninja on PATH:

```powershell
cmake --preset ninja-x64-release
cmake --build --preset ninja-release
ctest --preset ninja-release
```

Select the x64 MSVC environment first. MinGW, clang-cl, ARM64 and 32-bit targets are deliberately rejected: this code uses Microsoft structured exception handling, the Windows x64 ABI and MASM.

## Project layout

```text
.
├── CMakeLists.txt              # DLL, install rules, CTest and CPack
├── CMakePresets.json           # VS 2022, VS 2026 and Ninja presets
├── build.cmd                   # One-command Windows build entry point
├── cmake/                     # Shared target compiler/linker settings
├── include/sso_proxy/         # Internal C interfaces
├── src/
│   ├── proxy_main.c           # OpenGL initialization, logging and hotkeys
│   ├── asm/                   # Reviewed native visibility call wrappers
│   └── visibility/            # Patch lifecycle and shared classifier
├── generated/                 # Committed OpenGL forwarders, DEF and AOB plan
├── data/                      # Canonical export manifest and 18 hook sites
├── tests/                     # Native tests, Python tests, baseline fixtures
├── tools/                     # Build, generation and diagnostic utilities
├── docs/                      # User guide, architecture and repair history
└── out/                       # Generated builds, packages and test results
```

Generated files are committed so a normal Windows build needs no generator dependency. The reviewed `src/asm/visibility_hooks.asm` and small `tests/fixtures/baseline.inc` are also committed inputs. Regenerating assets does not discover new game layouts or replace those wrappers.

## Tests

`BUILD_TESTING` defaults to `ON`. CTest always includes two native helpers:

- **runtime:** 16 install/restore/recovery checks on an allocated synthetic PE, including helper-thread resumption and exception fallback.
- **forwarding:** all 368 OpenGL exports compared by name and ordinal, lazy loading of the distinct System32 library, and four contextless GL/WGL smoke calls.

If 64-bit Python 3.10+ is found, CTest also runs the existing **81 classifier cases** and an offline generated-asset freshness check. These use only Python's standard library; they do not load Cheat Engine or access a game process.

Optional execution of the **actual linked MASM** code requires Unicorn:

```powershell
python -m pip install -r tests/requirements.txt
.\build.cmd -AsmTests
```

Alternatively configure with `-DSSO_PROXY_ENABLE_ASM_TESTS=ON`. These tests cover 144 visibility-wrapper cases and 12 forwarding cases, including relocation beyond near-CALL range. They model native helpers; native C and Windows forwarding are tested separately. Use a virtual environment and set `-DPython3_EXECUTABLE=<absolute path>` if needed.

Use `ctest --test-dir out/build/vs2026-x64 -C Release --output-on-failure` to rerun tests. Results are in `Testing/Temporary/LastTest.log`; optional machine-readable classifier/assembly reports are next to the built DLL in `validation/`. Every linked DLL also gets its own `validation/proxy-symbols.json` from its map and hash. That file is diagnostic metadata, not a test-pass certificate.

These are isolated tests. They do not prove live game integration, crash-free gameplay, update compatibility, or a particular FPS improvement. The old CE v4 visual confirmation and later CE v5 counters are separate evidence.

Recorded local results and their exact limits are in [BUILD_VALIDATION.md](docs/BUILD_VALIDATION.md).

## Install and package

Read [the controls and installation guide](docs/USER_GUIDE.md). Disable the older CE visibility entries, close the game, copy **only `opengl32.dll`** beside `SSOClient.exe`, then relaunch. F5 enables hiding, F6 restores native behavior, and Ctrl+Numpad selects categories. Keep NumLock on.

To stage a portable runtime package using CMake directly:

```powershell
cmake --install out/build/vs2026-x64 --config Release --prefix out/install/Release
cpack --config out/build/vs2026-x64/CPackConfig.cmake -C Release
```

The runtime ZIP includes the DLL, user guide, read-only diagnostic and matching metadata. A map and any available PDB are included under `symbols/`. Test executables, test DLLs, the Windows OpenGL library and the game executable are excluded.

Create a source ZIP with:

```powershell
cpack --config out/build/vs2026-x64/CPackSourceConfig.cmake
```

The source package includes the committed build inputs and documentation and excludes `out/`, local IDE files and caches. Keep custom build directories under `out/` so source packaging excludes them. The GitHub workflow builds/tests the configurations and uploads runtime packages; it needs no game installation.

## Maintenance

For an intentional metadata change:

```powershell
python tools/generate_assets.py
python tools/generate_assets.py --check
```

This standard-library generator reads `data/` offline. Hook order is part of the assembly/config contract. See [architecture and maintenance](docs/ARCHITECTURE.md) before changing it. Build guards still target **645.348067**; AOB scanning does not establish that a later game's object offsets or call signatures are compatible.

The complete earlier analysis is retained as [historical reverse-engineering notes](docs/REVERSE_ENGINEERING.md). Old workspace paths and DLL hashes there are historical. For a newly built DLL, use its own map and generated metadata.

Build-system reference: [CMake presets](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html), [VS 2026 generator requirements](https://cmake.org/cmake/help/v4.2/generator/Visual%20Studio%2018%202026.html), and [MSVC runtime selection](https://cmake.org/cmake/help/latest/prop_tgt/MSVC_RUNTIME_LIBRARY.html).
