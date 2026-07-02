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
**Speedrun Home ("The Run") — frontend revamp slice 1 — ✅ MERGED to `main` on all 3 forks (2026-07-01)** and **verified on BOTH platforms** (David's desktop `just run` screenshot + Android emulator screenshot — same shared page renders identically). Per-repo `main`: anki **`52bcefa7e`** · Anki-Android-Backend **`a125ad5`** (rsdroid pin → `6341b6f61`) · anki-android **`2146d885e6`**. The 7-agent audit's 4 gate-blockers (desktop data path 403/404, exam-profile bootstrap, `closeWithCallback`, auto-open placement) were all fixed + code-verified before merge.

**✅ Mobile-first UX + START RUN + reviewer — MERGED to `main` (2026-07-01).** Per-repo `main`: anki **`af1138428`** · Anki-Android-Backend **`9aa21ec`** (rsdroid pin `eb4f5a3ff`; behind anki tip only by Android-irrelevant commits — re-pin at next AAR rebuild) · anki-android **`fdfd086031`**. Delivered: mobile-first responsive Home+Memory, Memory re-themed dark, Android dark shell, desktop+Android START RUN (real study + honest import/caught-up/Custom-Study), R1a desktop dark reviewer. **Two smoke-caught bugs fixed** (false "caught up" → `sched.deck_due_tree`; desktop double-fire → single dispatch), both from a bug-class QA sweep (12-agent, 1 real bug + coverage gap closed). Desktop David-verified. **Deferred post-Friday:** R1b Android reviewer theme + full reviewer chrome (shared `CardViewerActivity` scope risk).
- **Open:** (a) David: Android emulator re-confirm (post-merge) + **installer package + Windows-Sandbox clean-machine recording** (`docs/WEDNESDAY-DELIVERABLES.md`) + demo recordings (`docs/DEMO-VIDEO-SCRIPT.md`); (b) audit backlog in `FUTURE-PLANS.md` `[audit]`; (c) **Thursday:** Claude grounds `docs/plans/2026-07-03-friday-brief.md` into a full Friday plan (3 scores + AI service + sync demo) for Cursor review.
- **Installer/.dmg decision:** Windows installer satisfies the requirement; `.dmg` deferred (macOS-only; unsigned-via-macOS-CI is the documented fallback if ever required). See `docs/WEDNESDAY-DELIVERABLES.md`.
- **Optional infra:** `.claude/cursor-review-notify.ps1` (UserPromptSubmit nudge hook) written, NOT wired into `settings.json` — David relays manually (working well).
- **Lane note:** umbrella docs (incl. this file) are Cursor's lane. Claude should propose STATE/PROGRESS changes via `.claude/cursor-review.md`, not edit umbrella docs directly (avoids stale/duplicate sections + races).

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
