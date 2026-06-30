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
- ⏳ Phase-0 (first build): install `just` + N2 (`tools/install-n2`) + MSYS2 (`pacman -S git rsync`); build via `just run` / `just check`. Phase-2: Android SDK/NDK/emulator via Android Studio first-run (NDK version per `libs.versions.toml`).

- ✅ Plan written + **reviewed against PRD** (`docs/plans/2026-06-30-walking-skeleton-wed-mvp.md`). APIs/paths grounded in `repos/anki` (proto auto-discovery, generated service dispatch, `Tag.name`, `Collection::new()` test helper, justfile recipes, pylib wiring, `.version`=26.05 all confirmed). One defect found & patched: `pub(crate) mod service;` was declared before `service.rs` existed (Task 1.2/1.3 → E0583); now deferred to Task 1.5. Verdict: safe to execute Phases 0–2.

## Immediate next step
**Execute Phase 0** (Claude Code, via subagent-driven-development): install MSYS2 `rsync` + n2 (`tools/install-n2`) + `just`, then `just run` (launch) and `just check` (green) on an unmodified `repos/anki` checkout. Feasibility gate before Phase 1. Anki uses `just`, NOT `./ninja`/`./run`, per `repos/anki/CLAUDE.md`.

## Cadence
Mon=plan · Tue=heavy coding · Wed=both apps MVP (desktop+Android, NO AI) · Fri=AI+sync+3 scores · Sun=evals/ablation/ship.

## Key invariants (also in AGENTS.md)
- Mutations → `Collection::transact(Op::X, …)` returning `OpChanges`; never raw DB writes.
- `proto/anki/*.proto`: append-only field numbers.
- TDD: failing test first; tests read-only to implementer; `eval/holdout/` off-limits.
- Ground APIs via Serena/ast-grep/`cargo check` before editing.
- AI strictly after Wednesday (spec rule).
