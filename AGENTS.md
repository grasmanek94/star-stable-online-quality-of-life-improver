# Project notes

This is the standalone Windows x64 CMake source for the OpenGL visibility proxy. Start with README.md and docs/ARCHITECTURE.md. The historical reverse-engineering handoffs are retained in docs/; old workspace paths and DLL addresses there are not current build metadata.

Build with build.cmd, or use the VS 2026/2022 presets. Native tests run in helper processes and must keep their assertions enabled in Release. The shipping DLL must not define SSO_PROXY_TESTING. Preserve own-actor checks, pass-through error behavior, exact restoration and the ordered wrapper/AOB contract.

Generated assets are committed. Edit their canonical inputs in data/ and run tools/generate_assets.py; src/asm/visibility_hooks.asm and tests/fixtures/baseline.inc are reviewed maintained inputs. The generator needs only Python's standard library and must not depend on Cheat Engine, a game installation, absolute researcher paths or network downloads.

Use each newly built DLL's own map/validation/proxy-symbols.json, never a historical g_config RVA. Standard tests do not establish live gameplay safety or FPS improvement. Do not restart or play the user's game as part of a build task.
