# Architecture and maintenance

## Ownership of the sources

This standalone project supersedes the original `work/proxy/build_proxy.cmd` build. It has no include, generator, linker or test dependency on that workspace. Historical CE source and raw profiling data remain in the original research workspace.

`src/proxy_main.c` owns OpenGL initialization, logging and foreground hotkeys. `DllMain` only records the module and exit state. The first forwarded call runs one-time initialization, opens the absolute System32 library, resolves the committed named exports, and initializes the visibility state. The hotkey thread starts after one-time initialization releases. Other host executable names receive forwarding only.

`generated/gl_forwarders.asm` implements fast indirect jumps and lazy resolvers. The resolver preserves incoming GPR/SIMD arguments and the original stack layout. `data/opengl-exports.json` owns export names and ordinals; `generated/opengl32.def` is the DLL's entire public export surface. Project helper symbols are not DLL exports.

`src/visibility/visibility_runtime.c` owns build/layout validation, unique executable-section AOB lookup, local ownership checks, near-thunk allocation, patching, F6 restore, pass-through failures and retained recovery state. `src/visibility/classifier.inc` owns config/cache structures and pure classification decisions. The latter is included by the production runtime and test bridge, so tests execute the same classifier. Its `Q`, `D` and `B` readers are functions on purpose; the original CE/TCC experiment found nested pointer macros unsafe.

`src/asm/visibility_hooks.asm` contains the 18 reviewed native wrappers. It is maintained source, originally derived from the CE v5 loader. It is not regenerated on build. `data/visibility-sites.json` owns ordered AOB windows, call offsets and native target RVAs. `generated/hook_specs.inc` binds that order to `HideHook_0` through `HideHook_17`. Change the data, wrapper mapping, fixture and tests together.

## Runtime constraints

The supported client is 645.348067, timestamp `6AEB5BD3`, image size `014AF000`. The current signatures scan rather than using patch RVAs directly, but native target RVAs, object offsets, registry globals, vtables and config layout are still build-specific. A mismatched layout refuses visibility activation. The build does not require any client file.

All flags start at 1 and the master starts off. F5 enables the selected categories. F6 switches decisions to native behavior first and restores only exact owned/original windows. Unknown external changes are not overwritten. Code allocations, cached state and DLL remain mapped until process exit so an in-flight wrapper cannot enter freed code. A failed partial patch retains state for F6 recovery.

Near-game thunks contain absolute DLL addresses, allowing the DLL to load beyond signed 32-bit CALL range. Patching prepares allocations before pausing threads, bounds retries, checks instruction pointers and context bytes, changes only the five-byte CALLs, flushes the instruction cache and resumes handles in cleanup. Suspension is not a complete synchronization proof; live engine lifecycle behavior remains unverified.

The user's own rider, horse and pets are excluded by ownership/control and ancestry checks. NPC human/horse/animal classes often share `CPXQuestControl`, so those category splits use a documented engine-name heuristic. Checkpoint ancestors are protected. Selected rendering/animation is skipped; world file streaming, actor creation, arbitrary scenery and all quest/gameplay processing are not disabled.

## Build decisions

Use C17, MSVC and x64 MASM. Keep target flags in `cmake/CompilerOptions.cmake`; avoid global flag-string replacements. `/MT` is used for Release/RelWithDebInfo and `/MTd` for Debug. Static CRT thread notifications remain enabled. x64 ASLR and NX compatibility are retained. Incremental linking is off so link-map symbols identify actual entries for diagnostics and emulation. Release/RelWithDebInfo use linker dead-code elimination/folding.

Tests enable `assert` in their own translation units even for Release: the native harness has intentional assertion side effects. Do not remove that override. The shipping DLL is compiled separately without `SSO_PROXY_TESTING`; synthetic failure injection and test accessors are not in it. A per-target MSBuild property disables unrelated user-wide vcpkg auto-linking; the project has no external native library dependency.

`tools/build.ps1` discovers installed C++ toolchains with `vswhere`. VS 2026 requires CMake 4.2; VS 2022 uses the project's 3.25 minimum. No compiler version/edition path is embedded. `CMakePresets.json` supplies explicit generators and x64 architecture. Ninja requires an already configured x64 Developer Command Prompt.

`tools/write_metadata.ps1` runs after each link, reads that DLL/map, calculates SHA256 and records current symbol RVAs and the hook plan. It uses .NET hashing rather than module auto-loading, which can vary inside MSBuild's PowerShell environment. `tools/read-proxy-state.ps1` checks the installed DLL hash and loaded header before reading private offsets. Keep metadata with its matching DLL; never reuse the old v1 `g_config` RVA. Call counters are not on-screen actor counts or FPS measurements.

## Updating a game layout

1. Record the new executable identity and retain an unmodified baseline. Disable all older CE entries and remove the proxy while collecting a new baseline.
2. Use the official IDA MCP to reopen the new client database. Start from the same native update roles and the disassembly in the historical handoffs. Verify CALL signatures, self registers, return types, argument/stack use, native targets, local ownership checks and registry ancestry. Do not assume an AOB match proves semantic compatibility.
3. Update the PE guards, local safe-reference/global/vtable offsets and classifier layout checks only after confirming them. Keep own-actor protection and generation validation. Registry record parent is +40; actor+96 is not its hierarchy parent.
4. Update ordered `data/visibility-sites.json`, the matching assembly wrappers and the committed synthetic fixture. The small existing fixture represents the old layout and cannot validate a different client automatically.
5. Run the offline generator and freshness check. Build Release and Debug, run native and classifier tests, then enable the linked assembly tests. Inspect the rebuilt export table and metadata, and package the exact outputs tested.
6. Have the user verify local visibility, each category, F6 restoration, scene transitions and actual gameplay. Measure FPS with consistent settings/foreground state before claiming a performance benefit.

For the baseline, Config is 344 bytes: active at 0, category flags 16..26, cache base 88, capacity 96, epoch 100, vtables 104..199 and counters 256..343. Static assertions protect the config/counter layout. Hook category semantics and ABI details are in the full historical handoffs.

## Validation boundaries

The standard CTest suite runs helper processes only. The runtime suite modifies its own synthetic PE allocation and suspends/resumes one of its own helper threads. The forwarding suite loads the proxy before the real OpenGL library, compares 368 names/ordinals and checks four contextless calls. The classifier suite executes 81 cases in host-owned fixtures. Optional Unicorn tests execute actual linked assembly with modeled helper results at two image bases.

No test launches, injects into, plays, patches or even opens `SSOClient.exe`. Native driver-context creation, live proxy gameplay and controlled FPS remain separate integration work. A fresh source archive build is a portability test, not a game integration result.
