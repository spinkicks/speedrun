# Speedrun — Future Plans / Backlog

Everything we deliberately deferred, so nothing gets lost. Grouped by when it naturally lands. `docs/PROGRESS.md` tracks what's *done*; this tracks what's *next*. Not a commitment to do all of it — a menu.

## Friday workstream (next up, per cadence)
- **Headline learning-science engine change:** topic-aware **interleaving** + **points-at-stake** queue ordering in `rslib/src/scheduler/queue/builder/` (the *mutating* change via `transact`/`Op`; §8 ablation, 15% rubric). Deferred from Wednesday (we shipped the read-only RPCs first for zero corruption risk).
- **Self-hosted sync server** (`rslib/sync`) + **two-way sync** + offline-reconnect + **conflict rule** (latest-review-timestamp wins; §7b test). Lifts the 70% "no sync" cap.
- **Performance & Readiness scores:** Performance = P(correct on novel problem); **memory→performance gap meter** (§7d paraphrase test); Readiness = flat IRT → scaled 200–990 + conformal range + abstention. **Three scores on the phone.**
- **Polished three-number honesty dashboard (Svelte/TS):** Memory / Performance / Readiness each with range + abstain, built on the RPC seams. *(The Wednesday Memory score is demonstrated via the RPC; the full dashboard is coherent to build here when all three scores exist.)*
- **External AI/RAG service (FastAPI, off by default):** generate → SymPy/CAS verify → RAG source-ground → gold-set gate (§7f); mal-rule distractors. **LangGraph fits here** (stateful graph w/ verify/retry/abstain edges). App still scores with AI off.

## Sunday workstream (prove it + ship)
- Memory **calibration** (reliability chart + Brier/log loss on held-out) (§9.1).
- Performance accuracy on held-out exam questions (§9.2); score-mapping writeup + range (§9.3).
- **3-build ablation** (full / feature-off / plain Anki), equal study time, pre-registered metric (§8).
- **Leakage check** script (§7e); **crash ×20** + offline tests (§7g); **`make bench`** p50/p95/worst on a 50k-card deck (§7h, §10).
- Packaged desktop installer + **signed APK**; sync conflict handling; both apps score with AI off.
- Results report + memory/performance/readiness one-pagers + demo video + BrainLift.

## Agentic-workflow / tooling (the "software factory")
- **LangGraph adoption** for the AI service (manager's graph+agents vision): hierarchical spawn → managed agents; install `langchain-ai/langchain-skills` (`langgraph-fundamentals`, `langchain-rag`, `langgraph-human-in-the-loop`, `deep-agents-core`) via `npx skills` when the Friday AI service starts.
- **Context-engineering** (see `docs/CONTEXT-ENGINEERING.md`): dogfood the tips now; optionally install `addyosmani/agent-skills --skill context-engineering` if agent output starts drifting. Make "context-as-graph" explicit inside the LangGraph work (bounded context per node + checkpointer state).

## Architecture / cleanup (do-it-right refactors)
- **Relocate content toolchain** `repos/anki/speedrun/` → the umbrella `speedrun` repo, where root `AGENTS.md` says the content pipeline belongs (permanently removes the .venv/minilints class of problem). Deferred because A0–A2 already committed it in the fork.
- **arm64-v8a Android support** — add the target to the cargo-ndk AAR build for *physical* devices (currently x86_64-only for the emulator; fine for demo).
- **`.apkg` byte-reproducibility** — zero out genanki zip timestamps so rebuilding doesn't dirty the committed deck.
- **Upstreamability (bonus §13):** the `render.rs` Windows n2 fix is a genuine upstream-worthy patch; consider a PR to `ankitects/anki`. Same for a clean `SpeedrunService` add-on.
- **Branch/tracking hygiene (cosmetic):** the forks carry ~40+ inherited upstream branches (dependabot/contributor) — harmless; optionally prune for a clean list. Also reset `main` tracking to `origin/main` on the anki fork.

## Known CI/env items (non-blocking)
- **complexipy** tool crash on our diff; **installer/complexipy** CI checks — cosmetic/env, fix before any CI gate is required.

## Stretch / bonus ideas (only if core is rock-solid; §13 + BrainLift flagships)
- Knowledge-graph readiness model as a **v2 experiment that must beat the flat baseline** on held-out score prediction (the graph must *prove* it helps).
- Real-time sync (<1s), 100k-card perf w/ profiling, signed+notarized installers for mac/Win/Linux.
- **GRE Physics module** via the exam-profile abstraction (shared math-node transfer credit).
- BrainLift flagships: overtrain mode, counterexample gauntlet, calibration self-bet, prerequisite blast-radius diagnosis.
