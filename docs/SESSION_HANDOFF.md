# Continue work from this repository

## Current checkout

The user's maintained checkout is `C:\Users\Rafal\Documents\Codex\2026-11-15\tr\outputs\Star-Stable-OpenGL-proxy-CMake\SSO-Visibility-Proxy-1.1.0-source`, remote `https://github.com/grasmanek94/star-stable-online-quality-of-life-improver.git`, branch master. The old directory name is retained; code version is **1.2.1**. Older workspace tree `sso-visibility-proxy` and original work/proxy scripts are historical snapshots. Make future changes here and build here.

Read README.md, AGENTS.md, IMPLEMENTATION_STATUS.md, REQUEST_HISTORY.md, JOURNAL.md, ARCHITECTURE.md and LOADER_ADAPTERS.md. Earlier discovery and failures are in REVERSE_ENGINEERING.md and SSO-Visibility-Engineering-Handoff.md. The runtime's data/ files and MASM wrapper order are canonical; historical static addresses elsewhere are not instructions to patch a newly updated client blindly.

## Preserve these decisions

- Default8 hides remote riders/horses/pets only. Master starts off. F5 enables,F6 restores,F7 reloads INI; Ctrl+Numpad selects/enables. NumLock on. Preset9 riders/horses only.
- Preset0 enables all14 filters and cannot be overridden. Defaults0–4 aggressive,5–9 guarded. User permits NPC model hiding while preserving collision and known race cues. Own-body/checkpoint invariants remain even in0; broad particles may remove own cosmetics/cues/fog.
- Four adapters share one C/MASM core. No Cheat Engine dependency. ASI/explicit/ReShade entry requirements are documented; do not add loader-lock patching or assume a universal shader ABI.
- Build-specific layout guards remain645.348067. AOB lookup is implemented; arbitrary future-layout compatibility is not guaranteed. Follow the journal's repair checklist with a current official IDA MCP database.
- **GitHub Actions is disabled by request.** Preserve `.github/workflows/windows.yml.disabled` until the user requests re-enabling. Do not silently restore its .yml extension.

## Builds in this checkout

```powershell
.\build.cmd -Loader PROXY -Configuration Release -Package
.\build.cmd -Loader RESHADE -Configuration Release -Package
.\build.cmd -Loader ASI -Configuration Release -Package
.\build.cmd -Loader PLUGIN -Configuration Release -Package
```

VS2026 outputs are `out/build/vs2026-x64[-reshade|-asi|-plugin]/bin/<configuration>/`. VS2022 uses corresponding names. Runtime ZIPs are `out/packages/<LOADER>/<configuration>/`. Use `-AsmTests` when optional Python/Unicorn are installed. The build wrapper preserves per-configuration `validation/ctest.xml` and `ctest.log` as well as matching private-symbol metadata. Run `python tools/record_validation.py --preset vs2026-x64` after the documented seven-build matrix to update docs/build-validation.json from those reports.

After CPack runtime packages exist, make a source ZIP and optionally collect a combined bundle:

```powershell
cpack --config out/build/vs2026-x64/CPackSourceConfig.cmake -B out/packages/source
python tools/package_release.py
```

The optional standard-library collector writes `out/releases/1.2.1/`, containing all four runtime ZIPs, combined loader ZIP, complete source ZIP and manifest. It checks archive CRCs, module/metadata hashes, config dimensions and default8. Python is not needed for the normal native build or ordinary CPack packages. Generated binaries, caches and packages remain ignored by Git.

## Evidence map and boundaries

docs/research/README.md indexes actor v4/v5, cosmetic and particle IDA excerpts and the performance reports/normalized timing evidence. research/legacy-ce contains historical scripts/tables for provenance. They are separate from the maintained native runtime and may need original workspace fixtures/dependencies to rerun.

Client baseline645.348067: SHA256 `3CEC805521C70B64F1A33C5A0EFA67679B8112DACBE9594AB1B47301B4D3DE8D`, PE6AEB5BD3, image014AF000. Registry parent is record+40; safe-reference generation/index at actor+128/+132. Use fresh PID/module base and current DLL hash-bound metadata. Never reuse old g_config addresses, heap pointers or IDA instance IDs.

The older1.1 proxy was verified active with all11 flags and18 owned hooks during a60.877s foreground capture in essentially the same area.96.3 vs63.0 kernel presents/s, main-thread99.5%, pose sampled cost3.611→0.317ms/present. This was not a controlled camera/population A/B. New1.2 particles/grass and actual ReShade/ASI integration remain unverified live. Source/build completeness does not establish safe gameplay or a guaranteed0.43ms gain.

No build task should restart/play the game or replace its loaded module. The user controls gameplay/live checks. All current changes can be built/reviewed independently of a running client. Retain recovery/restore/ownership invariants and build matching metadata after every link.
