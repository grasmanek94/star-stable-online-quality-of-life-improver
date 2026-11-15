# Historical Cheat Engine experiments

This directory preserves the earlier research work and user-confirmed outcomes. It is **not** a native build/runtime dependency. Do not enable an old table alongside the current DLL.

- outputs/: working AOBv4 visibility table/scripts, later v5 category table, sampler/quick-performance diagnostics, notes and isolated validation summaries.
- work/: canonical historical Lua/C inputs, site plans and original generators/test scripts. These preserve the original work/outputs relative layout but may require original workspace fixtures, compiler tools or the installed Lua/CE test runtime. They are archival tools, not the current standalone CMake build.
- confirmed-user-outcomes.json: user confirmation that v3 and AOBv4 hid remote rider/horse/pets while preserving their own. It is a visual outcome, not a controlled FPS/chat test.

The XML encoding failure, ineffective preference-byte tests and sampler bypasses are documented in the handoffs. Sampler diagnostics did not establish an FPS gain and were not incorporated as enabled DLL optimizations. Current native code/configuration is at the repository root; current instructions are docs/USER_GUIDE.md and docs/SESSION_HANDOFF.md.
