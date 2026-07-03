# Speedrun — Future Plans / Backlog

Everything we deliberately deferred, so nothing gets lost. Grouped by when it naturally lands. `docs/PROGRESS.md` tracks what's *done*; this tracks what's *next*. Not a commitment to do all of it — a menu. **Updated 2026-07-01 after the 7-agent audit** (audit-sourced items marked `[audit]`).

## Friday workstream (SHIPPED + merged to main 2026-07-03 — full brief: `docs/plans/2026-07-03-friday-brief.md`)
- **✅ DONE — Due-card queue interleave** (the remaining half of the headline feature): weakness × topic-weight × interleave ordering at review time in `rslib/src/scheduler/queue/builder/` (PRD §4.65-66), ablation-gated. The new-card `ReorderNewByPointsAtStake` reposition (done) covers new-card ordering; this now covers the review queue too.
- **✅ DONE — Performance & Readiness scores (three scores on both platforms):** Performance = P(correct on novel problem) + **memory→performance gap meter** (§7d) + abstain; Readiness = flat IRT → scaled 200–990 + conformal range + give-up rule. ✅ The `Speedrun::Problem` note type + curated problem bank (**64 items, double-SymPy-verified**) shipped too. Computed **in-engine, deterministically, recompute-on-read** (no synced score blob). Proto additions stayed append-only on the frozen proto.
- **✅ DONE — External AI/RAG service (FastAPI, off by default):** generate → SymPy/CAS verify → RAG source-ground (hybrid BM25+dense, 82-passage) → gold-set gate (§7f); mal-rule distractors. Consolidated to umbrella `main` as `services/speedrun-ai/`, NEVER in rslib/rsdroid; requires `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`. App still scores fully with AI off.
- **Live sync demo** *(code path proven; recording still OPEN)*: desktop ↔ Android two-way against the self-hosted server + offline-reconnect run. §7b test already green; the **human-visible recording remains outstanding** (see `docs/SYNC-SELFHOST.md`).

## Sunday workstream (prove it + ship)
- **[OPEN] RUN** Memory **calibration** eval (reliability chart + Brier/log loss on held-out) (§9.1). *(LS1 calibration capture + Brier/ECE machinery shipped; the held-out RUN is what remains.)*
- **[OPEN] RUN** Performance accuracy on held-out exam questions (§9.2); **[OPEN]** score-mapping writeup + range (§9.3). ✅ `eval/holdout/` now EXISTS (`gre_math_gold.jsonl`, 50 triple-verified — agents must not read) + one-command eval entrypoint; leakage scan BEFORE any AI-generated content lands.
- **✅ DONE — 3-build ablation harness** (full / feature-off / plain), equal study time, pre-registered metric (§8) — `AblationMode` enum + harness shipped; results in `docs/ablation-s8-results.md` (M1/M2 pre-registered; M3 kept exploratory, not retro-promoted).
- **Leakage check** script (§7e); **[OPEN] crash ×20** + **[OPEN] offline** tests (§7g); **[OPEN] `make bench`** p50/p95/worst on a 50k-card deck (§7h, §10).
- Packaged desktop installer (done) + **[OPEN] signed APK**; both apps score with AI off.
- Results report + memory/performance/readiness one-pagers + demo video + **[OPEN] BrainLift final pass**.

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
**DISTINCT-IDENTITY MANDATE (David, 2026-07-02) — RAISE TO A FIRST-CLASS WORKSTREAM:** a first-time user (and a grader) must immediately read the running app as **Speedrun**, a substantial purpose-built GRE-Math trainer — NOT "Anki with a couple of extra pages." The bar: launcher/window says Speedrun (name + icon), first screen is *ours* ("The Run"), navigation is *ours*, the review surface is *ours*, and Anki's default chrome (deck picker, menus, upstream branding) is demoted to a maintenance/back-office surface a normal user never has to see. Concretely this means SHIPPING, not just backlogging: (1) **branding pass** — app name + launcher icon (Android) + window title/icon + a Speedrun wordmark/logo on Home; (2) **persistent nav shell** so Home/Study/Memory/Scores are one coherent app, not one-off dialogs; (3) **Anki-chrome trimming** — hide/relegate the deck picker + upstream menus by default. Every Friday score must land in OUR branded surface (Home/Scores), never in a new Anki-styled dialog. This is a **demo-critical, rubric-adjacent** deliverable (the "looks like a real, substantial app" signal), so it is scheduled alongside — not after — the Friday depth work.
**Status:** ACTIVE — pulled forward from "after Friday" by owner decision. Slice 1 (**Speedrun Home, "The Run"**) MERGED + verified on both platforms. Next up per the identity mandate: **Slice B (branding/de-Anki-fication)** — design-first spec then build; see slices below.
**Known UX gaps (small fixes):**
- `[found recording 2026-07-01]` **Desktop Memory dashboard has no "back to Home"** — it opens as its own QDialog; Home links into Memory but not vice-versa (one-way). Add a "‹ HOME" affordance in the shared Memory page (bridge `open:home` on desktop / nav-up on Android). Low priority; not submission-blocking.

**Remaining slices (design-first, one spec each):** — *per the identity mandate, slices 1 (nav shell) + 3 (branding) are the NEXT to build; they carry the "distinct, substantial app" signal for the demo/grader.*
1. **`[NEXT]` Nav shell** — persistent Speedrun navigation (Home / Study / Memory / Scores) across both platforms; Home links stop being one-off dialogs (also fixes the Memory "back to Home" gap above). One spec covering desktop + Android.
2. **Reviewer restyle** — our card-review experience (the highest-touch, most invariant-sensitive surface; do after scores exist).
3. **`[NEXT]` Branding assets / de-Anki-fication** — Speedrun app name + launcher icon (Android) + window title/icon (desktop) + a wordmark/logo on Home; replace upstream Anki branding on OUR surfaces. Cheap, high-visibility win — a grader sees "Speedrun" before reading a line of code.
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

## Learning-science research audit (2026-07-02) — coverage + gaps
3-subagent read-only audit of `research/` (~150 items). **Core thesis already built/landing:** points-at-stake interleave (Phase 1), 3 honest scores + conformal + abstention (Phase 2), §7d gap meter (Phase 2), honest topic mastery + Wilson (Wed), problem bank + timed mini-mock (Phase 3), neuro-symbolic gen + SymPy verifier + mal-rule distractors + gold-set gate (Phase 4), IRT difficulty, exam-profile abstraction, prerequisite DAG (structural).

**GREENLIT additions (David 2026-07-02, NON-BLOCKING — after host-phase core / else Sunday):**
- **LS1 Calibration self-bet** — pre-answer confidence (Sure/Think-so/Guess) on problem attempts only (NOT Anki revlog schema); Brier/ECE "overconfidence tax", abstains below threshold.
- **LS2 Worked-examples-first + faded worked examples** — Huang 2023 (retrieval drilling weak for math procedures); reuse `WorkedSolution`; example→faded→solo progression.
- **LS3 Honesty guardrail copy** — diminishing-returns flag, survivorship-bias note, desirable-difficulty messaging, strengthen abstention framing. (All in `.claude/cursor-review.md`.)

**DEFERRED gaps (surfaced, worth it later, NOT now — v2 / Sunday / stretch):**
- Counterexample gauntlet + adversarial-sibling problems (AI-service generation modes; BrainLift flagships).
- Misconception catalog + distractor↔misconception mapping (powers diagnosis; fold into AI distractors when time).
- Interference-aware scheduling (separate confusable topics); projected-decay readiness (score at exam-date memory state).
- Graph knowledge-tracing v2 (ONLY if it beats the flat IRT/PFA baseline on held-out score prediction — already the documented rule).
- Faded-step self-explanation grading (LLM-graded free-text) — high effort, LLM-judge reliability risk.
- Prerequisite blast-radius diagnosis (already a BrainLift flagship below).
- LS1 calibration — Android in-reviewer confidence capture (P2-D-class deferral): desktop uses card-JS→`pycmd` via `webview_did_receive_js_message` (zero `reviewer.py` edits); Android needs new native Kotlin (`AbstractFlashcardViewer.filterUrl`/`Signal`) in the untouched anki-android repo. MVP ships desktop capture + a read-only Calibration StatRow that shows on both platforms (the synced stat travels free). [LS1, 2026-07-02]
- LS1 calibration — sync-safe attempt-log TABLE (post-MVP upgrade from the config-blob store): per-row USN deltas instead of `speedrun:calibration_log` JSON blob (config sync, last-writer-wins). Deferred because a new table = schema-version bump → forces one-way full sync (AGENTS.md:20), which must NOT fire during the sync demo. Upgrade once the demo constraint is lifted. [LS1, 2026-07-02]
- Interactive-MCQ auto-grading — **DONE on desktop (2026-07-03, `feat/mcq-autograde`).** `Speedrun::Problem` choices are now clickable → the chosen option is graded **backend-side** against `CorrectAnswer` (not client-trusted) → persisted to the synced `speedrun:mcq_attempts` config blob (no schema/proto/model-field change); the engine's Performance (`topic_problem_stats`) now counts **objective key-checked correctness**, overriding self-rating, and falls back to self-rated (`button≥3`) when no auto-grade exists (backward-compatible). Retires the "self-reported until interactive grading" caveat on desktop. **Still deferred:** Android in-reviewer capture (same shared card JS renders; Android needs a native bridge to persist — the engine reads the blob regardless of platform, so Android inherits the read side once capture lands). [P2-D → desktop DONE 2026-07-03; Android capture deferred]
- Math-correctness pass on the 26 new RAG passages (Hefferon + MIT OCW 18.06) before the AI service is ever enabled — grounding context, not answer keys; AI service is OFF-by-default so non-blocking. [phase6/RAG #4, 2026-07-02]
- RAG hybrid-margin ceiling: last 5 uncovered gold items cite closed textbooks (Lay + Strang) — did NOT vendor; ≥5pt hybrid margin unmet (all arms saturate). Revisit only with legit open sources; never gold-peek. [RAG #4, 2026-07-02]

## Stretch / bonus ideas (only if core is rock-solid; §13 + BrainLift flagships)
- Knowledge-graph readiness model as a **v2 experiment that must beat the flat baseline** on held-out score prediction.
- Real-time sync (<1s), 100k-card perf w/ profiling, signed+notarized installers for mac/Win/Linux.
- **GRE Physics module** via the exam-profile abstraction (shared math-node transfer credit).
- BrainLift flagships: overtrain mode, counterexample gauntlet, calibration self-bet, prerequisite blast-radius diagnosis.
