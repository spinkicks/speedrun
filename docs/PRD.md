# Speedrun — Product Requirements Document (PRD)

**Exam:** GRE Mathematics Subject Test · **Platforms:** Desktop (Win/Mac/Linux) + Android (emulator OK) · **License:** AGPL-3.0-or-later (credit to Anki).

**Companion docs:** `brainlift/BrainLift.md` (thesis/SPOVs/evidence), `docs/ARCHITECTURE.md` (engine/build feasibility), `docs/DECISIONS.md` (decision log), `research/core-sources.md` (load-bearing sources). This PRD is the buildable design; the task-by-task implementation plan comes next (via the writing-plans skill).

> Status: design approved (Sections 1–8). To be refined with Claude's Workstream-C research (agentic workflow + codebase traversal).

---

## 1. Goal & success criteria
Build, on top of Anki, an **honest** GRE-Math study app that reports **three separate scores** (Memory, Performance, Readiness) — each with a range and a give-up rule — across **desktop + Android sharing one engine**, with a real change to Anki's **Rust** backend.

**Success = spec rubric compliance**, sequenced to our cadence:
- **Mon (today):** this PRD + plan.
- **Tue:** heavy coding (get ahead of Wednesday).
- **Wed:** both apps' MVPs live (desktop + Android), reviewing the same GRE deck, **no AI**; Rust change working with tests; memory model with honest range + give-up; clean-machine installer.
- **Fri:** AI added + checked; two-way sync; three scores on phone.
- **Sun:** prove it (calibration/ablation/evals) + ship installable builds.

**Hard limits to respect:** real Rust change (else 50% cap); phone companion sharing the engine + sync (else 70%); re-runnable tests (else 60%); held-out testing (else 60%); no fake readiness numbers (auto-fail); both apps run on a clean device (else 50%); no leaked test data (zeroes that score); AI claims need traceable sources.

## 1b. User persona & user stories

**Primary persona — "The quant-grad applicant."** A final-year math/physics/CS/econ undergrad or recent grad applying to math-heavy graduate programs that recommend or require the GRE Mathematics Subject Test. Technically sophisticated and self-motivated, but time-constrained (studying alongside coursework or a job) and skeptical of fluffy ed-tech. Has an uneven background (strong in some areas, rusty in others), wants an honest signal of readiness and the most efficient use of limited study time, and studies in two places: deep sessions at a desk and short reviews on a phone between commitments.
**Secondary persona (future):** the GRE Physics Subject Test applicant (enabled by the exam-profile abstraction).

**User stories** (As a test-taker, I want … so that …):
1. … my readiness shown as an honest projected score *with a range* (or "not enough data yet"), so that I can trust it and decide whether I'm ready to sit the exam. (SPOV 2)
2. … to see the gap between "I remember this" and "I can solve a timed problem on it," so that I spend time on what actually moves my score. (SPOV 1)
3. … the app to tell me the single best next thing to study, so that I put limited time on the highest-leverage topic. (SPOV 4)
4. … timed, mixed-topic practice that mirrors the real exam's pacing and topic-switching, so that test day feels familiar (and easy). (SPOV 3, 7)
5. … to review on my phone between classes and have it sync with my desktop, so that no progress is lost or double-counted. (two-apps-one-engine)
6. … every practice problem to be verified-correct and cite its source, so that I never learn a wrong fact. (SPOV 6)
7. … the app to build motivation by making me succeed (not by nagging me with streaks), so that I keep coming back. (SPOV 8)
8. … one coherent place for all GRE-math content instead of juggling books/PDFs/forums, so that my attention goes to learning, not reconciling sources. (SPOV 9)

**Definition of success (for the user):** they reach a calibrated readiness band they trust, having spent their study time on the highest-leverage gaps, and feel (and are) prepared on test day.

---

## 2. Architecture (Hybrid — Approach 3)
**Fulcrum:** a desktop Python/Qt add-on does NOT appear on Android. So anything cross-device lives in (a) the shared **Rust core**, or (b) **synced collection data**, or (c) is re-implemented per platform.

**Components:**
- **Forked Anki `rslib` (shared Rust core):** (1) new review-ordering in `scheduler/queue/builder/` (interleaving + points-at-stake); (2) read-only `SpeedrunService` RPC (memory range, coverage, later readiness). Ships to desktop (PyO3 `pylib/rsbridge`) + Android (rsdroid JNI).
- **Collection (SQLite, synced):** carries cards, practice problems, exam-profile config, scores. Syncs via self-hosted Anki sync server (`rslib/sync`).
- **Desktop:** forked Anki + Speedrun add-on (Python/Qt) + webview dashboard.
- **Android:** forked AnkiDroid linking our `rslib` via forked `Anki-Android-Backend` (rsdroid); minimal Kotlin views.
- **External Speedrun service (Python/FastAPI, OFF until Fri):** IRT/calibration + RAG generation + CAS verification; writes verified problems/scores into the collection (which sync). App must fully run with this **off**.
- **Content pipeline:** pre-Wed non-AI scraper/author → notes; post-Wed AI feeds the same note types.

## 3. Data model (all additive; rides in the synced collection)
**Note types (render via Anki MathJax):**
- **`Speedrun::Declarative`** (memory layer, FSRS-scheduled): `Front`, `Back`/cloze, `TopicID`, `Source`.
- **`Speedrun::Problem`** (performance layer): `Stem`, `Choices`/`NumericAnswer`, `CorrectAnswer`, `WorkedSolution`, `TopicID(s)`, `TechniqueTag` (memory→performance bridge to declarative cards), `Source`; later `IRTParams` (a/b/c), `MalRuleDistractors`.

**Taxonomy + DAG:** hierarchical tags (`calc::single_var::integration`) for membership + an **exam-profile record** in collection config (JSON): topic list, prerequisite edges, content weights, scoring/percentile tables. Keyed by `exam_id` (generalizes to GRE Physics; supports a shared math-node layer for transfer credit). Rust queue reads tags + weights; dashboards read the DAG.

**Scores/config:** a Speedrun config blob (memory range, performance, readiness post-Fri, coverage %, calibration history), written by the RPC/external service, read by both apps.

**Syncs:** all notes/tags/config/scores (USN deltas). **Doesn't sync:** the external service's model internals — it writes results into the collection, which then syncs. No new sync protocol.

## 4. The Rust change (`rslib`)
**4A. New review-ordering** (`scheduler/queue/builder/` — `gathering.rs`, `sorting.rs`, topic-aware `intersperser.rs`):
- Order due cards by **points-at-stake = topic content-weight × prerequisite-centrality × current-weakness**, then **interleave by topic** (no two adjacent same-technique items). Inputs from synced exam-profile config; "weakness" = FSRS-retrievability aggregate per topic (no IRT needed for Wed).
- **Ablation toggle** (config flag): full / feature-off / plain Anki.
- **Safety:** changes only the *order* of due cards, not scheduling state/intervals → read-mostly, low corruption risk, undo intact. Additive protobuf message/field.
- **Tests:** ≥3 Rust unit (weights respected; no adjacent same-topic; toggle-off = default) + 1 Python integration test.

**4B. Read-only `SpeedrunService` RPC:** `GetTopicMastery`, `GetCoverage` (Wed), `GetReadiness` (Fri). Returns memory range (FSRS retrievability by topic), coverage % vs exam-profile, give-up state. No transaction/undo needed.

## 5. The three honest numbers + give-up rule
- **Memory (Wed):** FSRS retrievability aggregated by topic → range (bootstrap/Wilson interval over per-card retrievabilities). Give-up below `N` graded reviews.
- **Performance (Fri):** P(correct on novel problem) from topic memory + IRT difficulty + technique mastery + timing + coverage. Memory→Performance **gap meter** = per-topic delta (card recall vs problem accuracy).
- **Readiness (Fri):** **flat model first** — IRT θ → equating-style raw→scaled (200–990) → percentile (ETS table). Point estimate = calculus-weighted topic sum (NOT a min()-gate). **Range** via conformal/CQR (widens under sparse data). Graph-readiness = v2 experiment benchmarked against this.
- **Honesty display:** point estimate + range + coverage % + percentile + "how sure" + single best next action + last-updated + give-up rule.
- **Give-up rule (explicit, config-driven):** no readiness until ≥2 timed mini-mocks AND coverage threshold AND interval < cutoff; otherwise "INSUFFICIENT DATA — do X to unlock."
- **Calibration (Sun):** memory calibration chart + Brier/log loss on held-out reviews; performance accuracy on held-out problems + paraphrase/transfer test; readiness method + range documented. Machinery: conformal/CQR, ECE, temperature scaling, selective-prediction threshold.

## 6. Content pipeline
**Pre-Wed (NO AI):** hand-authored calc+LA seed (declarative cards + problems w/ worked solutions, tagged) + a **deterministic scraper** (HTML/LaTeX/PDF parsers, no LLM) pulling from **open-licensed/public-domain** sources (OpenStax CC-BY, public-domain texts, openly-licensed repos), each with a `Source` citation + manual QA. **Copyright line:** ship only permissibly-licensed content; ETS released forms used only for our own IRT benchmarking, never redistributed. Rule-based topic tagging.

**Post-Wed (AI, Fri+):** external hybrid neuro-symbolic generator — LLM proposes SymPy **schema → CAS verifies → RAG-grounds to named source → gold-set gate → writes `Problem` notes** (synced); mal-rule distractors. Augments the pool; AI-off keeps the Wed bank working.

**Gold set + leakage:** 50 human-verified Q&A pairs for the §7f check + held-out eval; scraper dedups against this set (MinHash/n-gram) so eval items never leak into study.

## 7. Sync, offline & conflict
- **Self-hosted Anki sync server** (`rslib/sync`); both apps point at it; notes/reviews/config sync as USN deltas.
- **Offline:** both apps work offline; reviews accumulate locally; sync on reconnect.
- **Conflict model:** USN incremental; clean fast-forward when one side changed; true divergence forces a full-sync "upload or download" choice (no per-card auto-merge).
- **§7b test:** (1) 10+10 *different* cards offline → all 20 land, none lost/doubled (dedup by review id); (2) *same* card on both → **documented conflict rule: latest-review-timestamp wins** (with implausible-clock-skew guard); both reviews logged in `revlog`, card state resolves to the winner.
- **Phasing:** Wed = both apps review the same deck (two-way sync not required yet); Fri = verified two-way sync + conflict rule + offline-reconnect.
- **§7g:** kill mid-review ×20 → zero corruption (Anki `transact`); network off → AI off cleanly, apps keep working.

## 8. Testing & verification
- **7a–7h** mapped (Section in BrainLift KT 9 + above): Rust tests + undo/corruption proof; sync test; coverage map w/ abstention; paraphrase/transfer test; leakage scan; AI card check w/ pre-set cutoffs (wrong ≤2%→0 target, useful ≥80%, bad-teaching ≤15%); crash/offline; `make bench` (p50/p95/worst vs §10 targets).
- **§8 ablation (headline experiment):** 3 builds (full / feature-off / plain Anki), same learners/questions/time; **pre-registered metric: accuracy on held-out mixed-topic problems at equal study time**; report range + nulls.
- **Re-runnable + held-out (12%):** fixed seed, one-command setup, train/test split, leakage-clean; includes the **flat-vs-graph readiness benchmark**.
- **Verification workflow:** TDD where feasible; CI gate (build+tests+lint) per task; `make bench`; verification-before-completion gate. (Refine with Claude Workstream-C research → `docs/BUILD-WORKFLOW.md`.)
- **Speed/reliability targets (§10):** button p95<50ms, next-card<100ms, dashboard load<1s, refresh<500ms, sync<5s, cold start desktop<5s/phone<4s, no freeze>100ms, zero corruption.

## 9. Tech stack, repos, build & deploy
**Repos (forked):** `repos/anki` (cloned), `repos/anki-android` (cloned), `repos/Anki-Android-Backend` (rsdroid — cloning); sync server from `rslib/sync`.
**Stack:** Rust 1.92.0 (rslib + RPC); Python/uv (pylib wrappers, desktop add-on, external FastAPI service: IRT/calibration via numpy/scipy + conformal, RAG via BM25+dense+FAISS+reranker, SymPy verify, LLM API); TypeScript/Svelte (desktop dashboard); Kotlin (Android views); MathJax (both platforms). Build: Anki ninja/n2; AnkiDroid Gradle; cargo-ndk for the AAR.
**Build/deploy:** Desktop `./run`→`tools/build`→`tools/build-installer` (clean-machine installer); Speedrun add-on bundled. Android: AAR from forked rsdroid (`local_backend=true`) → APK → emulator/device. External service OFF by default (graceful degradation).
**Skills/plugins:** finalize from Claude Workstream-C research (language skills + custom skills like an "rslib-change" recipe + "speedrun-card-author").

## 10. Day-1 walking skeleton (the feasibility gate, from ARCHITECTURE.md)
1. Desktop forked Anki builds & runs (`./run`; `./ninja check` green).
2. No-op read RPC end-to-end (`SpeedrunService.GetCoverage` returns a constant) — proves proto→Rust→Python.
3. Self-hosted sync server up; desktop syncs against it.
4. Clone `Anki-Android-Backend`; stock `local_backend=true` AAR builds; AnkiDroid runs against it.
5. Rebuild AAR from our forked rslib (with the RPC); call from `libanki` — **true "one engine, two apps" milestone.**
6. Then real logic: queue-ordering change (core) → exam-profile + seed deck (data) → memory-range dashboard (RPC) → (Fri) external service for readiness + AI generation.

## 11. Risk register (from ARCHITECTURE.md)
1. **rsdroid build chain** (High) — clone + green `local_backend` AAR first; pin upstream anki rev.
2. **Engine fork drift** (High) — ONE forked anki feeds both bridges; additive proto.
3. **Windows desktop build friction** (Med) — follow `docs/windows.md`; relocate to `C:\anki` if long-path/linker errors.
4. **Undo/corruption** (Med-High) — `transact` + `Op` + additive fields; prefer read-only RPCs.
5. **Sync conflict expectations** (Med) — design tests around USN + forced one-way.
6. **iOS scope creep** (Med) — deferred.
7. **Mobile perf** (Low-Med) — keep IRT/RAG off-device.
8. **Math rendering** (Low) — bundled MathJax.

## 12. Open items to refine
- Fold in Claude's agentic-workflow + codebase-traversal research → `docs/BUILD-WORKFLOW.md` (loops, verification gates, skills to install, big-repo navigation).
- Detailed scraper source list + parser strategy (optional Claude research).
- Finalize exam-profile JSON schema + seed topic taxonomy/DAG for calc+LA.
- Confirm conflict-rule choice (latest-timestamp vs conservative-wins).
