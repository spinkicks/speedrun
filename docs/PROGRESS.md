# Speedrun — Progress Tracker (done / left), mapped to the spec

Living checklist. Legend: ✅ done · ⚠️ partial · ❌ not started. Keep honest (project thesis). **Last updated 2026-07-05 (Sun PM) — CODE SIDE 100% COMPLETE + VERIFIED ON BOTH SHELLS.** Per-repo `main`: anki **`b28c23648`** · anki-android **`5680917f79`** · Anki-Android-Backend **`ccccad3`** · umbrella `main` (RESULTS/VERIFY/PROOF-INDEX current).

> **2026-07-05 (Sun) headline — CODE COMPLETE.** Everything is built, merged, and verified: the Friday scope + LS1/2/3 + §8 ablation + AI service + all 7 sweep fixes + interactive MCQ auto-grade + 4 interactive visuals + the **clean sidebar shell** (Home/The Map/Memory/Start Run/Mini-mock, both platforms) + the **in-app AI toggle** (MSI path). **All Sunday model/challenge evals RAN + recorded** (`docs/RESULTS.md`): §9.1 calibration (Brier 0.0569), §9.2 performance, §7d paraphrase gap (Δ=0.204), §7e leakage (0 leaks CLEAN), §7f AI 3-count (47/47 useful, 0 wrong), §7g crash×20 (20/20), §7h `just bench` (button/next-card PASS, dashboard MISS@50k honest). **Signed arm64 release APK** built. **Sidebar native-verified on BOTH shells** (Cursor: Android emulator; Claude: desktop headless — 0 console errors, honest abstains). One-command setup: `scripts/speedrun-launch.ps1 -All`. Grader entry: `docs/VERIFY.md`. **Remaining = human only:** the recordings (demo video, both builds on clean devices, live+offline sync) + BrainLift PDF re-export + submit.

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

## Sunday — prove it & ship (✅ evals DONE; recordings remain)
- ✅ **Gold set + leakage clearance** — `eval/holdout/gre_math_gold.jsonl` (50, triple-verified); `eval/holdout/` off-limits to implementers.
- ✅ **3-build ablation harness** (§8) — `docs/ablation-s8-results.md` (M1 Full 0.0000 vs 0.7949; honest M2 miss).
- ✅ **Desktop installer** — release MSI (~194 MB, bundles+auto-imports deck), offline, 27/27; on GitHub Release `v0.1.0-early`.
- ✅ **§9.1 Memory calibration RUN** — Brier **0.0569** / log-loss **0.2177** / ECE **0.0042** + reliability chart (labeled simulated FSRS stream). `RESULTS.md §9.1`.
- ✅ **§9.2 Performance accuracy** (held-out) + **§9.3 score-mapping writeup** — sim predictive Brier 0.2486/AUC 0.6645 + hermetic auto-grader fidelity 50/50; θ→200–990+conformal method documented. `RESULTS.md §9.2/§1.3`.
- ✅ **§7d paraphrase/transfer gap** — recall 0.907 vs transfer 0.703, Δ=0.204 (70/70 SymPy-verified). `RESULTS.md §7d`.
- ✅ **§7e leakage check** — standalone run, **0 leaks CLEAN** (181 training vs 50 gold). `RESULTS.md §7e`.
- ✅ **§7f AI card 3-count** — 47/47 useful, 0 wrong, 0 bad-teaching (live gpt-4o judge). `RESULTS.md §7f`.
- ✅ **§7g crash ×20 + offline** — 20/20 integrity-ok; AI-off scores compute. `RESULTS.md §7g`.
- ✅ **§7h `just bench`** — button/next-card PASS §10 (~490×/2600×); dashboard MISS@50k (honest, documented). `RESULTS.md §7h`.
- ✅ **Signed release APK** — `AnkiDroid-play-arm64-v8a-release.apk` (50.2 MB), v2-signed, real device. Both apps score with AI off ✅.
- ✅ **Results report + model one-pagers** — `docs/RESULTS.md` (+ `VERIFY.md` grader guide + refreshed `PROOF-INDEX.md`).
- ✅ **Clean UX / sidebar** — persistent sidebar shell + in-app AI toggle; native-verified both shells.
- ⬜ **David (human only):** demo video (3–5 min, w/ "since MVP" beat) + both builds installing/running on clean devices + live two-way & offline sync recording + **BrainLift PDF re-export** + submit.
- ✅ **7 sweep bug fixes + 8 adversarial-hunt bugs** — ALL fixed+merged (engine/qt/services/android; Part-B both platforms). None in flight.

---

## Rubric weight coverage (updated 2026-07-03 PM — post sweep-fix + MCQ-autograde merge, visuals merging)
| Area | Weight | Status |
|---|---|---|
| Rust change & fit with Anki | 20% | ✅ read-only RPCs + a real **mutating** reorder via `transact` + due-card weakness×topic interleave; 66+ speedrun tests; §7a artifacts |
| Score accuracy & honest uncertainty | 20% | ✅ all three scores LIVE + honest. ✅ **Performance OBJECTIVELY KEY-CHECKED** (MCQ auto-grade). ✅ **held-out RUNS DONE** — §9.1 calibration Brier 0.0569, §9.2 performance + §9.3 score-mapping (`RESULTS.md`). |
| Study feature on learning science | 15% | ✅ points-at-stake reorder + due-card interleave + LS1/2/3 + MCQ practice/auto-grade + THE MAP; ✅ **§8 3-build ablation RAN** (honest M1 win + M2 miss); ✅ **§7d paraphrase gap RAN** (Δ=0.204) |
| AI checking & safety | 15% | ✅ service (OFF by default): SymPy verify + hybrid RAG + gold-set gate. ✅ **§7f 3-count RAN** (47/47 useful, 0 wrong, 0 bad-teaching); ✅ **§7e leakage RAN** (0 leaks CLEAN); baseline honest tie documented; every output cited |
| Fair re-runnable tests | 12% | ✅ ablation + gold set + leakage + **§7g crash×20 (20/20)** + **§7h `just bench`** all RAN + reproducible; `docs/VERIFY.md` gives copy-paste re-run commands |
| Two apps one engine + sync | 10% | ✅ one engine, both apps (AAR re-pinned `ccccad3` + signed APK); §7b conflict test ✅. ⬜ live two-way phone demo recording pending (human) |
| Useful product & clean UX | 8% | ✅ Speedrun Home + Memory + 3 scores + mini-mock + 4 interactive visuals + **clean persistent sidebar** (both platforms, native-verified) + in-app AI toggle; Manrope/#F4F7FA identity |

**Hard limits watch:** real Rust change ✅. Phone shares engine ✅; sync test ✅ (live demo recording pending — needed to fully lift the 70% cap). Clean-device: network-independent installer ✅ + clean-machine run recorded ✅ (re-record with current MSI) + **signed release APK** ✅. Held-out testing ✅ (§9.1/§9.2). Re-runnable ✅ (`VERIFY.md`). Leaked data ✅ **0 leaks CLEAN** (§7e). No fake numbers ✅ (everything abstains + labeled-simulated where simulated). **Only remaining cap-relevant item = the human sync + clean-device recordings.**
