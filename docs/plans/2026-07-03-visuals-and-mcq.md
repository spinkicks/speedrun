# Plan — Interactive visuals + MCQ auto-grade (2026-07-03 push)

**Goal:** make Speedrun visibly *not-Anki* by adding interactive, thesis-aligned visuals, and upgrade the Performance signal from self-rated to objectively key-checked. ~10h, two agents on Opus 4.8 High working in parallel.

**Owner split (disjoint files → clean parallel merges):**
- **Cursor** — all 4 visuals, pure Svelte/TS in the shared surface (renders desktop + Android). Branch `feat/speedrun-visuals` in an isolated worktree (`../anki-visuals-wt`) off anki `main` `cec324901`.
- **Claude** — interactive MCQ auto-grade (card JS + capture + engine) on `feat/mcq-autograde`; plus close bug #3 (Option 1) on `feat/speedrun-ai`.
- Each merges to anki `main` when it gates. Honesty rule throughout: abstaining data renders "—"/greyed, never a fabricated number.

**Constraints:** pure SVG for all charts (no new npm deps → AGPL-clean, deterministic, demo-safe). New "Map" is a client-side SvelteKit route reached via in-app nav (like Home↔Memory) → zero native wiring. Data comes from existing RPCs — no new engine work required to start the visuals.

---

## Workstream 1 (Cursor) — The Map: interactive prerequisite graph  ·  Flagship #7 / SPOV 4
- **Route:** new `ts/routes/speedrun-map/` + nav link from Home (client routing).
- **Data:** `GetExamProfile` (nodes, prerequisite edges, ETS weights) + `GetTopicMastery` (per-topic mastery) + `GetPerformanceReadiness` (coverage/scores).
- **Layout:** computed layered DAG (topological depth → columns) in pure SVG; small fixed exam DAG so deterministic.
- **Encoding:** node color = mastery (real → green scale; abstain → grey "—"); node size ∝ ETS weight; edges = prerequisite arrows.
- **Interaction:** tap node → BFS highlight of downstream "blast radius" (topics it caps) + dim others; hover/tap tooltip (topic, mastery-or-abstain, coverage, weight); legend; reset.
- **Verify:** svelte-check 0/0; renders at desktop + 360px; abstain state honest; no console/RPC errors.

## Workstream 2 (Cursor) — Calibration reliability diagram  ·  SPOV 2 / Insight 11
- **Placement:** Memory dashboard panel.
- **Data:** `GetCalibration` (`ReliabilityBin`: stated-confidence bucket, actual accuracy, count) + Brier/ECE.
- **Render:** reliability chart — x = stated confidence, y = actual accuracy, perfect-calibration diagonal, points/bars sized by count, overconfidence shading; Brier/ECE readout.
- **Honesty:** below LS1 threshold (<20 attempts) → "answer N more to unlock", no chart faked.

## Workstream 3 (Cursor) — Memory→Performance gap visual  ·  SPOV 1 / Flagship #4
- **Placement:** Memory dashboard (upgrades the existing GAP(Δ) column).
- **Data:** `GetTopicMastery` (recall) + `GetPerformanceReadiness` (performance) + gap Δ.
- **Render:** per-topic slope chart (recall dot → performance dot connected) or paired bars, sorted by gap; only rows where BOTH are real (else "—", per the P0 #3 fix).
- **Note:** once Claude's MCQ auto-grade lands, the "performance" dot reflects key-checked accuracy.

## Workstream 4 (Cursor) — Readiness gauge  ·  SPOV 2
- **Placement:** Home (where readiness lives).
- **Data:** `GetPerformanceReadiness` (point + conformal lo/hi on 200–990).
- **Render:** horizontal 200–990 number line with scale markers, the readiness point, and the **conformal range drawn as a band**. No percentile claim (we have no ETS norm table — honest).
- **Honesty:** abstain → "insufficient data" state, no gauge value.

## Workstream 5 (Claude) — Interactive MCQ auto-grade  ·  SPOV 1 (thesis-critical)
- Clickable choices in the `Speedrun::Problem` card → compare chosen option to `CorrectAnswer` → persist correctness where the engine reads it for Performance.
- Capture: desktop `pycmd` webview hook (LS1 pattern) + Android bridge parity as feasible (desktop-first OK). Store via LS1-style config-blob (no schema change → sync-demo-safe).
- Engine: Performance reads auto-graded correctness when present; falls back to self-rated (backward-compatible). Proto append-only if needed.
- Verify: UI-verify clickable card (desktop + 360px) + engine tests + apkg regen (additive field; model id unchanged if possible). Retires the "self-reported" caveat; un-defers the P2-D FUTURE-PLANS item.

## Not doing
- §13 graph-vs-flat experiment → **reframed** (graph's value = sequencing, per SPOV 4). Doc-only update to BrainLift/FUTURE-PLANS.
- Force-directed graph physics (chose curated layered layout for demo reliability).

## Demo narrative
Home (readiness gauge) → **Map** (tap a weak calculus node, blast radius lights up) → Memory (gap visual + reliability diagram) → answer a Problem (auto-graded MCQ). One cohesive "honest measurement, *visualized*" story.
