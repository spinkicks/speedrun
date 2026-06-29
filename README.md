# Speedrun

A desktop + mobile study app built on **Anki**, focused on a single graduate-level exam: the **GRE Mathematics Subject Test**.

> One exam. Two apps on one engine. A real Rust engine change. Honest scores (memory, performance, readiness) — each with a range, each able to refuse to answer when it lacks data.

Licensed **AGPL-3.0-or-later**, with credit to [Anki](https://github.com/ankitects/anki). Some upstream components are BSD-3-Clause.

## Why the GRE Mathematics Subject Test
This exam is the strongest fit for the project's thesis (memory ≠ performance ≠ readiness) *and* for being innovative:
- **An almost empty tool market** — no adaptive tool, no calibrated readiness predictor, and no knowledge-graph product exists for it.
- **A real prerequisite structure** — calculus is 50% of the exam *and* the prerequisite for much of the other 50% (real analysis, complex variables, ODEs), so a dependency-graph engine is genuinely valuable.
- **Native learning-science evidence** — the foundational interleaving study (Rohrer & Taylor 2007) is literally about shuffling *mathematics* problems.
- **Objective answers** — math problems have verifiable answers and worked solutions, making AI-card checking and gold sets clean.
- Official ETS content weights (Calculus 50% / Algebra 25% / Additional Topics 25%) give a defensible coverage map; scale is 200–990 (median ≈ 680 = 50th percentile).

We build *on top of* Anki the way Blazing Audio built on Brilliant: Anki/FSRS is the proven spaced-repetition memory chassis; we add a practice-problem engine, a prerequisite knowledge graph, and an honest, abstaining readiness model.

## Architecture: two apps, one engine
- **Desktop + shared engine:** `repos/anki` — fork of [`ankitects/anki`](https://github.com/ankitects/anki).
  The Rust backend (`rslib/`) is where our engine change lives; the desktop uses it directly.
- **Phone companion:** `repos/anki-android` — built on [`ankidroid/Anki-Android`](https://github.com/ankidroid/Anki-Android),
  which consumes Anki's Rust backend via `rsdroid`. Our Rust change ships to the phone through the same backend.

## Headline features
- **Prerequisite-aware *sequencing* / points-at-stake (the Rust change):** order reviews by topic centrality (graph leverage) × student weakness, plus topic-aware interleaving — implemented in the Rust scheduler queue. The graph drives study *order*; the score itself is a weighted sum, not a gate.
- **Interleaving (learning-science feature):** trains *technique selection*, the core skill of a mixed 66-problem exam (math-native RCT evidence, d≈0.83). Validated with the 3-build ablation (feature on / off / plain Anki).
- **Memory→performance bridge:** worked-examples-led practice-problem engine that tests whether a remembered technique transfers to a novel problem.
- **Honest, abstaining readiness:** a calibrated flat IRT/mastery projection on 200–990 with a conformal range that widens on sparse data and a give-up rule. A prerequisite-graph readiness model is a v2 experiment that must beat the flat baseline before adoption.

## Repository layout
```
Speedrun/
├── brainlift/     # The BrainLift (planning, SpikyPOVs, knowledge tree, evidence base)
├── docs/          # Architecture notes, model descriptions, exam coverage map
├── research/      # Raw research notes and source captures
└── repos/         # Upstream clones (anki, anki-android) — not tracked by this repo
```

## Status
Planning phase: BrainLift complete; app implementation not yet started.
