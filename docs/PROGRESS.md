# Speedrun — Progress Tracker (done / left), mapped to the spec

Living checklist. Legend: ✅ done · ⚠️ partial · ❌ not started. Keep honest (project thesis). **Last updated 2026-07-03 (Fri PM)** — after the full Friday-scope + LS1/2/3 + §8 ablation + AI-service batch-merge, plus all 7 sweep fixes + interactive MCQ auto-grade merged, and 4 interactive visuals merged to anki `main`. Per-repo `main`: anki `348db0c6c` · anki-android `6845e4e70a` · Anki-Android-Backend `70b8eaf` · umbrella `e36d765`.

> **2026-07-03 PM headline:** the entire build scope is shipped + merged, including **all 7 adversarial-sweep fixes** and the **interactive MCQ auto-grade** (Performance now objectively key-checked on desktop). **NEW:** 4 interactive pure-SVG visuals (THE MAP blast-radius + calibration reliability diagram + memory→performance gap slope + readiness gauge) are live-verified + Claude-reviewed and **merging to anki `main`** (SHA finalizes at merge). What's left is human demo/eval (emulator gate, sync-demo recording, demo video), the Sunday eval RUNS + robustness + signed APK + BrainLift pass, and one in-progress convenience item (installer bundles the seed deck + auto-imports on first launch).

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
- ✅ **Android emulator smoke DONE (2026-07-01):** `installPlayDebug` on `Pixel_10`; Speedrun Home renders identically to desktop (same shared page + engine — two-platform parity proven visually). One cosmetic follow-up: Android shell toolbar + system bars render white vs the dark page (theming slice; see FUTURE-PLANS — fix before recording). ⬜ David's recordings remain.

## ✅ Mobile-first UX + START RUN + reviewer — MERGED to `main` (2026-07-01)
Plan `docs/plans/2026-07-01-mobile-first-and-startrun-plan.md`. Triggered by David's on-device testing. Per-repo `main`: anki **`af1138428`** · Anki-Android-Backend **`9aa21ec`** (rsdroid pin `eb4f5a3ff` — behind anki tip only by Android-irrelevant commits; re-pin at next AAR rebuild) · anki-android **`fdfd086031`**.
- ✅ **M0** mobile-first responsive Home + Memory (stacked ≤768px → desktop columns; e2e no-overflow gate).
- ✅ **Memory-dark** re-theme (was light; live-probe verified dark; resolves the audit RangeBand-token finding).
- ✅ **M1** Android dark shell (scoped, no global theme change).
- ✅ **S1** desktop START RUN — real study + honest import/caught-up banners + Custom Study; **David-verified** (launches real review). Bug caught in smoke (false "caught up" — `deck_tree()` has no counts) → fixed via `sched.deck_due_tree()` (`f0a06ce68`) + Qt-free `decide_start_run` + characterization test.
- ✅ **S2** Android START RUN via `bridgeCommand` → native reviewer + snackbar fallbacks.
- ✅ **R1a** desktop reviewer minimal dark chrome (CSS-only, night-mode vars; David-verified). **R1b (Android reviewer) DEFERRED** post-Friday (shared `CardViewerActivity` — can't scope without over-reach); full-chrome polish also deferred.
- ✅ **QA sweep** (12-agent, bug-class hunt after the contract bug slipped): 45 contracts correct, 6 refuted, **1 real bug fixed** — desktop START RUN fired twice (pycmd≡bridgeCommand alias on Qt) → `(g.pycmd ?? g.bridgeCommand)` fires once (`af1138428`). Coverage gap (Playwright bypasses Qt bridge) closed with backend unit tests.
- ✅ **Installer packaged** (release MSI, offline, `test_installer.py` 27/27): `repos/anki/out/installer/dist/anki-26.05-win-x64.msi`. ✅ **Clean-machine install recorded** (`CleanTestInstall.mp4`, fresh `CleanTest` account). ✅ Android review session verified on emulator.
- ⬜ **David — remaining recordings** (`docs/PROOF-INDEX.md`): test results, phone review screen-recording, MVP demo video (`docs/DEMO-VIDEO-SCRIPT.md`) → submit.
- ⏭️ Post-Friday backlog: R1b Android reviewer theme, full reviewer chrome, i18n/FTL + MathJax labels (see FUTURE-PLANS `[audit]`).

## ✅ Friday (highest-weight day) — EXECUTED + MERGED (2026-07-02→03)
`docs/plans/2026-07-03-friday-ai-scores-sync.md` — executed subagent-driven with per-phase gate review. All merged to `main`:
- ✅ **Due-card queue-builder interleave** (weakness × ETS weight × topic interleave at review time, read-time, ablation-gated) — the remaining headline engine piece, done.
- ✅ **Problem layer:** `Speedrun::Problem` MCQ note type (`PROBLEM_MODEL_ID=2047815909`) + 64-problem bank (double-SymPy-verified) + timed mini-mock (filtered deck, `reschedule=true`).
- ✅ **Honest Performance** (P(correct) + mean-CI band + memory→performance gap Δ + abstention) and **Readiness** (flat IRT → scaled 200–990 + conformal range + give-up rule, in-engine deterministic).
- ✅ **OFF-by-default AI service** (`services/speedrun-ai/`): SymPy verify + hybrid RAG (82-passage corpus) + gold-set gate; kill-switched.
- ✅ **Three scores on the shared Svelte surface**, both platforms; Manrope/#F4F7FA re-skin folded in.
- ⬜ **Live sync demo** — §7b test green; the human-visible desktop↔Android recording remains.

## Prior 7-agent audit (2026-07-01) — RESOLVED
The audit that caught the above (UI shipped "code-complete" but never rendered on desktop: RPCs 403/404 + no profile bootstrap) is now fully addressed on `main`. Non-critical audit items remain itemized in `FUTURE-PLANS.md` under `[audit]`. Original finding text kept below for the record:
- ⚠️ **7-AGENT AUDIT FINDINGS (2026-07-01) — fixes assigned to Claude's current branch:**
  - **CRITICAL (desktop data path):** speedrun pages cannot reach the backend on desktop — `qt/aqt/mediasrv.py` `exposed_backend_list` lacks the 4 speedrun methods (POSTs 404) AND both dialogs use `AnkiWebViewKind.DEFAULT` which has no API access in `webview.py` `_profileForPage` (403 + warning popup). Android bridge is correctly wired. Dashboard has never actually rendered data on desktop.
  - **CRITICAL (demo blocker, both platforms):** exam profile is never bootstrapped into collection config — `GetExamProfile` returns `""` on any fresh collection (even after seed-deck import) → Home/Memory show the error state forever. Needs a bootstrap (engine `include_str!` fallback OR per-platform config seed).
  - **HIGH:** both dialogs missing `closeWithCallback` (DialogManager.closeAll → crash path on quit/profile-switch; auto-open Home makes this mainline). `get_topic_mastery` N+1 per-card queries (50k-deck bench blocker). Full-mode reorder determinism relies on SQLite implicit order, not a code contract (§8 ablation reproducibility).
  - **MEDIUM (backlogged in FUTURE-PLANS):** no i18n/FTL on speedrun pages; MathJax labels not implemented (spec item); RangeBand uses non-existent CSS tokens (`--accent`/`--frame-bg`) so band won't theme; empty-state conflates missing-profile vs no-cards; test gaps (FeatureOff mode, exact-position undo assert, child decks, Python modes 1/2); constants duplicated (0.9 / 20 / "gre_math"); no instrumentation test for the Android screen/bridge.
- ⬜ **David:** desktop + Android emulator smoke tests — **hold until Claude lands the critical fixes**, then record.

## ✅ Learning-science additions (2026-07-02) — MERGED
- ✅ **LS1 calibration** — pre-answer confidence self-bet (Sure/Think/Guess) → Brier/ECE, config-blob store (`speedrun:calibration_log`), desktop capture via webview hook, abstains <20 attempts, self-rated framing; `GetCalibration` RPC + 5th "Calibration" StatRow (both platforms). Android capture deferred (native Kotlin) — read-only stat still shows.
- ✅ **LS2 worked-examples-first + faded reveal** — progressive step reveal (LaTeX-safe, ground-truthed 0/134 split points inside math spans) + `ExampleFirst` field.
- ✅ **LS3 honesty-guardrail copy** — diminishing-returns / survivorship-bias / desirable-difficulty / abstention framing / self-reported caveat, all gated to render only on real data.

## ✅ §8 ablation harness (2026-07-02) — MERGED
- ✅ One build, three modes (`AblationMode` Full/FeatureOff/Plain); pre-registered metrics: M1 same-topic adjacency (Full **0.00** vs 0.79 baselines — decisive), M2 pre-registered secondary was mis-specified and reported honestly (not hidden), M3 exploratory. Results: `docs/ablation-s8-results.md`. (This was on the Sunday list; done early.)

## ✅ Interactive layer (2026-07-03 PM) — MERGED / merging
- ✅ **Interactive MCQ auto-grade** — MERGED (anki `a47dac310`). `Speedrun::Problem` choices are now clickable → the chosen option is graded **backend-side** against `CorrectAnswer` (not client-trusted) → persisted to the synced `speedrun:mcq_attempts` config blob (no schema/proto/model-field change). The engine's Performance (`topic_problem_stats`) now counts **objective key-checked correctness**, overriding self-rating and falling back to self-rated (`button≥3`) only when no auto-grade exists (backward-compatible). **Retires the "self-reported until interactive grading" caveat on desktop.** ⚠️ Android in-reviewer capture deferred (native bridge) — the engine reads the blob regardless of platform, so Android inherits the read side once capture lands.
- ✅ **4 interactive pure-SVG visuals** — `feat/speedrun-visuals`, live-verified + Claude-reviewed, **merging to anki `main`** (SHA finalizes at merge). Both platforms, honest abstains, **11/11 unit tests**:
  - ✅ **THE MAP** (`/speedrun-map`) — interactive prerequisite-graph; tap a node → **blast-radius** (every downstream topic it caps). Realizes **BrainLift Flagship #7** — the signature not-Anki visual.
  - ✅ **Calibration reliability diagram** (Memory) — predicted-confidence vs observed-accuracy, honest abstain below threshold.
  - ✅ **Memory→performance gap slope chart** (Memory) — per-topic slope between flashcard recall and timed novel-problem accuracy (§7d gap meter, visualized).
  - ✅ **Readiness gauge** (Home) — 200–990 with the conformal band drawn in.
- ✅ **All 7 adversarial-sweep bugs fixed+merged** — incl. #3 RAG grounding (semantic-embedding gate + fail-closed syllabus scoping) and #4 leakage; #1 single-card band-abstain and #2 Android `getCalibration` exposure landed earlier in the sweep. No sweep fixes remain in flight.
- ⚠️ **Installer bundles seed deck + auto-import on first launch** — IN PROGRESS (Claude). Bundle the seed deck into the installer and auto-import it on first launch so a grader sees live data immediately. Convenience only; not on any build critical path.

## Sunday — prove it & ship (partly done early)
- ✅ **Gold set + leakage clearance** — `eval/holdout/gre_math_gold.jsonl` (50, triple-verified, leakage-cleared); `eval/holdout/` created (implementer agents must NOT read it).
- ✅ **3-build ablation harness** (§8) — done (above).
- ✅ **Desktop installer** — release MSI, offline, 27/27.
- ⬜ Memory **calibration RUN** (reliability chart + Brier/log loss on held-out) (§9.1) — LS1 math shipped; the held-out evaluation run remains.
- ⬜ **Performance accuracy** on held-out exam questions (§9.2); score-mapping + range writeup (§9.3).
- ⬜ **crash ×20** + offline tests (§7g); **`make bench`** p50/p95/worst on 50k deck (§7h, §10).
- ⬜ **Signed APK** (+ arm64-v8a for physical devices); both apps score with AI off (✅ already true).
- ⬜ Results report + model one-pagers + demo video (3–5 min) + BrainLift final pass.
- ✅ **7 sweep bug fixes** (2026-07-03) — ALL fixed+merged: 2 P0 (single-card band-abstain; Android getCalibration) + 2 P1 AI-safety (#3 RAG grounding via semantic-embedding gate + fail-closed syllabus, #4 leakage) + 2 P2 calibration-capture + #7. None remain in flight.

---

## Rubric weight coverage (updated 2026-07-03 PM — post sweep-fix + MCQ-autograde merge, visuals merging)
| Area | Weight | Status |
|---|---|---|
| Rust change & fit with Anki | 20% | ✅ read-only RPCs + a real **mutating** reorder via `transact` + due-card weakness×topic interleave; 66+ speedrun tests; §7a artifacts |
| Score accuracy & honest uncertainty | 20% | ✅ all three scores LIVE + honest (Memory Wilson+abstain; Performance P(correct)+gap Δ+abstain; Readiness IRT→200–990+conformal+give-up). ✅ **Performance now OBJECTIVELY KEY-CHECKED** — interactive MCQ auto-grade (backend-graded against `CorrectAnswer`) retires the "self-reported" caveat on desktop (Android capture deferred). ✅ P0 single-card band-edge bug fixed+merged (abstains). ⬜ held-out calibration/accuracy RUNS remain (Sunday). |
| Study feature on learning science | 15% | ✅ points-at-stake reorder + due-card interleave + LS1 calibration + LS2 worked-examples-faded + LS3 honesty copy + interactive MCQ practice/auto-grade + THE MAP prerequisite-graph blast-radius; §8 ablation harness done |
| AI checking & safety | 15% | ✅ service shipped (OFF by default): SymPy verify + hybrid RAG + gold-set gate; adversarially reviewed. ✅ P1 gate-hardening fixes MERGED (#3 RAG grounding via semantic-embedding gate + fail-closed syllabus scoping, #4 leakage) |
| Fair re-runnable tests | 12% | ✅ ablation harness + gold set + leakage clearance done. ⬜ crash×20 / offline / `make bench` runs remain (Sunday) |
| Two apps one engine + sync | 10% | ✅ one engine, both apps (Phase 6 AAR + APK); §7b conflict test ✅. ⬜ live two-way phone demo recording pending |
| Useful product & clean UX | 8% | ✅ Speedrun Home + Memory + 3 scores + mini-mock on both platforms; Manrope/#F4F7FA identity; desktop data path fixed. ✅ **+ 4 interactive pure-SVG visuals** (THE MAP tap→blast-radius, calibration reliability diagram, memory→performance gap slope chart, readiness gauge) — both platforms, honest abstains |

**Hard limits watch:** real Rust change ✅ (read + mutating + interleave). Phone shares engine ✅; sync test ✅ (live demo recording pending — needed to fully lift the 70% cap). Clean-device: network-independent installer ✅ + clean-machine run recorded ✅ (installer seed-deck auto-import in progress — convenience). No fake numbers ✅ (everything abstains until it can't be wrong) — the P0 single-card band edge case is now fixed+merged (abstains when `cards_with_data<2`), keeping this true in the corner case.
