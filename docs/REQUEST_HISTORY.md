# User requests and resulting decisions

This is the project-relevant request history, in conversation order. Later refinements govern the implementation. It distinguishes observed outcomes from requested experiments; it is not a promise that every diagnostic improved performance.

## Investigation and early experiments

1. Trace CPU-bound Star Stable without source access and give developers useful hotspot evidence. Resolution/graphics changes did not affect the user's observed FPS. Crowds were associated with lower FPS; an early night scene was steady around80–90 versus occasional200. The user's300–600 expectation was an aspiration, not a measured achievable target.
2. Capture while the user plays or stands in place; the assistant should not play the game. Repeat a declined capture request when the user said the decline was accidental. Later captures explicitly required the game foreground; a browser-foreground recording was rejected for comparison.
3. Explain/setup official IDA MCP and investigate CPXTerrain, CPXQuestControl and animation sampler loops. Document addresses, interpretations and limitations for developers. The baseline metadata, handoffs, reports and raw IDA excerpts are preserved in docs/research and the engineering guides.
4. Create reversible Cheat Engine diagnostics for sampler/animation and visibility hypotheses. Sampler/MatrixAnimation/preference-byte tests produced no reported FPS benefit. They remain historical experiments, not default DLL optimizations.
5. Hide remote players, horses and pets while preserving local actors and messages. Early hide flags had no effect. Correct native fade branches hid players/horses; the added pet path then hid their pets. The user explicitly confirmed v3 and AOBv4 kept their own rider, horse and pets visible while hiding others. No controlled chat/FPS result was established by that confirmation.
6. Make the visibility paths resilient through AOB lookup and document the work exhaustively for a fresh AI session. Unique patterns, relationship checks, exact restoration, baseline RVAs, failed approaches and a repair checklist were retained. Future semantic/layout compatibility is still bounded; see IMPLEMENTATION_STATUS.md.

## Native project and expanded categories

7. Extend hiding to NPC actors/horses/pets, standalone and sale/display horses, coins and quest markers, with category controls. The first CE XML encoding error was a delivery issue; later native code does not load a CE table. Shared NPC classes require a documented name heuristic for species categories.
8. Build a native OpenGL proxy with F5 enable/F6 restore and category chords, then organize it as an easily built Windows CMake C/C++ project. Cheat Engine must not be a dependency. The original individual-category chords were subsequently replaced by presets.
9. Investigate additional visual-only optimizations while preserving obstacles, collision and race cues. A fresh capture verified all11 original flags and18 hooks active. The user corrected an interpretation that locations differed: it was essentially the same area. Reports explicitly retain this correction and the remaining uncontrolled camera/population differences.
10. Research and implement optional particle suppression around the observed0.4307 sampled ms/present budget; document thoroughly and include sources/CMake support. Add an intentionally broad option too. AmbientParticles, AllParticles and DetailGrass are implemented; particle children remain native. This budget is not a promised saving and no1.2 live gain is claimed.

## Final preset and loader refinements

11. Replace category chords with editable INI or JSON presets. Windows INI was chosen for a dependency-free native implementation. Ctrl+Numpad selects and enables; F7 reloads settings.
12. Ctrl+Numpad0 must enable literally every supported filter. It is an immutable all14-category preset with broad particles and extra gameplay protection off, while own-body/checkpoint invariants remain.
13. Presets1–9 should progressively reduce hiding;9 hides only remote riders and horses. The later boundary supersedes the earlier request for maximally gameplay-friendly preset1: **0–4 aggressive,5–9 gameplay-friendly defaults**. The4→5 transition keeps category switches but adds gameplay guards.
14. NPC models may be hidden in ordinary presets; preserve collision and known race cues. The user explicitly chose this over always preserving quest-giver models. The code does not patch collision/obstacle routines; conservative ancestry protection remains a heuristic.
15. Default selection must be **8: remote riders, horses and pets only**. This is implemented in built-in defaults, shipped INI and common host initialization. Master starts off until F5 or preset selection. Preset9 omits pets.
16. Add a ReShade compile target and, if feasible, generic support for shader/plugin/ASI loaders. Four adapters share one core: PROXY, RESHADE, ASI, PLUGIN. Generic initialization contracts are explicit; mapping an arbitrary DLL without calling an entry is not sufficient. No third-party loader or SDK is bundled.
17. Audit whether all requests were implemented and documented. IMPLEMENTATION_STATUS.md maps every final feature to code, default presets and notes, and records live-validation/layout/loader boundaries. No missing final-scope implementation stub was found.

## Repository delivery and current instruction

18. Put all updates, features, documentation, instructions, journals, request history and research work into the existing linked repository at the requested local directory; make appropriate commits, push and build there. The folder's historical1.1.0 name is retained, but the project version is1.2.0. It is now the maintained checkout.
19. **Disable the GitHub workflow for now.** Its configuration is preserved as `.github/workflows/windows.yml.disabled`; GitHub Actions does not discover that extension. No push/PR/manual workflow is active in this checkout. Rename it to windows.yml only when explicitly re-enabling CI. Local builds and tests remain available.
20. Add PE/RC metadata to DLLs and all PE outputs: FileDescription contains the repository URL and title Star Stable Online Frame Rate / Performance Fixer; ProductName uses that exact title; author grasmanek94; copyright2026-to-current-build-year generated through CMake. Commit and push when complete. Implemented for all loader/helper images; see PE_METADATA.md for exact fields and verification.
21. Create a GitHub release for that update and upload all four loader builds, combined bundle and source ZIP, with the previous release's exclusions. Prepare patch1.2.1, retain the1.2.0 release, inspect its published archive lists, preserve the8-file runtime layout and exclude local/uncommitted/generated/raw data from the committed-source ZIP. See releases/1.2.1.md for the asset and validation policy.

Build/runtime artifacts are generated under ignored out/. Portable source packages include this history and the research notes. Raw ETLs, game executables/IDBs, heap dumps, third-party binaries and private process snapshots are not source dependencies or repository content. Historical CE sources/tables are retained under research/legacy-ce and are not used by the native build.
