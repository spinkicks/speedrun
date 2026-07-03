# What We Built — honest narrative of Speedrun's changes on top of Anki

> **Purpose:** a talking-script / explainer of everything we changed, why, and its HONEST status (real now / scaffolding / pending). Companion to `docs/DEMO-VIDEO-SCRIPT.md` (the click-by-click demo). **This is the honesty project — every claim here is marked real / scaffolding / pending. Do not present scaffolding or pending items as done, and never show a fabricated number on camera.** Last updated 2026-07-03 (Fri).

## One-paragraph honest positioning
Speedrun is built **on** Anki, not instead of it. Anki's proven memory engine (FSRS spaced repetition) stays the chassis; we did **not** rewrite the scheduler or invent a memory model. What we added on top and have now **shipped**: an **honest measurement layer** with **three real scores** — Memory (recall with confidence intervals + abstention), Performance (P(correct) on real problems + a memory→performance gap meter), and Readiness (flat-IRT → GRE-scaled 200–990 with a conformal range and a give-up rule) — every one of which **abstains rather than guess** below data thresholds; an evidence-based **scheduling** feature (weakness×exam-weight **due-card interleave** at read-time **and** points-at-stake **new-card** reordering); exam-specific **content** (topic DAG + seed deck + a curated **Problem MCQ bank** + **timed mini-mocks**); **learning-science** features (pre-answer **calibration** self-bets, **worked-examples-first** with faded steps, and honesty-guardrail copy); an **OFF-by-default external AI service** that proposes → SymPy-verifies → RAG-grounds → gold-gates problems (the app works fully with AI off); a **branded, de-Anki-fied cross-platform shell** (Manrope wordmark, near-white accent, mobile-first dark surface, "Speedrun Home" on desktop + Android from one engine); **self-hosted sync**; and a **network-independent installer**. What is **still pending** (human/Sunday): the emulator visual gate, a live desktop↔Android sync recording + demo video, the Sunday eval RUNS (calibration reliability, Brier/log-loss, held-out performance accuracy, robustness/bench), a signed APK, and a handful of in-flight bug fixes — see § Pending.

---

## 1. The engine change (Rust, `rslib`) — the required "real change to Anki's backend"
All additive; lives in a self-contained `rslib/src/speedrun/` module + one **frozen, append-only** proto service (`proto/anki/speedrun.proto`) plus a read-time addition in the scheduler queue builder. Tiny, surgical upstream contact (see `docs/artifacts/upstream-files-touched.md`).

**6 RPCs on `SpeedrunService`:**
| RPC | Type | What it does | Honest status |
|---|---|---|---|
| `GetCoverage` | read-only | How many required exam topics your deck actually covers | ✅ real |
| `GetTopicMastery` | read-only | **Memory** score: per-topic recall from FSRS retrievability → **Wilson 95% interval** + **abstain** below min-reviews / min-cards | ✅ real |
| `GetExamProfile` | read-only | The exam's topic DAG + ETS weights + equating/thresholds (from synced config; baked-in default) | ✅ real |
| **`ReorderNewByPointsAtStake`** | **mutating** | Repositions **new cards** by topic weight + round-robin **interleave**; via `transact(Op::SortCards)`, undo-safe; ablation modes Full/FeatureOff/Plain | ✅ real (**new-card order**) |
| `GetPerformanceReadiness` | read-only | **Performance** (P(correct) on `Speedrun::Problem` MCQs, mean-CI band, memory→performance gap Δ) **and** **Readiness** (flat IRT → scaled 200–990 + conformal range + give-up rule). Abstains below thresholds; emits unlock requirements | ✅ real (abstains honestly) |
| `GetCalibration` (LS1) | read-only | Calibration report from logged pre-answer self-bets → **Brier / ECE**; abstains below the attempt threshold | ✅ real (abstains honestly) |

**Due-card queue interleave (not an RPC):** a **read-time** ordering pass in the scheduler's `QueueBuilder` orders due reviews by **weakness × ETS-weight** (points-at-stake) and interleaves topics, gated by `AblationMode` (Full permutes; FeatureOff/Plain = untouched Anki). **No `transact`** — it's a pure in-memory permutation of the already-gathered/limited/buried set; scheduling state is unchanged (proven by an order-only safety test). This completes the headline scheduling change; the persisted **new-card** reposition (`Op::SortCards`) satisfies the mutating-op requirement. ✅ real.

**Why Rust (not a Python add-on):** the change must run identically on desktop *and* Android from one engine; only `rslib` is shared across both bridges. Mutations honor Anki's invariant (`transact`/`OpChanges`, undo, `pragma integrity_check ok`). Proto is frozen + append-only (new field numbers only). Scores are **recomputed on read** from already-synced inputs (revlog + FSRS state + exam-profile config + baked IRT `b`), so both platforms produce byte-identical numbers with no separate synced score blob.

**Tests:** **66+ passing Rust speedrun tests** (unit + integration) + Python integration tests + a §7b sync test. Undo + integrity proven for the mutating op; determinism pinned for Full-mode reorder + interleave.

## 2. Learning science — what's REAL vs Anki baseline
- **Memory science = Anki's FSRS** (we did **not** change it; do not claim we did). ✅ (Anki's)
- **Our additions Anki lacks — now REAL:**
  - **Memory** topic score: FSRS retrievability → Wilson 95% interval + abstention. ✅ real (our strongest differentiator).
  - **Performance** score: P(correct) on novel `Speedrun::Problem` MCQs (mean-CI band) + a **memory→performance gap meter (Δ)** = declarative recall − problem accuracy. Abstains below the problem-attempts threshold. ✅ real.
  - **Readiness** score: flat IRT (calculus-weighted topic sum, **not** a min()-gate) → exam **equating table** → **200–990 + percentile**, with a **conformal range** that widens under sparse data, and a **give-up rule** that abstains (with unlock requirements) until **≥2 timed mini-mocks** + coverage + interval-width thresholds are met. **Exam-level Readiness shows on Home; per-topic Readiness abstains by design** (engine truth). ✅ real (abstains honestly).
  - **Calibration (LS1):** pre-answer confidence self-bet → **Brier / ECE**. ✅ real (see §7).
  - **Weakness-weighted review-queue interleave** + **new-card** points-at-stake reorder. ✅ real (see §1).
- **Config-driven, not hard-coded:** give-up thresholds, IRT/equating table, and mode all come from the synced exam-profile config (Decision 12). IRT item difficulty (`b`) is fit **offline** and baked into each Problem note — scoring never depends on the AI service being up (kill-switch safe, deterministic, reproducible).

## 3. Content pipeline (deterministic, AI is OFF by default)
- **Exam-profile DAG** (`speedrun/exam_profiles/gre_math.json`): leaf topics (calc + linear algebra), ETS weights (sum 1.0), acyclic prereq graph, plus equating table + thresholds. ✅ real.
- **35-card seed deck** (`gre_math_seed.apkg`): hand-authored calc+LA cards, hierarchical `calc::…`/`linear_algebra::…` tags, a Source on every card. Tag↔topic alignment audit-verified. ✅ real.
- **`Speedrun::Problem` MCQ note type** (`PROBLEM_MODEL_ID = 2047815909`, permanent) + a **64-problem curated bank**, every problem **double-SymPy-verified** (symbolic + numeric). Problems live in a distinct `Speedrun::GRE Math::Problems` subdeck so mini-mock filters target only problems. ✅ real.
- **Deterministic open-licensed scraper** (FLEX, keyword-rule tagging, no AI). ✅ real.

## 4. Problem bank + timed mini-mock (the "novel problem" study feature)
- **Problem bank:** the 64-problem `Speedrun::Problem` MCQ bank above — the substrate for the Performance/Readiness scores and the mini-mock. ✅ real.
- **Timed mini-mock:** an Anki **filtered deck** over `deck:"Speedrun::GRE Math::Problems"` (default **10 problems @ 2.5 min/q**, config-driven), launched from Home; **`reschedule=true` so attempts actually score**. Per-answer wall-clock lands in `revlog.taken_millis` with **zero engine change**. Distinct mini-mock **sessions** are detected from the problem revlog to drive the Readiness ≥2-mock give-up gate. ✅ real on desktop; Android imports the bank + reviews the Problems subdeck (bespoke Android mini-mock UI deferred).

## 5. Learning-science features (LS1 / LS2 / LS3)
- **LS1 — Calibration (pre-answer self-bet).** Before answering, the learner places a confidence self-bet (**Sure / Think / Guess**); outcomes → **Brier score + ECE** via `GetCalibration`. Bets are captured on desktop via a webview hook and stored in a synced config blob (`speedrun:calibration_log`). **Abstains below ~20 attempts**, and the UI frames it as **self-rated** confidence (not a model prediction). ✅ real (calibration RUNS/reliability chart are Sunday — see § Pending).
- **LS2 — Worked-examples-first + faded steps.** New material leads with a fully worked example, then **fades step reveal** (LaTeX-safe) so the learner completes progressively more of each step. ✅ real.
- **LS3 — Honesty-guardrail copy.** In-product framing on diminishing returns, survivorship bias, desirable difficulty, abstention, and a self-reported caveat — **all gated to render only on real data** (never over real-looking placeholders). ✅ real.

## 6. Quality: the §8 ablation harness + hardening passes
- **Ablation harness (§8):** `AblationMode` **Full / FeatureOff / Plain**, with **pre-registered** metrics.
  - **M1 — same-topic adjacency:** Full **0.00** vs **0.79** for both baselines — **decisive** (the interleave does exactly what it claims).
  - **M2 — pre-registered secondary:** the metric was **mis-specified**; we report that **honestly** rather than spin it.
  - **M3 — exploratory.**
  - Results doc: `docs/ablation-s8-results.md`. ✅ real (harness + M1 result).
- **Hardening:** P0 honesty fixes (no fake numbers, Memory declared-only, coverage=problems, mean-CI band, mini-mock reuse), P1 AI-safety fixes, P2 mini-mock hardening, P3 nits — all merged. ✅ real.

## 7. The external AI service (OFF by default) — `services/speedrun-ai/`
- A **separate FastAPI + LangGraph** app in the umbrella repo's `services/speedrun-ai/` — **never** imported into `rslib`/`rsdroid` (kill-switch confirmed: no network/AI imports in the engine). **The whole app scores and studies with AI OFF**, from the curated bank.
- **Disabled unless** `SPEEDRUN_AI_ENABLED=1` **and** `OPENAI_API_KEY` are set. ✅ OFF by default.
- **Pipeline:** LLM **proposes** a symbolic schema → **SymPy verifies** (symbolic `simplify(diff)==0` + numeric random-point check) → **hybrid RAG grounds** it (BM25 + dense → RRF over an **82-passage corpus**, every card cites a named source) → **mal-rule distractors** → **gold-set gate** → **emit** a verified `Speedrun::Problem` `.apkg` **or abstain**. ✅ real.
- **Safety evidence (§7f, pre-registered):** wrong-answer **0%** (verify-gate by construction; any post-gate wrong ⇒ halt & fix the verifier), **leakage 0** scanner wired into the gate, kill-switch structural proof. RAG beats baselines on Recall@10 but did **not** clear the pre-registered **≥5-pt** margin — reported honestly (saturation + a linear-algebra source-coverage gap; the corpus is not gold-fit). LLM-judge useful/bad-teaching rates are pending (cutoffs pre-registered).
- **Gold set:** `eval/holdout/gre_math_gold.jsonl` — **50 problems, triple-verified, leakage-cleared**. Implementer agents must **NOT** read the holdout; the gate reads it only at runtime.

## 8. The product shell — "our own app on Anki's engine" (UI + branding)
- **De-Anki-fied identity:** a **Manrope ExtraBold** wordmark, a **near-white `#F4F7FA`** accent (replaced the amber), "Speedrun" on the desktop title/icon + Android launcher, trimmed Anki chrome. Pure presentation, zero engine. ✅ real.
- **Speedrun Home ("The Run")** — a branded landing that **auto-opens on launch** (config-gated), rendering your run with honest 95% **error-brackets** and abstention, the three scores, and START RUN / mini-mock actions. One shared SvelteKit page renders on **both** desktop (Qt dialog) and Android (PageFragment) from the same code + engine. ✅ real.
- **Memory dashboard** — shared Svelte page: coverage header, per-topic recall + range band + abstain, scale-aware Performance/Readiness bands, the §7d **gap-Δ column**, grouped by root, sort toggle. ✅ real, dark-themed to match "The Run".
- **Mobile-first dark shell:** pages reflow phone-first (~360px stacked) → desktop columns (≥768px); Android dark shell + START RUN (real study + honest import/caught-up/Custom-Study states); desktop reviewer restyle. ✅ real (desktop David-verified; Android emulator visual gate pending — see § Pending).

## 9. Two apps, one engine + sync + installer
- **One engine, two apps:** the same forked `rslib` compiles to desktop (PyO3) and Android (JNI AAR via cargo-ndk); proven by an instrumentation test asserting identical backend version and by the same UI rendering on both. **Phase 6:** rsdroid re-pinned to the P0-honesty-complete engine `8ca3112d7` (pre-LS1), **AAR rebuilt**, and the **Android APK compiled with the P0 Speedrun UI bundled in the AAR (verified)**. ✅ real. **Note:** the shipped AAR pin predates the LS1/LS2/LS3/P2 merge that landed on anki `main` (`c54afe2b1`); a fresh AAR rebuild on current `main` is pending and must include the in-flight Android `getCalibration` exposure fix (`fix/p0-android-getcalibration`) or Android Home breaks — see §11 Pending.
- **Self-hosted sync:** `anki-sync-server` (in-fork) + a §7b two-way conflict test (offline reviews all land, latest-mtime-wins, documented honest caveat). ✅ test real; a **live desktop↔phone sync demo recording is pending** (§ Pending).
- **Network-independent installer:** vendored the Briefcase Windows/mac templates in-tree so a clean machine builds the desktop installer with no submodule fetch. ✅ real (clean-install recorded — see `docs/PROOF-INDEX.md`).

## 10. What to say / not say (honesty guardrails for any demo or writeup)
Reviewers **can now be shown the real work**: the **three scores** (Memory, Performance, Readiness) **when they are not abstaining**, the **calibration self-bet** flow (framed as self-rated), the **Problem MCQs**, the **timed mini-mock**, and the **AI service — but only when you explicitly enable it** to demo the AI path.

- ✅ SAY: "honest topic **Memory** with confidence intervals + abstention"; "**Performance** = P(correct) on real problems, with a memory→performance gap meter"; "**Readiness** = flat-IRT → 200–990 with a conformal range and a give-up rule (needs ≥2 timed mini-mocks)"; "**calibration** self-bets → Brier/ECE (self-rated)"; "weakness×weight **due-card interleave** + points-at-stake **new-card** order"; "one engine → two apps, one shared UI"; "self-hosted sync with a tested conflict rule"; "clean-machine installer"; "an **OFF-by-default** AI generator that SymPy-verifies + gold-gates every problem (the app works with AI off)".
- ❌ DON'T SAY / DON'T DO: never show a **fabricated number** — every score **abstains below its thresholds**, and that abstention **is** the honest story (don't fake a Readiness/Performance/calibration number to fill a screen). Never claim **"we improved / changed FSRS"** (we did not). Don't call calibration a model prediction (it's self-rated). Don't present the AI as always-on or as "the app's brain" — it's an optional, verified content generator. Don't claim the §5-pt RAG margin was met (it wasn't). Don't present anything in § Pending as done.

## 11. Pending (human / Sunday — do NOT present as done)
- **Visual/demo gates:** Android **emulator visual gate**; **live desktop↔Android self-hosted sync** recording; the **demo video**.
- **Sunday eval RUNS:** calibration **reliability chart** + **Brier/log-loss** on held-out; **performance accuracy** on held-out; the **score-mapping writeup**; **robustness** (crash×20, offline, `make bench` p50/p95 on a 50k deck); **signed APK**; final **BrainLift** pass.
- **In-flight bug fixes (on branches):** 7 newly-found bugs — **2 P0 demo-visible** (single-card 0%–100% band edge case; Android `getCalibration` exposure), **2 P1** (AI-safety), **2 P2** (calibration-capture).

---
*See also: `docs/PROOF-INDEX.md` (proof artifacts), `docs/PROGRESS.md` (done/left), `docs/DECISIONS.md` (why), `docs/ablation-s8-results.md` (§8 results), `docs/plans/2026-07-03-friday-ai-scores-sync.md` (Friday plan), `brainlift/BrainLift.md` (thesis/evidence).*
