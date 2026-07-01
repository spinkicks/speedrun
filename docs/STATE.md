# Speedrun — START HERE (current state & handoff)

**If you're a fresh chat/agent: read this, then `docs/PROGRESS.md` (done/left tracker) → `docs/FUTURE-PLANS.md` (backlog) → `docs/DECISIONS.md` → `docs/PRD.md` → `docs/BUILD-WORKFLOW.md` → `brainlift/BrainLift.md`. Run steps: `docs/RUN-MVP.md`. Context hygiene: `docs/CONTEXT-ENGINEERING.md`. `AGENTS.md` (root) auto-loads the invariants.**

## What this is
Speedrun: an honest GRE **Mathematics Subject Test** study app built on **Anki** (desktop + Android sharing one Rust engine). Owner: David Ordonez (GitHub `spinkicks`). License AGPL-3.0-or-later, credit Anki.

## Status (as of 2026-07-01, Wed afternoon — post wed-plus merge + full audit)
- ✅ Planning artifacts complete: BrainLift (9 SPOVs), PRD, ARCHITECTURE, BUILD-WORKFLOW, DECISIONS. Toolchain + Serena MCP working (see git history of this file for setup details).
- ✅ **Walking skeleton** (Mon–Tue): forked Anki builds/runs; `SpeedrunService.GetCoverage` read-only RPC via TDD; one-engine-two-apps proven on the `Pixel_10` x86_64 emulator (instrumentation test, backendVersion 26.05 both platforms).
- ✅ **Wednesday MVP + Wednesday-Plus — ALL MERGED TO `main` on all 3 forks (2026-07-01):**
  - Engine: 5 RPCs on `SpeedrunService`, proto FROZEN — `GetCoverage`, `GetTopicMastery` (Wilson 95% + abstain), `GetExamProfile` (synced config), **`ReorderNewByPointsAtStake`** (mutating via `transact(Op::SortCards)`, undo-safe, ablation Full/FeatureOff/Plain), `GetPerformanceReadiness` (always-abstain scaffolding).
  - Content: `gre_math.json` exam DAG + 35-card seed deck (tag↔topic alignment audit-verified) + deterministic scraper. NO AI anywhere.
  - Installer: network-independent (Briefcase templates vendored; SyncSubmodule dropped).
  - Dashboard: shared Svelte Memory page on both platforms (desktop Qt dialog + Android PageFragment; AAR auto-bundles sveltekit assets).
  - Sync: `anki-sync-server` in-fork + §7b conflict test (revlog union + latest-wins, honest caveat documented) → `docs/SYNC-SELFHOST.md`.
- **Per-repo `main` pins (single source of truth):** anki **`1fed9e109`** · Anki-Android-Backend **`d4086e0`** (contains `299bb44` rsdroid `anki`-submodule pin → **`a0ead51c9`**; note the pin is a wed-plus-branch commit, ancestor-equivalent content to main tip) · anki-android **`a56dda6cfb`** · umbrella `spinkicks/speedrun` `main` = latest. All FF, no merge commits; `feat/speedrun-wed-plus` branches kept as backup. Upstream tracking on `main` fixed on all forks.

## Immediate next step
**Speedrun Home ("The Run") — frontend revamp slice 1 — IN PROGRESS (Claude, branch `feat/speedrun-home`).** Spec: `docs/design/speedrun-home-spec.md` (APPROVED); mockup: `docs/design/mockups/speedrun-home.html`. Progress at last check: H0 grounding ✅ → H1 shared Svelte home page ✅ (reviewed) → H2 desktop shell ✅ (`SpeedrunHome` dialog, config-gated auto-open on launch, START RUN → overview-state bridge) → H3 Android + AAR rebuild 🔄. **Cursor gate before merge to `main`.**

**⚠️ 7-AGENT AUDIT (2026-07-01, Cursor/Fable) — critical fixes assigned to Claude's current branch (see PROGRESS.md for the full list):**
1. **CRITICAL — desktop data path broken:** speedrun RPC POSTs from the webview 404/403 on desktop — the 4 methods are missing from `exposed_backend_list` (`qt/aqt/mediasrv.py` ~L728) AND `AnkiWebViewKind.DEFAULT` has no API access (`qt/aqt/webview.py` `_profileForPage` ~L135). Fix = add snake_case methods to the list + use/add an API-enabled webview kind. Android is fine (its bridge is wired).
2. **CRITICAL — exam profile never bootstrapped:** fresh collections return `""` from `GetExamProfile` → Home/Memory stuck in error state even after importing the seed deck. Needs a bootstrap path.
3. **HIGH:** missing `closeWithCallback` on both dialogs (quit-crash path, mainline once Home auto-opens); `get_topic_mastery` N+1 (bench risk); Full-mode reorder determinism not contractual (§8 risk).

**Then:** David's smoke tests + recordings (desktop `just run` → auto-opens Home; Android emulator per RUN-MVP) — **after** the critical fixes land. Friday planning brief is ready: `docs/plans/2026-07-03-friday-brief.md` (Claude grounds it into a full plan Thursday).

## Mission-control operating notes (for a fresh Cursor chat)
- **Roles (updated 2026-07-01):** Cursor = mission control — orchestration, review, docs, git, design specs. Claude Code (separate app, "Main Orchestration 2" session) = builds engine/Android **and, since today, frontend** (`ts/`+`qt/` — David's call; it keeps the proven subagent-driven-development loop). Cursor avoids concurrent writes in `repos/*` while Claude builds; umbrella docs are Cursor's lane exclusively.
- **Watch Claude's output (Claude → Cursor):** hook writes digests to `.claude/watch.log` (project-level `.claude/settings.json` Stop/SubagentStop hook → `claude-digest.ps1` — survives Claude restarts). Reconnect: background-run `Get-Content .claude/watch.log -Wait -Tail 0` with output-notify on `\]\[(Stop|SubagentStop)\]`. For live detail read the newest transcript: `~/.claude/projects/C--Users-davir-Ultra-Alpha-Speedrun/<newest>.jsonl` (currently `01774af5-…`).
- **Review channel (Cursor → Claude):** `.claude/cursor-review.md` — Cursor writes gate feedback / fix requests here (Pending block at top; move to Resolved when done). Claude reads it at each gate or when David says "read cursor-review.md". Umbrella-only (never pushed to forks). Optional proactive nudge: `.claude/cursor-review-notify.ps1` is a **UserPromptSubmit** hook (written, NOT yet wired into `settings.json`) that surfaces a one-line "new pending review" nudge on David's next prompt if the file changed — non-interrupting (rides on David's own messages, never fires mid-thinking, always exits 0). To enable, add a `UserPromptSubmit` entry to `.claude/settings.json` pointing at that script (do it at a calm moment, not mid-build — editing settings can prompt Claude to re-review).
- **Git:** umbrella docs commit to `spinkicks/speedrun` `main`; pushes to `main` may trigger a smart-mode approval card (expected — approve). The PowerShell `git : ... RemoteException` on push is COSMETIC; check the `->` ref-update line. Code lands on the forks; strategy docs stay in the PRIVATE umbrella only (never push AGENTS.md/strategy to public forks).
- **Key docs:** `docs/PROGRESS.md` (done/left + audit findings), `docs/FUTURE-PLANS.md` (backlog), `docs/plans/2026-07-03-friday-brief.md` (Friday requirements), `docs/RUN-MVP.md` (run steps), `docs/design/*.md` (UI contracts), `docs/artifacts/` (§7a).

## Cadence
Mon=plan · Tue=heavy coding · Wed=both apps MVP (desktop+Android, NO AI) · Fri=AI+sync+3 scores · Sun=evals/ablation/ship.

## Key invariants (also in AGENTS.md)
- Mutations → `Collection::transact(Op::X, …)` returning `OpChanges`; never raw DB writes.
- `proto/anki/*.proto`: append-only field numbers (frozen 2026-07-01 @ `20dd7a2ea`; later additions append-only).
- TDD: failing test first; tests read-only to implementer; `eval/holdout/` off-limits (not yet created — Sunday).
- Ground APIs via Serena/ast-grep/`cargo check` before editing.
- AI strictly after Wednesday (spec rule).
