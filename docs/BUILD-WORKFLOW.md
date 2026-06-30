# Speedrun — Build Workflow & Agentic "Software Factory"

Synthesized from `research/claude-running agentic workflow software factory.md` and `research/claude-navigating codebase.md`. This is our concrete playbook for building Speedrun with AI agents across the 4-language Anki/AnkiDroid codebase. Date-flag fast-moving tool features; verify before relying.

## 1. Tooling split (which tool for what)
- **Claude Code (have v2.1.186)** = primary orchestration: Rust engine changes, the cross-repo Android build, TDD enforcement (hooks), plan mode, subagents, worktrees. Strongest deterministic enforcement.
- **Cursor** = IDE-resident Svelte/TS UI work, fast inline edits, semantic "where is X?" search (indexed), multi-root cross-repo browsing.
- Drive both from one root **`AGENTS.md`** (cross-tool standard), referenced by `CLAUDE.md` and `.cursor/rules`.

## 2. The loop (research → plan → execute(TDD) → verify → review)
Maps to our installed **superpowers** skills: brainstorming → writing-plans → subagent-driven-development → executing-plans → verification-before-completion → TDD.
- Separate planning from coding (plan mode / Shift+Tab). Humans make ~70% of *planning* decisions; the agent makes ~80% of *execution* decisions.
- **Show evidence, not assertions** (test output, commands run). A **fresh subagent grades the work** (reviewer ≠ implementer).
- Two-stage per-task review: spec-compliance, then code-quality.

## 3. Subagents & worktrees
- Orchestrator → workers for independent, well-bounded tasks with a **frozen contract** (e.g., generate the TS interface / proto first, hand to both UI + RPC subagents). Start with 2–3 focused subagents, not a swarm (parallel agents cause file races / stale views / `.git/index.lock` contention).
- Hard isolation via **git worktrees** (`wt.sh`); merge via **PR-per-agent**. Ideal for the **3-build interleaving ablation** (off / random / topic-aware). **Do NOT** parallelize the rslib change and the rsdroid AAR until the engine API is frozen (cross-repo coupling).

## 4. Determinism over trust — Claude Code hooks (`.claude/settings.json`)
"Hooks guarantee behavior; prompts suggest it."
- **PostToolUse** on edits: `*.rs` → `./ninja format` + `cargo clippy` (inject errors back as feedback); `*.py` → `ruff`/`black`; `*.svelte|*.ts` → `prettier` + `svelte-check`. (Guard against formatter re-entry loops.)
- **PreToolUse** denials: raw SQL writes outside `storage/`; `.proto` field-number edits/renumbering; edits to test paths (anti-gaming); destructive `rm -rf`.
- **Stop**: run `./ninja check` for the touched stack; block completion on failure (check `stop_hook_active` to avoid loops).
- Add **`tdd-guard`** (blocks edits that skip RED / over-implement). Keep held-out evals in `eval/holdout/` that implementing agents cannot read/edit.

## 5. Verification gates (machine-checkable "done")
A task is "done" only when the relevant commands exit 0:
- Rust change: `cargo test -p anki <module>::` ≥3 pass; `./ninja check:rust` green.
- Python integration: `uv run pytest pylib/tests/test_*_integration.py` exits 0 (drives real backend via rsbridge).
- Undo/no-corruption: integration test asserts undo restores state; `PRAGMA integrity_check` = `ok`.
- One engine, two apps: desktop `./run` + AnkiDroid build load the SAME rslib (assert backend version string).
- Two-way sync: scripted two-collection sync; USN incremental path; forced full-sync on schema change.
- Three scores: unit tests assert each score ∈ range and returns ABSTAIN under the give-up rule.
- AI: every answer has a named source; beats BM25 baseline (nDCG/recall); gold-set pass-rate ≥ threshold; deterministic (fixed seed, temp 0).
- `make bench`: one command prints p50/p95/worst on a 50k-card deck.
- Crash test: kill mid-review ×20; `integrity_check`=ok each time.
- License: REUSE/AGPL header check.

## 6. Data-integrity invariants (encode in AGENTS.md + hooks)
- Every mutating backend op goes through `Collection::transact(Op::X, |col| {…})` returning `OpChanges`. Never write the DB directly; never `transact_no_undo` for user-facing mutations. (Types: `rslib/src/ops.rs`; impl `rslib/src/collection/transact.rs`; undo `rslib/src/undo/`.)
- `proto/anki/*.proto`: ONLY append new fields with NEW numbers; never renumber/reuse; `reserved` removed fields. (DB-persisted bytes must stay parseable.)
- Sync: USN incremental deltas only; no CRDT; schema change (`scm`) forces one-way full sync.

## 7. Codebase traversal (repos too big for one context window)
Three-layer search, escalate as needed: **lexical** (ripgrep) → **structural** (ast-grep) → **semantic** (Cursor index / embeddings — a recall aid, not exhaustive).
- **Serena MCP** (LSP: rust-analyzer + Kotlin LSP + ts) = go-to-definition / find-references / symbol-precise edits → kills hallucinated APIs. Highest-leverage add.
- **Repo maps:** `npx repomix <subtree> --compress` (signature-level packs); Aider `--map-tokens`; ctags for symbol index.
- **Loop:** explore (Explore subagent) → plan (read-only) → **ground every API via Serena/ast-grep/`cargo check`** → edit (prefer Serena `replace_symbol_body`, no line drift) → verify (`./ninja check`).
- **"Find the 3–5 files in rslib's scheduler/queue" recipe:** start at `proto/anki/scheduler.proto` (`rpc GetQueuedCards`) → `SchedulerService` impl → `rslib/src/scheduler/queue/builder/` (`QueueBuilder`, `gather_cards`, `build`). Ground names with `ast-grep -l rust -p 'QueueBuilder::new($$$A)'` + Serena `find_referencing_symbols`.

## 8. cargo-ndk / Android AAR runbook (the #1 schedule risk — de-risk FIRST)
In the `Anki-Android-Backend` fork:
- `git checkout … --recurse-submodules`; match `rust-toolchain.toml` to the anki submodule's Rust version.
- Install NDK version from `gradle/libs.versions.toml` (`versions.ndk`); `sdkmanager --install "ndk;$VERSION"`.
- `rustup target add aarch64-linux-android x86_64-linux-android armv7-linux-androideabi i686-linux-android`; `cargo install cargo-ndk`.
- **Run `./build.sh` BEFORE any `cargo check`** (submodule artifacts must be generated first).
- ABI→jniLibs mapping is exact: `aarch64-linux-android→arm64-v8a`, `armv7a-linux-androideabi→armeabi-v7a`, `i686-linux-android→x86`, `x86_64-linux-android→x86_64`.
- Keep `BACKEND_VERSION` (`Anki-Android-Backend/gradle.properties`) == `ext.ankidroid_backend_version` (`Anki-Android/build.gradle`).
- In AnkiDroid: `local_backend=true` in `local.properties` → uses `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`; add Kotlin wrapper in `libanki/`.
- Banned: OpenSSL/vendored C deps in rslib (cross-compile trap) — prefer rustls.

## 9. Environment setup (Phase 0) — install list with versions
Status on this machine: have Node v24.11.1, Python 3.14, Claude Code 2.1.186, gh 2.95. Missing below.
- **Rust:** `rustup` (toolchain auto-pinned by `rust-toolchain.toml` = 1.92.0 in our anki fork). `winget install Rustlang.Rustup`.
- **N2/Ninja:** `bash tools/install-n2` (use MSYS2 bash on Windows).
- **Python deps:** `uv` (`winget install astral-sh.uv`); Anki manages its own venv via uv.
- **JS:** yarn (`corepack enable` with Node 24, or `npm i -g yarn`).
- **JDK 21 (Temurin):** `winget install EclipseAdoptium.Temurin.21.JDK`; set `JAVA_HOME`.
- **Android:** Android SDK + cmdline-tools; NDK version from `libs.versions.toml`; `cargo install cargo-ndk`; `rustup target add` the 4 Android targets.
- **Windows build notes:** MSVC Build Tools + Windows SDK; MSYS2 (`pacman -S git rsync`); path short/no-spaces (relocate to `C:\anki` if linker/long-path errors).
- **Grounding/agentic tools:** `npm i -g @ast-grep/cli` (ast-grep), `npx repomix` (no install), Serena via `uv tool install` (see §10).
> Recommendation: run Phase 0 as the FIRST step of the build session and verify by `./run` (desktop) + a stock `local_backend` AAR — installing blind without building risks version mismatches.

## 10. MCPs / plugins / skills to add
- **Serena MCP (DO):** `uv tool install` then register in Cursor (`.cursor/mcp.json` / settings) and Claude Code. Attach to all three repos. Onboarding fills context — start a fresh chat after it completes.
- **ast-grep MCP (optional):** experimental server for structural search in-agent.
- **Skills already installed:** superpowers (brainstorming, writing-plans, subagent-driven-development, executing-plans, verification-before-completion, TDD) + firebase + cursor skills.
- **Custom skills to author for us:** `rslib-change` (proto→Rust→Python recipe + invariants), `cargo-ndk-runbook` (§8), `speedrun-card-author` (note-type authoring + topic tagging), `make-bench` (perf harness).

## 11. Day-of execution playbook
- **Phase 0 (setup):** install toolchains (§9); write root + per-stack `AGENTS.md`; wire Claude Code hooks (§4) + tdd-guard; install Serena/ast-grep; create `wt.sh` + `make bench` skeleton. Tool split: Claude Code = engine/Android/orchestration; Cursor = Svelte/TS UI.
- **Phase 1 (→Wed):** `./run` clean baseline; TDD a tiny real `rslib` change (queue builder or read-only RPC) — ≥3 Rust tests (RED→GREEN), route mutations through `transact`, additive proto; Python-calling integration test (undo + integrity_check). 
- **Phase 2 (→Wed):** de-risk the AAR (§8); `local_backend=true`; SAME engine on desktop + Android (assert backend version). Walking skeleton complete.
- **Phase 3 (→Fri):** interleaving 3-build ablation (worktrees); three scores w/ ranges + abstention; two-way sync + conflict test.
- **Phase 4 (→Sun):** external AI/RAG service (outside native libs); AI eval gates (held-out, deterministic); crash tests; final `make bench`; CI matrix green; REUSE/AGPL check.
- **Continuous:** per-task two-stage review; `/compact` at ~60% context; PR-per-agent; show evidence.

## 12. Caveats (verify before relying)
- Cursor/Claude Code version features move weekly (subagents, multi-root, hooks) — verify with `--version` / changelogs.
- Embeddings have a proven recall ceiling — semantic search complements, never replaces, exact search.
- TDD gaming is real (agents delete/weaken tests) — read-only tests + tdd-guard + PreToolUse denials are non-optional.
- Keep `AGENTS.md` short/command-focused — bloated context files *reduce* success and add >20% cost (ETH study).
