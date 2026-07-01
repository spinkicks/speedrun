# Speedrun — Progress Tracker (done / left), mapped to the spec

Living checklist. Legend: ✅ done · ⚠️ partial · ❌ not started. Keep honest (project thesis). **Last updated 2026-07-01 (Wed afternoon)** — after the wed-plus merge to `main` on all 3 forks AND the 7-agent full audit (findings below).

## ✅ Done — foundation (walking skeleton, Mon–Tue)
- ✅ Anki forked & building from source; `just run` / `just check` green (known complexipy tool crash only).
- ✅ One engine, two apps PROVEN: AAR cross-compiled from our `rslib` (cargo-ndk, NDK 29.0.14206865); AnkiDroid instrumentation test asserts `getCoverage().backendVersion == "26.05"` == desktop.
- ✅ Windows build fixes (render.rs OS-separator for n2, out-of-tree uv venv, Defender exclusion) — render.rs is upstream-worthy.

## ✅ Done — Wednesday MVP + Wednesday-Plus (ALL merged to `main` on all 3 forks, 2026-07-01)
**Engine (5 RPCs on `SpeedrunService`, proto FROZEN):**
- ✅ `GetCoverage`, `GetTopicMastery` (FSRS retrievability → mastered proportion + Wilson 95% + abstain) — read-only.
- ✅ `GetExamProfile` (exam DAG from synced config) — read-only.
- ✅ **`ReorderNewByPointsAtStake`** — the mutating change: `transact(Op::SortCards)`, new-card positions only, undo-safe, integrity `ok` persisted AND post-undo, ablation modes Full/FeatureOff/Plain. 5 Rust + 1 Python tests.
- ✅ `GetPerformanceReadiness` — deterministic always-abstain SCAFFOLDING (non-AI, clearly marked).
**Content:** ✅ exam-profile DAG (`gre_math.json`, weights sum 1.0, acyclic, tag↔topic alignment AUDIT-VERIFIED clean); ✅ 35-card calc+LA seed deck w/ Source fields; ✅ deterministic FLEX scraper (no AI).
**Installer:** ✅ network-independent (Briefcase win/mac templates vendored in-tree; `SyncSubmodule` dropped; installer tests pass).
**Dashboard:** ✅ shared Svelte Memory page on BOTH platforms (desktop Tools → "Speedrun: Memory" dialog; Android PageFragment; AAR auto-bundles the page — no-404 confirmed). ⚠️ but see CRITICAL audit finding below (desktop data path).
**Sync:** ✅ `anki-sync-server` in-fork + §7b two-way conflict test (10+10 same-card revlog union, integrity ok; honest caveat documented) + `docs/SYNC-SELFHOST.md`. Full sync suite 25/25.
**Git:** ✅ all on `main` — anki `1fed9e109`, Anki-Android-Backend `299bb44` (rsdroid pin `a0ead51c9`) + `d4086e0` (Cargo.lock `--locked`), anki-android `a56dda6cfb`. Branches kept as backup. Upstream tracking fixed.
**Docs:** ✅ `BUILD-PREREQS.md`, `SYNC-SELFHOST.md`, §7a artifacts (refreshed 07-01), design specs (`memory-dashboard-spec.md`, `speedrun-home-spec.md` APPROVED).

## ✅ Speedrun Home ("The Run", revamp slice 1) — MERGED to `main` (2026-07-01)
Branded auto-open landing on BOTH platforms, per `docs/design/speedrun-home-spec.md`. Shared Svelte page (`ts/routes/speedrun-home/`) — flat/sharp/terminal aesthetic, splits with honest 95% error-brackets, amber pace accent, honest footer. Desktop: `SpeedrunHome` QDialog, config-gated auto-open on launch (post-sync, safeMode-skipped) + Tools entry + START RUN→overview bridge. Android: PageFragment + nav + menu. **Cursor-verified via David's `just run` screenshot** — Home auto-opened rendering live data (9 topics, coverage 0/9, honest abstain rows) = the audit's render-proof rule satisfied. Merged: anki `52bcefa7e` · Anki-Android-Backend `a125ad5` (rsdroid pin → `6341b6f61`) · anki-android `2146d885e6`.
- ✅ **All 4 audit gate-blockers fixed + code-verified** (commit `6341b6f61` + `52bcefa7e`): desktop data path (`AnkiWebViewKind.SPEEDRUN` API access + 4 methods in `exposed_backend_list` — fixed Home AND Memory), exam-profile bootstrap (`include_str!` default, both platforms), `closeWithCallback` on both dialogs, auto-open moved into post-sync `_onsuccess` + safeMode guard. 15/15 Rust tests, Python data-proof test, adversarial review (couldn't refute), Playwright e2e (RPCs 200 + render).
- ⬜ **David:** Android emulator smoke (post-merge confirmation) + recordings.

## Prior 7-agent audit (2026-07-01) — RESOLVED
The audit that caught the above (UI shipped "code-complete" but never rendered on desktop: RPCs 403/404 + no profile bootstrap) is now fully addressed on `main`. Non-critical audit items remain itemized in `FUTURE-PLANS.md` under `[audit]`. Original finding text kept below for the record:
- ⚠️ **7-AGENT AUDIT FINDINGS (2026-07-01) — fixes assigned to Claude's current branch:**
  - **CRITICAL (desktop data path):** speedrun pages cannot reach the backend on desktop — `qt/aqt/mediasrv.py` `exposed_backend_list` lacks the 4 speedrun methods (POSTs 404) AND both dialogs use `AnkiWebViewKind.DEFAULT` which has no API access in `webview.py` `_profileForPage` (403 + warning popup). Android bridge is correctly wired. Dashboard has never actually rendered data on desktop.
  - **CRITICAL (demo blocker, both platforms):** exam profile is never bootstrapped into collection config — `GetExamProfile` returns `""` on any fresh collection (even after seed-deck import) → Home/Memory show the error state forever. Needs a bootstrap (engine `include_str!` fallback OR per-platform config seed).
  - **HIGH:** both dialogs missing `closeWithCallback` (DialogManager.closeAll → crash path on quit/profile-switch; auto-open Home makes this mainline). `get_topic_mastery` N+1 per-card queries (50k-deck bench blocker). Full-mode reorder determinism relies on SQLite implicit order, not a code contract (§8 ablation reproducibility).
  - **MEDIUM (backlogged in FUTURE-PLANS):** no i18n/FTL on speedrun pages; MathJax labels not implemented (spec item); RangeBand uses non-existent CSS tokens (`--accent`/`--frame-bg`) so band won't theme; empty-state conflates missing-profile vs no-cards; test gaps (FeatureOff mode, exact-position undo assert, child decks, Python modes 1/2); constants duplicated (0.9 / 20 / "gre_math"); no instrumentation test for the Android screen/bridge.
- ⬜ **David:** desktop + Android emulator smoke tests — **hold until Claude lands the critical fixes**, then record.

## Friday — AI + 3 scores + sync demo (full brief: `docs/plans/2026-07-03-friday-brief.md`)
- ⚠️ **Interleaving headline:** new-card points-at-stake reorder ✅ DONE; the **due-card queue-builder interleave** (weakness × weight × interleave at review time, PRD §4.65-66) is the remaining Friday engine piece.
- ⚠️ **Sync:** server + §7b test ✅ DONE; remaining = live desktop↔phone two-way demo + offline-reconnect run.
- ❌ **Performance model** P(correct on novel problem) + **memory→performance gap meter** (§7d) — needs the `Speedrun::Problem` note type + problem bank first.
- ❌ **Readiness** flat IRT → scaled 200–990 + conformal range + give-up rule (scaffolding RPC exists; needs append-only proto additions: percentile, scale semantics, gap delta, unlock requirements).
- ❌ **External AI/RAG service** (FastAPI + LangGraph, off by default): generate → SymPy/CAS verify → RAG source-ground → gold-set gate (§7f).
- ⚠️ **Three scores on phone** (Memory live; Perf/Read columns scaffolded, abstaining).
- ❌ App still scores with **AI off** (needs curated Problem bank).

## Sunday — prove it & ship
- ❌ Memory **calibration** (reliability chart + Brier/log loss on held-out) (§9.1).
- ❌ Performance accuracy on held-out exam questions (§9.2); score mapping + range writeup (§9.3).
- ❌ **3-build ablation harness** (full / feature-off / plain), equal study time, pre-registered metric (§8) — engine `AblationMode` exists; the harness/builds do not.
- ❌ **Leakage check** script (§7e — `eval/holdout/` does not exist yet); **crash ×20** + offline tests (§7g); **`make bench`** p50/p95/worst on 50k deck (§7h, §10).
- ❌ Packaged **installers** (desktop) + **signed APK** (+ arm64-v8a for physical devices); both apps score with AI off.
- ❌ Results report + model one-pagers + demo video (3–5 min) + BrainLift final pass.

---

## Rubric weight coverage (updated 2026-07-01 post-audit)
| Area | Weight | Status |
|---|---|---|
| Rust change & fit with Anki | 20% | ✅ read-only RPCs + a real **mutating** reorder via `transact` w/ tests; strengthen Fri with due-queue interleave; §7a artifacts refreshed |
| Score accuracy & honest uncertainty | 20% | ⚠️ Memory score LIVE (Wilson + abstain, engine-verified); Performance/Readiness scaffolding only (always-abstain — honest) |
| Study feature on learning science | 15% | ⚠️ points-at-stake new-card reorder + ablation modes built; due-card interleave + 3-build harness remain |
| AI checking & safety | 15% | ❌ Friday (service, CAS verify, RAG, gold gate) |
| Fair re-runnable tests | 12% | ❌ eval/holdout, ablation harness, leakage, bench all pending (Sunday) |
| Two apps one engine + sync | 10% | ⚠️ one engine ✅ both apps; §7b conflict test ✅; live two-way phone demo pending |
| Useful product & clean UX | 8% | ⚠️ Memory dashboard shipped (desktop data-path fix in flight); Speedrun Home "The Run" landing today |

**Hard limits watch:** real Rust change ✅ (read + mutating). Phone shares engine ✅; sync test ✅ (live demo pending — needed to fully lift the 70% cap). Clean-device: installer now network-independent ✅ (actual clean-machine run still to record). No fake numbers ✅ (everything abstains until it can't be wrong).
