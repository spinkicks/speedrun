# Speedrun — START HERE (current state & handoff)

**If you're a fresh chat/agent: read this, then `docs/PROGRESS.md` (done/left tracker) → `docs/FUTURE-PLANS.md` (backlog) → `docs/DECISIONS.md` → `docs/PRD.md` → `docs/BUILD-WORKFLOW.md` → `brainlift/BrainLift.md`. Run steps: `docs/RUN-MVP.md`. Context hygiene: `docs/CONTEXT-ENGINEERING.md`. `AGENTS.md` (root) auto-loads the invariants.**

## What this is
Speedrun: an honest GRE **Mathematics Subject Test** study app built on **Anki** (desktop + Android sharing one Rust engine). Owner: David Ordonez (GitHub `spinkicks`). License AGPL-3.0-or-later, credit Anki.

## Status (as of 2026-07-03, Fri AM — FULL Friday scope + LS1/2/3 + ablation + AI service ALL MERGED to `main` on all repos; only human demo/eval + 7 bug fixes remain)

**TL;DR (2026-07-03):** Everything on the Friday plan plus the 3 greenlit learning-science additions, the §8 ablation harness, the P0/P1/P2/P3 fix batches, and the OFF-by-default AI service are **built, gate-reviewed, and merged to `main` on all four repos.** Every **feature** branch is merged to `main` (0 unmerged as of the 07-03 batch-merge); the only branches not on `main` are the 7-bug adversarial-sweep fixes still in flight (see below). **Per-repo `main`:** anki **`c54afe2b1`** · Anki-Android-Backend **`14c2992`** · anki-android **`f2cf66ac35`** · umbrella `spinkicks/speedrun` latest. **Remaining = human/Sunday only:** Android emulator visual gate, live desktop↔Android sync-demo recording, demo video, Sunday eval RUNS (calibration reliability + Brier/log-loss, performance accuracy on held-out, score-mapping writeup), robustness (crash×20 / offline / `make bench`), signed APK, final BrainLift pass. Plus **7 bugs** from the 2026-07-03 adversarial sweep are being fixed on branches (2 P0 demo-visible, 2 P1 AI-safety, 2 P2 calibration) — see `.claude/cursor-review.md`.

## Status (historical — as of 2026-07-02, Thu AM — Wed MVP shipped+recorded; Friday plan approved & executing + branding slice greenlit)
- ✅ Planning artifacts complete: BrainLift (9 SPOVs), PRD, ARCHITECTURE, BUILD-WORKFLOW, DECISIONS. Toolchain + Serena MCP working (see git history of this file for setup details).
- ✅ **Walking skeleton** (Mon–Tue): forked Anki builds/runs; `SpeedrunService.GetCoverage` read-only RPC via TDD; one-engine-two-apps proven on the `Pixel_10` x86_64 emulator (instrumentation test, backendVersion 26.05 both platforms).
- ✅ **Wednesday MVP + Wednesday-Plus — ALL MERGED TO `main` on all 3 forks (2026-07-01):**
  - Engine: 5 RPCs on `SpeedrunService`, proto FROZEN — `GetCoverage`, `GetTopicMastery` (Wilson 95% + abstain), `GetExamProfile` (synced config), **`ReorderNewByPointsAtStake`** (mutating via `transact(Op::SortCards)`, undo-safe, ablation Full/FeatureOff/Plain), `GetPerformanceReadiness` (always-abstain scaffolding).
  - Content: `gre_math.json` exam DAG + 35-card seed deck (tag↔topic alignment audit-verified) + deterministic scraper. NO AI anywhere.
  - Installer: network-independent (Briefcase templates vendored; SyncSubmodule dropped).
  - Dashboard: shared Svelte Memory page on both platforms (desktop Qt dialog + Android PageFragment; AAR auto-bundles sveltekit assets).
  - Sync: `anki-sync-server` in-fork + §7b conflict test (revlog union + latest-wins, honest caveat documented) → `docs/SYNC-SELFHOST.md`.
- **Per-repo `main` pins (single source of truth):** anki **`1fed9e109`** · Anki-Android-Backend **`d4086e0`** (contains `299bb44` rsdroid `anki`-submodule pin → **`a0ead51c9`**; note the pin is a wed-plus-branch commit, ancestor-equivalent content to main tip) · anki-android **`a56dda6cfb`** · umbrella `spinkicks/speedrun` `main` = latest. All FF, no merge commits; `feat/speedrun-wed-plus` branches kept as backup. Upstream tracking on `main` fixed on all forks.

## Immediate next step (2026-07-03) — everything buildable is MERGED; only human demo/eval + 7 bug fixes remain
1. **7 bug fixes (in progress, Claude on branches; Cursor merges):** from the 2026-07-03 adversarial sweep — P0 #1 single-card `0%–100%` band (engine, abstain when `cards_with_data<2`), P0 #2 Android `getCalibration` exposure (needed before any AAR rebuild on current anki `main`), P1 #3/#4 AI grounding+leakage gates (on `feat/speedrun-ai`, OFF-by-default → not demo-blocking), P2 #5/#6 calibration-capture hygiene. See `.claude/cursor-review.md`.
2. **David — demo/record (the only build-independent work):** Android emulator visual gate (3 scores + calibration buttons + faded reveal + Manrope) → live desktop↔Android self-hosted sync demo (`docs/SYNC-SELFHOST.md`) → MVP demo video (`docs/DEMO-VIDEO-SCRIPT.md`).
3. **Sunday workstream** (`docs/FUTURE-PLANS.md`): eval RUNS (calibration reliability + Brier/log-loss; performance accuracy on held-out; score-mapping writeup), robustness (crash×20 / offline / `make bench` p50/p95 on 50k deck), signed APK, final BrainLift pass. (Ablation harness + gold set + Problem bank are already shipped.)

### History (all ✅ MERGED — kept for the audit trail)
- **Wed MVP (2026-07-01):** one engine two apps; 5 RPCs; honest Memory (Wilson+abstain); Speedrun Home + Memory dashboard; START RUN; self-hosted sync + §7b test; offline installer (release MSI, 27/27). Clean-machine install recorded (`CleanTestInstall.mp4`).
- **Fri scope (2026-07-02→03):** Performance + Readiness scores (in-engine, honest, abstaining); due-card weakness×topic interleave; `Speedrun::Problem` bank (64, double-SymPy-verified) + timed mini-mock; AI/RAG service (OFF by default, SymPy + gold-gate); Manrope/#F4F7FA identity; Phase 6 AAR rebuild + APK.
- **LS additions (2026-07-02):** LS1 calibration, LS2 worked-examples-faded, LS3 honesty-copy.
- **Quality (2026-07-02→03):** §8 ablation harness (pre-registered M1/M2/M3); P0 honesty + P1 AI-safety + P2 mini-mock + P3 nit batches.
- **David inputs — ALL RESOLVED:** wordmark = Manrope; accent = `#F4F7FA`; `PROBLEM_MODEL_ID=2047815909`; OpenAI key in `services/speedrun-ai/.env`; gold set delivered (`eval/holdout/gre_math_gold.jsonl`, 50, triple-verified, leakage-cleared).

## Per-repo `main` pins (updated 2026-07-03 AM, post-Friday batch-merge)
- **anki `main` = `c54afe2b1`** — Phases 0–6 + P0/P1/P2/P3 fixes + LS1 calibration + LS2 worked-examples + LS3 honesty-copy + §8 ablation harness + Manrope/white identity. (Merged as the FF stack `fix/p2-minimock`→`fix/p3-nits`, then a clean 3-way with `feat/ablation-harness`.)
- **anki-android `main` = `f2cf66ac35`** — P0 Android (real mini-mock + bridge parity). Phase 6 consume branch was a no-op (== main).
- **Anki-Android-Backend `main` = `14c2992`** — Phase 6 rsdroid re-pin to the P0-complete engine + AAR rebuilt (21 MB, x86_64, UI-in-AAR verified). NOTE: an AAR rebuild on the *current* anki `main` (`c54afe2b1`) needs the Android `getCalibration` fix first (bug P0 #2, in progress) or Android Home errors.
- **umbrella `spinkicks/speedrun` `main`** — AI service (`services/speedrun-ai/`, OFF by default, RAG corpus 82) consolidated in; all gate-approval docs + this file.
- **Branch status:** every **feature** branch in all 4 repos is an ancestor of `main` (fully merged) as of the 2026-07-03 batch-merge; backup `feat/*` branches retained. **EXCEPTION — intentionally NOT yet merged:** the 7-bug sweep fix branches `fix/p0b-band-abstain` (anki), `fix/p0-android-getcalibration` (anki-android), `fix/p2-calibration-capture` (anki), and the AI-safety fixes on `feat/speedrun-ai` (umbrella) — see "Immediate next step".
- **Current fork tips (2026-07-03 PM, post sweep-fix merges):** anki **`cec324901`** (feature SHA `c54afe2b1` + README banner + P0 #1 band-abstain + P2 #5/#6 calibration-capture), anki-android **`6845e4e70a`** (`f2cf66ac35` + README banner + P0 #2 getCalibration exposure), Anki-Android-Backend **`70b8eaf`** (`14c2992` + README banner). **Sweep-fix status:** #1/#2/#5/#6 MERGED; #3 (AI grounding gate) + #4 (leakage) HELD on `feat/speedrun-ai` pending #3's deeper re-fix (AI is OFF-by-default → non-blocking). AAR-rebuild safety restored (getCalibration now on anki-android main).

## CRITICAL PATH — ✅ COMPLETE (2026-07-03). All build phases done + merged.
The entire Gate 2 → Phase 3 → Phase 4 (AI) → Phase 5 → Phase 6 chain plus the Manrope branding, LS1/2/3, and §8 ablation are **built, gate-reviewed, and merged to `main`.** What remains is not on any build critical path — it's the human demo/eval work + the 7 sweep bug fixes (see "Immediate next step" above).
- **✅ Gate 2** (proto + honest Performance/Readiness), **✅ Phase 3** (Problem bank + mini-mock), **✅ Phase 4** (AI service, kill-switched), **✅ Phase 5** (3 scores on shared Svelte, both platforms), **✅ Phase 6** (AAR re-pin + rebuild + APK), **✅ Manrope slice**, **✅ LS1/2/3**, **✅ §8 ablation**.
- **David's remaining actions:** the emulator visual gate + live sync demo recording + demo video (all human/record-only), then the Sunday eval/robustness/signed-APK/BrainLift work.
- **Audit backlog** (`FUTURE-PLANS.md` `[audit]`) = NON-critical; address opportunistically.
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
