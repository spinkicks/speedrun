# Navigating, Comprehending & Safely Editing Anki/AnkiDroid Without Loading Everything Into Context — A 2025-2026 Field Guide

## TL;DR
- **Use Claude Code as your primary driver for cross-repo agentic editing of Anki/rslib/AnkiDroid, and use Cursor's indexed semantic search as a fast "where does X live?" lookup.** Claude Code's agentic grep + Explore subagents + plan mode handle large unfamiliar codebases and the proto/PyO3/JNI seams better than embedding RAG; Cursor's Merkle-tree-indexed semantic search wins for fuzzy conceptual recall. The 2025-2026 consensus is hybrid: lexical (ripgrep) → structural (ast-grep) → semantic (embeddings), escalating only as needed.
- **Add Serena MCP (LSP-backed go-to-definition / find-references) to whichever agent you use.** It is the single highest-leverage addition for "verify the call path before editing," because it gives the agent real symbolic navigation instead of text guessing — directly attacking hallucinated APIs across rslib (rust-analyzer) and AnkiDroid (Kotlin LSP).
- **Generate a compressed repo map (Aider/repomix) per repo, keep a short, command-focused AGENTS.md/CLAUDE.md per repo, and follow an explore→plan→ground→edit→verify loop** with `./ninja check` as the verification gate. Ground every claimed API against ast-grep/Serena/`cargo check` before editing.

## Key Findings

### 1. The three-layer search model is the organizing principle (ESTABLISHED, 2025-2026)
Independent practitioner and vendor analyses converge on the same model: code search for agents is three layers — **lexical** (grep/ripgrep), **structural** (ast-grep/tree-sitter), and **semantic** (embeddings/repo-map). The right question is order, not winner: start with ripgrep for known strings/symbols, escalate to ast-grep when the query is structural (and your regex starts matching comments/strings), and use embeddings only when you don't know the symbol name and need conceptual recall.

There is hard evidence that embeddings have a mathematical ceiling. Per Weller et al., *"On the Theoretical Limitations of Embedding-Based Retrieval"* (Google DeepMind, arXiv:2508.21038, Aug 2025): on the LIMIT benchmark (50K docs) "models struggle to reach even 20% recall@100," and on LIMIT small (46 docs) "models cannot solve the task even with recall@20"; the best single-vector model (Promptriever Llama3 8B, 4096-dim) hit only 54.3% recall@2 versus BM25 near-perfect. Conversely, semantic search clearly helps when used as a complement: per Cursor's engineering blog *"Improving agent with semantic search,"* combining semantic search with grep achieved "on average 12.5% higher accuracy in answering questions (6.5%–23.5% depending on the model)," and agent code-retention "increases to 2.6% on large codebases with 1,000 files or more," measured on their internal Cursor Context Bench. **Takeaway: treat embeddings as a recall aid, never as exhaustive search.**

### 2. Cursor and Claude Code take opposite architectural bets
- **Cursor = persistent semantic index.** On indexing, Cursor computes a Merkle tree of file hashes, chunks code locally (AST-aware via tree-sitter), uploads chunks to generate embeddings (OpenAI/custom models), and stores vectors + obfuscated paths + line numbers in Turbopuffer. Source code is "gone after the life of the request"; indexes are deleted after 6 weeks of inactivity. The Merkle tree enables incremental re-index of only changed files; sync runs every ~5 minutes; semantic search becomes available at 80% index completion. Cursor also ships "Instant Grep" (claims to outperform ripgrep on large codebases) and an Explore subagent that fans out parallel searches in its own context window.
- **Claude Code = agentic search, no index.** Claude Code uses Glob/Grep/Read/Bash in a reasoning loop rather than embeddings. Its built-in **Explore** subagent (read-only: Glob, Grep, Read, read-only Bash; runs on a cheaper model like Haiku, fresh context) keeps heavy search out of the main window. The **Plan** subagent gathers context during plan mode. The main agent's system prompt explicitly instructs: *"When exploring the codebase to gather context or to answer a question that is not a needle query…it is CRITICAL that you use the Task tool with subagent_type=Explore."* **DATE-FLAG:** In April 2026 (v2.1.117/118) Claude Code removed its ripgrep-based Grep/Glob on macOS/Linux native builds and switched to embedded ugrep + bfs invoked via Bash; Windows/npm builds retained prior behavior.

### 3. Multi-repo support: both can do it, differently (DATE-FLAG — fast moving)
- **Cursor**: Multi-root workspaces (`.code-workspace` with multiple `folders`) index all roots for `@codebase`. On April 24 2026 Cursor shipped multi-root workspaces letting a single agent session make cross-repo changes spanning frontend/backend/shared libs. Caveats: each root multiplies indexing surface/memory; rules do NOT cross workspace roots; worktrees are disabled for multi-root. Use aggressive `.cursorignore`.
- **Claude Code**: No index, so "multi-repo" = pointing it at a parent dir or adding repos; subagents + agent teams (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) handle parallel cross-repo work. CLAUDE.md is read hierarchically.

This matters for the user's three-repo setup (anki, anki-android, Anki-Android-Backend): Cursor multi-root gives you cross-repo semantic search of the proto/JNI seam; Claude Code requires explicitly directing it across repos but won't go stale.

### 4. Aider's repo map is the reference implementation of compressed code-graph context (ESTABLISHED)
Aider builds a repo map by parsing every file with tree-sitter (using `tags.scm` query files that mark `name.definition.*` vs `name.reference.*`), building a graph where files are nodes and symbol references are edges, then running a **personalized PageRank** to rank symbols by importance, rendering top-ranked definitions as elided code views within a token budget (`--map-tokens`, default ~1k). Edge weights boost chat files 50x, mentioned identifiers 10x, and well-named (8+ char) identifiers 10x; reference counts are square-rooted to prevent any single symbol dominating. Results are cached in a SQLite disk cache keyed by mtime; 130+ languages are supported. This is the canonical "compressed map fed to an agent" pattern — and it works for Rust, Kotlin, and TS. Standalone reimplementations exist (RepoMapper, available as an MCP server) for use outside Aider.

### 5. ast-grep is the structural-search workhorse (ESTABLISHED, Rust + Kotlin supported)
ast-grep (`sg`) matches tree-sitter AST structure, not text. Patterns look like code with `$VAR` (single named node), `$$$ARGS` (multi), `$$VAR` (include unnamed). YAML rules compose **atomic** (`pattern`, `kind`, `regex`, `nthChild`, `range`), **relational** (`inside`, `has`, `follows`, `precedes` — with `stopBy: end` and `field`), and **composite** (`all`, `any`, `not`, `matches`) rules. Languages include Rust, Kotlin, TypeScript, Tsx, Python, and more. There is an experimental **ast-grep MCP server** for Cursor/Claude Code, and ast-grep ships a Claude Code skill / `.mdc` prompt for agentic rule development. Version note: ESQuery-style `kind` selectors arrived in v0.39.1.

### 6. Serena MCP (and LSP-based MCP servers) close the "verify call path" gap (EMERGING→ESTABLISHED)
Serena is a free, MIT-licensed MCP server that wraps real language servers (LSP) — rust-analyzer for Rust, a Kotlin LSP, typescript-language-server, etc. — exposing symbol-level tools: `get_symbols_overview`, `find_symbol` (by name path like `UserService/authenticate`), `find_referencing_symbols`, `find_implementations`/`find_declaration`, `get_diagnostics_for_file`, plus symbol-precise edits (`replace_symbol_body`, `insert_after_symbol`). It addresses code by symbol-name-path, not line numbers, so edits compose without line drift. It works with Claude Code, Cursor, Codex, etc. Install via `uv tool install` (the maintainers explicitly warn against MCP-marketplace installs as outdated). Latest release v1.5.1 (May 18, 2026) per third-party tracking; ~24K GitHub stars. Caveats: the onboarding pass fills context (start a fresh conversation after it completes); Kotlin support is via community LSP and may be less robust than Rust/TS; `node_modules` and build dirs must be ignored.

### 7. Sourcegraph: Cody's free/pro tiers are GONE; Amp + Cody Enterprise remain (DATE-FLAG)
Per Sourcegraph's blog *"Changes to Cody Free, Pro, and Enterprise Starter plans"*: "As of July 23, 2025, the following plans will no longer be available," with "New signups for Cody Free and Pro… unavailable starting June 25, 2025." Individual users were directed to **Amp**, Sourcegraph's agentic tool; per Sourcegraph/Wikipedia, "In December 2025, Sourcegraph announced that Amp would be spun-off to become a separate company" (co-founders Quinn Slack and Beyang Liu departed to found Amp Inc.; Dan Adler became Sourcegraph CEO). Cody Enterprise survives, now bundled inside Sourcegraph Enterprise as a sales-led product starting at $16K. The enterprise value prop is a SCIP-powered cross-repo code graph plus an MCP server feeding agents. **Recommendation for this user: not worth it** — a solo/small dev making targeted Anki changes can't access the discontinued individual tiers, and the enterprise product is overkill. The SCIP protocol itself remains open source.

### 8. Context-packing tools compress repos into ingestible form (ESTABLISHED)
- **repomix**: packs a repo into one AI-friendly file (XML/Markdown/JSON); `--compress` uses tree-sitter to extract key code elements (signatures, not bodies); git-aware (respects .gitignore), Secretlint security scan, token counting, `--include`/`--ignore` globs, MCP server, can generate Claude skill output.
- **gitingest**: swap "hub"→"ingest" in a GitHub URL for a digest; `pip install gitingest`; PAT for private repos.
- **code2prompt**: Rust, TUI, Handlebars templates, token counting, git diff/log extraction, MCP server.
- **files-to-prompt** (Simon Willison): minimal, pipe-friendly, Claude-XML output.

For a repo the size of rslib you must filter aggressively (exclude generated proto output, tests, assets) and/or use `--compress`; whole-repo packing of Anki will blow past any context window.

### 9. AGENTS.md is now a cross-tool standard — but keep it command-focused, not architectural (ESTABLISHED 2025-2026)
AGENTS.md emerged August 2025 (OpenAI/Codex, Amp, Google Jules, Cursor, Factory). Per the Linux Foundation press release (Dec 9, 2025): "Released by OpenAI in August 2025… AGENTS.md has already been adopted by more than 60,000 open source projects and agent frameworks including Amp, Codex, Cursor, Devin, Factory, Gemini CLI, GitHub Copilot, Jules and VS Code," and was donated to the Agentic AI Foundation (AAIF) under the Linux Foundation alongside MCP and Block's goose. Tool-specific files still exist (CLAUDE.md for Claude Code, `.cursor/rules/*.mdc` for Cursor).

Crucially, **more context is not always better.** Per Gloaguen, Mündler, Müller, Raychev & Vechev (ETH Zurich/LogicStar.ai), *"Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?"* (arXiv:2602.11988, Feb 2026): across a 138-task AGENTBENCH on Sonnet 4.5, GPT-4.1, o4-mini and Qwen 3, "context files tend to reduce task success rates compared to providing no repository context, while increasing inference cost by over 20%." The practical reading: keep these files short and high-signal — exact build/test/lint commands, hard constraints, and non-standard patterns — and drop generic "architecture overview" prose. For Claude Code specifically, the community rule of thumb is CLAUDE.md ≤200 lines, pruned ruthlessly (instructions are followed ~70% of the time; hooks enforce at 100%).

### 10. Anti-hallucination = grounding + plan-then-act (ESTABLISHED)
The consensus pattern is **explore → plan (read-only) → ground every API claim → edit → verify**. Claude Code's plan mode (Shift+Tab) restricts to read-only until you approve. Requiring evidence (file paths, line numbers) in prompts forces retrieval over guessing. Anthropic's research report *"How Claude Code is used in practice"* quantifies why guidance matters: "A session rated intermediate or up reaches verified success 28-33% of the time," versus a novice-rated session reaching strict "verified success 15% of the time" — planning, grounding, and verification are what move that number. Grounding via grep/LSP/`cargo check` converts plausible-sounding guesses into verified facts. For typed languages, Anthropic explicitly recommends a code-intelligence plugin for "precise symbol navigation and automatic error detection after edits" — which is exactly what Serena provides for rslib and AnkiDroid.

## Details

### How this maps to Anki's architecture specifically
The proto codegen dispatch-by-`(service_index, method_index)` and the three language bindings (PyO3 `rsbridge`, JNI `rsdroid`) are exactly the kind of seam where agents hallucinate. The engine truth lives in Rust; Python `pylib` and Kotlin `libanki` are thin proxies generated/mirrored from the same `proto/anki/*.proto`. So the highest-value grounding move is: **resolve the proto definition first, then the Rust service impl, then the generated binding** — using structural search + LSP, not text grep.

Verified code shapes (fetched from `main`, June 2026) that make structural search reliable:
- `rslib/src/collection/transact.rs`: the real signature is `pub(crate) fn transact<F, R>(&mut self, op: Op, func: F) -> Result<OpOutput<R>> where F: FnOnce(&mut Collection) -> Result<R>`. There is also `transact_inner` (takes `Option<Op>`) and `transact_no_undo`. (Confirmed verbatim from the file.)
- `rslib/src/ops.rs`: `pub enum Op { Custom(String), AddDeck, AddNote, AddNotetype, AnswerCard, BuildFilteredDeck, Bury, ChangeNotetype, ClearUnusedTags, CreateCustomStudy, EmptyCards, EmptyFilteredDeck, FindAndReplace, ImageOcclusion, Import, RebuildFilteredDeck, RemoveDeck, RemoveNote, RemoveNotetype, RemoveTag, RenameDeck, ReparentDeck, RenameTag, ReparentTag, ScheduleAsNew, SetCardDeck, SetDueDate, GradeNow, SetFlag, SortCards, Suspend, ToggleLoadBalancer, UnburyUnsuspend, UpdateCard, UpdateConfig, UpdateDeck, UpdateDeckConfig, UpdateNote, UpdatePreferences, UpdateTag, UpdateNotetype, SetCurrentDeck, SkipUndo }` with `impl Op { pub fn describe(&self, tr: &I18n) -> String { … } }`. (Confirmed verbatim — 182 lines; also defines `StateChanges`, `OpChanges`, `OpOutput<T>`.)
- `proto/anki/scheduler.proto`: two services. `service SchedulerService { rpc GetQueuedCards(GetQueuedCardsRequest) returns (QueuedCards); rpc AnswerCard(CardAnswer) returns (collection.OpChanges); rpc SchedTimingToday(generic.Empty) returns (SchedTimingTodayResponse); … }` and `service BackendSchedulerService { … }`. RPCs follow `rpc Name(ReqType) returns (RespType);` and long ones wrap the `returns (...)` to the next line; response types are often package-qualified (`collection.OpChanges`, `generic.Empty`). (Confirmed verbatim.)
- `QueueBuilder` lives in `rslib/src/scheduler/queue/builder/`; `QueueBuilder::new()` initializes a `Context`; `gather_cards()` orchestrates gathering; a `build` method produces the queue. (Names confirmed via repo documentation; open the file to confirm the exact field list and signatures.)

### Artifact A — Repo-map generation commands

Aider repo map (best-ranked map; needs aider installed) — run inside each repo root:
```
aider --map-tokens 4096 --show-repo-map > rslib_map.txt
```

repomix (compressed signature-level pack, per subtree — keeps tokens sane):
```
# Compressed map of just the scheduler engine:
npx repomix rslib/src/scheduler --compress --style markdown -o scheduler_pack.md
# Full rslib minus generated/proto noise:
npx repomix rslib --compress \
  --ignore "**/*_generated.*,**/target/**,**/*.proto" -o rslib_pack.md
```

code2prompt / gitingest (quick alternatives):
```
code2prompt rslib/src/scheduler --tokens
# or a zero-install digest of a GitHub subtree:
#   https://gitingest.com/ankitects/anki
```

ctags symbol index (fast, agent/editor-readable; good for "where is symbol X defined"):
```
ctags -R --languages=Rust,Kotlin,Python,TypeScript \
  --fields=+n+S --extras=+q -f tags rslib pylib qt ts
# query with readtags: readtags -t tags QueueBuilder
```

### Artifact B — ast-grep queries targeting real Anki patterns
All are written against the actual code shapes above. Run from repo root; add `-l rust`/`-l kotlin` as shown.

Find all proto RPC method declarations (proto isn't a default ast-grep language, so use ripgrep as the lexical layer):
```
rg -n '^\s*rpc\s+\w+\(' proto/anki/*.proto
```

Find every call site of the collection transaction wrapper (Rust):
```
ast-grep -l rust -p '$COL.transact($OP, $CLOSURE)'
# narrow to a specific op:
ast-grep -l rust -p '$COL.transact(Op::AnswerCard, $CLOSURE)'
```

Find the `Op` enum and its variants (`find_op_enum.yml`):
```yaml
id: find-op-enum
language: rust
rule:
  kind: enum_item
  has:
    field: name
    pattern: Op
```

Find backend service-trait impls on `Collection` (the proto-generated service traits like `SchedulerService`):
```yaml
id: find-service-impls
language: rust
rule:
  kind: impl_item
  all:
    - has: { field: trait, regex: 'Service$' }
    - has: { field: type, pattern: Collection }
```

Find Rust functions returning `Result<OpOutput<...>>` (the op-producing engine API surface):
```yaml
id: op-output-returning-fns
language: rust
rule:
  kind: function_item
  has:
    field: return_type
    pattern: Result<OpOutput<$T>>
    stopBy: end
```

Find Kotlin calls into the generated backend (AnkiDroid side — verifies the JNI binding call path):
```
ast-grep -l kotlin -p 'col.backend.$METHOD($$$ARGS)'
# or the generated backend directly:
ast-grep -l kotlin -p 'backend.answerCard($$$ARGS)'
```

Safe structural codemod with interactive review (e.g. renaming a helper call):
```
ast-grep -l rust -p 'old_helper($$$A)' -r 'new_helper($$$A)' --interactive
```

### Artifact C — "Find the 3-5 files I need to change in rslib's scheduler/queue and verify them" recipe
Use Claude Code in plan mode (Shift+Tab) with Serena MCP attached; or Cursor in Ask mode with `@codebase`.

**Step 0 — Setup (once).** Attach Serena MCP to the anki repo root. Write a ≤200-line `AGENTS.md`/`CLAUDE.md` recording build commands (`./run`, `./ninja check`, `./ninja format`, `./ninja fix`), the proto→prost→Python/TS codegen flow, and the rule "engine logic lives in rslib; pylib/libanki are generated proxies — never edit generated `_pb2`/`_generated` files." Generate a compressed map: `npx repomix rslib/src/scheduler --compress -o sched_pack.md`.

**Step 1 — Scope (read-only, in plan mode).** Prompt: *"Using the Explore subagent and Serena, identify the 3-5 files that implement deck queue building in rslib. Start from the proto definition for queued cards and trace to the Rust impl. Report file paths + line numbers + symbol names. Do not edit."* Expect: `proto/anki/scheduler.proto` (`rpc GetQueuedCards`), the `SchedulerService` impl exposing it, and `rslib/src/scheduler/queue/builder/` (`QueueBuilder`, `gather_cards`, `build`), plus `scheduler/queue/mod.rs`.

**Step 2 — Ground the call path with structural + symbolic search (not memory).**
```
ast-grep -l rust -p 'QueueBuilder::new($$$A)'
ast-grep -l rust -p 'fn gather_cards($$$A)'
```
Then Serena: `find_symbol QueueBuilder`, `find_referencing_symbols QueueBuilder/build`, `find_symbol SchedulerService/get_queued_cards`. This confirms the real method names exist and shows every caller — defeating hallucinated APIs.

**Step 3 — Confirm the proto/binding seam.** Verify the RPC exists (`rg 'rpc GetQueuedCards' proto/anki/scheduler.proto`) and that Python/Kotlin just proxy it (`rg -n 'get_queued_cards|getQueuedCards' pylib ../anki-android/libanki`). If your change alters the proto, you must regenerate (the build does this via `rslib/proto/build.rs`) — flag this explicitly, since it ripples into PyO3, TS, and the separate rsdroid JNI bridge.

**Step 4 — Plan and get approval.** Have the agent write the change as a numbered plan referencing exact files/symbols/line ranges, with the verification commands. Review it; correct misunderstandings before any code is written.

**Step 5 — Edit surgically.** Prefer Serena's `replace_symbol_body` (no line drift) for the `QueueBuilder` method(s). Keep edits scoped to rslib; do not touch generated bindings.

**Step 6 — Verify (the gate).** Run `./ninja check` (full) or scope to Rust: `cargo check`/`cargo test` in rslib, plus `./ninja format`. Use Serena `get_diagnostics_for_file` for fast per-file feedback before the full build. If proto changed, rebuild so PyO3 + TS regenerate (and rebuild rsdroid separately). For AnkiDroid, swap the local backend (`local_backend=true` in `local.properties`) to test the JNI side. Require a test that fails on the pre-change behavior.

### Cursor vs Claude Code — decision table for this user

| Need | Use | Why |
|---|---|---|
| "Where does X live?" fuzzy/conceptual | **Cursor** `@codebase` semantic search | Indexed embeddings; fast conceptual recall on 1k+ files |
| Trace exact call path / find all callers before editing | **Serena MCP** (in either) | LSP find-references beats both grep and embeddings |
| Multi-step agentic edit in rslib | **Claude Code** plan mode + Explore | Agentic search won't go stale; plan-then-act; subagents isolate context |
| Cross-repo change (anki ↔ Anki-Android-Backend) | **Cursor** multi-root workspace OR **Claude Code** pointed at parent dir | Cursor indexes both roots; CC needs explicit direction but no index drift |
| Structural search / codemod (Op variants, service impls) | **ast-grep** CLI (in either) | AST-precise, no false positives in comments/strings |
| Manual reading + small edits | **Cursor** editor | Better IDE ergonomics |
| Long autonomous multi-file refactor | **Claude Code** | Subagents, hooks, agent teams |

## Recommendations

**Stage 1 — Set up grounding infrastructure (do this first).**
1. Install ast-grep (`brew install ast-grep` or `cargo install ast-grep --locked`) and Serena MCP (`uv tool install`), attaching Serena to all three repos.
2. Write one short `AGENTS.md` per repo (build/test commands + the "rslib is the engine, bindings are generated" rule + non-standard patterns; skip generic architecture prose per the ETH Zurich finding). Mirror to `CLAUDE.md` (Claude Code) and `.cursor/rules/` (Cursor). Keep ≤200 lines.
3. Generate compressed repo maps with `repomix --compress` per major subtree and an Aider map at `--map-tokens 4096`; regenerate on demand or on a pre-commit hook so they stay fresh.

**Stage 2 — Use the right tool per task** (per the decision table). Default to Claude Code + Serena for engine edits; reach for Cursor's semantic index for conceptual lookups and cross-repo browsing.

**Stage 3 — Always run the explore→plan→ground→edit→verify loop.** Never let the agent edit before it has shown you file paths + line numbers + confirmed-via-LSP symbol names. Make `./ninja check` the non-negotiable gate, and require a regression test.

**Benchmarks/thresholds that change the recommendation:**
- If repos exceed your local indexing memory or Cursor indexing is slow → narrow `.cursorignore`, index per-domain workspaces, or drop Cursor indexing and rely on Claude Code agentic search + Serena.
- If the agent keeps hallucinating APIs despite grep → that's the signal to lean harder on Serena LSP and require evidence (paths/lines) in every prompt.
- If your AGENTS.md/CLAUDE.md grows past ~200 lines or you notice degraded agent behavior/cost → prune it; the arXiv evidence shows bloated context files *reduce* success and add >20% cost.
- If you ever need org-scale cross-repo graph across many repos (not your current case) → only then consider Sourcegraph Enterprise/Amp.
- Re-evaluate Cursor/Claude Code feature claims monthly — both ship weekly (DATE-FLAG everything in §2/§3).

## Caveats
- **Fast-moving (DATE-FLAGGED):** Cursor's multi-root + multitask (April 24 2026), Claude Code's ugrep/bfs switch (April 2026, native builds only), agent teams (experimental), and Claude model context sizes (Opus 4.x advertises a native 1M window but quality degrades past roughly 300-400k tokens; Sonnet ~200k) all change frequently. Verify with `claude --version` / the Cursor changelog before relying on a specific flag.
- **Embeddings have a proven hard ceiling** (DeepMind LIMIT, arXiv:2508.21038); don't treat Cursor semantic search as exhaustive — it complements, not replaces, exact search. Cursor's index also reflects only your local checkout and needs a pull + re-index to see teammates' changes.
- **Serena Kotlin support** is via community LSP and may be less robust than Rust (rust-analyzer) or TS; expect slower startup and occasional gaps on AnkiDroid.
- **Source reliability:** The Anki code shapes in §Details (`transact`, the `Op` enum, `scheduler.proto`) were verified verbatim against the live `main` branch (June 2026). `QueueBuilder`'s exact field list and method signatures come from repo documentation, not a verbatim file fetch — open `rslib/src/scheduler/queue/builder/mod.rs` to confirm. Claude Code internals (Explore subagent prompt, tool lists) are partly sourced from reverse-engineered community write-ups corroborated against Anthropic's official docs.
- **Subagent token cost:** Anthropic notes subagent-heavy workflows can use ~7x the tokens of single-thread sessions; Explore is cheap (Haiku) but custom general-purpose subagents are not.
- This guide assumes you already have both Cursor and Claude Code licensed; it does not evaluate pricing.