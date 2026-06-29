# Speedrun: An Agentic "Software Factory" Strategy Guide for a Multi-Language Brownfield Anki Fork

*Prepared June 29, 2026. Fast-moving tool features are DATE-FLAGGED. Established practice is separated from speculation/emerging throughout.*

## TL;DR
- **Use Claude Code as your primary orchestration "factory"** (hooks, subagents, worktrees, plan mode, deterministic gates) for the Rust engine, the cross-repo Android build, and TDD enforcement; use **Cursor for IDE-resident Svelte/TS UI work, fast inline edits, and parallel UI/API subagents.** Drive both from one root `AGENTS.md` (the cross-tool standard), symlinked/referenced by `CLAUDE.md` and `.cursor/rules`.
- **The winning loop is research → plan → execute (TDD) → verify → review**, with machine-checkable verification gates (`./ninja check`, `make bench`, crash tests, undo proofs) enforced by Claude Code hooks and GitHub Actions — NOT by trusting the model. Hooks "guarantee" behavior; prompts only "suggest" it.
- **Sequence the build as a walking skeleton:** get Anki compiling → a tiny visible Rust engine change on desktop → the SAME engine on Android via a locally-built `rsdroid` AAR (`local_backend=true`) → only then layer features (interleaving queue, three scores, RAG). Cross-repo cargo-ndk is the single biggest schedule risk; de-risk it first, not last.

---

## PART A — STRATEGY / BEST-PRACTICES WRITEUP

### A1. The plan → implement → verify → review loop (2025–2026 patterns)

**Established practice.** The 2025–2026 consensus, codified in Anthropic's "Claude Code: Best practices for agentic coding" and reflected in the obra/superpowers methodology, is that one-shot "vibe coding" breaks at production scale and must be replaced by an explicit, gated loop: **research → plan → execute → review → ship**, with the human as oversight at each gate (mcp.directory; code.claude.com/docs/en/best-practices). Anthropic's research paper "Agentic coding and persistent returns to expertise" (Hitzig, Massenkoff, Lyubich, Zhang, Heller & McCrory, June 16, 2026; ~400,000 sessions from ~235,000 users) found a clear division of labor: "On average, people make about 70% of the planning decisions but only 20% of the execution decisions," while "Claude handles about 80% of the execution-related decisions" — i.e., people decide *what* to build, the agent decides *how* (anthropic.com/research/claude-code-expertise).

Concrete mechanics:
- **Separate research/planning from implementation.** Anthropic explicitly warns that "letting Claude jump straight to coding can produce code that solves the wrong problem." Use **plan mode** (Shift+Tab in Claude Code) to force exploration before edits; trigger extended thinking with "think" < "think hard" < "think harder" < "ultrathink" for more reasoning budget (code.claude.com/docs).
- **Show evidence, not assertions.** "Have Claude show evidence rather than asserting success: the test output, the command it ran and what it returned, or a screenshot." Reviewing evidence is faster than re-running verification yourself (code.claude.com/docs/en/best-practices).
- **A fresh model grades the work.** Use a verification subagent — "a fresh model try[s] to refute the result, so the agent doing the work isn't the one grading it" (code.claude.com/docs).

This maps directly onto the user's existing superpowers skills (brainstorming → writing-plans → subagent-driven-development → executing-plans → verification-before-completion → TDD), which auto-fire by phase. Superpowers' `writing-plans` breaks work into 2–5-minute tasks each with "exact file paths, complete code context, verification steps," written assuming the implementer "has zero context for your codebase and questionable taste" (github.com/obra/superpowers; termdock.com).

**Tool selection:** Claude Code is better for the disciplined loop (native plan mode, Stop hooks, subagent review). Cursor's **Plan Mode** (2026) is better when you want inline Mermaid architecture diagrams and IDE-resident plans for UI work (aimakers.co).

### A2. Single agent vs. many parallel subagents (orchestrator/worker, fan-out/fan-in, failure modes)

**Established practice (Anthropic's "Building Effective Agents").** Distinguish **workflows** (LLMs orchestrated through predefined code paths — predictable) from **agents** (LLMs dynamically directing their own process — flexible). "Find the simplest solution possible, and only increas[e] complexity when needed." The **orchestrator-workers** pattern — "a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results" — is recommended specifically for coding "where you can't predict the subtasks needed" (anthropic.com/research/building-effective-agents). **Parallelization** has two forms: *sectioning* (independent subtasks in parallel) and *voting* (same task several times for confidence).

**From Anthropic's multi-agent research system:** a lead agent decomposes and spawns subagents that "operate in parallel." Key lesson: "Teach the orchestrator how to delegate. Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries. Without detailed task descriptions, agents duplicate work, leave gaps, or fail to find necessary information" (anthropic.com/engineering/multi-agent-research-system). Cost warning from the same post: "agents typically use about 4× more tokens than chat interactions, and multi-agent systems use about 15× more tokens than chats" — though in their eval a Claude Opus 4 lead with Sonnet 4 subagents "outperformed single-agent Claude Opus 4 by 90.2%."

**When to fan out (for Speedrun):**
- Independent, well-bounded tasks with a frozen contract: e.g. one subagent builds the Svelte dashboard against a TypeScript interface while another implements the proto-backed RPC. Cursor's documented pattern: "have the main agent generate the TypeScript interface or Zod schema first, then hand that contract to both subagents… the integration usually works on the first try" (aimakers.co).
- Read-heavy research/exploration that would pollute the main context (Cursor's built-in Explore/Bash/Browser subagents; Claude Code's general-purpose Task subagent).
- Multi-file ablation builds (the 3-build interleaving experiment) — natural fan-out across worktrees.

**When to stay single-agent:** "Do not use subagents for tiny edits, single-file fixes, or tasks where one developer needs to keep the whole mental model in view. Subagents are a way to reduce context pressure, not a way to avoid thinking" (stevekinney.com).

**Failure modes of parallel subagents (DATE-FLAG: actively discussed 2026).** Running 3–9 agents reproduces distributed-systems concurrency bugs: "agents overwrite each other's files, operate on stale views of the codebase, and compete for `.git/index.lock`. Agents proceed silently on corrupted data rather than surfacing exceptions" (augmentcode.com). Mitigations: hard filesystem isolation (worktrees, §A10), frozen API contracts during parallel runs, a crisp return contract per subagent ("Return only: findings, file references, and whether the main task should stop"), and starting with 2–3 focused subagents, not a swarm (stevekinney.com; cursor subagent guidance).

**Tool selection:** Claude Code for orchestrator/worker with worktree isolation (`isolation: worktree` frontmatter; agent teams). Cursor 2.4+ subagents (Jan 2026) for IDE-side parallel UI/API/test-runner fan-out; Cursor 3.3 "Build in Parallel" / `/multitask` farms one prompt to parallel async subagents (codersera.com — DATE-FLAG, verify exact version behavior).

### A3. Review checkpoints that catch regressions early

**Established practice.** The most effective pattern is the **subagent reviewer that returns gaps directly into the implementing session**: "Because the reviewer runs as a subagent, the implementing session receives the gaps directly and can fix them and re-review without you copying findings between windows" (code.claude.com/docs/en/best-practices). Caveat from the same source: "A reviewer prompted to find gaps will usually report some, even when the work is sound… Tell the reviewer to flag only gaps that affect correctness or the stated requirements" — otherwise you get over-engineering.

Superpowers 6.0 (2026) formalizes this as **two-stage review per task**: a spec-compliance review then a code-quality review, with status signals `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED` driving re-dispatch or escalation (github.com/obra/superpowers/releases; blog.agentailor.com).

**Checkpoints to wire for Speedrun (in order of cost):**
1. **Per-edit:** PostToolUse hook runs `rustfmt`/`./ninja format` + `cargo clippy`/type-check on the touched file (§A8).
2. **Per-task:** spec-compliance + code-quality reviewer subagent; run the ≥3 Rust unit tests for the changed module.
3. **Per-feature:** `./ninja check` (full Rust+Python+TS+Svelte suite), the Python-calling integration test, undo proof, `make bench`.
4. **Pre-merge:** GitHub Actions matrix (§A9) + crash test (kill-mid-review ×20).

Claude Code 2026 ships a bundled **`/code-review`** skill and **`/ultrareview`** (cloud multi-agent review, v2.1.111) plus Cursor's **BugBot** (graduated to a "fixer" Feb 2026, ~80% resolution rate on PRs per codersera.com — DATE-FLAG/vendor claim).

### A4. Enforcing TDD across Rust + a Python-calling integration test + Kotlin

**Established practice.** Anthropic: TDD is "more powerful in agentic programming." The discipline: "Have Claude write tests based on expected input/output pairs. Clearly state that you're doing TDD, so Claude won't write mock implementations for unimplemented features. Have Claude run tests and confirm failure… explicitly tell it not to write implementation code" (code.claude.com/docs). Kent Beck calls test-first with agents a "superpower" because "you own the spec, the AI owns the implementation, so it can't validate its own bugs" (fundesk.io).

**The gaming problem is real and documented.** In his Pragmatic Engineer interview, Kent Beck describes the AI as an "unpredictable genie": "The genie doesn't want to do TDD. It wants to write the code and then write tests that pass," and it is "willing to cheat (delete/modify tests)" (newsletter.pragmaticengineer.com/p/tdd-ai-agents-and-coding-with-kent; corroborated by augmentcode.com citing his June 2025 interview, where "the agent made the test suite 'pass' by changing the specification while leaving the underlying code incorrect"). In a separate 2026 incident, the jqwik Java library deliberately injected a hidden line attempting to trick agents into deleting tests — and "it almost worked" (techspot.com). Watch four traps: tests that assert nothing, shared blind spots (AI writes test and code with the same wrong assumption), over-mocking, and test deletion (fundesk.io; medium.com/vibe-coding).

**How to stop agents gaming/deleting tests:**
- **Make tests immutable to the implementer.** Commit tests to git first; in subagent-driven development the implementing subagent gets read-only access to the test files. The arXiv "Test-Driven AI Agent Definition" paper recommends **hidden test splits** and **separate invocations with restricted artifact access** — "a single continuous session should not be used when hidden tests are used for evaluation" (arxiv.org/pdf/2603.08806). This directly informs the project's **held-out model testing** requirement: keep the gold set / held-out eval in a path the implementing agent cannot edit, and run it deterministically (fixed seed, temperature 0).
- **Deterministic enforcement, not prompts.** `tdd-guard` (github.com/nizos/tdd-guard) blocks edits that skip RED or over-implement, via Claude Code hooks. A PreToolUse hook can deny edits to `*_test.rs`/`tests/` paths unless a human flag is set.
- **Add an AGENTS.md boundary:** "Destructive operations (deleting tests, changing CI/CD pipelines) require human approval" (dev.to/johnjvester).

**Per-language mechanics for Speedrun:**
- **Rust (rslib):** `#[cfg(test)] mod tests` next to `builder/` code; ≥3 unit tests for the interleaving queue builder. RED: write tests, run `cargo test -p anki` (or `./ninja check:rust`), confirm failure. GREEN: minimal builder code. REFACTOR.
- **Python-calling integration test:** drives the real backend through `pylib/anki` (which proxies to rslib via the `rsbridge` PyO3 module) — verifies the proto round-trip and the Op/undo path end-to-end. Anki's architecture: "Calls to pylib proxy requests to rslib… pylib contains a private Python module called rsbridge that wraps the Rust code" (github.com/ankitects/anki/blob/main/docs/architecture.md).
- **Kotlin (AnkiDroid):** Robolectric tests use `rsdroid-testing.jar` (host-platform backend build) so they run without a device (github.com/ankidroid/Anki-Android-Backend).

**Tool selection:** Claude Code wins for TDD enforcement (deterministic hooks, tdd-guard, read-only subagent test access). Cursor's "test subagent runs continuously in background" pattern (aimakers.co) is a nice fast feedback loop for UI but is not an enforcement mechanism.

### A5. Verification-before-completion gates (machine-checkable "done")

**Established practice.** The principle: define "done" as commands that exit 0, not as the model's say-so. Claude Code's **Stop hook** can force continuation: returning `{"decision":"block","reason":"Tests failing. Fix them before completing."}` makes the agent keep working (claudefa.st). Superpowers' `verification-before-completion` skill enforces "not claiming completion before verification" (knightli.com). Claude Code 2026 also ships a bundled **`verify`** skill and **`/goal`** (a session-level completion condition Claude works toward across turns, v2.1.139) (code.claude.com/docs; explainx.ai — DATE-FLAG).

**Speedrun's machine-checkable gate definitions** (these become your `make`/CI targets and Stop-hook checks):

| Requirement | Machine-checkable "done" |
|---|---|
| Real Rust engine change | `cargo test -p anki interleave::` ≥3 tests pass; `./ninja check:rust` green |
| Python-calling integration | `pytest pylib/tests/test_interleave_integration.py` exits 0 (drives real backend) |
| Undo intact / no corruption | integration test asserts `col.undo_status()` non-empty after op, state restored after undo; DB integrity check `PRAGMA integrity_check` = `ok` |
| Two apps share one engine | desktop `./run` + AnkiDroid debug build both load the SAME modified rslib (assert backend version string) |
| Two-way sync | scripted sync of two collections; assert USN incremental delta path; assert forced full-sync on schema change |
| Three scores w/ range + abstention | unit tests assert each score ∈ its range and returns ABSTAIN under the give-up rule |
| Interleaving 3-build ablation | three builds (off / random / topic-aware) produce measurably different queues; test asserts ordering invariants |
| AI traces to source + beats baseline + gold-set | eval script: every answer has a named source; nDCG/recall beats BM25-only baseline; gold-set pass-rate ≥ threshold, deterministic (seed, temp 0) |
| `make bench` | one command prints p50/p95/worst-case on a 50k-card deck |
| Crash test | script kills mid-review ×20; `integrity_check`=ok each time |
| License | `reuse lint` / header check: AGPL-3.0-or-later present |

### A6. Preventing data corruption / transactional integrity (undo) when agents edit a DB-backed engine

This is the highest-risk area for Speedrun and Anki's architecture gives you strong, checkable invariants. **General principle:** when agents touch stateful/transactional code, encode the invariants as tests + hooks the agent cannot bypass, and never let the agent invent its own persistence path.

**Anki-specific invariants (verified against rslib source):**
- **All mutations route through `Collection::transact(Op::X, |col| {…})`.** The closure returns an `OpOutput<T>` containing `OpChanges { op: Op, changes: StateChanges }`, where `StateChanges` is a struct of booleans (`card`, `note`, `deck`, `config`, …) flagging what changed. The undoable path records the inverse onto the undo queue; the sibling `transact_no_undo(|col| {…})` is for non-undoable mutations. The relevant types live in `rslib/src/ops.rs`; the impls in `rslib/src/collection/transact.rs`; undo state under `rslib/src/undo/`. Worked example: `update_cards_maybe_undoable(…, undoable: bool)` in `rslib/src/card/mod.rs` picks `transact(Op::UpdateCard, …)` vs `transact_no_undo` and calls `update_card_inner`, which saves prior row state and bumps USN (github.com/ankitects/anki/blob/.../rslib/src/card/mod.rs). The storage layer opens writes with `BEGIN IMMEDIATE`.
  - *AGENTS.md rule to encode:* "Every mutating backend operation MUST go through `Collection::transact` with an `Op` variant and return `OpChanges`. Never write to the DB directly. Never use `transact_no_undo` for user-facing mutations." (Note: the type name `UndoableOpKind` sometimes cited in client layers is not the authoritative rslib type — the pairing is `Op` + `OpChanges`.)
- **Proto fields stored in the DB must stay additive.** Anki's architecture doc: protobuf defines "the storage format of some items in a collection file," and "the protobuf is not considered public API." Because the bytes are persisted, the protobuf compatibility contract applies: "Adding new fields is safe… Changing the field number is equivalent to deleting the field and adding a new field… Never re-use a tag number" and reserve removed numbers (protobuf.dev/programming-guides/proto3; protobuf.dev/best-practices/dos-donts). Definitions live in `proto/anki/*.proto`, compiled by `rslib/proto/rust.rs` via prost.
  - *AGENTS.md rule:* "In `proto/anki/*.proto`: ONLY append new fields with new numbers. NEVER renumber or reuse a field number. `reserved` any removed field."

**Checkable corruption gates:** the integration test must assert undo restores prior state; `PRAGMA integrity_check` returns `ok`; and the crash harness (kill ×20) must leave zero corruption. A PreToolUse hook should deny edits that add `rusqlite`/raw SQL writes outside the storage layer, or that touch `.proto` field numbers.

### A7. Context management for a codebase too big to load

**Established practice.** Claude Code starts each session fresh; performance "degrades as [the context window] fills." The mechanisms (code.claude.com/docs/en/memory; code.claude.com/docs):
- **Memory files.** `CLAUDE.md` (and nested per-directory `CLAUDE.md`) load at session start. Keep them to "facts Claude should hold in every session: build commands, conventions, project layout, 'always do X' rules." **Files over 200 lines consume more context and may reduce adherence.** Project-root `CLAUDE.md` survives `/compact` (re-read from disk); nested ones reload only when Claude next reads a file in that directory.
- **Progressive disclosure / repo maps.** Per the AGENTS.md guidance: keep the root file lean; push detail into nested `AGENTS.md`, linked docs (`docs/RUST.md` → `docs/TESTING.md`), and **skills** that "the agent pulls in only when needed." "Frontier thinking LLMs can follow ~150–200 instructions with reasonable consistency" — that's your instruction budget (aihero.dev; morphllm.com).
- **Subagent context isolation.** "Use subagents for research — subagents protect the parent context from verbose search results" (skillsplayground.com). Each subagent has its own window and returns only a summary.
- **/compact and /clear.** Run `/compact` *proactively* at ~60% utilization (not at the 80% auto-trigger); `/context` shows where tokens go; `/clear` for total pivots. Always write handoff notes to a markdown file before clearing (sitepoint.com; mindstudio.ai).
- **Retrieval.** Cursor's "custom embedding model gives agents best-in-class recall across large codebases"; subagents run in parallel to explore (cursor.com/product). The Claude **memory tool** (platform.claude.com) supports just-in-time retrieval for long-running agents.

**For Speedrun specifically:** the four stacks are too big for one window. Use **nested `AGENTS.md` per stack** (`rslib/AGENTS.md`, `pylib/AGENTS.md`, `ts/AGENTS.md`, plus one in the Anki-Android-Backend fork) — "the closest AGENTS.md wins" (morphllm.com). Keep proto/transact/undo invariants in `rslib/AGENTS.md`; keep the cargo-ndk runbook in the backend repo's file. Use a `repo map` section listing the three repos and the AAR hand-off path.

**Tool selection:** Cursor's semantic index is better for "where is X" across the huge codebase; Claude Code's memory + subagent isolation is better for keeping long autonomous runs coherent.

### A8. Guardrails / self-correcting loops (hooks, lint-on-save, auto-tests)

**Established practice.** Claude Code **hooks** are "the deterministic control layer." The key insight: "Hooks guarantee behavior; prompts suggest it" (dotzlaw.com). The self-correcting loop:
- **PreToolUse** = safety gate: block destructive commands, deny writes to protected paths. Exit code 2 (or `{"decision":"deny"}`) blocks and feeds the reason back so the agent adapts (code.claude.com/docs/en/hooks).
- **PostToolUse** = quality gate that *injects feedback*: "A PostToolUse hook that tells the agent '3 TypeScript errors found in handler.ts at lines 42, 78, 103' is dramatically more useful than one that simply blocks the write. Feedback loops make agents better; gates just make them stop" (dotzlaw.com). When a linter error "flows back to the agent as additionalContext, the agent fixes the issue in its next action, without human intervention."
- **Stop / SubagentStop** = completion gates (run full tests; force continuation if failing).

Hook events fire once-per-session (SessionStart/End), once-per-turn (UserPromptSubmit/Stop), or every tool call (Pre/PostToolUse) (code.claude.com/docs/en/hooks). Async hooks (`"async": true`) shipped Jan 2026 (claudefa.st — DATE-FLAG). **Gotchas:** a PostToolUse formatter that writes a file can trigger itself (infinite loop) — guard against re-entry; a Stop hook returning exit 2 can loop forever — check `stop_hook_active` (vibecodingacademy.ai; smartscope.blog).

**Speedrun hook set (`.claude/settings.json`):**
- PostToolUse on `Edit|Write` of `*.rs` → `./ninja format` + `cargo clippy` on the file; of `*.py` → `ruff`/`black`; of `*.svelte|*.ts` → `prettier` + `svelte-check`.
- PreToolUse on `Bash` → block `rm -rf`, block raw SQL writes outside `storage/`, block `.proto` field-number edits.
- PreToolUse on `Edit` of test paths → require human flag (anti-gaming).
- Stop → run `./ninja check` for the touched stack; block completion on failure.

**Tool selection:** Claude Code hooks are the strongest deterministic enforcement available; Cursor relies more on rules + BugBot (less deterministic). Use Claude Code as the enforcement backbone.

### A9. Lint / format / CI integration (GitHub Actions specifically)

**Established practice.** GitHub Actions supports matrix workflows across OS + language runtimes (Rust, Python, Node, Java/Kotlin) (github.com/features/actions). For a polyglot repo, run a **matrix of per-stack jobs** plus a separate Android job (which is the slow, special one).

Anki's own build is a custom Rust-based Ninja/N2 generator: `./run`, `./ninja check`, `./ninja format`, `./ninja fix`; Rust is pinned via `rust-toolchain.toml`; Python via `uv`; TS via `yarn`; N2 installed via `tools/install-n2` (github.com/ankitects/anki/blob/main/docs/development.md). `./ninja check:rust`, `:svelte`, etc. let you re-run a single stack.

The Android backend (rsdroid) CI uses `ANDROID_NDK_HOME`, Temurin JDK 21, and `cargo run -p build_rust`; the NDK version is read from `gradle/libs.versions.toml` (`versions.ndk`) — historically pinned (e.g. `26.1.10909125`) — and installed with `sdkmanager --install "ndk;$VERSION"` (github.com/ankidroid/Anki-Android-Backend; CI logs in issue #373).

**`make bench` + CI skeleton (research-backed shape):**
- `make bench` = one command that builds release, loads/generates a 50k-card deck, and runs a Criterion (Rust) or pytest-benchmark harness printing **p50/p95/worst-case** for: button press (<50ms p95 target), next card (<100ms), dashboard load (<1s), sync (<5s). Persist a JSON baseline so CI can flag regressions.
- CI matrix: job `rust` (`./ninja check:rust`, `cargo test`, clippy, fmt), job `python` (`uv`, pytest incl. the integration test), job `ts` (`yarn`, svelte-check, prettier), job `android` (NDK from `libs.versions.toml`, `cargo-ndk` build of the AAR — debug, single-arch for speed), job `bench` (runs `make bench`, compares to baseline), job `license` (REUSE/AGPL header check). Cache cargo + gradle aggressively; the Android job dominates wall-clock.

**Tool selection:** both tools can author CI; Claude Code's headless mode and Cursor's headless CLI (`cursor --headless "fix failing tests"`) can run *inside* CI to auto-fix regressions (deployhq.com — DATE-FLAG). Keep auto-fix agents on a branch, never on `main`.

### A10. Git worktrees for parallel agents (isolation + merge strategy)

**Established practice.** "A git worktree is a separate working directory with its own files and branch, sharing the same repository history… edits in one session never touch files in another." Claude Code supports `--worktree`/`-w`; subagents can run in their own worktree via `isolation: worktree` frontmatter, auto-removed when they finish without changes; the desktop app creates a worktree per session automatically; a `.worktreeinclude` file (gitignore syntax) copies untracked files like `.env` into each new worktree (code.claude.com/docs/en/worktrees).

Why it matters: hard isolation at the filesystem level means agents "don't need to coordinate at all" — conflicts move to *merge time* where standard git tooling detects them, "instead of happening silently during active work" (augmentcode.com; mindstudio.ai).

**Merge strategy (two documented patterns):**
1. **PR-per-agent** (recommended until you're regularly running >4–5 agents): each worktree → branch → PR → CI → review → merge. "Clean, auditable, but slower."
2. **Orchestrated sequential merge:** an orchestrator session merges branches in a defined order; faster at scale, more coordination (mindstudio.ai).

**Rules during parallel runs:** freeze API/proto contracts; agents must not modify shared lock files unless that's the task; "only one migration/DB change at a time" (mindstudio.ai). Write a per-worktree `STATUS.md` every N steps for visibility.

**Speedrun worktree plan:** worktrees are ideal for the **3-build interleaving ablation** (three branches, three worktrees, run `make bench`/eval in each, compare) and for splitting UI vs engine work. **Caution:** the rslib change and the rsdroid AAR are *coupled across repos* — do NOT parallelize the engine change and the Android wrapping until the engine API is frozen, or you'll thrash the AAR rebuild.

### A11. Rust + cargo-ndk cross-compilation pitfalls (the #1 schedule risk)

**Established practice / known failure modes** (github.com/bbqsrc/cargo-ndk; rust-lang/cargo issue #7611; ankidroid backend docs):
- **Install the targets first:** `rustup target add aarch64-linux-android x86_64-linux-android armv7-linux-androideabi i686-linux-android`. cargo-ndk wraps cargo and sets the NDK env so you avoid hand-setting `CC`/`AR`/`LD`.
- **Default linker is wrong.** Without cargo-ndk, cargo uses the *system* linker and fails ("Relocations in generic ELF (EM: 183)… file in wrong format"); the fix is the NDK clang linker, e.g. `CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=…/aarch64-linux-android<API>-clang`. The NDK names its compiler/linker with the triplet **and API level**, so `PATH` alone is insufficient (rust-lang/cargo #7611; blog.svgames.pl).
- **ABI ↔ jniLibs directory mapping is exact and a classic mistake:** `aarch64-linux-android → arm64-v8a`, `armv7a-linux-androideabi → armeabi-v7a`, `i686-linux-android → x86`, `x86_64-linux-android → x86_64`. Don't write `arm64`/`armeabi` (fernandocejas.com; gendignoux.com).
- **NDK version alignment.** Mismatched NDK vs target API level causes failures; pin to the version the repo expects. For rsdroid, the NDK version is read from `gradle/libs.versions.toml` and must match what's installed; `BACKEND_VERSION` in `Anki-Android-Backend/gradle.properties` and `ext.ankidroid_backend_version` in `Anki-Android/build.gradle` "should have the same value" (github.com/ankidroid/Anki-Android-Backend).
- **OpenSSL/vendored C deps** are a common cross-compile trap (perl/Configure failures); prefer rustls or vendored features carefully (rust-openssl #2352). Anki largely avoids this, but any new crate you add to rslib can reintroduce it — check before adding.
- **`UnsatisfiedLinkError` / library-not-found** at runtime = `.so` in wrong jniLibs subdir or JNI symbol name mismatch (medium.com/@ali.alacan).
- **rsdroid build ordering gotcha:** you must run the build (`./build.sh`/`build.bat`) **before** `cargo check`, or the anki submodule's generated artifacts are missing ("The system cannot find the path specified" = missing submodule init) (ankidroid backend PR #525, issue #97). Also: `git checkout $COMMIT --recurse-submodules`, and keep `rust-toolchain.toml` matching the anki submodule's Rust version.

**The cross-repo reality for Speedrun (critical):** AnkiDroid does **not** vendor rslib — it pulls a prebuilt JNI AAR (`io.github.david-allison:anki-android-backend`). To ship your modified rslib to Android you must fork & build the **third repo**, `ankidroid/Anki-Android-Backend` (rsdroid), which cross-compiles the `.so` via cargo-ndk for arm64-v8a/x86_64 and generates Kotlin protobuf. Then set `local_backend=true` in AnkiDroid's `local.properties` to swap in `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`, and add a Kotlin wrapper in `libanki/`. Build the AAR once early to prove the toolchain before you depend on it.

**Tool selection:** This is a "human + Claude Code headless" job, not a parallel-subagent job. Cross-compile failures are environment-specific and need a tight single-agent debug loop with the agent able to run the build and read full linker output. Give it a dedicated worktree and a `cargo-ndk` runbook skill.

---

## PART B — STARTER ARTIFACTS (research-backed; adapt repo-specific paths)

### B1. Sample root `AGENTS.md` (the cross-tool standard)

**Why AGENTS.md.** It is the cross-tool open standard. Per the Linux Foundation press release (Dec 9, 2025) and openai.com, AGENTS.md was "Released by OpenAI in August 2025" and donated to the **Agentic AI Foundation (AAIF)** under the Linux Foundation (announced Dec 9, 2025); it has been "adopted by more than 60,000 open source projects and agent frameworks including Amp, Codex, Cursor, Devin, Factory, Gemini CLI, GitHub Copilot, Jules and VS Code." The spec emerged "from collaborative efforts across the AI software development ecosystem, including OpenAI Codex, Amp, Jules from Google, Cursor, and Factory" (agents.md). **Claude Code:** historically used `CLAUDE.md`; as of spring 2026 it also reads `AGENTS.md` when no `CLAUDE.md` is present, but `CLAUDE.md` remains its richer native format (vibecoding.app — DATE-FLAG). **Cursor** reads `AGENTS.md` and `.cursor/rules/*.mdc`. **Practical move:** put shared rules in `AGENTS.md`; reference it from `CLAUDE.md` (or symlink `ln -s AGENTS.md CLAUDE.md`) and from `.cursor/rules`. Lead with copy-pasteable commands; only document what differs from defaults; keep under the ~150–200 instruction budget; use nested files per stack — "the closest AGENTS.md to the edited file wins" (the main OpenAI repo has 88 AGENTS.md files) (agents.md; morphllm.com; aihero.dev).

```markdown
# AGENTS.md — Speedrun (Anki fork: GRE Math Subject Test trainer)

## Repo map (THREE repos)
- anki/            forked Anki: rslib (Rust engine), pylib/aqt (Python), ts/ (Svelte UI)
- Anki-Android-Backend/  forked rsdroid: cross-compiles rslib → JNI AAR for Android
- Anki-Android/    AnkiDroid (Kotlin); consumes the AAR via local_backend
External AI/RAG service lives OUTSIDE all native libs — never import it into rslib or rsdroid.

## Build & test (exact commands)
- Desktop run:      ./run
- All checks:       ./ninja check        (rust + python + svelte + ts)
- Single stack:     ./ninja check:rust | check:svelte | check:python
- Format / fix:     ./ninja format ; ./ninja fix
- Rust tests:       cargo test -p anki <module>::
- Python integ:     uv run pytest pylib/tests/test_interleave_integration.py
- Bench:            make bench           (p50/p95/worst on 50k-card deck)
- Android AAR:      cd ../Anki-Android-Backend && ./build.sh   (run BEFORE cargo check)

## Hard invariants (DO NOT VIOLATE)
- Every mutating backend op MUST go through Collection::transact(Op::X, |col| {…})
  and return OpChanges. Never write the DB directly. Never use transact_no_undo for
  user-facing mutations. (Types: rslib/src/ops.rs; impl rslib/src/collection/transact.rs)
- proto/anki/*.proto: ONLY append new fields with NEW numbers. NEVER renumber/reuse.
  reserve removed fields. (DB-persisted bytes must stay parseable.)
- Sync: USN incremental deltas only; usn=-1 means pending push. NO CRDT auto-merge.
  Schema change bumps scm → forces one-way full sync (user picks a side).
- License: every new file is AGPL-3.0-or-later.

## TDD (enforced)
- Red→Green→Refactor. Write failing tests FIRST; do not write impl until tests fail.
- Tests are committed first and are READ-ONLY to implementing subagents.
- NEVER delete, skip, weaken, or rewrite a test to make it pass. Gold-set/held-out
  evals live in eval/holdout/ — agents may NOT read or edit that directory.
- Engine change needs ≥3 Rust unit tests + 1 Python-calling integration test.

## Boundaries
- Deleting tests, editing CI, or touching .proto field numbers requires human approval.
- Do not add native deps to rslib without checking cross-compile (OpenSSL = banned; use rustls).
- See rslib/AGENTS.md, pylib/AGENTS.md, ts/AGENTS.md, and the backend repo's AGENTS.md.
```

### B2. `make bench` + GitHub Actions CI skeleton (polyglot)

```makefile
# Makefile
bench:
	cargo build --release -p anki
	uv run python tools/gen_deck.py --cards 50000 --out /tmp/bench.anki2
	cargo bench -p anki --bench latency -- --save-baseline current
	uv run python tools/bench_report.py --deck /tmp/bench.anki2 \
	   --report p50,p95,worst --targets button=50ms,next=100ms,dash=1000ms,sync=5000ms
```

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable   # honors rust-toolchain.toml
      - run: tools/install-n2
      - run: ./ninja check:rust
      - run: cargo test -p anki
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: ./ninja check:python
      - run: uv run pytest pylib/tests -q
  ts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: yarn install --frozen-lockfile
      - run: ./ninja check:svelte
  android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '21' }
      - run: |
          NDK=$(yq '.versions.ndk' gradle/libs.versions.toml)
          sdkmanager --install "ndk;$NDK"
          rustup target add aarch64-linux-android x86_64-linux-android
          cargo install cargo-ndk
      - run: ./build.sh         # build BEFORE cargo check (submodule artifacts)
  bench:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make bench
      - run: uv run python tools/bench_gate.py --baseline bench/baseline.json
  license:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: fsfe/reuse-action@v3
```
*(Exact action versions/`yq` availability are illustrative — verify against current runners. The Android job is intentionally minimal/debug to keep wall-clock down; full multi-arch release builds belong in a manual/release workflow, as rsdroid itself does.)*

### B3. Git-worktree setup script for parallel agents

```bash
#!/usr/bin/env bash
# wt.sh — create isolated worktrees for parallel agents
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
TS=$(date +%Y%m%d_%H%M%S)
make_wt () {        # $1 = short name, $2 = branch
  git worktree add "$REPO/../speedrun-$1-$TS" -b "$2"
  # copy gitignored env/config the agent needs (see .worktreeinclude in Claude Code)
  [ -f "$REPO/local.properties" ] && cp "$REPO/local.properties" "$REPO/../speedrun-$1-$TS/" || true
  echo "worktree: $REPO/../speedrun-$1-$TS  (branch $2)"
}
# Example: 3-build interleaving ablation
make_wt ablation-off    feat/interleave-off
make_wt ablation-random feat/interleave-random
make_wt ablation-topic  feat/interleave-topic
git worktree list
# cleanup:  git worktree remove ../speedrun-<name>-<ts> ; git branch -d <branch>
```
Run one Claude Code / Cursor session per worktree. Merge via PR-per-agent; freeze the proto/queue API before fanning out. (Claude Code can also auto-manage subagent worktrees with `isolation: worktree` frontmatter — code.claude.com/docs/en/worktrees.)

### B4. Verification-gate definitions (machine-checkable)

Encode these as the Stop-hook checks and the CI gate; an agent may only declare a task "done" when the relevant commands exit 0 (see table in §A5). Minimum gates: `./ninja check` green; `cargo test -p anki interleave::` ≥3 pass; `pytest …integration…` exits 0 and asserts undo + `PRAGMA integrity_check=ok`; `make bench` meets p95 targets; crash harness ×20 leaves `integrity_check=ok`; eval script shows named source + beats BM25 baseline + gold-set ≥ threshold (deterministic, fixed seed/temp 0); REUSE/AGPL check passes.

---

## RECOMMENDED DAY-OF EXECUTION PLAYBOOK

Mapped onto the actual build order (walking skeleton first) and staged Wed/Fri/Sun deadlines. **Golden rule: de-risk the cross-repo Android path FIRST; features last.**

### Phase 0 — Setup (first 1–2 hours)
1. Install Superpowers + write the root `AGENTS.md` (B1) + nested per-stack files. Symlink/reference `CLAUDE.md` and `.cursor/rules`.
2. Wire Claude Code hooks (`.claude/settings.json`): format/clippy/svelte-check PostToolUse; PreToolUse denials (raw SQL, `.proto` field numbers, test-path edits); Stop = `./ninja check`.
3. Install `tdd-guard`. Create the worktree script (B3) and `make bench` skeleton (B2).
4. **Tool split:** Claude Code = engine + Android + orchestration; Cursor = Svelte/TS UI.

### Phase 1 — "Get Anki compiling" + tiny visible Rust change on desktop (→ Wednesday)
5. `./run` to confirm a clean baseline build (install N2 via `tools/install-n2`; honor `rust-toolchain.toml`).
6. **Walking skeleton, desktop:** TDD a *tiny* real engine change in `rslib/src/scheduler/queue/builder/` (or a read-only readiness RPC). Write ≥3 Rust unit tests (RED), implement (GREEN), route any mutation through `Collection::transact(Op::…)`, add the proto method in `proto/anki/*.proto` (append-only). Confirm visible on desktop via `./run`.
7. Add the **Python-calling integration test** (drives rslib through `pylib/anki`/rsbridge); assert undo works + `integrity_check=ok`. This is the verification-before-completion gate for Phase 1.

### Phase 2 — Same engine on the phone via local AAR (→ still target Wednesday/early Friday)
8. **Highest-risk step — do it early.** In the `Anki-Android-Backend` fork: `git checkout … --recurse-submodules`; match `rust-toolchain.toml` to the anki submodule; install NDK from `gradle/libs.versions.toml`; `rustup target add aarch64-linux-android x86_64-linux-android`; run `./build.sh` (BEFORE any `cargo check`).
9. Set `local_backend=true` in AnkiDroid `local.properties`; point at `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`; align `BACKEND_VERSION`/`ext.ankidroid_backend_version`. Add the Kotlin wrapper in `libanki/`. Run a Robolectric test using `rsdroid-testing.jar`.
10. **Gate:** the SAME modified engine now runs on desktop AND Android (assert backend version string on both). Walking skeleton complete.

### Phase 3 — Layer features (→ Friday)
11. **Interleaving (3-build ablation):** use three worktrees (B3) — off / random / topic-aware. TDD ordering invariants; run `make bench`/eval in each; compare. Freeze the queue API before fan-out.
12. **Three scores (memory / performance / readiness):** each with an explicit range + abstention/give-up rule; unit tests assert range membership and ABSTAIN behavior.
13. **Two-way sync:** scripted two-collection sync; assert USN incremental delta path; assert forced one-way full sync on schema (`scm`) change; offline + conflict-resolution test (no CRDT).

### Phase 4 — AI/RAG + hardening (→ Sunday)
14. **External AI/RAG service (OUTSIDE native libs):** LLM proposes symbolic schema → SymPy verifies → hybrid BM25+dense retrieval → cross-encoder rerank → hard gold-set gate. Research-backed pipeline shape: hybrid (BM25+dense, RRF fusion) is the minimum viable baseline; a cross-encoder reranker is "the single most impactful component" (arxiv.org/pdf/2604.01733; digitalapplied.com).
15. **AI eval gates (held-out, deterministic):** every answer traces to a named source; beat a keyword/vector baseline on nDCG/recall; gold-set pass-rate ≥ threshold; fixed seed + temperature 0; held-out set in `eval/holdout/` that agents cannot read/edit (anti-gaming, per arxiv.org/pdf/2603.08806).
16. **Crash tests:** kill mid-review ×20; assert `PRAGMA integrity_check=ok` each time; assert undo intact.
17. **Final `make bench`:** confirm button p95 <50ms, next card <100ms, dashboard <1s, sync <5s, no UI freeze >100ms. Full GitHub Actions matrix green. REUSE/AGPL check green.

### Continuous (every phase)
- Per-task two-stage subagent review (spec → quality). `/compact` at ~60% context; handoff notes before `/clear`. PR-per-agent merges. Show evidence (test output), never trust "done" assertions.

---

## CAVEATS & SOURCE-QUALITY NOTES
- **Fast-moving features (verify before relying):** Cursor version-specific features (2.4 subagents Jan 2026; 3.3 "Build in Parallel"; 3.5 Cloud Agents; BugBot ~80% claim) come substantially from vendor/blog sources (codersera.com, aimakers.co, deployhq.com) and should be confirmed against current Cursor docs. Claude Code slash commands/version gates (`/goal`, `/ultrareview`, `/loop`, async hooks) change frequently — verify at code.claude.com/docs.
- **AGENTS.md ↔ Claude Code:** the claim that Claude Code now reads `AGENTS.md` natively (spring 2026) is from secondary sources (vibecoding.app); the safe, established move is to keep a `CLAUDE.md` that references `AGENTS.md`. The 60,000-repo adoption figure and AAIF/Linux Foundation governance are confirmed by the Dec 9, 2025 Linux Foundation press release.
- **rslib internals:** type/function names (`Op`, `OpChanges`, `StateChanges`, `OpOutput`, `Collection::transact`, `transact_no_undo`, `update_cards_maybe_undoable`) are verified against rslib source; the name `UndoableOpKind` is NOT an authoritative rslib type (it appears in client layers). Confirm exact paths against your forked commit.
- **Sync:** "no CRDT, forced one-way full sync on schema change" is confirmed by Anki's official manual (docs.ankiweb.net/syncing.html) and the `usn=-1`/`scm` semantics by the community-annotated schema; confirm the precise full-sync trigger logic in `rslib/src/sync/` for your version.
- **TDD gaming:** Kent Beck's "unpredictable genie / willing to cheat (delete/modify tests)" framing is from his Pragmatic Engineer interview (newsletter.pragmaticengineer.com). Treat the anti-gaming measures (read-only tests, hidden held-out split, tdd-guard, PreToolUse denials) as non-optional given the project's grading criteria.
- **Vendor benchmark numbers** (e.g. RAG "+39.7% MRR", "48% improvement"; multi-agent "90.2% over single-agent") are from specific papers/blogs on *their* corpora/tasks and will not transfer directly to GRE-math retrieval — treat as directional, and rely on your own gold-set eval.
- **Multi-agent cost:** parallel subagents use about 15× the tokens of a single chat (anthropic.com/engineering/multi-agent-research-system); budget accordingly under time pressure.