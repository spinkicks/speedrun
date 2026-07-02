# Friday — AI + Three Scores + Sync Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` (fresh implementer per task + spec-then-quality review). Steps use checkbox (`- [ ]`) syntax. This plan is GROUNDED (every file:line verified 2026-07-01 via a 6-agent read-only sweep of the actual source). **Do not execute until Cursor approves this plan.**

**Goal:** Ship the highest-weight day — the due-card queue interleave (completes the headline Rust change), a Problem note-type + curated bank + timed mini-mocks, honest Performance & Readiness scores (flat IRT → 200–990 + conformal + give-up), an OFF-by-default external AI generation/verify service, all three scores on both platforms, and a live two-way self-hosted sync demo.

**Architecture:** Engine work (Rust queue ordering + read-time scoring) lands in `repos/anki` on a `feat/friday-*` branch off `main`; the append-only proto additions extend the FROZEN `speedrun.proto`; the AI service is a NEW top-level `services/` app in the umbrella repo (never imported by rslib/rsdroid); the shared Svelte surface renders all three scores on desktop + Android; AAR is re-pinned + rebuilt ONCE at the end.

**Tech stack:** Rust (rslib scheduler + speedrun), Python (pylib wrappers, content toolchain, FastAPI+LangGraph service), Svelte/TS (shared UI), Kotlin (Android shell), genanki (.apkg), self-hosted `anki-sync-server`.

**Rubric at stake (highest-weight day):** Score accuracy & honest uncertainty 20% · Rust change (remaining half) 20% · Study feature (remaining half) 15% · AI checking & safety 15% · Fair re-runnable tests 12% · Two-apps-one-engine + sync 10%.

---

## EXECUTION STATUS (updated 2026-07-02 PM)
- **Phase 0 — DONE** (Gate 0 `e485bbb94`): N+1 batch + Full-mode determinism.
- **Phase 1 — DONE** (Gate 1 `51f1e1718`): read-time due-card interleave (ablation-gated, order-only).
- **Phase 2 — DONE** (Gate 2; FF-merged to anki `main` @ `c302082b4`): append-only proto + honest in-engine Performance/Readiness + Python tests.
- **Phase 3 — DONE** (Gate 3; `feat/friday-problems` @ `191bea607`, pushed): `Speedrun::Problem` note type (`PROBLEM_MODEL_ID=2047815909`) + 64-problem curated bank (twice SymPy-verified, all correct) + timed mini-mock (filtered deck, `reschedule=true` so attempts score) + regenerated apkg. `just check` green mod. complexipy. UI-verify PASS.
- **Phase 4.1 — DONE** (Gate 4.1; `feat/speedrun-ai` @ `f9f8b48`, pushed): SymPy verifier safety gate; twice adversarially reviewed (false-pass found+fixed) → SAFE; 32 tests.
- **Phase 4.2 — DONE** (`feat/speedrun-ai` @ `1f43b8e`, pushed): FastAPI + LangGraph verify/retry/abstain graph, OFF by default, real verify node, stubbed-LLM tests (45 tests).
- **Phase 5 — DONE** (Gate 5; `feat/friday-ui` @ `fcd166704`, pushed): three honest scores on the shared UI — widened TS `ScaffoldCell`, scale-aware range bands + gap-Δ column on Memory, real Perf/Readiness (200–990) on Home, all abstain-honest (no fabricated numbers). svelte-check 0/0, 10 vitest, UI-verify PASS (Memory+Home @ 360px+desktop). Per-topic readiness always abstains (engine truth) → real Readiness is exam-level `overallReadiness` on Home.
- **Track B (branding)** — token-swap + Manrope + SPEED/RUN wordmark DONE on `feat/branding-identity` (`86182e1a9`); awaiting David's screenshot gate.
- **Phase 4 — COMPLETE** (`feat/speedrun-ai` @ `991886c`, pushed; umbrella worktree `..\speedrun-ai-wt`; primary checkout = `main`). 4.1 verifier (`f9f8b48`, twice-reviewed SAFE) + 4.2 FastAPI/LangGraph graph (`1f43b8e`, OFF by default) + 4.3 hybrid RAG BM25+dense→RRF + 56-passage corpus (`ff13d4f`; dense arm = TF-IDF fallback for hermetic tests) + 4.4 §7f gate (`991886c`): wrong-answer **0%** (verify-gate by construction), **leakage-0** scanner wired into graph gate, Recall@10 hybrid ≥ baselines (but ≥5pt margin NOT met — honest: saturation + 20% LA source-coverage gap; corpus NOT gold-fit), useful/bad-teaching pending LLM-judge (cutoffs pre-registered), kill-switch structural proof. 86 tests, ruff clean, hermetic.
- **Combined visual branch — READY:** `feat/friday-combined` @ `fdc634b91` (off `main`, pushed) = Phase-5 scores + Manrope/white branding; merge-safe (engine/content diff vs main empty), UI-verified (16/16 e2e, computed-style branding checks, honest scores). **Awaiting David's ONE `just run`+emulator visual gate**, then Cursor FF-merges it to `main`.
- **REMAINING:** **Phase 6 (AAR re-pin + rebuild ONCE + live desktop↔Android self-hosted sync demo) — BLOCKED** on David's visual gate → Cursor FF-merge of `feat/friday-combined` (frontend) to anki `main` (engine already there) so the AAR bundles the final frontend. Then re-pin rsdroid → final anki `main` SHA, rebuild AAR, assembleDebug, live sync demo (`docs/SYNC-SELFHOST.md`). **Non-blocking:** LS1 (calibration Brier/ECE) / LS2 (faded worked-examples) / LS3 (honesty copy) — do after core, slip to Sunday if tight; LS3 is a natural fold into the next UI touch. **Optional (David/Cursor call):** topic-driven corpus expansion (canonical LA refs) to lift RAG coverage; real mal-rule distractor node (shuffle + 5 choices).

---

## Hard invariants (carry through every task)
- **Mutations** go through `Collection::transact(Op::X)` returning `OpChanges`; **read-only RPCs need no transact**. The due-card interleave is **read-time ordering → NO transact** (only the already-shipped new-card reposition mutates, via `Op::SortCards`).
- **`proto/anki/speedrun.proto` is FROZEN append-only** @ `20dd7a2ea`: new fields/messages get NEW numbers, never renumber/reuse. Verified next-free numbers: `ScoreScaffold`=5, `TopicScaffold`=4, `PerformanceReadinessResponse`=4, `GetPerformanceReadinessRequest`=2, `TopicMastery`=9, `CoverageResponse`=5, `ExamProfileResponse`=3.
- **No fake numbers = auto-fail** (PRD:21). Everything abstains until it cannot be wrong. Mirror the Memory abstain discipline (`abstained = graded_reviews < min_reviews || cards_with_data == 0`, `rslib/src/speedrun/service.rs:160`).
- **AI lives in the umbrella `services/` ONLY** — never rslib/rsdroid (kill-switch confirmed: no network/AI imports in `rslib/src/speedrun/`). App fully scores with AI off from the curated bank.
- **`eval/holdout/` is UNREAD by agents** — the 50 gold pairs are authored by David/Cursor. Never read/echo/generate into it.
- **Config-driven, never hard-code structural numbers** (Decision 12): give-up thresholds (N graded reviews, ≥2 mini-mocks, coverage %, interval cutoff), IRT/equating table all come from the synced exam-profile config.
- **AGPL-3.0-or-later** headers on all `rslib`/`pylib`/`qt`/`ts` files and the new `services/`; **GPL-3.0-or-later** on `anki-android`.
- **`.proto` edits require a full `just check`** (regenerates Rust/Python/TS bindings); `cargo check` alone won't surface generated-type drift. New files in globbed dirs need `out/rust/debug/configure.exe` re-run (see `[[new-files-need-configure-rerun]]`).

---

## Design decisions (Claude's calls — the brief delegates these; confirm at review)

**D1 — Performance model = in-engine deterministic, with IRT difficulty fit OFFLINE.**
The brief (Item 3) says "external service (numpy/scipy IRT) OR a deterministic in-engine approximation — pick ONE with rationale." **Chosen: in-engine deterministic.** The LIVE Performance/Readiness read path computes from synced collection data (FSRS state + problem revlog + exam-profile config), abstaining below thresholds — exactly like `get_topic_mastery`. IRT **item difficulty (`b`)** is fit **offline** (numpy/scipy, one-shot, runnable inside the AI service or a standalone script) and **baked into each `Speedrun::Problem` note** (`IRTParams` field) + the equating table into the exam-profile config. Rationale: (a) **kill-switch safe** — scoring never depends on the AI service being up; (b) **deterministic + reproducible** — required for the ablation harness and the "fair re-runnable tests" rubric; (c) **honest** — no stochastic live fit; abstains when data is thin. A live service-side IRT fit would couple scoring to service uptime and add nondeterminism — worse on two rubric axes.

**D2 — Scores are RECOMPUTED on read, NOT persisted in a separate synced score blob.**
The brief (Item 4) says "scores persist in the synced config blob (both platforms read identical numbers)." **Deviation with rationale (confirm):** because Performance/Readiness are **deterministic functions of already-synced inputs** (revlog, FSRS memory state, exam-profile config, baked IRT `b`), recomputing on each read yields **byte-identical numbers on both platforms without a separate score blob** — and avoids Anki's whole-config-blob sync-overwrite semantics (no per-key merge; `changes.rs:214-218`) and the "few kilobytes" config limit (`collection.py:920-922`). What DOES persist in the synced exam-profile config: the equating table, give-up thresholds, and IRT params (small, static). If Cursor wants literal score persistence for audit, we can add a `speedrun:scores:{exam_id}` JSON blob written via `set_config_json(..., Op::SkipUndo)` — flagged, not default.

**D3 — Extend `GetPerformanceReadiness` (append-only), do NOT split into `GetPerformance`/`GetReadiness`.** The current shape already carries both scores as two `ScoreScaffold`s per `TopicScaffold` in one round-trip with existing TS wiring. Add a `scale` enum on `ScoreScaffold` so 200–990 Readiness isn't misread as the 0–1 band the TS `RangeBand` assumes. Splitting adds proto surface + a second call for no benefit at Friday scope.

**D4 — Mini-mock = Anki filtered deck over `tag:Speedrun::Problem` (no new engine mechanic).** Per-answer wall-clock is ALREADY captured in `revlog.taken_millis` (`rslib/src/revlog/mod.rs:55-57`) with zero engine change. Desktop reuses the Custom-Study/filtered-deck path already wired in `qt/aqt/speedrun.py`. A bespoke timed-session widget is deferred (would need re-implementing on Android).

---

## Prerequisite verification (Phase 0 — do FIRST, before bench/ablation mean anything)

Grounding found **4 of 5 carry-in fixes already merged** (desktop data path, exam-profile bootstrap, `closeWithCallback`, auto-open). **Two are NOT confirmed done** and gate everything measurable:

### Task 0.1 — Batch `get_topic_mastery` (kill the N+1)
**Files:** Modify `repos/anki/rslib/src/speedrun/service.rs:105-178`; Test `repos/anki/rslib/src/speedrun/mod.rs` (tests block).
**Current (grounded):** for each topic it does `search_cards(...)` (`service.rs:133`) then a per-card loop calling `self.storage.get_card(cid)` (`:138`) AND `self.storage.get_revlog_entries_for_card(cid)` (`:149-151`) — N+1 per topic. `FSRS::new(None)` is already built once (`:127`), so only the DB fetches need batching.

- [ ] **Step 1 — failing test:** in `mod.rs` tests, add `test_get_topic_mastery_batched_matches_unbatched`: build a col with ~30 cards across 2 topics + revlog, call `get_topic_mastery`, assert identical output to the pre-batch values (pin expected counts) AND assert (via a query counter or a `#[cfg(test)]` fetch counter) that card+revlog reads are ≤ 2 queries per topic, not N. Run `cargo test -p anki speedrun::test_get_topic_mastery_batched` → expect FAIL.
- [ ] **Step 2 — implement:** replace the per-card loop with a bulk fetch: gather all `CardId`s per topic, then `self.storage.get_all_cards()`-style batched read (grep `storage/card/mod.rs` for an existing "get many cards by id" or add a `get_cards(&[CardId])` helper using a single `SELECT ... WHERE id IN (...)`), and a batched revlog read (`storage/revlog/mod.rs` — add `get_revlog_entries_for_cards(&[CardId])` mirroring `get_revlog_entries_for_card` at `:115-120`). Keep the FSRS math identical.
- [ ] **Step 3 — green:** `cargo test -p anki speedrun` passes; values unchanged.
- [ ] **Step 4 — commit:** `feat(speedrun): batch get_topic_mastery reads (remove N+1 before bench)`.

### Task 0.2 — Full-mode determinism regression test (prereq #5)
**Files:** Test-only `repos/anki/rslib/src/speedrun/mod.rs` (tests block). No product code (interleave is deterministic by construction — `interleave_by_topic` uses stable buckets + fixed topic order + `push_back/pop_front`, `mod.rs:81-97`).

- [ ] **Step 1 — write the contract test:** `test_reorder_new_full_is_deterministic` — build a fixed collection, run `speedrun_reorder_new(deck, weights, ABLATION_MODE_FULL)` twice (fresh transact each), assert the resulting new-card position vector is **byte-identical** across runs; and `test_interleave_by_topic_stable` asserting a fixed input → fixed output vector. Run → expect PASS (documents the contract; guards future regressions).
- [ ] **Step 2 — commit:** `test(speedrun): pin Full-mode reorder determinism contract`.

> Gate 0 → Cursor review: "prereqs green, N+1 gone, determinism pinned." Then proceed.

---

## Phase 1 — Item 1: Due-card queue interleave (completes the Rust change; §4.65-66)

**Approach (grounded):** Anki gathers reviews (limits + burying applied) into `QueueBuilder.review: Vec<DueCard>` **already ordered by SQL** (`review_order_sql`, `storage/card/mod.rs:859`); `QueueBuilder` never re-sorts reviews and **no `sort_review` exists**. We add a **read-time** `QueueBuilder::sort_review()` called from `build()` (`builder/mod.rs:187`, right after `sort_new()`, before `merge_day_learning`), gated by `AblationMode`. Full = weakness×ETS-weight ordering + topic interleave; FeatureOff/Plain = leave the SQL order untouched (no-op). **No transact** (pure in-memory permutation of the already-gathered/limited/buried set).

**Mode + weights source:** `AblationMode` is NOT currently threaded into the builder. Read a synced config key `speedrun:review_interleave_mode` (default = FeatureOff, so untouched-Anki behavior for everyone who hasn't opted in) in `QueueBuilder::new` (`builder/mod.rs:129-184`, mirror the `fsrs` bool read at `:181`); read topic weights from the already-synced exam-profile config (`exam_profile.rs`).

### Task 1.1 — Thread ablation mode + weights into QueueBuilder
**Files:** Modify `repos/anki/rslib/src/scheduler/queue/builder/mod.rs` (`QueueBuilder` struct `:105-114`, `new` `:129-184`, `QueueSortOptions` `:96-103`).
- [ ] Add a `review_interleave: Option<ReviewInterleaveCtx>` field to `QueueBuilder` (topic weights + mode), populated in `new` from `col.get_config_optional("speedrun:review_interleave_mode")` + the exam profile. Default `None` (= off) when unset or mode ∈ {FeatureOff, Plain}.
- [ ] TDD: unit-test that `new` yields `None` when the config key is absent (untouched Anki), `Some(Full)` when set to full.

### Task 1.2 — `sort_review()` weakness×weight + topic interleave (read-time)
**Files:** Create `repos/anki/rslib/src/scheduler/queue/sorting.rs` addition (`sort_review` next to `sort_new` at `:14`); reuse `rslib/src/speedrun/mod.rs` `interleave_by_topic` (`:68`) + `topic_index_for_tags` (`:103`); reuse the FSRS retrievability computation pattern from `service.rs:135-154`.
**Weakness signal:** per review card, compute current FSRS retrievability (lower retrievability = weaker = higher priority) × topic ETS weight = points-at-stake; order topics by descending aggregate points-at-stake; then `interleave_by_topic` so no two adjacent cards share a topic when avoidable. `DueCard` (`builder/mod.rs:33-42`) carries `note_id` but NOT tags/memory_state → `sort_review` must fetch card+note per review card (bulk fetch, reusing the Task 0.1 batched readers to avoid a new N+1 at build time).

- [ ] **Step 1 — failing tests (≥3 Rust, per PRD:69 acceptance):**
  - `test_sort_review_orders_by_points_at_stake`: two topics, one weak/high-weight, assert its cards precede the strong/low-weight topic's.
  - `test_sort_review_interleaves_topics`: assert no two adjacent review cards share a topic when ≥2 topics have cards.
  - `test_sort_review_ablation_modes`: Full permutes; FeatureOff and Plain leave `self.review` in the SQL-gathered order (identical to no-op).
  - `test_sort_review_preserves_set`: output is a permutation of input (same ids, same length — no dropped/added/buried cards, limits intact).
- [ ] **Step 2 — implement `sort_review()`** mirroring `sort_new` (`sorting.rs:14-36`): read `self.review_interleave`; if `None` return; else bulk-fetch card+note for `self.review` ids, compute points-at-stake, bucket by `topic_index_for_tags`, order buckets by aggregate weakness×weight, `interleave_by_topic`, then reorder `self.review` to match. Call it from `build()` at `builder/mod.rs:187` after `self.sort_new()`.
- [ ] **Step 3 — determinism:** ensure a stable tiebreaker (card id) so output is deterministic; add `test_sort_review_deterministic` (two builds → identical order).
- [ ] **Step 4 — Python integration test (1, per acceptance):** `repos/anki/pylib/tests/test_speedrun_interleave.py` — build a col with tagged review-due cards across topics, set the config to Full, call `col.sched` queue build (or the reviewer queue), assert the review order matches the Full contract and that FeatureOff yields Anki default.
- [ ] **Step 5 — safety assertion:** a test proving `sort_review` changes only ORDER, not scheduling state (card `due`/`interval`/`reps` unchanged before/after build).
- [ ] **Step 6 — `just check`** (full build; ignore only the known complexipy `❌` crash). Commit: `feat(scheduler): read-time due-card interleave by weakness×ETS-weight (ablation-gated, no transact)`.

> **Invariant reconciliation to state in the PR:** read-time ordering needs no `transact`; the persisted new-card reposition (`speedrun_reorder_new`, `Op::SortCards`) already satisfies the mutating-op requirement. The frozen `ReorderNewByPointsAtStake` RPC only touches new cards — do not conflate.

> Gate 1 → Cursor review of the engine diff + ablation-mode mapping + test evidence.

---

## Phase 2 — Items 3 & 4: Proto additions + Performance & Readiness (read-time, honest)

### Task 2.1 — Append-only proto additions
**Files:** Modify `repos/anki/proto/anki/speedrun.proto` (append fields only).
- [ ] Add to `ScoreScaffold` (after field 4, `:149`):
  ```proto
  double percentile = 5;         // 0..100; 0 while abstaining
  ScoreScale scale = 6;          // interpret point/lower/upper units
  int64 last_updated = 7;        // TimestampSecs of the inputs used
  ```
  and a new enum (append-only, new type):
  ```proto
  enum ScoreScale {
    SCORE_SCALE_UNIT = 0;        // 0..1 (Performance, recall)
    SCORE_SCALE_GRE_200_990 = 1; // Readiness scaled score
  }
  ```
- [ ] Add to `TopicScaffold` (after field 3, `:142`): `double gap_delta = 4;  // declarative_recall - problem_accuracy (§7d gap meter)`.
- [ ] Add to `PerformanceReadinessResponse` (after field 3, `:136`): `string abstain_reason = 4;` and `repeated UnlockRequirement unlock_requirements = 5;` with a new message `UnlockRequirement { string kind = 1; double have = 2; double need = 3; string human = 4; }` (drives "answer 12 more calculus items").
- [ ] Keep `scaffolding` bool; flip it to `false` per-topic once a real score is emitted. `GetPerformanceReadiness` rpc + `BackendSpeedrunService {}` unchanged (auto-delegates).
- [ ] `just check` to regenerate Rust/Python/TS bindings (do NOT hand-edit generated files). Commit: `feat(proto): append-only Performance/Readiness fields (percentile, scale, gap_delta, unlock) — proto stays frozen-compatible`.

### Task 2.2 — Performance score in-engine (P(correct on novel problem); §5.75)
**Files:** Modify `repos/anki/rslib/src/speedrun/service.rs:210-236` (`get_performance_readiness`); add helpers in `rslib/src/speedrun/mod.rs` (after the const block `:26-31`); add `PERF_MIN_PROBLEM_ATTEMPTS` config-resolved threshold.
**Model (D1):** per topic, Performance = a deterministic combine of (a) FSRS topic recall (reuse `get_topic_mastery` internals — batched), (b) observed problem accuracy on that topic from `Speedrun::Problem` cards' revlog (Wilson interval), (c) coverage. Abstain (`abstained=true`, `scale=UNIT`) below the problem-attempts threshold. Optional refinement: weight by baked IRT `b` if present in Problem notes (else skip — honest).
- [ ] **Step 1 — failing Rust tests:** `test_performance_abstains_below_threshold` (few problem attempts → abstained), `test_performance_scores_with_data` (enough correct/incorrect problem revlog → point in (0,1) with Wilson lower/upper), `test_performance_gap_delta` (gap_delta = declarative recall − problem accuracy).
- [ ] **Step 2 — implement:** in `get_performance_readiness`, for each topic compute FSRS recall (batched), problem accuracy from revlog filtered by `has_rating_and_affects_scheduling()` on `Speedrun::Problem` cards, Wilson band, `gap_delta`; set `scale=UNIT`, `abstained` per threshold, `last_updated`. Read-only (no transact).
- [ ] **Step 3 — green + `just check`.** Commit: `feat(speedrun): real in-engine Performance score + §7d gap meter (abstains honestly)`.

### Task 2.3 — Readiness score: flat IRT → 200–990 + conformal + give-up (§5.78)
**Files:** `rslib/src/speedrun/service.rs` (same RPC), `rslib/src/speedrun/mod.rs` (equating + conformal helpers + constants), exam-profile config (equating table + thresholds — read via `exam_profile.rs` pattern).
**Model (PRD:76):** flat — θ estimated from problem responses; point estimate = **calculus-weighted topic sum** (NOT a min()-gate); raw→scaled via the exam-profile **equating table** → 200–990 + percentile; **range via conformal/CQR**, widening under sparse data (`scale=GRE_200_990`).
**Give-up rule (config-driven, PRD:78):** abstain with `abstain_reason` + `unlock_requirements` until **≥2 timed mini-mocks AND coverage ≥ threshold AND interval width < cutoff**. Thresholds come from the exam-profile config (don't hard-code). "Timed mini-mock" count = distinct mini-mock sessions detected from problem revlog (see Phase 3).
- [ ] **Step 1 — failing tests:** `test_readiness_gives_up_without_two_mocks` (unlock_requirements populated, abstained), `test_readiness_scaled_200_990` (θ → equating table → in [200,990] + percentile), `test_readiness_interval_widens_sparse` (fewer items → wider conformal band), `test_readiness_is_weighted_sum_not_min` (a single weak prereq does NOT zero the score).
- [ ] **Step 2 — implement** the equating lookup (from config table) + conformal interval + give-up gate; emit `UnlockRequirement`s ("answer N more {topic} items", "complete {2−k} more timed mini-mocks"). Read-only.
- [ ] **Step 3 — green + `just check`.** Commit: `feat(speedrun): flat-IRT Readiness → 200–990 + conformal range + config-driven give-up`.

### Task 2.4 — Python wrappers + webview exposure
**Files:** `repos/anki/pylib/anki/speedrun.py` (already has `performance_readiness` wrapper `:56-58` — no change needed since fields are additive); confirm `qt/aqt/mediasrv.py:770-774` `exposed_backend_list` still lists `get_performance_readiness` (it does).
- [ ] Verify no new RPC → no new exposure needed. Add a `pylib/tests/test_speedrun_scores.py` integration test hitting the real RPC on a seeded col (abstain + scored paths). Commit.

> Gate 2 → Cursor review: proto diff (append-only correctness), scoring math, abstain/give-up honesty, D1/D2 confirmation.

---

## Phase 3 — Item 2: Problem note type + curated bank + timed mini-mock

### Task 3.1 — `Speedrun::Problem` genanki model + loader
**Files:** Modify `repos/anki/speedrun/seed/build_seed_deck.py` (add second model at `:25-44`, loader parallel to `:52-57`, build loop `:60-76`); new `repos/anki/speedrun/seed/problems_calc.yaml` + `problems_linear_algebra.yaml`; test `repos/anki/speedrun/tests/test_seed_deck.py`.
**Model:** single MCQ model (GRE Math is all MCQ), **NEW fixed `PROBLEM_MODEL_ID`** — *David must pick this permanent id* (never reuse `1607392319`). Fields: `Stem, Choices, NumericAnswer, CorrectAnswer, WorkedSolution, TopicID, TechniqueTag, Source, IRTParams` (IRTParams empty until the offline fit). `guid_for(stem, topic, "problem")` (distinct salt). `tags=[topic, "Speedrun::Problem"]`. Put problems in a distinct subdeck `Speedrun::GRE Math::Problems` so mini-mock filtered searches target only problems.
- [ ] **Step 1 — failing seed test:** mirror `test_seed_deck.py:13-31` for problems: every problem note has non-empty Stem/CorrectAnswer/WorkedSolution/Source, `TechniqueTag` present, topic ∈ scored leaves (`gre_math.json`). Run via `bash speedrun/uvw.sh pytest tests/ -v` → FAIL.
- [ ] **Step 2 — implement** the model + `load_problems()` + build loop; author a minimal starter set (David curates the real floor — see Open Questions). Validate topics against `_leaf_topic_ids()` (`build_seed_deck.py:47-49`).
- [ ] **Step 3 — green;** regenerate `out/gre_math_seed.apkg` (whitelisted in `.gitignore`). Commit (content toolchain): `feat(seed): Speedrun::Problem MCQ note type + curated problem bank + validation`.

### Task 3.2 — Timed mini-mock (desktop; D4)
**Files:** Modify `repos/anki/qt/aqt/speedrun.py` (add a mini-mock bridge command + logic near `_custom_study` `:108-121`); `qt/aqt/speedrun_logic.py` (add `decide_mini_mock` analogue to `decide_start_run:38`); Svelte `ActionBar`/Home button (fire ONE bridge cmd — see `[[desktop-aliases-pycmd-bridgecommand]]`).
- [ ] Build a filtered deck via `col.sched.add_or_update_filtered_deck(FilteredDeckForUpdate)` with search `deck:"Speedrun::GRE Math::Problems" -is:suspended`, `card_limit=N` (N from config/Decision 13, default 10), then launch the reviewer. Per-answer `taken_millis` lands in revlog automatically (no engine change).
- [ ] Detect a "mini-mock session" for the give-up rule: a helper reads problem revlog grouped by session (e.g. contiguous problem answers within a time window) — count distinct sessions for the ≥2 gate. TDD in `pylib/tests`.
- [ ] Android scope this cycle: import the Problem bank + native reviewer over the Problems subdeck (bespoke Android mini-mock UI deferred). Note in plan.
- [ ] Commit: `feat(home/desktop): timed mini-mock over Speedrun::Problem filtered deck`.

> Gate 3 → Cursor review; David confirms problem-bank floor + `PROBLEM_MODEL_ID`.

---

## Phase 4 — Item 5: External AI generation + verify service (OFF by default)

**Layout (NEW top-level, umbrella):** `services/speedrun-ai/` (FastAPI + LangGraph app, its own venv — NOT under `repos/anki`, which would trip `check:minilints`). `eval/holdout/` (NEW top-level; **CURSOR authors the 50 gold pairs (Friday permits AI) under a verification protocol — SymPy answer-check + source-grounding + leakage-scan + David spot-check; Claude's implementer agents NEVER read/write it** — independence of the gate is preserved because the generator + its build agents never see the held-out set). Install `langchain-ai/langchain-skills` (`langgraph-fundamentals`, `langchain-rag`, `langgraph-human-in-the-loop`, `deep-agents-core`) at the start of this phase.

**Pipeline (Decision 11):** LLM proposes symbolic schema → **SymPy instantiates + verifies** (symbolic `simplify(diff)==0` + numeric random-point check `eps=1e-9`) → **RAG source-grounding** (BM25 + dense bi-encoder via FAISS → RRF `k=60` → cross-encoder rerank) → **mal-rule distractors** (Brown & Burton) → **gold-set gate** → emit verified `Speedrun::Problem` notes as a genanki `.apkg` for manual import (same emit mechanism as Task 3.1).

**§7f pre-registered cutoffs (VERBATIM):** wrong-answer ≤ 2% (target 0; any wrong post-gate ⇒ **halt & fix the verifier**), useful ≥ 80%, bad-teaching ≤ 15%, **leakage 0** (MinHash/LSH + embedding sim ≥ 0.85 or 13-gram match ⇒ auto-fail that card). Full hybrid RAG must beat the better baseline by **≥5 pts Recall@10** on the 50 gold pairs.

### Task 4.1 — SymPy verifier FIRST (it is the gate)
**Files:** `services/speedrun-ai/verify/sympy_verifier.py` + tests.
- [ ] TDD: given a symbolic schema + candidate answer, assert `verify()` returns True only when symbolic AND numeric checks pass; malformed/ambiguous/ill-posed → False. This is the hard gate that makes AI-off safe. Build + test this before any LLM call.

### Task 4.2 — FastAPI app + LangGraph verify/retry/abstain graph (OFF by default)
**Files:** `services/speedrun-ai/app.py`, `services/speedrun-ai/graph.py`, `services/speedrun-ai/README.md`.
- [ ] App is disabled unless an explicit env flag + API key are present (OFF by default). LangGraph nodes: propose → SymPy-verify → RAG-ground → distractors → gold-gate → emit/abstain, with retry/abstain edges. TDD the graph transitions with a stubbed LLM.

### Task 4.3 — RAG grounding (hybrid BM25+dense→RRF→rerank)
**Files:** `services/speedrun-ai/rag/`.
- [ ] Build the hybrid retriever; a baseline-beat test on the gold set (metrics computed by the harness in 4.4). Every emitted card cites a named source; drop-if-unverifiable (mirror `scraper/scrape_openstax.py` discipline).

### Task 4.4 — Gold-set gate harness + §7f report + kill-switch proof
**Files:** `services/speedrun-ai/eval/gate.py` (reads `eval/holdout/` ONLY at runtime — Cursor authors + owns the pairs; Claude's implementer agents must NOT read/embed them during dev), `services/speedrun-ai/eval/README.md`. **Gold-set schema (Cursor-owned, stable):** JSONL, one object per pair — `{id, question, topic_id, choices[], correct_answer, worked_solution, source_citation, difficulty_hint}` — align the harness reader to this so Cursor can author in parallel.
- [ ] Harness computes the three §7f rates + leakage scan + Recall@10 baseline comparison and **fails the build if any cutoff is violated**. Pre-register the cutoffs in the README before looking at results.
- [ ] **Kill-switch proof (record for the demo):** with the service stopped, the desktop + Android apps still compute Memory/Performance/Readiness from the curated bank (Phase 2/3). Capture this.
- [ ] Commit(s) on the umbrella repo (Cursor's lane — leave staged/PR per channel protocol): `feat(services): OFF-by-default AI problem generator + SymPy gate + RAG + §7f gold-set harness`.

> Gate 4 → Cursor review; David supplies LLM/API key + authors the 50 gold pairs. Parallel-safe with Phases 1–3 (umbrella repo, no engine coupling).

---

## Phase 5 — Item 6a: Three scores on the shared UI (both platforms)

**Grounding:** the TS boundary currently DROPS the score ranges — `ScaffoldCell` (`ts/lib/speedrun/data.ts:87-89`) stores only `{ abstained }` even though the proto/RPC already deliver `point/lower/upper`. Memory renders real ranges; Performance/Readiness render `"—"`.

### Task 5.1 — Widen the TS scaffold to carry ranges + scale
**Files:** `repos/anki/ts/lib/speedrun/data.ts` (`ScaffoldCell` `:87-89`, `loadScaffoldMap` `:95-107`).
- [ ] Extend `ScaffoldCell` to `{ abstained, point, lower, upper, percentile, scale, gapDelta }`; populate from `t.performance`/`t.readiness` in `loadScaffoldMap` (defensive optional-chaining with abstain default). Vitest for the mapping. (Proto already has the fields after Task 2.1 — regenerated types.)

### Task 5.2 — Memory table renders Performance/Readiness as range bands
**Files:** `repos/anki/ts/routes/speedrun-memory/TopicRow.svelte` (cells `:33-34`, `:41-42`), reuse `RangeBand.svelte`.
- [ ] Replace the `"—"` cells with the abstain-branch pattern already used for the recall column (`TopicRow.svelte:24-39`): if abstained → lock/unlock text (from `unlock_requirements`), else `<RangeBand>` — **scale-aware** (200–990 rendered on its own axis, not the 0–1 track). Add the §7d gap-delta column.
- [ ] e2e (Playwright, headless): assert Performance/Readiness cells render a band when data present and abstain text when not, at 360px + desktop.

### Task 5.3 — Home surface: Performance stat + un-stub Readiness
**Files:** `repos/anki/ts/routes/speedrun-home/StatRow.svelte` (`:39-47` hardcoded Readiness stub, no Performance stat), `speedrun-home/data.ts` (`loadHome` `:42-45` add `loadScaffoldMap`).
- [ ] Wire `loadHome` to fetch scaffold; add a Performance headline stat + feed real Readiness (200–990 + percentile + range); keep abstain honesty copy.
- [ ] Commit: `feat(ui): render Memory/Performance/Readiness with range+abstain on Home+Memory (both platforms)`.

**UI-verification subagent (MANDATORY, every UI-affecting task in this phase):** before marking any UI task done, dispatch a fast dedicated subagent that renders the affected shared Svelte page headlessly (Playwright / `just test-e2e`) at **~360px AND desktop**, asserts zero console errors + zero failed `/_anki/*` POSTs + no horizontal overflow, **captures a screenshot and visually inspects it**, and reports pass/fail + screenshot path. Independent automated render proof (keeps main context lean) — must pass BEFORE David's human `just run`/emulator gate; does NOT replace it (a subagent can't observe the native Qt/Android window).

> Gate 5 → Cursor review + David desktop `just run` visual gate.

---

## Phase 6 — Item 6b: AAR re-pin/rebuild + live sync demo (single end-of-cycle)

### Task 6.1 — Re-pin rsdroid + rebuild AAR ONCE
**Files:** `repos/Anki-Android-Backend` (rsdroid `anki` submodule pin), rebuild.
- [ ] After all engine changes merge to `spinkicks/anki main`, bump the rsdroid `anki` submodule to that final SHA, rebuild: `cargo run -p build_rust` (a.k.a. `build.bat`) → `rsdroid/build/outputs/aar/rsdroid-release.aar`. `anki-android` consumes it via `local_backend=true`. `:AnkiDroid:assembleDebug` green.
- [ ] Fix the stale SHA reference in `docs/RUN-MVP.md:57` (`a0ead51c9`) while here.
- [ ] Commit (anki-android + Anki-Android-Backend feat branches).

### Task 6.2 — Live two-way self-hosted sync demo
**Files:** follow `docs/SYNC-SELFHOST.md` verbatim (no new server code — Anki's built-in `anki-sync-server`).
- [ ] Start: `SYNC_USER1="test:test" SYNC_PORT=8088 SYNC_BASE="$PWD/out/syncserver-data" cargo run --release -p anki-sync-server`; healthcheck exit 0.
- [ ] Desktop → `http://127.0.0.1:8088/`; Android emulator → `http://10.0.2.2:8088/`. Study on one, sync, sync the other, assert identical Memory/Performance/Readiness numbers (D2: recomputed-identical because inputs synced). Offline-reconnect run. Capture for the recording.
- [ ] The `§7b` conflict test (`cargo test -p anki sync::speedrun_two_way`) already proves append-only two-way + conflict behavior — cite it; the live launch is the demo layer (honest caveat per `SYNC-SELFHOST.md:70-75`: union holds because real reviews have distinct ms ids).

> Gate 6 → David records the clean two-way sync + three-scores-on-phone demo.

---

## Sequencing (one shared checkout; mirror wed-plus phase-gates)
`Phase 0 (prereqs) → Phase 1 (engine interleave) → Phase 2 (proto + scores)` on `feat/friday-engine` off `main` → **merge/freeze** → `Phase 4 (AI service, PARALLEL-SAFE in umbrella)` can start anytime after Phase 3's note type exists → `Phase 3 (problem layer)` → `Phase 5 (UI)` → `Phase 6 (AAR re-pin + rebuild ONCE + sync demo)`. Cursor FF-merges at each gate; `main` untouched until review.

## Test inventory (rubric: fair re-runnable tests 12%)
- Item 1: ≥3 Rust (points-at-stake order, topic interleave, ablation-mode diff, set-preservation, determinism) + 1 Python integration + safety (order-only) test.
- Items 3/4: Rust abstain/score/gap/give-up/scale/weighted-sum-not-min tests + Python RPC integration.
- Item 2: seed validation tests + mini-mock session-detection test.
- Item 5: SymPy verifier tests, LangGraph transition tests, RAG baseline-beat (≥5 pts Recall@10), §7f gate (halts on any breach), leakage-0.
- Ablation harness (§8): 3-build (Full / FeatureOff / Plain) comparison is now meaningful because Item 1 respects `AblationMode` and determinism is pinned (Task 0.2).

## Open questions for David (block specific tasks — answer at review)
1. **Problem-bank floor per topic** (gates Item 2/3 honesty; abstention covers the rest). — *blocks Task 3.1 real content.*
2. **Which LLM/API + key** for the generation service (needed Friday AM). — *blocks Task 4.2.*
3. **Mini-mock length** (recommend 10 problems @ 2.5 min/q per Decision 13). — *blocks Task 3.2 config default.*
4. **Gold-set authorship → RESOLVED: Cursor authors all 50** (David's call — Friday permits AI) in `eval/holdout/` under the verification protocol (SymPy answer-check + source-grounding + leakage-scan + David spot-check); Claude's implementer agents must NOT read/write it. — *blocks Task 4.4 gate run; Cursor delivers before it.*
5. **`PROBLEM_MODEL_ID`** — permanent genanki model id for `Speedrun::Problem` (David picks; never reuse `1607392319`). — *blocks Task 3.1.*
6. **Confirm D1** (in-engine deterministic Performance) and **D2** (recompute-on-read, no separate score blob) and **D3** (extend not split) and **D4** (filtered-deck mini-mock).

## Self-review (against the brief)
- Every brief Item (1–6) + both unverified prereqs (#4 N+1, #5 determinism) map to a task. ✅
- Proto touches are append-only with verified next-free numbers; `GetPerformanceReadiness` stays compatible. ✅
- Read-time interleave = no transact; invariant reconciliation stated. ✅
- AI isolated to `services/`; kill-switch proof is an explicit task; `eval/holdout/` untouched by agents. ✅
- No fake numbers: every score abstains below config-driven thresholds. ✅
- The two delegated decisions (Performance model; persistence) are made with rationale and flagged for confirmation. ✅
