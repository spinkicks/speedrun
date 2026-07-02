# Speedrun — Future Plans / Backlog

Everything we deliberately deferred, so nothing gets lost. Grouped by when it naturally lands. `docs/PROGRESS.md` tracks what's *done*; this tracks what's *next*. Not a commitment to do all of it — a menu. **Updated 2026-07-01 after the 7-agent audit** (audit-sourced items marked `[audit]`).

## Friday workstream (next up, per cadence — full brief: `docs/plans/2026-07-03-friday-brief.md`)
- **Due-card queue interleave** (the remaining half of the headline feature): weakness × topic-weight × interleave ordering at review time in `rslib/src/scheduler/queue/builder/` (PRD §4.65-66). The new-card `ReorderNewByPointsAtStake` reposition (done) covers new-card ordering; this covers the review queue.
- **Performance & Readiness scores:** Performance = P(correct on novel problem) — needs the `Speedrun::Problem` note type + curated problem bank first; **memory→performance gap meter** (§7d paraphrase test); Readiness = flat IRT → scaled 200–990 + conformal range + give-up rule. **Three scores on the phone.** Proto additions are append-only on the frozen proto: percentile, scale semantics (0-1 vs 200-990), `gap_delta`, `abstain_reason`/`unlock_requirements`.
- **External AI/RAG service (FastAPI + LangGraph, off by default):** generate → SymPy/CAS verify → RAG source-ground (hybrid BM25+dense) → gold-set gate (§7f); mal-rule distractors. Lives in the umbrella repo, NEVER in rslib/rsdroid. App still scores with AI off.
- **Live sync demo:** desktop ↔ Android two-way against the self-hosted server + offline-reconnect run (§7b test already green; this is the human-visible proof).

## Sunday workstream (prove it + ship)
- Memory **calibration** (reliability chart + Brier/log loss on held-out) (§9.1).
- Performance accuracy on held-out exam questions (§9.2); score-mapping writeup + range (§9.3). Create `eval/holdout/` (does not exist yet) + one-command eval entrypoint; leakage scan BEFORE any AI-generated content lands.
- **3-build ablation harness** (full / feature-off / plain), equal study time, pre-registered metric (§8) — map builds to the engine's `AblationMode` enum (already shipped).
- **Leakage check** script (§7e); **crash ×20** + offline tests (§7g); **`make bench`** p50/p95/worst on a 50k-card deck (§7h, §10).
- Packaged desktop installer + **signed APK**; both apps score with AI off.
- Results report + memory/performance/readiness one-pagers + demo video + BrainLift final pass.

## Engineering-quality backlog `[audit 2026-07-01]` (non-critical findings; criticals went straight to Claude's branch)
**Engine:**
- `get_topic_mastery` batching — replace per-card `get_card` + `get_revlog_entries_for_card` loops with bulk queries (mirror `get_revlog_entries_for_searched_cards_after_stamp`); required before the 50k bench.
- Reorder determinism contract — sort/preserve explicit order in Full mode (mirror `FeatureOff`'s `sort_unstable`) + a run-twice determinism regression test; currently relies on SQLite implicit row order (§8 reproducibility risk).
- Tag-matching case consistency — coverage/reorder match case-sensitively; `get_topic_mastery` goes through Anki search which is case-insensitive. Normalize once.
- Test gaps: `FeatureOff` mode; `Full` + empty weights (currently still mutates — decide + test intended semantics); child-deck inclusion; undo restores EXACT positions (not just integrity); Python modes 1/2; reject unknown `AblationMode` instead of `unwrap_or(Full)`.
- `get_topic_mastery` touches the in-memory scheduler cache (`&mut self`) — harmless but not strictly read-only; note for reviewers.
**Web:**
- i18n/FTL pass on all speedrun pages (currently hardcoded English; repo convention is `@generated/ftl` `tr.*`).
- MathJax topic labels (memory-dashboard-spec item that silently didn't ship).
- Theming: RangeBand uses non-existent tokens (`--accent`, `--frame-bg`) → fixed fallback colors in both light/dark; swap to real tokens. (Speedrun Home intentionally uses its own "The Run" tokens per spec — the fix applies to the Memory page.)
- Empty states: distinguish "exam profile not configured" from "profile OK, no matching cards"; add real spinner; hide 0/0 coverage flash while loading.
- Centralize duplicated constants (masteryThreshold 0.9, minReviews 20, examId "gre_math") shared TS-side; they're also duplicated in Rust defaults.
- A11y: aria-label on RangeBand, `type="button"`, focus states; drop the lock emoji for a styled glyph.
**Android:**
- Instrumentation test for the SpeedrunMemory/Home screens (add to `PagesTest`) + a bridge round-trip test (current tests cover JNI directly + registration parity only).
- Wire `reorderNewByPointsAtStake` into the Android bridge when a UI needs it (deliberately unwired today).
- Menu placement: speedrun entries are last in the DeckPicker overflow; consider promotion once stable.
**Desktop:**
- `self.web = None` after cleanup + `activateWindow()` on show + load-flash mitigation (peers' pattern) on both speedrun dialogs.
- Localize dialog window titles (menu label already goes through FTL).
**Content/build:**
- Seed-deck tests validate topics against ALL profile ids while the builder enforces leaf-only — tighten test to leaf ids.
- Cross-layer test: import seed deck → assert `get_topic_mastery` finds cards for all 9 leaf topics.
- `.apkg` byte-reproducibility (genanki zip timestamps) or explicitly document non-determinism; seed test currently rewrites the committed `.apkg` on every pytest run.
- Machine-readable JSON schema validation for exam profiles; assert containers weight==0 + names present.
- Trim vendored Briefcase template cruft (`.github/`, CONTRIBUTING) if desired — cosmetic.

## Agentic-workflow / tooling (the "software factory")
- **LangGraph adoption** for the AI service (manager's graph+agents vision): install `langchain-ai/langchain-skills` (`langgraph-fundamentals`, `langchain-rag`, `langgraph-human-in-the-loop`, `deep-agents-core`) when the Friday AI service starts.
- **Context-engineering** (see `docs/CONTEXT-ENGINEERING.md`): dogfood the tips; make "context-as-graph" explicit inside the LangGraph work.
- `[audit]` **Visual-verification protocol:** every UI gate must include an actual screenshot render check (the Memory dashboard shipped "code-complete" without ever being rendered on desktop — which is how the API-access gap survived review).

## Product frontend / UX revamp — OWNER PRIORITY ("our own app on Anki's skeleton")
**Vision (David, 2026-07-01):** Speedrun is its OWN product. `rslib` is the skeleton/backend; the frontend & UX are ours — not Anki's default reviewer / deck-picker / theming.
**Status:** ACTIVE — pulled forward from "after Friday" by owner decision. Slice 1 (**Speedrun Home, "The Run"**) is in build today on `feat/speedrun-home` per the approved `docs/design/speedrun-home-spec.md` (flat/sharp/terminal aesthetic; splits with honest error-brackets; amber pace accent; auto-open on launch, config-gated).
**Known UX gaps (small fixes):**
- `[found recording 2026-07-01]` **Desktop Memory dashboard has no "back to Home"** — it opens as its own QDialog; Home links into Memory but not vice-versa (one-way). Add a "‹ HOME" affordance in the shared Memory page (bridge `open:home` on desktop / nav-up on Android). Low priority; not submission-blocking.

**Remaining slices (design-first, one spec each):**
1. **Nav shell** — persistent Speedrun navigation (Home / Study / Memory / Scores) across both platforms; Home links stop being one-off dialogs.
2. **Reviewer restyle** — our card-review experience (the highest-touch, most invariant-sensitive surface; do after scores exist).
3. **Branding assets** — logo/icon set, app name/launcher on Android, window title/icon on desktop.
   - `[verified 2026-07-01]` **Android shell theming:** on the Speedrun Home/Memory PageFragments, the `MaterialToolbar` (top) and the system status/navigation bars (bottom) render WHITE against the dark "The Run" page — theme them to the dark palette (fragment toolbar color + `statusBarColor`/`navigationBarColor` or a dark theme on `SingleFragmentActivity`). Cosmetic; visible in any phone demo/recording, so fix before recording. WebView page itself is correctly dark.
4. **Anki-chrome trimming** — desktop menu slimming, Android launch-activity + theme; deck picker demoted to a maintenance surface.
5. Fri scores land directly in OUR UI (Home/scores page), not in new Anki-styled dialogs.
**Guardrails:** engine invariants untouched (pure presentation/navigation); every slice spec'd → reviewed → built → screenshot-verified; Memory-page restyle to "The Run" tokens folded into the nav-shell slice (two aesthetics coexist until then — accepted, flagged in audit).

## Architecture / cleanup (do-it-right refactors)
- **Relocate content toolchain** `repos/anki/speedrun/` → the umbrella repo (permanently removes the .venv/minilints class of problem). Deferred because it's already committed in-fork.
- **arm64-v8a Android support** — add the target to the AAR build for physical devices (x86_64-only today; fine for emulator demo). `ALL_ARCHS=1` exists in build_rust.
- **Upstreamability (bonus §13):** the `render.rs` Windows n2 fix is genuinely upstream-worthy; consider a PR to `ankitects/anki`. Possibly also the complexipy cp1252 crash report (tool bug, not our code).
- **Branch pruning (cosmetic):** forks carry ~40+ inherited upstream branches; optionally prune. (`main` upstream tracking: FIXED 2026-07-01.)

## Known CI/env items (non-blocking)
- **complexipy** tool crash on our diff (Windows cp1252 bug inside the tool) — cosmetic; fix/report before any CI gate is required.

## Stretch / bonus ideas (only if core is rock-solid; §13 + BrainLift flagships)
- Knowledge-graph readiness model as a **v2 experiment that must beat the flat baseline** on held-out score prediction.
- Real-time sync (<1s), 100k-card perf w/ profiling, signed+notarized installers for mac/Win/Linux.
- **GRE Physics module** via the exam-profile abstraction (shared math-node transfer credit).
- BrainLift flagships: overtrain mode, counterexample gauntlet, calibration self-bet, prerequisite blast-radius diagnosis.
