# Upstream files touched & future-merge difficulty

Fork: `spinkicks/anki` (+ the two Android forks). Baseline: pristine upstream (`ankitects/anki`, `ankidroid/Anki-Android`, `ankidroid/Anki-Android-Backend`). **Updated 2026-07-01 to cover the cumulative surface through wed-plus (`main` @ `1fed9e109`)** — supersedes the wed-mvp version that listed 4 files. (Speedrun Home work on `feat/speedrun-home` will add: `ts/routes/speedrun-home/**` new, plus small additive edits to the same qt shell files + mediasrv/webview for the API-access fix.)

## New files (ours; zero merge-conflict risk — upstream never touches these)
- `proto/anki/speedrun.proto` — the service contract (5 RPCs; frozen, append-only).
- `rslib/src/speedrun/{mod.rs, service.rs, exam_profile.rs}` — pure logic + service impl + config helper.
- `pylib/anki/speedrun.py`, `pylib/tests/test_speedrun.py` — Python wrapper + integration tests.
- `qt/aqt/speedrun.py` — the SpeedrunMemory (+Home, on the current branch) dialogs.
- `ts/routes/speedrun-memory/**`, `ts/lib/speedrun/data.ts` — shared Svelte dashboard + data layer.
- `speedrun/**` — deterministic (non-AI) content toolchain: exam profile, seed deck (+ `.apkg`), FLEX scraper, tests, uvw wrappers.
- `qt/installer/windows-template/**`, `qt/installer/mac-template/**` — vendored Briefcase templates (were submodules; now plain files).
- AnkiDroid fork: `pages/SpeedrunMemoryFragment.kt`, `common/destinations/SpeedrunMemoryDestination.kt`, `libanki/.../BackendSpeedrun.kt`.

## Modified upstream files — the merge-conflict surface
### repos/anki (11 files)
| File | Change | Merge difficulty |
|---|---|---|
| `rslib/src/lib.rs` | +1: `pub mod speedrun;` | Trivial (additive line) |
| `rslib/proto/src/lib.rs` | +1: `protobuf!(speedrun, "speedrun");` | Trivial (additive line) |
| `pylib/anki/collection.py` | +2: import + instantiate `SpeedrunManager` | Trivial |
| `rslib/src/scheduler/new.rs` | +5: `set_new_position_speedrun` crate-visible shim | Trivial (additive fn) |
| `rslib/src/sync/collection/tests.rs` | +107: §7b conflict test appended | Trivial (append-only test) |
| `build/ninja_gen/src/render.rs` | +8/−2: OS-native separator for the runner path | Low — self-contained, upstreamable Windows fix |
| `build/configure/src/installer.rs` | −17: SyncSubmodule actions removed, glob-only input | Low — small, isolated to `build_installer()` |
| `.gitmodules` | −10: two briefcase submodule blocks removed | Low — but any upstream template bump must be re-vendored manually (accepted trade-off for network-independence) |
| `qt/aqt/mediasrv.py` | +1: `"speedrun-memory"` in `is_sveltekit_page` (+ speedrun entries in `exposed_backend_list` pending on `feat/speedrun-home`) | Trivial (list entries) |
| `qt/aqt/forms/main.ui` | +7: `actionSpeedrunMemory` + menuTools entry | Trivial (additive XML) |
| `qt/aqt/main.py` | +4: qconnect + `onSpeedrunMemory` handler | Trivial |
| `qt/aqt/__init__.py` | +2: import + `_dialogs` registry row | Trivial |
| `ftl/qt/qt-misc.ftl` | +1: menu label string | Trivial |
### repos/anki-android (5 files)
`pages/PageWebViewClient.kt` (+1 whitelist), `pages/PostRequestHandler.kt` (+4 method registrations), `navigation/AnkiDroidNavigator.kt` (+2), `DeckPicker.kt` (+menu branch), `res/menu/deck_picker.xml` (+item) — all additive, trivial.
### repos/Anki-Android-Backend
`anki` submodule pin → our fork `a0ead51c9`; `Cargo.lock` (+2 deps, `--locked` reproducibility); `build_rust/src/main.rs` `.\gradlew.bat` Windows fix. All low.

## Assessment
All engine/UI logic lives in **new files**; the upstream contact is **small, additive, list/registry-style edits** plus two isolated build fixes (`render.rs` upstreamable; installer vendoring an accepted divergence). Rebasing onto a new Anki release should be conflict-free or a trivial re-application everywhere except the vendored templates (re-vendor on template bumps). The additive-frozen-proto rule keeps the wire contract compatible across both bridges. (`AGENTS.md`/`CONTRIBUTORS`/`.claude/` also differ from upstream but are project-meta, not engine code.)
