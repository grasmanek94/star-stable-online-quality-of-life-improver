# Build validation — 2026-11-15

This source migration was validated on Windows x64 with Visual Studio 2026 (MSVC 19.51.36252.0), Windows SDK 10.0.26100.0 and CMake 4.5.0-rc1. The code remains guarded to game client 645.348067. Detailed per-configuration hashes, private config RVAs and results are in [build-validation.json](build-validation.json). Those hashes describe the recorded builds, not every future rebuild.

- **Release, Debug, RelWithDebInfo:** build succeeded and all five CTest suites passed. Each configuration checked 16 runtime scenarios, 368 named/ordinal exports, 81 classifier cases, generated assets, 144 actual linked visibility-wrapper cases and 12 actual linked forwarder cases.
- **Ninja Release:** configured/built successfully from an x64 MSVC environment; all four standard CTest suites passed.
- **Source portability:** extracted the CPack source ZIP into a directory containing spaces, explicitly disabled Python discovery, then ran the one-command build/test/package wrapper successfully. The two native CTest suites passed. No original workspace source or dependency path was used by that build.
- **Install/CPack:** staged the runtime package and checked source/runtime ZIP contents. Source packaging excludes build outputs and binaries. Runtime packaging includes matching symbol metadata and excludes test programs.
- **Dependencies:** the three recorded DLLs import only `KERNEL32.dll` and `USER32.dll`; the proxy lazily loads the actual System32 OpenGL library. The C runtime is static. Cheat Engine, Lua and Python are not runtime or normal build dependencies.

Python's standard library is optional for the additional classifier/freshness checks and offline asset regeneration. Unicorn is optional for assembly emulation. No dependency manager or network download runs as part of a normal build. The existing locally installed Unicorn package was used to exercise the optional suite.

The VS 2022 presets and GitHub Actions workflow are provided but were not run against a separate VS 2022 installation or remote runner. The tested compiler installation here is VS 2026. No live game process was opened, modified, restarted or played for these checks. Live proxy integration, complete gameplay lifecycle behavior and FPS results remain unverified.
