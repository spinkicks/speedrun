# Speedrun — START HERE (current state & handoff)

**If you're a fresh chat/agent: read this, then `docs/DECISIONS.md` → `docs/PRD.md` → `docs/BUILD-WORKFLOW.md` → `brainlift/BrainLift.md`. `AGENTS.md` (root) auto-loads the invariants.**

## What this is
Speedrun: an honest GRE **Mathematics Subject Test** study app built on **Anki** (desktop + Android sharing one Rust engine). Owner: David Ordonez (GitHub `spinkicks`). License AGPL-3.0-or-later, credit Anki.

## Status (as of 2026-06-29, planning day)
- ✅ BrainLift complete (`brainlift/BrainLift.md`) — **9 SPOVs**, evidence-grounded, sources curated in `research/core-sources.md`. (SPOV 7 = owner's "overtrain" hypothesis; 8 = motivation follows success / Garon-Carrier; 9 = consolidation lowers cognitive load / Sweller.)
- ✅ PRD complete (`docs/PRD.md`) — hybrid architecture, data model, Rust change, 3 scores, content pipeline, sync, testing, tech stack, walking skeleton, risks.
- ✅ Architecture/feasibility (`docs/ARCHITECTURE.md`) and Build workflow (`docs/BUILD-WORKFLOW.md`).
- ✅ Decision log (`docs/DECISIONS.md`).
- ✅ GitHub: forks `spinkicks/anki`, `spinkicks/Anki-Android`, `spinkicks/Anki-Android-Backend`; umbrella `spinkicks/speedrun` (private, docs pushed). Local clones in `repos/` with `origin`=fork, `upstream`=original.
- ✅ Agent config: root `AGENTS.md` + `repos/anki/AGENTS.md` + `repos/Anki-Android-Backend/AGENTS.md`, `CLAUDE.md`, `.cursor/rules/speedrun.mdc`, `.cursor/mcp.json` (Serena), `repos/anki/.claude/settings.example.json` (hooks template).
- ✅ Toolchain (desktop) COMPLETE: Rust (rustup host has 1.96; the anki fork **auto-pins & builds with 1.92.0** via `repos/anki/rust-toolchain.toml` — verified active) (+ all Android targets), JDK 21 (JAVA_HOME set), uv, Node, **yarn 1.22**, ast-grep, repomix, **cargo-ndk**, gh, Claude Code 2.1.186, **Android Studio**.
- ✅ Serena MCP working: installed as uv tool (`C:\Users\davir\.local\bin\serena.exe`); use `serena start-mcp-server --context claude-code --project <anki>`. Claude Code shows Connected; Cursor `.cursor/mcp.json` points to the direct binary.
- ✅ **Phase-0 COMPLETE & reviewed** (2026-06-30): installed MSYS2 `rsync` + n2 (`tools/install-n2`) + `just`; `just run` launches forked Anki; `just build`/test suites green. Windows snag fixed: protoc codegen hit a transient Defender file-rename lock → resolved durably with an admin Defender **exclusion on `repos/anki`** (`Add-MpPreference -ExclusionPath`). Deferred (non-blocking, CI/env — fix before Wed installer deliverable): (1) Briefcase **installer template-clone** failure (network/template version); (2) **complexipy-diff vs main** lint. dprint/cosmetic formatting handled in-fork. Phase-2 (later): Android SDK/NDK/emulator via Android Studio first-run (NDK version per `libs.versions.toml`).

- ✅ Plan written + **reviewed against PRD** (`docs/plans/2026-06-30-walking-skeleton-wed-mvp.md`). APIs/paths grounded in `repos/anki` (proto auto-discovery, generated service dispatch, `Tag.name`, `Collection::new()` test helper, justfile recipes, pylib wiring, `.version`=26.05 all confirmed). One defect found & patched: `pub(crate) mod service;` was declared before `service.rs` existed (Task 1.2/1.3 → E0583); now deferred to Task 1.5. Verdict: safe to execute Phases 0–2.

- ✅ **Phase-1 COMPLETE & reviewed** (2026-06-30): `SpeedrunService.GetCoverage` read-only RPC landed via TDD on branch `feat/speedrun-coverage-rpc`, **pushed to `spinkicks/anki`** at **`b8b5369e7936ed5aa66c3fe5e613ba88c7ef15b7`** (the Phase-2 submodule pin). 4 Rust tests + 1 Python integration test green; `check:rust`, `check:pytest:pylib`, `check:minilints`, `check:format:proto` all pass; only the two known environmental groups remain (complexipy-diff ×2, installer ×2 — defer to before Wed installer deliverable). Licensing: David added to `repos/anki/CONTRIBUTORS` (BSD-3 CLA, company-approved as personal work); files carry AGPL-3.0-or-later headers. Two plan corrections found+patched in execution: (1) new `.proto` service needs explicit `protobuf!(speedrun, "speedrun");` registration in `rslib/proto/src/lib.rs`; (2) declared+registered service forces `Collection: SpeedrunService` impl before the crate compiles, so real in-crate GREEN is the Task 1.5 convergence, not 1.3.

## Immediate next step
**Phase 2 — One engine, two apps (Android).** #1 schedule risk (rsdroid build chain). Point `repos/Anki-Android-Backend` `anki` submodule at fork pin `b8b5369e…`, install exact NDK (ground from repo, don't hardcode) + confirm 4 Android Rust targets + cargo-ndk, build AAR (`build.bat`/`build.sh` BEFORE `cargo check`), `local_backend=true`, then AnkiDroid calls `get_coverage` and asserts `backend_version == "26.05"` == desktop. **Needs David's machine:** Android SDK/NDK install (Android Studio first-run) + an x86_64 emulator. Anki uses `just`, NOT `./ninja`/`./run`.

## Cadence
Mon=plan · Tue=heavy coding · Wed=both apps MVP (desktop+Android, NO AI) · Fri=AI+sync+3 scores · Sun=evals/ablation/ship.

## Key invariants (also in AGENTS.md)
- Mutations → `Collection::transact(Op::X, …)` returning `OpChanges`; never raw DB writes.
- `proto/anki/*.proto`: append-only field numbers.
- TDD: failing test first; tests read-only to implementer; `eval/holdout/` off-limits.
- Ground APIs via Serena/ast-grep/`cargo check` before editing.
- AI strictly after Wednesday (spec rule).
