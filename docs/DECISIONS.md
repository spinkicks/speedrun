# Speedrun — Decision Log & Project State

Captures the key decisions and rationale (much of which originated in planning chats) so anyone can pick up the project. Living document.

## Owner
- David Ordonez (math background; chose GRE to leverage that expertise).

## What we're building
**Speedrun**: a study app built **on top of Anki** for **one** graduate-level exam — the **GRE Mathematics Subject Test** — shipping on **desktop + mobile sharing one engine**, with a real change to Anki's **Rust** backend, and three honest, separately-reported scores (memory / performance / readiness) each with a range and a "give-up" rule. License: **AGPL-3.0-or-later**, credit to Anki.

## Decision 1 — Exam: GRE Mathematics Subject Test (was MCAT)
- **First chose MCAT**, fully researched it (see `research/research-notes.md` §1–2).
- **Switched to GRE Math Subject Test** because (manager approved GRE; wants innovation):
  1. **Almost empty tool market** — no adaptive tool, no calibrated readiness predictor, no knowledge-graph product exists. Max innovation.
  2. **Real prerequisite structure** — calculus is 50% AND a prerequisite for much of the rest (analysis, complex, ODEs). A dependency-graph engine is genuinely useful here (unlike flat MCAT/General-Quant).
  3. **Native interleaving evidence** — Rohrer & Taylor (2007) is literally about shuffling *math* problems.
  4. **Objective answers** — clean AI gold sets + verifiable problem generation.
  5. **Owner expertise** — faster, more credible execution.
- **Cost accepted:** thinner real-score validation data + ~5k takers/yr (irrelevant for a graded project). We lean into abstention + supplement with curated/generated problems.
- Rejected: LSAT/GMAT/USMLE (poor flashcard fit or weaker thesis); GRE General Quant (saturated market, flat/shallow content).

## Decision 2 — "Build on top of Anki," not "be Anki"
- Anki/FSRS = the proven **memory/spaced-repetition chassis** (the backbone). Analogy: Blazing Audio built on Brilliant.
- **We add our own layers:** a practice-problem (performance) engine, a prerequisite-topic taxonomy/DAG, an IRT/calibrated readiness model, and RAG-based problem generation. The required Rust change lives in the engine; most added value is layered on top.

## Decision 3 — Headline learning-science feature = Interleaving, implemented as the Rust change
- Interleaving (technique-selection training) is both the §8 study feature (15%) AND the §7a Rust change (20%) — one build covers both.
- Strongest evidence of any option, math-native: Rohrer et al. (2020) RCT, 61% vs 38%, d≈0.83.
- Implemented as **topic-aware interleaving + points-at-stake sequencing** in `rslib/src/scheduler/queue/builder/`.

## Decision 4 — Prerequisite DAG: use for SEQUENCING + DIAGNOSIS, not score-gating; graph-readiness is a falsifiable v2
- Score is **number-right → a topic-weighted sum** (calculus as a strong multiplier), NOT a min() over prerequisites.
- The KT literature shows graph/deep models only modestly (and unreliably) beat flat IRT/BKT, especially under sparse data (Khajah 2016; Xiong 2016; Gervet 2020).
- **Therefore:** ship a **calibrated FLAT IRT/mastery readiness model first**; the prerequisite-graph readiness model is a **v2 experiment that must beat the flat baseline on held-out score prediction** (also satisfies §13's "prove the graph beats keyword/vector").
- The graph's defensible value: study sequencing (Gagné/KLI), diagnosis ("your weakest prerequisite"), and robustness under sparse data.

## Decision 5 — Pareto framing (corrected, honest)
- NOT a literal 20/80. Real: **~30% of topics ≈ ~70% of questions.** Calculus ≈ 50%; **calc + all algebra ≈ 70–75%**; **calc + linear algebra ≈ 55–60%**. "50% calculus" is partly a bucketing artifact. All subtopic counts are estimates with high per-form variance.

## Decision 6 — Honest readiness model
- Output: point estimate + range + % coverage + percentile + "how sure" + best next action; **abstain** below a data threshold.
- Stack: IRT/equating for the estimate; conformal/CQR intervals (widen under sparse data); Brier/ECE calibration + temperature scaling; selective-prediction abstention.
- Anchor: AAMC-equivalent here = released ETS forms + supplemented curated/generated problems.

## Decision 7 — AI = RAG, source-grounded, makes the student think
- Every AI output (generated problems/tutoring) cites a named source, is checked against a gold set (objective answers + worked solutions), and must beat a keyword/vector baseline.
- Pedagogy: lead with **worked examples → interleaved + spaced practice**. Do NOT assume the retrieval/testing effect transfers cleanly to math problem-solving (Huang et al. 2023).

## Decision 8 — Mobile target: Android-first (confirmed feasible), iOS deferred
- **Android via AnkiDroid** — feasible, medium risk. Critical finding: AnkiDroid pulls a *prebuilt* backend AAR, so to ship our modified `rslib` we must fork & build a **third repo, `ankidroid/Anki-Android-Backend` (rsdroid)** — ✅ DONE: cloned to `repos/Anki-Android-Backend`, built, merged; `local_backend=true` swap works (proven Tue on the emulator).
- **iOS deferred** — AnkiMobile is closed-source; building a Swift shell over rslib's FFI is not realistic in a 1-week build.
- **One forked `anki` repo feeds BOTH bridges** (desktop PyO3 `pylib/rsbridge` + Android JNI rsdroid). Keep proto changes additive.
- Full details, the proto→Rust→Python steps, sync model, and the day-1 walking skeleton: `docs/ARCHITECTURE.md`.

## Decision 9 — Where our layers live (from architecture review)
- **Rust core** only for logic that changes *what the scheduler shows / how cards are scheduled* (queue builder `scheduler/queue/builder/`, answering, a read-only readiness RPC). This is where the required engine change is justified.
- **Add-on / external** for everything else: prerequisite DAG (data + read RPC), IRT/readiness training (external service), RAG problem generation (external service; cards imported as notes + synced). Keeps the mobile `.so` small.
- **Math rendering:** use Anki's already-bundled **MathJax** (both platforms) — author with `\(...\)`/`\[...\]`. No KaTeX needed.
- **Sync:** self-host from `rslib/sync`; conflict model is USN incremental + forced one-way full-sync (no per-card auto-merge) — design the offline/conflict test accordingly.

## Decision 10 — "Weaponized honesty" is the flagship position; a curated bold feature set
- Competitive research confirms the calibration/abstention machinery is **absent from all ed-tech** → it's our trust differentiator AND a novel engagement loop. See BrainLift "Flagship Features."
- Top features: three-number honesty dashboard (w/ intervals); abstention UX ("INSUFFICIENT DATA — unlock by…"); **calibration self-bet** (Brier-scored confidence, "overconfidence tax"); memory→performance gap meter; counterexample gauntlet; points-at-stake topic-aware interleaving (the Rust change); prerequisite-DAG "blast radius" diagnosis; adversarial sibling problems + mal-rule distractors; the encoded 99th-percentile playbook.
- Anti-features (deliberate): no vanity streaks, no dopamine gamification, no single confident readiness number.

## Decision 11 — AI = hybrid neuro-symbolic, gated
- Pipeline: LLM proposes a symbolic schema → **SymPy instantiates + verifies** (symbolic + numerical) → **RAG-grounds** (hybrid BM25+dense → RRF → cross-encoder rerank, which beats keyword/vector) → **hard gold-set gate** before display. Distractors from **mal-rules** (Brown & Burton). AI-off ships a curated human-verified bank. Pre-registered §7f cutoffs: wrong-answer ≤2% (target 0), useful ≥80%, bad-teaching ≤15%, leakage 0.

## Decision 12 — Exam-profile abstraction (multi-exam groundwork for GRE Physics)
- Split **exam-specific data** (taxonomy, DAG, weights, scoring/percentile tables, item pools, timing, scoring rule) from **shared engine** (scheduler, FSRS, IRT, interleaving, readiness, sync, RAG). A **shared math-node layer** gives cross-exam transfer credit. Adding GRE Physics later = new data files + an `ExamProfile` record, no engine change. NEVER hard-code structural numbers (read from config). Full schema in `research/claude-GRE Physics plus multi-exam extensibility.md`.

## Decision 13 — Testimonial-derived defaults (the 99th-percentile playbook)
- Calculus-first weighted plan; stereotyped-pattern decks for the low-yield tail; timed "mock-pace" interleaving at ~2.5 min/q; auto error-log → spaced review; conserved-mock readiness (don't burn the ~6 released forms early); formula/shortcut card type; coverage/triage dashboard. Frame honestly (self-selection/survivorship bias; score value diminishes past ~80th pct).

## Decision 14 — Execution decisions from build week (recorded 2026-07-01)
- **Proto FROZEN** @ anki `20dd7a2ea` (wed-plus Phase E): 5 RPCs on `SpeedrunService`; all later changes append-only with new field numbers.
- **Interleaving implementation deviation from Decision 3:** wed-plus shipped points-at-stake as a **persisted new-card reposition** via `transact(Op::SortCards)` (undo-safe, corruption-free) instead of the queue-builder change; the **due-card queue-builder interleave** (read-time, no transact needed) was the Friday completion — **✅ shipped & merged 2026-07-03** (weakness × topic due-card interleave, ablation-gated; see Decision 15). Rationale: satisfy the mutating-op invariant with zero risk to review scheduling first.
- **rsdroid `anki` submodule pin** → `a0ead51c9` (the wed-plus HEAD containing frozen proto + the Svelte page — NOT the freeze commit, because the AAR auto-bundles the sveltekit assets from the pinned tree).
- **All 3 forks consolidated to `main`** (2026-07-01, owner call "everything on main"): anki `1fed9e109` · Anki-Android-Backend `299bb44`+`d4086e0` · anki-android `a56dda6cfb`. FF-only; feature branches kept as backup. Cursor executes merges at reviewed gates.
- **Frontend revamp direction approved ("The Run"):** Speedrun is its OWN app on Anki's engine. Slice 1 = branded Home (splits + honest error-brackets, flat/sharp/terminal, amber pace accent, auto-open on launch) per `docs/design/speedrun-home-spec.md` + approved mockup. Owner pulled this forward (visible frontend changes same-day); heavier slices sequenced around Friday's scoring work.
- **Lane update:** Claude Code builds the frontend too (owner call; keeps the proven subagent-driven loop). Cursor = mission control: specs, reviews, gates, docs, git. Cursor avoids concurrent writes in `repos/*` while Claude builds.
- **Installer strategy:** Briefcase win/mac templates vendored in-tree (network-independent clean-machine build); supersedes the wed-mvp "populate submodules" fix; accepted trade-off = manual re-vendor on upstream template bumps.

## Decision 15 — Friday scope merged (recorded 2026-07-03)
The Friday depth work landed as one batch merge; all three forks + umbrella are back on `main`. Per-repo main SHAs: anki `c54afe2b1` · Anki-Android-Backend `14c2992` · anki-android `f2cf66ac35` · umbrella latest.
- **Headline feature completed (closes the Decision 14 "Friday completion" loop):** the **due-card queue-builder interleave** shipped — weakness × topic-weight interleave at review time in `rslib/src/scheduler/queue/builder/`, ablation-gated. Together with the wed-plus new-card `ReorderNewByPointsAtStake` reposition (via `transact`/`OpChanges`), both halves of the points-at-stake interleaving feature are now live.
- **Three honest scores on both platforms:** Memory (Wilson CI + abstain), Performance (P(correct) + memory→performance gap Δ + abstain), Readiness (flat IRT → 200–990 scale + conformal interval + give-up rule).
- **D1 — in-engine deterministic scoring:** Performance/Readiness are computed **in the Rust engine, recompute-on-read**; there is **no synced score blob** (avoids stale/divergent scores across devices and keeps the mobile `.so` self-contained).
- **D4 — timed mini-mock via a filtered deck:** the `Speedrun::Problem` MCQ bank (64 items, double-SymPy-verified) drives a timed mini-mock built as a **filtered deck** (`reschedule=true`), reusing Anki's proven temporary-deck machinery instead of new scheduling code.
- **LS1 calibration storage = config-blob (MVP):** the calibration log persists to a **config blob** (`speedrun:calibration_log`) with desktop capture + Brier/ECE + self-rated (Sure/Think-so/Guess) framing; params are constants (0.9 / 0.65 / 0.4, abstain < 20). A **sync-safe attempt-log TABLE was deliberately deferred** — a new table forces a schema-version (`scm`) bump → one-way full sync (AGENTS.md invariant), which must NOT fire during the sync demo. Upgrade once the demo constraint lifts.
- **Interactive-MCQ auto-grading DEFERRED:** `Speedrun::Problem` remains a show-answer/self-rate card (revlog stores only `button_chosen`, never the chosen option), so Performance "correct" is self-assessed. Interim shipped = self-grade-against-key copy + honesty caveat. Real fix (clickable choices → compare to `CorrectAnswer` → persist correctness, desktop + Android) is its own both-platforms feature.
- **§8 ablation — M3 kept exploratory (honest record):** the ablation harness (`AblationMode` Full / FeatureOff / Plain) ships with pre-registered metrics M1/M2; **M3 was NOT retro-promoted to pre-registered** since it was added after the fact — it stays exploratory to keep the pre-registration honest. Results in `docs/ablation-s8-results.md`.
- **Branding:** Manrope ExtraBold wordmark + `#F4F7FA` surface — the "looks like a real, substantial app" identity signal (Decision 10 / distinct-identity mandate).
- **External AI service consolidated to umbrella `main`, OFF by default:** `services/speedrun-ai/` (FastAPI, SymPy verify + hybrid RAG 82-passage + gold-set gate) requires `SPEEDRUN_AI_ENABLED=1` **and** `OPENAI_API_KEY`; both apps score fully with AI off. Lives OUTSIDE all native libs (never imported into rslib/rsdroid). Gold set `eval/holdout/gre_math_gold.jsonl` (50, triple-verified) is off-limits to agents.
- **Still pending (human / Sunday):** emulator visual gate, live sync-demo recording, demo video, the Sunday eval RUNS, robustness (crash ×20 / offline / `make bench`), signed APK, BrainLift final pass; 7 bug fixes in progress.

## Decision 16 — Interactive visuals + MCQ auto-grade + installer-bundles-deck (recorded 2026-07-03 PM)
This batch turns several previously-textual thesis claims into live, honest UI and closes the Decision 15 "Performance is self-reported" loop. Per-repo main SHAs: anki `348db0c6c` · umbrella `e36d765`.
- **Four interactive visuals shipped (pure-SVG, shared Svelte surface, both platforms, honest abstains):**
  1. **The Map** (`/speedrun-map`) — an interactive prerequisite graph where tapping a weak node lights its downstream **blast radius** (every topic it caps). This **realizes BrainLift Flagship Feature #7** ("Prerequisite-DAG blast-radius diagnosis") as a real screen, using the graph for *diagnosis/sequencing* (its defensible strength), not score-gating.
  2. **Calibration reliability diagram** (on Memory) — plots stated confidence vs. observed accuracy (the SPOV 2 calibration self-bet, made visible).
  3. **Memory→performance gap chart** (on Memory) — the explicit recall-vs-timed-accuracy delta per topic.
  4. **Readiness gauge** (on Home) — the 200–990 point estimate with its range.
  All four are **pure SVG** (no chart lib), render identically on desktop `ts/` and the Android WebView, and **abstain honestly** (show "insufficient data / unlock by…" rather than a fake shape) below the data threshold.
- **Interactive-MCQ auto-grading MERGED → Performance is now key-checked (reverses Decision 15's "DEFERRED"):** clickable choices are compared to `CorrectAnswer` and correctness is persisted, so Performance "correct" is now **objectively graded, backend-authoritative** — retiring the "self-reported/self-assessed" caveat. Stored in the **config-blob** store (same MVP mechanism as `speedrun:calibration_log`); crucially **no `.proto` field change and no note/model change** were needed, so it stayed inside the AGENTS.md sync invariants (no `scm` bump, no forced full sync during the demo).
- **All 7 adversarial-sweep bugs fixed;** notably **bug #3 — AI grounding hardened:** the AI layer now gates on a **semantic-embedding** grounding check and the syllabus lookup is **fail-closed** (unknown/ungrounded → refuse, not guess). Consistent with Decision 7/11 (source-grounded, gold-set-gated) and keeps the AI honest when it can't verify.
- **Installer will bundle + auto-import the seed deck (in progress):** the win/mac installer (Briefcase, vendored templates per Decision 14) will **ship the seed deck and auto-import it on first launch** so a grader gets a populated, ready-to-run app with zero manual import. Convenience/grading affordance only; the deck remains ordinary imported notes (no engine change).
- **External AI service unchanged / still OFF by default:** `services/speedrun-ai/` continues to require `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`; both apps score fully with AI off (Decision 15).

## Open questions / TODO research
- [x] Architecture & build feasibility → `docs/ARCHITECTURE.md` (DONE; desktop low-risk, Android medium, iOS deferred).
- [x] Innovation landscape (Math Academy, ALEKS, Khanmigo, Korbit) — DONE; white space confirmed. `research/claude-innovation landscape plus bold ideation.md`.
- [x] GRE-Math 99th-percentile testimonials & strategies — DONE. `research/claude-gre math 99th percentile testimonials and strategies.md`.
- [x] AI math problem generation + verification — DONE. `research/claude-AI math-problem generation plus verification.md`.
- [x] Multi-exam extensibility ("exam profile" abstraction) — DONE. `research/claude-GRE Physics plus multi-exam extensibility.md`.
- [x] Creative-features brainstorm pass — DONE (folded into BrainLift "Flagship Features").
- [x] PRD / docs plan (coverage map → topic taxonomy + DAG data; readiness-model spec; problem-sourcing plan; day-1 walking skeleton) — DONE (`docs/PRD.md`; walking skeleton complete, see Decision 15).
- [ ] NEXT (Sunday): **run** the evals (memory calibration reliability/Brier + performance accuracy on held-out + score-mapping writeup) — the harness/gold set exist; the RUNS are pending.
- [ ] NEXT (Sunday): **signed APK** (x86_64 emulator AAR built; signing + arm64 for physical devices outstanding) + robustness gates (crash ×20 / offline / `make bench`) + BrainLift final pass.

## File map
- `brainlift/BrainLift.md` — the BrainLift (Purpose, 6 SPOVs, Experts, Insights, Knowledge Tree, rubric map).
- `research/research-notes.md` — consolidated research (GRE chosen §0/§0b; MCAT alt §1–2; learning science §3; calibration §3b; engine §4).
- `research/claude-gre-deepdive.md` — external deep-dive (Claude): Pareto/graph stress-test, citations/DOIs, DAG.
- `research/claude-innovation landscape plus bold ideation.md` — Math Academy deep-dive, competitor matrix, white-space verdict, 18 bold feature ideas.
- `research/claude-gre math 99th percentile testimonials and strategies.md` — top-scorer strategies + feature-mapping.
- `research/claude-AI math-problem generation plus verification.md` — hybrid neuro-symbolic pipeline, CAS verification, RAG, safety, eval cutoffs.
- `research/claude-GRE Physics plus multi-exam extensibility.md` — GRE Physics spec, cross-exam DAG, exam-profile schema.
- `docs/DECISIONS.md` — this file.
- `docs/ARCHITECTURE.md` — build & engine architecture, feasibility verdict, walking skeleton.
- `repos/anki`, `repos/anki-android` — upstream clones (not tracked).
