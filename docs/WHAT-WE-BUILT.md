# What We Built — honest narrative of Speedrun's changes on top of Anki

> **Purpose:** a talking-script / explainer of everything we changed, why, and its HONEST status (real now / scaffolding / planned). Companion to `docs/DEMO-SCRIPT.md` (the click-by-click demo, written later). **This is the honesty project — every claim here is marked real / scaffolding / planned. Do not present scaffolding or planned items as done.** Last updated 2026-07-01 (Wed).

## One-paragraph honest positioning
Speedrun is built **on** Anki, not instead of it. Anki's proven memory engine (FSRS spaced repetition) stays the chassis; we did **not** rewrite the scheduler or invent a memory model. What we added on top: an **honest measurement layer** (topic-level mastery with real confidence intervals and abstention), a **modest evidence-based scheduling feature** (points-at-stake new-card interleaving), exam-specific **content + coverage/prerequisite structure**, a **branded cross-platform product shell** (our own "Speedrun Home" + Memory dashboard on desktop and Android from one shared codebase), **self-hosted sync**, and a **network-independent installer**. The differentiated learning-science engine (readiness modeling, calibration, weakness-driven scheduling, AI problem generation) is scoped and in progress — **not yet built**.

---

## 1. The engine change (Rust, `rslib`) — the required "real change to Anki's backend"
All additive; lives in a self-contained `rslib/src/speedrun/` module + one frozen proto service (`proto/anki/speedrun.proto`). ~1,100 authored lines; tiny, surgical upstream contact (see `docs/artifacts/upstream-files-touched.md`).

**5 RPCs on `SpeedrunService`:**
| RPC | Type | What it does | Honest status |
|---|---|---|---|
| `GetCoverage` | read-only | How many required exam topics your deck actually covers | ✅ real |
| `GetTopicMastery` | read-only | Per-topic recall from FSRS retrievability → **Wilson 95% interval** + **abstain** below data threshold | ✅ real (our strongest differentiator) |
| `GetExamProfile` | read-only | The exam's topic DAG + ETS weights (from synced config; baked-in default) | ✅ real |
| **`ReorderNewByPointsAtStake`** | **mutating** | Repositions **new cards** by topic weight + round-robin **interleave**; via `transact(Op::SortCards)`, undo-safe; ablation modes Full/FeatureOff/Plain | ✅ real, but **new-card order only** (not the review queue) |
| `GetPerformanceReadiness` | read-only | Placeholder for Performance/Readiness scores | ⚠️ **SCAFFOLDING — always abstains, no model** |

**Why Rust (not a Python add-on):** the change must run identically on desktop *and* Android from one engine; only `rslib` is shared across both bridges. Mutations honor Anki's invariant (`transact`/`OpChanges`, undo, `pragma integrity_check ok`). Proto is frozen + append-only.

**Tests:** ~15 Rust (pure unit + integration) + Python integration + a §7b sync test. Undo + integrity proven for the mutating op.

## 2. Learning science — what's REAL vs Anki baseline (read `§ Honest answer` in chat)
- **Memory science = Anki's FSRS** (we did not change it). ✅ (Anki's)
- **Our additions Anki lacks:** topic mastery + Wilson interval + abstention ✅ real; points-at-stake **new-card** interleaving ✅ real (limited scope); exam-weighted coverage + prerequisite DAG ✅ structural (not yet an active scheduling/diagnosis feature).
- **Planned, NOT built:** weakness-weighted **review-queue** interleave; Performance model (P correct on novel problem); Readiness (flat IRT → 200–990 + conformal + give-up); memory→performance gap meter; calibration (Brier/reliability); graph-based diagnosis. → Friday/Sunday.

## 3. Content pipeline (deterministic, NO AI)
- **Exam-profile DAG** (`speedrun/exam_profiles/gre_math.json`): 9 leaf topics (calc + linear algebra), ETS weights (sum 1.0), acyclic prereq graph. ✅ real.
- **35-card seed deck** (`gre_math_seed.apkg`): hand-authored calc+LA cards, hierarchical `calc::…`/`linear_algebra::…` tags, a Source on every card. Tag↔topic alignment audit-verified. ✅ real.
- **Deterministic open-licensed scraper** (FLEX, keyword-rule tagging, no AI). ✅ real.

## 4. The product shell — "our own app on Anki's engine" (UI)
- **Speedrun Home ("The Run")** — a branded landing that **auto-opens on launch** (config-gated), rendering your run as **splits** with honest 95% **error-brackets** and abstention. Flat/sharp/terminal aesthetic (dark `--ink`, amber pace accent, monospace numerals). One shared SvelteKit page renders on **both** desktop (Qt dialog) and Android (PageFragment) from the same code + engine. ✅ real, merged, verified on both platforms.
- **Memory dashboard** — shared Svelte page: coverage header, per-topic recall + range band + abstain, grouped by root, sort toggle. ✅ real (desktop + Android). Being re-themed dark to match "The Run".
- **Mobile-first responsive** (M0 ✅ merged): pages reflow phone-first (~360px stacked) → desktop columns (≥768px); fixed the one-word-per-line wrapping.
- **In progress (branch `feat/speedrun-mobile-first`):** Android dark shell (M1 ✅ code), **START RUN** launching real study + honest "import"/"caught up"/Custom Study states (S1 desktop, S2 Android), and a **full reviewer restyle** to "The Run" (R1 — presentation only, both platforms). ⏳ in progress / needs David's GUI+emulator gates.

## 5. Two apps, one engine + sync + installer
- **One engine, two apps:** the same forked `rslib` compiles to desktop (PyO3) and Android (JNI AAR via cargo-ndk); proven by an instrumentation test asserting identical backend version, and now by the same UI rendering on both. ✅ real.
- **Self-hosted sync:** `anki-sync-server` (in-fork) + a §7b two-way conflict test (10+10 offline reviews all land, latest-mtime-wins, documented honest caveat). ✅ test real; live desktop↔phone sync demo = Friday.
- **Network-independent installer:** vendored the Briefcase Windows/mac templates in-tree so a clean machine builds the desktop installer with no submodule fetch. ✅ real.

## 6. What to say / not say (honesty guardrails for any demo or writeup)
- ✅ SAY: "honest topic mastery with confidence intervals + abstention", "points-at-stake new-card interleaving", "one engine → two apps, one shared UI", "self-hosted sync with a tested conflict rule", "clean-machine installer".
- ❌ DON'T SAY (not built yet): "readiness score", "performance prediction", "calibrated", "the AI checks problems", "weakness-driven scheduling", "we improved FSRS". Performance/Readiness **abstain by design** today — that's the honest story, not a finished score.

---
*See also: `docs/PROGRESS.md` (done/left), `docs/DECISIONS.md` (why), `docs/plans/2026-07-03-friday-brief.md` (what's next), `brainlift/BrainLift.md` (thesis/evidence).*
