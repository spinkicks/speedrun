# GRE Physics Subject Test: Research Report for the "Speedrun" Exam-Profile Architecture

## TL;DR
- The GRE Physics Subject Test is alive and viable as a second module: as of 2025–26 it is one of only three remaining ETS Subject Tests (Mathematics, Physics, Psychology), but since September 2023 it is **computer-delivered, approximately 70 five-choice questions in 2 hours**, scored 200–990 in 10-point steps with **rights-only scoring (no guessing penalty)** — so the widely-cited "100 questions / 170 minutes / paper / ¼-point penalty" facts are now OUTDATED and must not be hard-coded.
- Physics shares heavy mathematical machinery with the GRE Math test (single/multivariable calculus, linear algebra, ODEs/PDEs, vector calculus, Fourier methods), which validates the "exam profile" abstraction: the scheduler, FSRS memory model, IRT calibration, interleaving and readiness-display logic are all SHARED; only the content taxonomy, prerequisite graph, content weights, scoring/percentile tables and item pools are exam-specific.
- The GRE Physics prep market is as thin as the Math market for *adaptive/calibrated* tooling — it is served almost entirely by static books (Kahn & Anderson's *Conquering the Physics GRE*), four free released exams (GR8677/GR9277/GR9677/GR0177), forums (physicsgre.com) and ad-hoc Anki decks; **no adaptive, knowledge-graph, IRT-calibrated readiness predictor exists**, and adjacent products (Math Academy, ALEKS, Khanmigo) do not cover graduate physics exam prep. This is clear white space.

## Key Findings

1. **Current structure (post-Sept 2023):** approximately 70 five-choice MCQs, 2 hours, computer-delivered at test centers and at home, offered in three windows (September, October, April). The official ETS Content and Structure page states verbatim: "The test consists of approximately 70 5-choice questions" and "Total testing time is 2 hours and 50 minutes for the Mathematics Test and 2 hours for the Physics and Psychology Tests."
2. **The task brief's structural numbers are stale.** "~100 questions / 170 minutes / paper-based / ¼-point guessing penalty" described the *pre-2023* exam. The current exam is rights-only scored with ~70 questions in 120 minutes. Build the engine to read these from config, never constants.
3. **Scoring:** Total scaled score 200–990 in 10-point increments; since Sept 2023, three percent-correct subscores (Classical Mechanics; Electromagnetism; Quantum Mechanics & Atomic Physics) reported 0–100. Raw correct count → equated scaled score.
4. **Percentiles (ETS Interpretive Data):** Per Table 2A (©2025, all individuals tested July 1, 2021–June 30, 2024): **Physics Test — 4,759 test takers, mean 724, SD 167.** The 990 cap maps to the 96th percentile (ETS Table 2B footnote, verbatim: "For the Physics Test, the percent of test takers scoring lower than 990 is 96"). Physics test-takers skew high (a strong, self-selected population).
5. **Content weights (official ETS):** Confirmed verbatim against the ETS GRE Physics Test Practice Book: Classical Mechanics 20%, E&M 18%, Quantum Mechanics 13%, Atomic Physics 10%, Thermodynamics & Statistical Mechanics 10%, Optics & Wave Phenomena 8%, Special Relativity 6%, Laboratory Methods 6%, Specialized Topics 9%. (Note: the brief's "QM 12% / Optics 9%" are superseded by the current ETS figures of 13% / 8%.)
6. **Math overlap is large and explicit.** ETS itself lists the required mathematical methods: "single and multivariate calculus, coordinate systems (rectangular, cylindrical and spherical), vector algebra and vector differential operators, Fourier series, partial differential equations, boundary value problems, matrices and determinants, and functions of complex variables."
7. **Learning-science transfer is strong.** Interleaving (Rohrer & Taylor) is the most-studied effect in mathematics and transfers directly to physics problem-type discrimination; the worked-example effect has a robust physics evidence base, with the important caveat that it only appears when diagram/text split-attention is eliminated.
8. **Market white space is real.** No adaptive/IRT/knowledge-graph product targets GRE Physics; the strongest assets are static.

## Details

### 1. Structure & Scoring

**Status and availability (2025–26).** The GRE Physics Subject Test remains offered. ETS discontinued Chemistry after April 2023; Biology and Literature in English were discontinued in 2021; Biochemistry earlier. The surviving three are Mathematics, Physics and Psychology (ETS, verbatim: "The GRE Chemistry Test was discontinued in May 2023. The GRE Biology Test and the GRE Literature in English Test were discontinued in May 2021"). Tests run in three roughly two-week windows per year (September, October, April), retakeable every 14 days.

**Format change (critical recency caveat).** After the April 2023 administration, all three remaining Subject Tests moved to computer-delivered format, and Physics/Psychology were shortened from "nearly 3 hours" to 2 hours. The official ETS Content and Structure page now states: "Total testing time is 2 hours and 50 minutes for the Mathematics Test and 2 hours for the Physics and Psychology Tests," and "The test consists of approximately 70 5-choice questions." Many third-party pages (PrepScholar, Number2, Pravegaa, university SPS pages) still say ~100 questions/170 min/paper — these reflect the legacy exam and should not be trusted over ETS.

**Answer choices:** five options (A–E) per question, single best answer; "some grouped in sets based on diagrams, graphs, experimental data, and physical situations." SI units throughout; a Table of Information with constants and conversions is provided.

**Scoring mechanics:** Total scaled score 200–990, 10-point increments; the usable range is narrower than 200–990. The number correct (total correct score) is converted to an equated scaled score so editions are comparable. Since September 2023, three percent-correct subscores (Classical Mechanics; Electromagnetism; Quantum Mechanics & Atomic Physics) are reported on a 0–100 scale; pre-Sept-2023 subscores used a 20–99 scale. The three subscores are based on raw bases of 14, 13, and 16 questions respectively (per the ETS Practice Book).

**Guessing penalty — RESOLVED:** The legacy exam (and 2nd-edition prep books) used a ¼-point penalty for wrong answers. The current ETS guidance is rights-only: "Your score will be determined by the number of questions you answer correctly. Questions you answer incorrectly or for which you mark no answer ... are counted as incorrect. Nothing is subtracted from a score if you answer a question incorrectly." So the optimal strategy is now: never leave a blank.

**Percentiles (ETS Interpretive Data, Table 2B):**

| Scaled score | Physics percentile (% scoring lower) |
|---|---|
| 990 | 96 |
| 960 | 95 |
| 900 | 79 |
| 800 | 62 |
| 700 | 45 |
| 600 | 27 |
| 500 | 9 |
| 400 | 1 |

Mean 724, SD 167, N=4,759 (Table 2A cohort: July 2021–June 2024). **Data caveat:** ETS's Table 2B header states its percentile cohort is "July 1, 2019, and June 30, 2023," conflicting with the July 2021–June 2024 cohort cited for Table 2A in the same document — treat both as versioned, re-verifiable data and reconcile at each cycle. The population is small and elite (self-selected physics majors applying to PhD programs), so a "good" raw fraction maps to a comparatively modest percentile, and the 990 cap maps to only the 96th percentile because the top ~4% are undifferentiated by design.

### Content breakdown table (with primary math prerequisites)

| Content area | ETS weight (current) | Primary math prerequisites |
|---|---|---|
| Classical Mechanics | 20% | Single/multivariable calculus; ODEs (oscillators); vector algebra; linear algebra (coupled oscillations, normal modes); calculus of variations (Lagrangian/Hamiltonian) |
| Electromagnetism | 18% | Vector calculus (div/grad/curl); multivariable calculus; PDEs & boundary-value problems; ODEs (circuits) |
| Quantum Mechanics | 13% | Linear algebra (operators, eigenvalues); ODEs/PDEs (Schrödinger eq.); Fourier analysis; complex variables |
| Atomic Physics | 10% | Algebra; some linear algebra/quantum scaffolding; basic calculus |
| Thermodynamics & Statistical Mechanics | 10% | Multivariable calculus (partial derivatives); probability/combinatorics; some PDEs |
| Optics & Wave Phenomena | 8% | ODEs/PDEs (wave equation); Fourier analysis; trigonometry/complex exponentials |
| Special Relativity | 6% | Algebra; linear algebra (Lorentz transformations, four-vectors) |
| Laboratory Methods | 6% | Error propagation (calculus); statistics (Poisson, counting); log plots |
| Specialized Topics (nuclear, particle, condensed matter, astrophysics, math methods) | 9% | Mixed; some linear algebra, calculus, complex variables |

**Topic-overlap analysis with GRE Math.** The GRE Math test is ~50% calculus and applications, ~25% algebra (incl. linear & abstract algebra), ~25% additional topics. The shared tooling layer with Physics is substantial: single/multivariable calculus underpins essentially every Physics area; linear algebra gates quantum mechanics and special relativity; ODEs gate oscillations, circuits and the Schrödinger equation; vector calculus gates E&M; Fourier/PDE methods gate waves and quantum. The conceptual physics content (Newton's laws, Maxwell's equations, etc.) does NOT overlap — only the mathematical machinery does. This is exactly the right granularity for a shared "math skill" node layer feeding two distinct content layers.

### 2. Prerequisite structure & cross-exam dependency graph

**Internal physics dependencies:** Calculus → Classical Mechanics → (E&M, Thermodynamics). Linear algebra + ODEs → Quantum Mechanics. Classical Mechanics + E&M → Optics/Waves. Classical Mechanics → Special Relativity. Quantum Mechanics → Atomic Physics → Specialized Topics (nuclear/particle/condensed matter). Lab Methods depends on statistics/error analysis and draws on all experimental areas.

**Cross-exam dependency graph (adjacency list).** Nodes prefixed `M:` are GRE-Math (shared math skills); `P:` are GRE-Physics content nodes. Edges point prerequisite → dependent.

```
# MATH (shared skill layer)
M:single_var_calculus      -> M:multivar_calculus, P:classical_mechanics, P:special_relativity
M:multivar_calculus        -> M:vector_calculus, P:thermo_stat_mech, P:classical_mechanics
M:vector_calculus          -> P:electromagnetism
M:linear_algebra           -> P:quantum_mechanics, P:special_relativity
M:odes                     -> P:classical_mechanics, P:electromagnetism, P:optics_waves, P:quantum_mechanics
M:pdes_boundary_value      -> P:electromagnetism, P:optics_waves, P:quantum_mechanics
M:fourier_analysis         -> P:optics_waves, P:quantum_mechanics
M:complex_variables        -> P:quantum_mechanics, P:specialized_topics
M:probability_statistics   -> P:thermo_stat_mech, P:lab_methods

# PHYSICS (content layer)
P:classical_mechanics      -> P:electromagnetism, P:thermo_stat_mech, P:optics_waves, P:special_relativity
P:electromagnetism         -> P:optics_waves
P:quantum_mechanics        -> P:atomic_physics
P:atomic_physics           -> P:specialized_topics
P:thermo_stat_mech         -> P:specialized_topics
P:lab_methods              -> (terminal; draws on all experimental areas)
P:special_relativity       -> P:specialized_topics
```

This DAG is directly renderable (e.g., Graphviz). The `M:` layer is reusable across both the Math and Physics exam profiles; the engine treats a math node as "satisfied" if mastery is demonstrated in *either* exam, enabling transfer credit for users who studied the Math module first.

### 3. Tool-market gap

**Existing GRE Physics resources (all essentially static):**
- **Prep books:** *Conquering the Physics GRE* (Yoni Kahn & Adam Anderson, Cambridge, 3rd ed. 2018; ISBN 978-1-108-40956-8) is the canonical text — written by two MIT physicists, it reviews all nine content areas and includes three full-length practice exams with worked solutions. It is described as the "only comprehensive reference book specifically tailored to the topics on ETS's Physics GRE." Others: Sterling Test Prep GRE Physics (1300+ questions), Princeton Problems in Physics, Schaum's 3000 Solved Problems, plus standard texts (Halliday/Resnick, Griffiths, Purcell).
- **Free released exams:** Four ETS exams are widely circulated — GR8677 (1985), GR9277 (1990), GR9677 (2001), GR0177 (2004); an older GR0877 (2011) also circulates. Hosted by Brandeis, OSU, etc.; solutions at grephysics.net (Yosun Chang's compilation of ~400 released problems) and David Latchman's/Taylor Faucett's solution sets.
- **Forums:** physicsgre.com is the dominant community (test prep, problem discussion, score/profile threads).
- **Flashcards/Anki:** Scattered community decks (CWRU's free pGRE flashcard set; user-shared AnkiWeb decks; MilesCranmer's anki_science). All static, none calibrated, none adaptive.

**Adaptive/calibrated tooling:** none specific to GRE Physics. There is no IRT-calibrated readiness predictor, no knowledge-graph sequencing product, no spaced-repetition+practice hybrid for this exam. PrepScholar markets a "machine learning" GRE program but for the *General* test, not the Physics Subject Test.

**Adjacent products do not fill the gap:**
- **Math Academy:** concept-level knowledge graph with mastery tracking, spaced review, worked-example-first lessons, interleaving/"non-interference" — architecturally the closest analog and a strong design template — but covers K–12 through university math and ML math, NOT physics or exam-specific GRE Physics prep.
- **ALEKS:** adaptive via Knowledge Space Theory, but math, chemistry, statistics, accounting only — no physics subject-exam track (only "Math Prep for College Physics").
- **Khanmigo/Khan Academy:** AI tutor + content library across math/science; SAT prep via College Board partnership, but no graduate subject-exam (GRE Physics) coverage.

**Conclusion:** The GRE Physics market is a near-empty quadrant for adaptive/calibrated tooling — even thinner than Math in absolute size (smaller test-taker pool, 4,759 over three years) but with a highly motivated, sophisticated user base (physics PhD applicants) and a clean, well-documented content spec. The Math Academy model proves the pedagogy works; no one has applied it to GRE Physics.

### 4. Exam profile abstraction (schema design)

**Separation of concerns.**

*MUST be exam-specific (data, loaded per profile):*
- Topic taxonomy / content nodes
- Prerequisite graph (DAG edges)
- Content weights (for blueprint-matched practice and readiness weighting)
- Scoring scale + raw→scaled equating + percentile tables
- Item/problem pools (tagged to nodes)
- Time limits, section structure, # questions, # answer choices
- Scoring rule (rights-only vs. penalty) and give-up/abstention thresholds

*SHARED across exams (engine, code):*
- Scheduler/queue engine (Anki Rust backend)
- FSRS memory model (stability/retrievability, desired-retention) via fsrs-rs
- IRT/calibration machinery (external service)
- Interleaving logic
- Readiness-display framework
- Sync, RAG/explanation services

**Proposed schema (YAML exam profile + additive protobuf sketch).**

```yaml
exam_profile:
  id: "gre_physics"
  version: "2026.1"
  display_name: "GRE Physics Subject Test"
  status: "active"            # active | discontinued
  last_verified: "2026-06-29"
  delivery:
    mode: "computer"          # computer | paper
    num_questions: 70         # approximate; do NOT hard-code 100
    num_choices: 5
    total_time_minutes: 120
    sections: [{ name: "single", timed: false, questions: 70 }]
    calculator_allowed: false
    reference_sheet: "table_of_information"
  scoring:
    scale_min: 200
    scale_max: 990
    increment: 10
    rule: "rights_only"        # rights_only | fractional_penalty
    penalty_per_wrong: 0.0
    subscores:
      - { id: "classical_mech", scale: [0,100], raw_base: 14 }
      - { id: "em",             scale: [0,100], raw_base: 13 }
      - { id: "qm_atomic",      scale: [0,100], raw_base: 16 }
    raw_to_scaled_table_ref: "tables/gr_physics_equate_2026.csv"
    percentile_table_ref:     "tables/gr_physics_pct_2021_2024.csv"
    norm_cohort: "2021-07-01..2024-06-30"
    norm_mean: 724
    norm_sd: 167
    norm_n: 4759
  content_weights:            # current ETS
    classical_mechanics: 0.20
    electromagnetism: 0.18
    quantum_mechanics: 0.13
    atomic_physics: 0.10
    thermo_stat_mech: 0.10
    optics_waves: 0.08
    special_relativity: 0.06
    lab_methods: 0.06
    specialized_topics: 0.09
  taxonomy_ref: "graphs/gre_physics_nodes.yaml"
  prereq_graph_ref: "graphs/gre_physics_dag.yaml"
  shared_math_layer_ref: "graphs/shared_math_nodes.yaml"
  item_pool_ref: "pools/gre_physics_items"
  abstention:
    enabled: true
    give_up_seconds: 180        # high-scorer pacing heuristic
    confidence_capture: true    # capture sure/guess/eliminated per item
```

```protobuf
// Additive protobuf changes (new fields, reserved tags, backward compatible)
message ExamProfile {
  string id = 1;
  string version = 2;
  string display_name = 3;
  Delivery delivery = 4;
  Scoring scoring = 5;
  map<string, double> content_weights = 6;
  string taxonomy_ref = 7;
  string prereq_graph_ref = 8;
  string item_pool_ref = 9;
  Abstention abstention = 10;
  string shared_math_layer_ref = 11;   // enables cross-exam transfer credit
  string status = 12;
  string last_verified = 13;
}

message Scoring {
  int32 scale_min = 1;
  int32 scale_max = 2;
  int32 increment = 3;
  enum Rule { RIGHTS_ONLY = 0; FRACTIONAL_PENALTY = 1; }
  Rule rule = 4;
  double penalty_per_wrong = 5;
  repeated Subscore subscores = 6;
  string raw_to_scaled_table_ref = 7;
  string percentile_table_ref = 8;
  double norm_mean = 9;
  double norm_sd = 10;
}

message KnowledgeNode {
  string id = 1;                 // e.g., "P:quantum_mechanics" or "M:linear_algebra"
  Layer layer = 2;               // enum { MATH, PHYSICS, ... }
  repeated string prereq_ids = 3;
  repeated string item_ids = 4;
  double exam_weight = 5;
}
```

Because items, nodes, weights and tables are all *references* (not code), adding GRE Physics means shipping new data files and an `ExamProfile` record — the Rust scheduler, FSRS optimizer (fsrs-rs), IRT service and interleaving logic are untouched. The `shared_math_layer_ref` is the key cross-exam primitive: a `M:` node mastered in the Math module satisfies the same node as a Physics prerequisite.

### 5. High-scorer strategies & learning-science transfer

**High-scorer strategies (from physicsgre.com 990-scorer threads, Kahn & Anderson, university SPS guides):**
- **Master the most-tested ~two-thirds.** Classical Mechanics + E&M alone are 38% of the exam; the first two years of undergrad physics cover the bulk. Forum 990-scorers note ~75% of questions come from freshman/sophomore-level material; the last ~10–15% (advanced QM, specialized topics) reward depth/breadth.
- **Drill the released exams under timed conditions.** GR8677/GR9277/GR9677/GR0177 are the gold standard; the 2001-era GR0177 is considered most representative of the current test. Score, log per-question confidence (sure/guess/eliminated), and review — one forum user tracked guess accuracy at 27–40% (better than the 20% random baseline), confirming educated guessing adds net points under rights-only scoring.
- **Memorize key formulas and constants** for instant recall (no time to derive; only the Table of Information is provided). Multiple 990-scorers report cramming a few dozen core equations.
- **Estimation / order-of-magnitude and answer elimination** are decisive — many items are solvable by dimensional analysis, limiting cases, or ruling out 2–3 choices.
- **Pacing:** legacy exam ~1.7 min/question (100 in 170 min); current ~1.7 min/question (70 in 120 min). Strategy: first pass for no-calc/quick items, mark and return to the rest. Because scoring is now rights-only, answer every question.
- **Practice harder-than-test problems** (e.g., Irodov) to build speed on the easier-but-tricky GRE items, per multiple 950+ forum reports.

**Learning-science transfer assessment:**

*Interleaving (Rohrer & Taylor) — Strong transfer.* The canonical results are in mathematics: Taylor & Rohrer (2010, *Applied Cognitive Psychology* 24:837–848) found interleaved practice nearly doubled next-day test scores — 4th-graders scored **77% (interleaved) vs 38% (blocked), effect size = 1.21.** Rohrer, Dedrick & Burgess (2014, *Psychonomic Bulletin & Review* 21(5):1323–1330) replicated this in a classroom RCT: grade-7 students (n=140) on an unannounced test two weeks later scored **72% (interleaved) vs 38% (blocked), d = 1.05**, and showed the benefit is not limited to superficially similar problems. Rohrer, Dedrick & Stershic (2015, *J. Educational Psychology* 107(3):900–908) confirmed the effect again. The mechanism — forcing the learner to *choose* the right strategy from the problem itself — is precisely the skill the Physics GRE tests (mixed-topic, no labeled sections). Interleaving Physics content nodes (and mixing math-tool retrieval) should transfer directly. This is also exactly what Math Academy implements as "non-interference."

*Worked-examples-first (Sweller worked-example effect) — Strong but conditional in physics.* The effect is well documented (Sweller & Cooper 1985, *Cognition and Instruction* 2:59–89; reviews by Atkinson et al. 2000), and Math Academy already uses worked-example-first lessons. The crucial physics caveat is from Sweller's own retrospective (Sweller 2023, *Educational Psychology Review* 35:95, DOI 10.1007/s10648-023-09817-2), verbatim: "We tried kinematics problems in physics classes and again found no worked example effect.... Data indicated that the worked example effect could readily be obtained provided geometry and kinematics worked examples were structured to reduce working memory load by reducing or eliminating split attention." The original data are in Ward & Sweller (1990, *Cognition and Instruction* 7(1):1–39), which recovered the effect in kinematics and geometric optics only when diagrams and text were physically integrated. So for a physics module, worked examples must integrate diagram + equation + text (not split a figure from a separate caption). The PER literature (Badeau, White, Ibrahim, Ding & Heckler 2017, *Physical Review Physics Education Research* 13:020112, DOI 10.1103/PhysRevPhysEducRes.13.020112) shows self-explanation and analogical comparison of worked *synthesis* examples significantly improve intro calculus-based-physics problem-solving (exact effect sizes should be verified against the original PDF). Meta-analytic benchmarks place worked-example effects in physics around d ≈ 0.70 (Crissman 2006, via secondary citation). Faded worked examples (gradually removing solution steps) are supported by Atkinson, Renkl & Merrill (2003, *J. Educational Psychology* 95(4):774–783) and engineering RCTs (Moreno, Reisslein & Ozogul 2009, *J. Engineering Education* 98(1):83–92).

*Honest/calibrated readiness reporting — Highly appropriate and a differentiator.* With a published percentile table and rights-only scoring, the app can map estimated ability (via IRT on the item pool) to an honest predicted scaled-score band and percentile, with explicit uncertainty — rather than vanity metrics. Forum culture is sophisticated and skeptical (users track per-question guess accuracy), so calibrated, non-inflated readiness display will resonate with this audience.

## Recommendations

**Stage 1 — De-risk the data layer (before any code).** Lock the *current* exam spec into an `ExamProfile` data file: ~70 questions, 120 min, computer-delivered, rights-only, 200–990/10-step scale, the nine current ETS weights (QM 13%, Optics 8%), and the ETS percentile table. Add a `last_verified` date and a CI check that fails if any structural number is hard-coded in engine code. *Benchmark to change course:* if ETS revises the format again (watch the ETS Content & Structure page and Fact Sheet each cycle), bump `version` only — no engine change should be required.

**Stage 2 — Build the shared math node layer first.** Since the Math module already exists, factor its calculus/linear-algebra/ODE/vector-calculus/Fourier nodes into a `shared_math_layer` referenced by both profiles. This delivers immediate transfer credit and is the cheapest proof that the abstraction works. *Threshold:* if >60% of Physics prerequisite math nodes already exist in the Math taxonomy (they should, given the overlap), the Physics build is mostly content authoring, not engineering.

**Stage 3 — Seed item pools from free + licensed content.** Use the four released ETS exams (~400 problems) for calibration anchoring and pattern modeling, but author original items for the live pool (ETS questions are copyrighted — use released items for benchmarking/IRT anchoring and worked-example pedagogy reference, not redistribution). Tag every item to a content node and capture per-attempt confidence (sure/guess/eliminated) to feed both IRT and the abstention/give-up logic.

**Stage 4 — Implement pedagogy that is proven to transfer.** (a) Interleave content nodes and math-tool retrieval (the exam is unsectioned and mixed — interleaving is the matched training signal). (b) Worked-example-first lessons with diagram+equation+text *integrated* to avoid the split-attention failure mode that Sweller documented for kinematics. (c) Faded worked examples as the bridge to independent problem-solving. (d) Calibrated readiness: IRT ability → predicted scaled-score band + percentile with stated uncertainty.

**Stage 5 — Position against the white space.** Market explicitly as the only adaptive, calibrated GRE Physics tool (vs. static books/forums). The Math Academy knowledge-graph model is the design north star; the differentiator is exam-specific calibration and honest readiness, for a small but highly motivated audience.

## Caveats
- **Recency / conflicting sources.** The single biggest risk in this domain is stale data. The brief's "~100 questions / 170 minutes / paper-based / ¼-point penalty" describes the pre-September-2023 exam. The current ETS spec is ~70 questions, 120 minutes, computer-delivered, rights-only. Many high-ranking third-party pages (PrepScholar, Number2, some university pages, Pravegaa) still publish the legacy numbers — do not trust them over ETS.
- **Content-weight discrepancy.** The brief lists QM 12% and Optics 9%; the current ETS Content & Structure page and Practice Book list QM 13% and Optics 8%. Use the live ETS values and re-verify each cycle.
- **Percentile cohort conflict and volatility.** ETS re-norms annually; the figures here come from the 2025–26 Interpretive Data document, but note its own Table 2A (cohort July 2021–June 2024) and Table 2B header (cohort July 2019–June 2023) state different cohorts — treat percentile tables as versioned data, not constants, and reconcile against the latest ETS PDF before shipping.
- **Small population.** 4,759 Physics test-takers over three years — a small, elite, self-selected pool. Market size is modest; the opportunity is depth and quality for a motivated niche, not scale.
- **GRE optionality trend.** Many physics/astronomy PhD programs made the Physics GRE optional or stopped requiring it post-2020 (cost/bias concerns); policies vary program-by-program (e.g., Stanford Physics "accepts but does not require"). Demand exists but is softer than a decade ago. This is a strategic demand risk worth monitoring.
- **Copyright.** ETS exam items are copyrighted; released exams may be used for practice/benchmarking but not redistributed commercially. Build original item pools.
- **PER effect-size precision.** The Badeau et al. (2017) study's exact effect sizes should be verified against the original PDF; the physics worked-example meta-analytic benchmark (d ≈ 0.70, Crissman 2006) is cited via secondary literature.

## References (key sources, full URLs)
- ETS — GRE Subject Test Content and Structure: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html
- ETS — GRE Subject Tests (overview/scoring): https://www.ets.org/gre/score-users/about/subject-tests.html
- ETS — Understanding Your GRE Subject Test Scores: https://www.ets.org/gre/test-takers/subject-tests/scores/understand-scores.html
- ETS — GRE Subject Test Scores (discontinuation dates): https://www.ets.org/gre/test-takers/subject-tests/scores.html
- ETS — Subject Test to be Computer Delivered (2023 change): https://www.ets.org/gre/score-users/subject-test-changes.html
- ETS — Subject Test Interpretive Data Table 2 (percentiles): https://www.ets.org/pdfs/gre/gre-guide-table-2.pdf
- ETS — Interpreting Your GRE Scores 2025–26: https://www.ets.org/pdfs/gre/interpreting-gre-scores.pdf
- ETS — GRE Physics Test Practice Book (content weights, GR0177): https://www.ets.org/content/dam/ets-india/pdfs/gre/practice-book-physics.pdf
- Kahn & Anderson, Conquering the Physics GRE (Cambridge): https://www.cambridge.org/core/books/conquering-the-physics-gre/246A74EF5DF0A31A404539325CA16A59
- grephysics.net (released-exam solutions): http://grephysics.net
- physicsgre.com forum: https://physicsgre.com
- Taylor & Rohrer (2010), Applied Cognitive Psychology 24:837–848: https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1598
- Rohrer, Dedrick & Burgess (2014), Psychon Bull Rev 21(5):1323–1330: https://pubmed.ncbi.nlm.nih.gov/24578089/
- Sweller (2023), Educ Psychol Rev 35:95 (split-attention caveat): https://link.springer.com/article/10.1007/s10648-023-09817-2
- Badeau et al. (2017), Phys. Rev. PER 13:020112: https://journals.aps.org/prper/abstract/10.1103/PhysRevPhysEducRes.13.020112
- Math Academy (knowledge-graph pedagogy): https://www.mathacademy.com/how-it-works
- ALEKS (Knowledge Space Theory): https://www.aleks.com/index
- FSRS / Open Spaced Repetition (Rust backend): https://github.com/open-spaced-repetition/fsrs-rs