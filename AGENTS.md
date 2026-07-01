# AGENTS.md — Speedrun (Anki fork: GRE Math Subject Test trainer)

Cross-tool agent guide (Cursor + Claude Code). Keep this short; per-stack details live in nested AGENTS.md inside each repo (closest file wins). Full plan: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/BUILD-WORKFLOW.md`. Thesis: `brainlift/BrainLift.md`.

## Repo map (workspace root contains 4 git repos)
- `repos/anki/`            — fork of ankitects/anki. rslib (Rust engine), pylib/qt (Python), ts/ (Svelte UI). Desktop app + the Rust change.
- `repos/anki-android/`    — fork of AnkiDroid (Kotlin). The phone app.
- `repos/Anki-Android-Backend/` — fork of rsdroid. Cross-compiles rslib → JNI AAR for Android.
- (this repo) `speedrun`   — docs, BrainLift, research, external AI service, content pipeline.
The external AI/RAG service lives OUTSIDE all native libs — never import it into rslib or rsdroid.

## Tooling split (updated 2026-07-01)
- Claude Code = the builder: Rust engine, cross-repo Android build, AND the Svelte/TS + Qt frontend (owner call; keeps one subagent-driven build loop). TDD enforcement.
- Cursor = mission control: design specs, phase-gate reviews, umbrella docs, git merges/consolidation, monitoring. Avoids concurrent writes in `repos/*` while Claude builds.
- **Cross-agent channels:** Claude→Cursor via `.claude/watch.log` (Stop-hook digests Cursor tails); Cursor→Claude via `.claude/cursor-review.md` (gate feedback Claude reads at each gate). Both umbrella-only.

## Hard invariants (DO NOT VIOLATE)
- Every mutating backend op MUST go through `Collection::transact(Op::X, |col| {…})` returning `OpChanges`. Never write the DB directly; never `transact_no_undo` for user-facing mutations. (rslib/src/ops.rs, collection/transact.rs, undo/)
- `proto/anki/*.proto`: ONLY append new fields with NEW numbers. Never renumber/reuse; `reserved` removed fields.
- Sync: USN incremental deltas only; no CRDT; schema (`scm`) change forces one-way full sync.
- Every new file is AGPL-3.0-or-later. Credit Anki.

## TDD (enforced)
- Red → Green → Refactor. Write failing tests FIRST; do not write impl until tests fail.
- Tests are committed first and are READ-ONLY to implementing subagents. Never delete/skip/weaken a test to pass.
- Held-out evals + gold set live in `eval/holdout/` — agents may NOT read or edit that directory.
- The engine change needs ≥3 Rust unit tests + 1 Python-calling integration test.

## Grounding loop (codebase too big for one context window)
explore (Explore subagent) → plan (read-only) → GROUND every API via Serena (LSP) / ast-grep / `cargo check` → edit (prefer Serena `replace_symbol_body`) → verify (`just check`). Never edit before showing file paths + line numbers + LSP-confirmed symbol names.

## Boundaries (require human approval)
- Deleting tests, editing CI, touching `.proto` field numbers, adding native deps to rslib (OpenSSL banned — use rustls).

## Key commands (run inside repos/anki unless noted)
- Anki now drives builds via **`just`** recipes. Per `repos/anki/CLAUDE.md`, do NOT call `./ninja`, `./run`, or `tools/` scripts directly.
- Desktop run: `just run` · All checks: `just check` · Rust tests: `just test-rust` (or `cargo test -p anki <module>::` for quick iteration) · Format: `just format`
- `just` itself must be installed in Phase 0 (it wraps `tools/ninja`; N2 + MSYS2 rsync are the other Phase-0 gaps).
- Python integ: `uv run pytest pylib/tests/...`
- Android AAR: `cd ../Anki-Android-Backend && cargo run -p build_rust` (== `build.bat`; Windows host)
