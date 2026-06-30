# Speedrun — START HERE (current state & handoff)

**If you're a fresh chat/agent: read this, then `docs/DECISIONS.md` → `docs/PRD.md` → `docs/BUILD-WORKFLOW.md` → `brainlift/BrainLift.md`. `AGENTS.md` (root) auto-loads the invariants.**

## What this is
Speedrun: an honest GRE **Mathematics Subject Test** study app built on **Anki** (desktop + Android sharing one Rust engine). Owner: David Ordonez (GitHub `spinkicks`). License AGPL-3.0-or-later, credit Anki.

## Status (as of 2026-06-29, planning day)
- ✅ BrainLift complete (`brainlift/BrainLift.md`) — 6 SPOVs, evidence-grounded, sources curated in `research/core-sources.md`.
- ✅ PRD complete (`docs/PRD.md`) — hybrid architecture, data model, Rust change, 3 scores, content pipeline, sync, testing, tech stack, walking skeleton, risks.
- ✅ Architecture/feasibility (`docs/ARCHITECTURE.md`) and Build workflow (`docs/BUILD-WORKFLOW.md`).
- ✅ Decision log (`docs/DECISIONS.md`).
- ✅ GitHub: forks `spinkicks/anki`, `spinkicks/Anki-Android`, `spinkicks/Anki-Android-Backend`; umbrella `spinkicks/speedrun` (private, docs pushed). Local clones in `repos/` with `origin`=fork, `upstream`=original.
- ✅ Agent config: root `AGENTS.md` + `repos/anki/AGENTS.md` + `repos/Anki-Android-Backend/AGENTS.md`, `CLAUDE.md`, `.cursor/rules/speedrun.mdc`, `.cursor/mcp.json` (Serena), `repos/anki/.claude/settings.example.json` (hooks template).
- ✅ Toolchain (desktop): Rust 1.96 (+ Android targets), JDK 21, uv, Node, ast-grep, repomix, gh, Claude Code 2.1.186.
- ⏳ In progress / verify: cargo-ndk, Android Studio (SDK/NDK/emulator), Serena MCP first-run build. yarn + N2 + ANDROID_HOME/JAVA_HOME env vars pending (Phase 0).

## Immediate next step
Write the **implementation plan** via the `writing-plans` skill, scoped to the **walking skeleton → Wednesday MVP** (Phases 0–2): get Anki building (`./run`) → tiny Rust change + read-only `SpeedrunService` RPC with TDD (≥3 Rust tests + 1 Python integration) → same engine on Android via local AAR (`local_backend=true`). Save to `docs/plans/`.

## Cadence
Mon=plan · Tue=heavy coding · Wed=both apps MVP (desktop+Android, NO AI) · Fri=AI+sync+3 scores · Sun=evals/ablation/ship.

## Key invariants (also in AGENTS.md)
- Mutations → `Collection::transact(Op::X, …)` returning `OpChanges`; never raw DB writes.
- `proto/anki/*.proto`: append-only field numbers.
- TDD: failing test first; tests read-only to implementer; `eval/holdout/` off-limits.
- Ground APIs via Serena/ast-grep/`cargo check` before editing.
- AI strictly after Wednesday (spec rule).
