# Friday Brief — AI + three scores + sync demo (requirements, for Claude to ground into a full plan)

> **STATUS: BRIEF (requirements-level).** This is Cursor's requirements input, produced 2026-07-01 from the post-wed-plus PRD gap analysis. Claude turns it into a grounded, task-by-task plan (Serena/ast-grep/`cargo check` grounding, TDD) on Thursday, for Cursor review before execution. It is NOT itself an executable plan.

**Cadence slot:** Friday = "AI added & checked; phone syncs; three scores." Rubric at stake: Score accuracy & honest uncertainty (20%) + AI checking & safety (15%) + remaining halves of the Rust-change (20%) and study-feature (15%) areas + sync demo (10% area). This is the highest-weight day of the project.

**Hard rules carried forward:** mutations via `transact(Op::X)`; proto additions APPEND-ONLY (proto frozen @ `20dd7a2ea`; new fields/messages get new numbers); AI lives in the umbrella repo ONLY (never rslib/rsdroid); app must fully work with AI off; TDD (failing test first); `eval/holdout/` stays unread by agents; no fake numbers — abstain until thresholds are met.

## Prerequisite fixes (carry-in from the 2026-07-01 audit — do these FIRST if not already landed on `feat/speedrun-home`)
1. Desktop webview→backend data path (exposed_backend_list + API-enabled webview kind).
2. Exam-profile bootstrap on fresh collections.
3. `closeWithCallback` on speedrun dialogs.
4. `get_topic_mastery` batching (N+1) — needed before any bench or 50k testing.
5. Reorder Full-mode determinism contract + regression test — needed before the ablation harness means anything.

## Item 1 — Due-card queue interleave (completes the headline engine change)
- PRD §4.65-66: order the REVIEW queue by weakness × topic ETS-weight × interleave (no two adjacent same-topic when avoidable), at queue-build time in `rslib/src/scheduler/queue/builder/`.
- Read-time ordering (queue builder computes order, doesn't persist) — reconcile the invariant note explicitly in the plan: no `transact` needed for read-time ordering; the persisted new-card reposition (done) already satisfies the mutating-op requirement.
- Must respect the existing `AblationMode` semantics so the 3-build ablation maps cleanly: Full = weakness-weighted interleave on; FeatureOff = Anki default order; Plain = untouched Anki.
- Weakness signal: per-topic FSRS retrievability (reuse `get_topic_mastery` internals — batched version).
- Tests: ≥3 Rust (ordering properties, ablation-mode differences, determinism) + 1 Python integration.

## Item 2 — Problem layer (prerequisite for Performance/Readiness)
- `Speedrun::Problem` note type (PRD §3.56): stem, choices, correct answer, worked solution, topic tag(s), technique tag, Source; timing metadata.
- Curated seed problem bank (human-verified, NO AI needed to ship it): enough per leaf topic for mini-mocks (owner's math background = author/curate fast; released ETS forms stay out of study content per leakage rules).
- Timed mini-mock session mechanic (even minimal: N problems, wall-clock captured per answer) — needed by the Readiness give-up rule ("≥2 timed mini-mocks").

## Item 3 — Performance score: P(correct on novel problem)
- Inputs per PRD §5.75: topic memory (FSRS) + IRT item difficulty + technique mastery + timing + coverage.
- Friday-realistic scope: fit/score via the external service (numpy/scipy; flat IRT 2PL/3PL on problem revlog) OR a deterministic in-engine approximation — Claude's plan should pick ONE with rationale.
- **Gap meter (§7d):** per-topic Δ(declarative recall − problem accuracy); UI column on the dashboard/Home; paraphrase/transfer eval design goes in the plan (execution can be Sunday).
- Abstain below data thresholds (mirror the Memory abstain discipline).

## Item 4 — Readiness score: flat IRT → 200–990 + conformal + give-up
- θ → scaled 200–990 via equating-style table from the exam profile config; percentile alongside.
- Conformal/CQR interval; widen under sparse data.
- Give-up rule (PRD §5.78): abstain until ≥2 timed mini-mocks AND coverage ≥ threshold AND interval width < cutoff; emit actionable unlock text ("answer 12 more calculus items").
- **Proto additions (append-only) the scaffolding can't express:** percentile, scale semantics (Performance 0–1 vs Readiness 200–990), `gap_delta`, `abstain_reason`/`unlock_requirements`, last-updated. Consider splitting `GetPerformance` from `GetReadiness` if cleaner; keep `GetPerformanceReadiness` compatible.
- Scores persist in the synced config blob (both platforms read identical numbers).

## Item 5 — External AI service (FastAPI + LangGraph, OFF by default)
- Location: umbrella repo (`services/` or similar), NEVER imported by rslib/rsdroid.
- Pipeline (Decision 11): LLM proposes symbolic schema → SymPy instantiates + verifies (symbolic + numeric) → RAG source-grounding (hybrid BM25+dense → RRF → rerank) → mal-rule distractors → gold-set gate → emits verified `Speedrun::Problem` notes for import.
- §7f pre-registered cutoffs: wrong-answer ≤2% (target 0), useful ≥80%, bad-teaching ≤15%, leakage 0. Build the 50-pair gold set + gate harness (gold set lives in `eval/holdout/` — created by David/Cursor, unread by agents).
- LangGraph for the verify/retry/abstain graph (install the langchain-skills per FUTURE-PLANS).
- Kill-switch proof: service down → apps keep scoring from the curated bank (record this).

## Item 6 — Three scores on the phone + sync demo
- Extend the shared Svelte surface (Home "The Run" + Memory page) so Memory / Performance / Readiness all render with range + abstain on BOTH platforms; rebuild AAR once at the end (single re-pin, same as wed-plus discipline).
- Live two-way sync demo: desktop ↔ Android against self-hosted `anki-sync-server` (SYNC-SELFHOST.md steps); offline-reconnect run; capture for the recording.

## Sequencing constraint (one shared checkout)
Engine items (1, proto for 3/4) → merge/freeze → AI service (parallel-safe: umbrella repo) → UI (6) → AAR re-pin + rebuild once. Mirror the wed-plus phase-gate pattern with Cursor review at each gate.

## Open questions for David (answer before/at Thursday planning)
1. Problem bank sourcing: how many problems can you curate/author Thursday-night–Friday, per topic? (Floor needed for IRT to be honest; abstention covers the rest.)
2. Which LLM/API for the generation service (needs a key by Friday morning)?
3. Mini-mock length/timing (e.g., 10 problems @ 2.5 min/q per Decision 13)?
4. Gold-set authorship: you write/verify the 50 pairs (agents must not) — schedule ~1-2h.
