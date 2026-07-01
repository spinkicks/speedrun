<!-- DRAFT for Cursor to review/place. Produced by the Wednesday-MVP execution
     (Claude Code). Not committed by Claude per the umbrella-docs ownership split.
     Figures generated from: git diff <merge-base upstream/main> .. feat/speedrun-wed-mvp -->

# Upstream files touched & future-merge difficulty

Fork: `spinkicks/anki`. Branch: `feat/speedrun-wed-mvp`. Baseline: pristine
`ankitects/anki` (`upstream/main`). Covers the cumulative Speedrun engine work
(Phase 1 `GetCoverage` + Phase B `GetTopicMastery` + the Windows build fix).

## New files (ours; zero merge-conflict risk — upstream never touches these)
- `proto/anki/speedrun.proto` — the read-only service contract.
- `rslib/src/speedrun/mod.rs` — pure logic (`coverage`, `topic_aggregate`, `wilson_interval`) + unit/integration tests.
- `rslib/src/speedrun/service.rs` — `impl SpeedrunService for Collection` (`get_coverage`, `get_topic_mastery`).
- `pylib/anki/speedrun.py` — `SpeedrunManager` wrapper (`coverage`, `topic_mastery`).
- `pylib/tests/test_speedrun.py` — Python integration tests.
- `speedrun/**` — deterministic (non-AI) content toolchain: exam profile, seed deck (+ `.apkg`), FLEX scraper, tests, and the out-of-tree-venv `uvw` wrappers.

## Modified upstream files — the ENTIRE merge-conflict surface (4 files)
| File | Change | Merge difficulty |
|---|---|---|
| `rslib/src/lib.rs` | +1 line: `pub mod speedrun;` | Trivial — one additive line in the module list. |
| `rslib/proto/src/lib.rs` | +1 line: `protobuf!(speedrun, "speedrun");` | Trivial — one additive, alphabetized line. |
| `pylib/anki/collection.py` | +2 lines: import + instantiate `SpeedrunManager` | Trivial — additive next to the other managers. |
| `build/ninja_gen/src/render.rs` | +8 / -2: emit the `runner` path with the OS-native separator | Low — a self-contained, genuinely upstreamable Windows-compat fix (n2 on Windows can't `CreateProcess` a relative forward-slash path). Isolated to one `writeln!`. |

## Installer (Phase C) — NO upstream change
The clean-machine installer builds without touching any installer source. The
Briefcase Windows/macOS templates are **git submodules** (`ankitects/briefcase-*-app-template`)
that the existing build initializes via `SyncSubmodule` (`git submodule update
--checkout --init`, `build/ninja_gen/src/installer.rs`). The earlier
"template-clone failure" was purely that those submodules were never populated —
and, on Windows, that the `SyncSubmodule` edge itself couldn't run until the
`render.rs` path fix let n2 spawn the runner. With that fix in place, a clean
checkout populates the templates automatically and both installer tests pass.
`.gitmodules` and the installer sources are unchanged.

## Assessment
All engine/logic changes are **new files**. The upstream contact is **4 files:
4 additive lines + 1 isolated Windows-compat build fix** — no edits to existing
function bodies (except the one `render.rs` `writeln!`). Rebasing onto a new Anki
release is expected to be conflict-free or a trivial re-application. The
additive-proto rule keeps the wire contract compatible across both bridges.
(Note: `AGENTS.md`/`CONTRIBUTORS`/`.claude/` also differ from upstream but are
project-meta, not engine code.)
