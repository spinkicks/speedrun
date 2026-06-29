# Speedrun BrainLift — Research Notes

Working capture of sources and facts feeding the BrainLift. Each entry: key facts + link.

> **EXAM DECISION (final): GRE Mathematics Subject Test.** MCAT was researched first and evaluated as a strong alternative; we switched to the GRE Math Subject Test for: (1) an almost empty tool market (max innovation), (2) a real prerequisite dependency graph (calc underpins ~half the rest), (3) native interleaving evidence (Rohrer & Taylor used math problems), (4) objective answers (clean AI gold sets), and (5) the owner's math expertise. The learning-science (§3), calibration-methodology (§3b), and Anki-engine (§4) notes are exam-agnostic and still apply. The MCAT-specific sections (§1, §2) are retained as the alternative considered.

---

## 0. GRE Mathematics Subject Test (CHOSEN EXAM)

### Structure & scoring (ETS official + interpretive data)
- **~66 multiple-choice questions, 170 min** (one continuous block, 5 choices each). Computer-delivered; offered 3×/yr; **5-yr** validity. **~5,000 takers/year** (vs ~930k GRE General Quant).
- **Scale 200–990 (10-pt increments)**, number-right scoring then equated. **Median ≈ 680 = 50th percentile; ~880 = 90th; ~900 = 93rd; ~800 = 74th; ~500 = 14th.** Mean ≈ 680, SD ≈ 161.
- Links: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html ; https://www.ets.org/content/dam/ets-india/pdfs/gre/fact-sheet-math.pdf ; https://en.wikipedia.org/wiki/GRE_Mathematics_Test

### Official content weights (coverage map + Pareto core)
- **Calculus 50%** (single/multivariable diff & integral calc + applications, coordinate geometry, trig, ODEs).
- **Algebra 25%** (elementary, linear algebra, abstract algebra: groups/rings/fields, number theory).
- **Additional Topics 25%** (intro real analysis; discrete math: logic/set theory/combinatorics/graph theory/algorithms; plus topology, geometry, complex variables, prob/stats, numerical analysis).
- **Pareto:** calculus + linear algebra ≈ **65–70%** of scorable content (community consensus + official 50% calc weight). High-yield core = calc + linear algebra + intro real analysis.

### Prerequisite (dependency-graph) structure — STRONGLY cumulative
- single-var calc → multivar/vector calc; calc + limits/sequences → real analysis; linear algebra → abstract algebra + numerical analysis; calc → complex variables + ODEs; set theory/logic → discrete + topology. Calculus is the dominant root node. → motivates the readiness graph + points-at-stake scheduling.

### Tool landscape — NEARLY EMPTY (the wedge)
- Only: ETS Math Practice Book (1 full test PDF) + historical released forms (GR0568, GR1768); dated books (Princeton Review; REA — criticized); academic PDFs (Ian Coley "Math GRE Bootcamp," Charles Rambo practice + solutions, mathsub.com); one modest non-adaptive app (Varsity Tutors). No comprehensive maintained Anki deck.
- **No adaptive engine, no calibrated readiness predictor, no knowledge-graph/prerequisite tool exists.** Largest unmet need in the landscape.
- Links: https://www.mathsub.com/resources/ ; https://sites.math.rutgers.edu/~iacoley/gre/lecture-notes.pdf ; https://www.rambotutoring.com/GREpractice.pdf

### Anki/SRS fit (honest)
- Anki = memorization/retention engine, NOT a problem-solving trainer. Strong card targets: theorem statements **with hypotheses/conditions**, definitions, named results (residue theorem, rank-nullity, convergence tests), standard derivatives/integrals, Taylor series, counterexamples (LaTeX/MathJax + cloze). Avoid memorizing whole problems.
- **50% calculus is procedural → must wrap Anki in a timed problem bank.** This is exactly the "build on top of Anki" architecture (Anki = declarative layer; our engine = procedural/performance layer).
- Links: https://leananki.com/remember-formulas-using-anki/ ; https://unisium.io/guides/how-study-physics-math-anki

### GRE-math high-scorer consensus (community)
- "Review Stewart's Calculus + do problems"; calc + linear algebra are the high-yield core; abstract algebra/topology/numerical deep cuts are low-yield per hour. Sources: Math StackExchange, mathsub.com.

---

## 0b. GRE deep-dive validation — Pareto, prerequisite graph, KG literature (cross-checked: 2 agents + Claude)

> Full external deep-dive (Claude, with citations + DOIs + mermaid DAG) saved at `research/claude-gre-deepdive.md`. Key refinement from Claude: **calculus + linear algebra ≈ 55–60%** (not 65–70%); **calculus + ALL algebra ≈ 70–75%**. Score is a topic-weighted sum (calculus as multiplier), NOT a min() over prerequisites. Testing effect does not cleanly transfer to math problem-solving (Huang et al. 2023) → lead with worked examples. Knowledge-graph beats flat is shaky under sparse data → ship flat IRT/BKT first, graph as falsifiable v2.

### Pareto claim: PARTIALLY CONFIRMED, MODERATE (not a literal 80/20)
- No official per-topic question counts exist; ETS says weights "vary by edition." Best evidence = crowd-sourced sub-topic estimates + an independent tally of released form GR0568.
- Realistic quantification: **~3–4 of ~12 topic areas (single-var calc, multivar calc, linear algebra, elementary algebra) ≈ 65–75% of questions.** Literal "20% of topics = 80%" is an **overstatement**; defensible framing = **"~30% of topics ≈ ~70% of questions."**
- Long tail (~0–3 questions each): complex analysis, topology, numerical analysis (~0 on released forms), graph theory, prob/stat.
- **"50% calculus" is partly a bucketing artifact:** strict classification of analysis-flavored questions (limits, sequences/series, continuity) as *real analysis* drops calculus to ~38–45% (GR0568 independent tally: ~38% calc / ~33% algebra / ~29% additional). ETS folds analysis into "calculus and its applications."
- Caveat: 3 of 4 commonly-cited released forms (GR8767/9367/9768) predate a 2001 difficulty rescaling → weak evidence for the current test.
- Sources: ETS fact sheet; Rambo GR0568 solutions (http://www.rambotutoring.com/GR0568.pdf); mathsub.com; dzackgarza GRE workshop notes; Cheenta; Math/Academia StackExchange.

### Prerequisite structure: CONFIRMED, STRONG (university curricula + MAA CUPM)
- Proposed DAG (edge = prerequisite-for): PA→SVC; SVC→MVC; (SVC,MVC,LA)→ODE; SVC→LA; (SVC+Proof)→RA; MVC→RA; (RA+MVC)→CA; LA→AA; Proof→{AA,RA}; LA→NA; RA→TOP; LA→NT(partial); Proof→DM.
- **SVC (single-var calculus) = highest out-degree root; LA = secondary hub.** The two highest-frequency exam areas ARE the two structural roots → validates head-weighted, graph-driven study order.
- Sources: Stanford Math flowchart; U. Arizona prereq flowchart; Grinnell sequence; Georgia Tech BS Math; MAA 2015 CUPM Guide.

### Knowledge-graph / prerequisite-modeling literature: STRONG as scaffold, MODEST for raw prediction
- **Supported as representational + pedagogical scaffold, esp. under sparse data:** Knowledge Space Theory (Doignon & Falmagne) → ALEKS; Gagné learning hierarchies → KLI framework (Koedinger, Corbett, Perfetti); prerequisite-aware knowledge tracing.
- **Graph-enabled study tactics have the strongest (often causal, math-specific) evidence:** spacing, interleaving (Rohrer & Taylor 2007; Rohrer 2012; Rohrer, Dedrick & Stershic 2015), worked examples (Sweller & Cooper 1985), retrieval practice.
- **SKEPTICAL FINDING (important):** for *raw predictive accuracy*, flat well-featured models (PFA, logistic regression, IRT, extended BKT) frequently **match or beat** graph/deep models (DKT); explicit expert prerequisite structure often adds little marginal AUC. Refs: Khajah 2016 ("How Deep is Knowledge Tracing?"), Wilson 2016, Xiong 2016, Gervet 2020 ("How/When Does KT Work?").
- Knowledge tracing: Corbett & Anderson (1995) BKT; Piech et al. (2015) DKT.
- **DESIGN IMPLICATIONS (bake into the build):**
  1. The graph's real value = **scheduling, pedagogy, and sparse-data robustness**, NOT necessarily beating flat models on prediction. Pitch it that way (honest).
  2. **Benchmark the graph model against a tuned flat baseline (PFA/IRT)** — this is also literally required by the project (§ "beat a simpler method"). Treat the graph as a *falsifiable hypothesis* refined from data.
  3. **Calibrate the readiness score:** IRT/equating for the point estimate; temperature scaling for probabilities; conformal/CQR intervals; selective abstention under sparse data (KT probabilities are miscalibrated out of the box).
- Score estimation: IRT for ability-from-responses; equating for raw→scaled (200–990); calibration (Brier 1950, ECE), conformal prediction, selective prediction.

### Net effect on the BrainLift (to apply in the merge)
- Soften SPOV 4's "20/80" → "~30% of topics ≈ ~70%, and calc + linear algebra are both the highest-frequency areas AND the prerequisite roots."
- Reframe the knowledge-graph value as scaffolding + sparse-data + scheduling (not a prediction-accuracy silver bullet), and commit to benchmarking it against a flat baseline (satisfies §13 "prove it beats keyword/vector" honestly).

---

## 1. MCAT structure, scoring, psychometrics  *(ALTERNATIVE CONSIDERED — not chosen)*

### AAMC — How is the MCAT Scored?
- No curve; scores are **scaled and equated** across forms so a given scaled score means the same thing regardless of test date/form.
- Each section: number-correct → scaled **118–132** via equating (tailored per form). Wrong answers = unanswered (no penalty).
- **Percentile ranks** updated every May 1 using the most recent 3 years of data.
- Link: https://students-residents.aamc.org/mcat-scores/how-mcat-exam-scored

### MCAT structure (Wikipedia, AAMC-sourced)
- 4 sections, ~7.5 hrs incl. breaks. Computer-based, fixed forms (NOT adaptive).
- Question counts / time:
  - Chemical & Physical Foundations of Biological Systems — 59 Q / 95 min
  - Critical Analysis & Reasoning Skills (CARS) — 53 Q / 90 min
  - Biological & Biochemical Foundations of Living Systems — 59 Q / 95 min
  - Psychological, Social & Biological Foundations of Behavior — 59 Q / 95 min
  - **Total ≈ 230 questions**
- Each section **118–132 (median 125)**; total **472–528 (median 500)**.
- **2024–2025 percentiles:** mean scaled score **500.7**, SD **10.8**. (Full score→percentile table captured: e.g., 500≈48th, 508≈73rd, 515≈91st, 518≈95th, 520≈97th, 522≈99th.)
- Content organized into **10 Foundational Concepts** + **4 Scientific Inquiry & Reasoning Skills (SIRS)**:
  1. Knowledge of Scientific Concepts & Principles  ← the only skill a flashcard directly trains
  2. Scientific Reasoning & Problem Solving
  3. Reasoning about the Design & Execution of Research
  4. Data-based & Statistical Reasoning
- **CARS = 3 reasoning skills, requires NO outside knowledge**; passages 500–600 words, humanities/social sciences, deliberately unfamiliar.
- **Validity:** MCAT predicts USMLE Step 1 (small-to-medium; Bio section most correlated historically). Used as a major admissions metric.
- Link: https://en.wikipedia.org/wiki/Medical_College_Admission_Test

### Implication for our models
- A "finished" deck directly trains **SIRS Skill 1 only** → ~1 of 4 science skills, and **0 of CARS's 3 skills**. CARS ≈ 53/230 ≈ **23% of questions** is structurally untouchable by flashcards.
- Score→percentile table is the backbone of the readiness display (point estimate + range + percentile).
- Fixed (non-adaptive) forms make a calibrated score-mapping more tractable than GMAT.

---

## 2. MCAT tools / what they miss (practitioner evidence)  *(ALTERNATIVE CONSIDERED)*

### Jack Westin — "The Question-First Strategy That 90th Percentile Scorers Use"
- **"The MCAT is not a content exam. It is a reasoning exam that happens to require a foundation of content knowledge."**
- **"Familiarity is not retention. Recognition is not recall."** (passive content review = "the illusion of learning")
- Many 90th-percentile scorers did NOT spend the most time on content review; students who memorized everything (e.g., all amino acids, glycolysis cold) often score ~60th percentile.
- **Three error categories:** content gap / reasoning error / execution error — each needs a *different* fix; more content review does not fix reasoning errors.
- **Key claim:** for students in the **500–510 range, the MAJORITY of wrong answers are reasoning errors, not content gaps** → they keep reviewing content and scores stay flat.
- Recommended split: **70% questions + deep wrong-answer review / 30% targeted content** (inverse of what most students do).
- "Discomfort during practice is the process working" (productive struggle).
- Competitor signal: "JW+ adds adaptive scheduling that tells you which gaps to address after each session."
- Link: https://jackwestin.com/blog/how-to-prepare-for-mcat-without-studying-content/

### Competitive landscape (the market is split in two; nobody owns the bridge)
**Memory-only tools (run on Anki/FSRS — measure recognition recall, stop there):**
- Anki + FSRS: models per-card Difficulty/Stability/Retrievability to a desired retention (default 0.90). "Readiness" proxy = % cards recalled when due — NOT a score. https://faqs.ankiweb.net/what-spaced-repetition-algorithm
- AnKing MCAT (~6,200 cards, AnkiHub; UWorld tagging = cross-reference only, not transfer measurement); MileDown (~2,900), Jack Sparrow (527 creator, question-style cards), Mr. Pankow (Psych/Soc gold standard). All free decks. "Score guarantee: none."
- **Memm** (~$125–339): curated spaced-rep app by 99.9th-pct scorers; "comprehension before memorization" — but still measures only recall, no performance/score. Closest philosophical cousin to our memory layer; stops where our thesis begins. https://memm.io/

**Performance tools (measure passage questions — but don't link back to memory or output calibrated readiness):**
- UWorld QBank (3,000+ Qs, 2 FLs, analytics + peer benchmark; from $339): performance measured, but no memory-state model and "readiness" = raw FL score/vibes, no calibrated estimate. https://gradschool.uworld.com/mcat/question-bank/
- Blueprint (up to ~10 FLs, best analytics): the ONLY vendor with a disclosed accuracy claim — **diagnostic mean diff 0.3 pts, n=91** — but that's *baseline equivalence*, NOT a forward readiness prediction, and **no uncertainty band**. Its FLs deflate ~2–5 pts. https://blueprintprep.com/mcat/score-increases
- Jack Westin (free QBank ~6,700, daily CARS; JW+ $29.99 "adaptive schedule" = time/task mgmt, not memory modeling). 
- AAMC official (FLs $35 ea; only ~5 scored FLs): trustworthy performance + the de-facto readiness anchor (avg of last 2 FLs), but static/sparse, no memory model, no uncertainty, no continuous tracking.
- Khan Academy (free): content delivery; measures essentially nothing.

**THE COMMON GAP (our wedge):** Market splits into two non-communicating halves — memory tools optimize retrievability of isolated facts; performance tools test passage application. **No product models the transfer function between them** ("you recall fact X but fail the passage that needs X"). "Readiness" is everywhere as marketing, nowhere as calibrated measurement. The single accuracy figure that exists (Blueprint 0.3pt, n=91) is for a diagnostic, not a living readiness estimate with uncertainty. → Speedrun = proven memory engine (FSRS) + the two missing layers: (1) memory→performance transfer measurement, (2) calibrated, uncertainty-aware readiness.

### High-scorer strategies (515+/520+/528) — convergent expert + first-person evidence
- **Practice > passive review once a foundation exists:** ~70/30 practice-to-content split (Shemmassian); 8–10 FLs, 40%+ timed practice (ScoreSmarter). "Reviewing them builds your score" (SDN).
- **Deep review of WHY (incl. correct-but-unsure answers):** 2–3 error types cause 60–70% of misses (Jack Westin). Error logs + error-type categorization universal.
- **AAMC materials treated as sacred; normalize 3rd-party FLs** (528 scorer: bombed PR then +16 on AAMC next day). Trust AAMC for prediction.
- **Anki = supplement, not substitute:** "non-negotiable daily" for content/Psych-Soc; **useless for CARS** (consensus). ~20–30% time on Anki, 40–50% on questions.
- **CARS = daily, deeply-reviewed passage practice over months** — but volume alone plateaus (~9 passages/week with deep review > 200 shallow). Spiky: "the doubt you allow with extra time is the problem."
- **Track FL score ladders over time** to gauge readiness (Zach Highley 500→511→513→518 actual).
- **HYPOTHESIS 5 QUANTIFIED (best citation for SPOV1):** Premier MCAT Prep — at 505, content gaps ≈ 35% of misses; by 510+, content gaps drop to 15–20% while **reasoning errors ≈ 40%+** of misses. https://premiermcatprep.com/blog/mcat-score-not-improving
- Spiky high-scorer takes: read fewer content books (528: stopped content books after ~2 months); make your own cards; use LSAT RC for CARS; even 528 needs luck on a few coin-flip questions (not pure method).
- Source quality: mostly convergent expert opinion + n=1 verified accounts (not RCTs); strength = consistency. Anchor claims: Premier's content→reasoning shift + the universal 70/30 practice split & deep-review habit.

---

## 3. Learning science evidence base

### Interleaving (engine of our headline feature)
- The Learning Scientists — "Learn To Study Using… Interleaving": switching between ideas; helps choose the correct strategy (problem solving) and see links/differences; don't switch too often; pair with retrieval.
  - Link: https://www.learningscientists.org/blog/2016/8/11-1
- Rohrer, D., & Taylor, K. (2007). The shuffling of mathematics problems improves learning. *Instructional Science, 35,* 481–498.
- Rohrer, D. (2012). Interleaving helps students distinguish among similar concepts. *Educational Psychology Review, 24,* 355–367.
- Reframe: interleaving = a **discrimination trainer** (builds choose-the-method competence), not just a spacing variant.

### Learning ≠ Performance / desirable difficulties
- Soderstrom & Bjork (2015), *Learning Versus Performance* — in-the-moment performance is a poor (sometimes negative) predictor of durable learning.
  - https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/11/soderstorm_ra_learningvsperformance.pdf
- Bjork & Bjork (2011), *Making Things Hard on Yourself, But in a Good Way* (desirable difficulties; storage vs retrieval strength).
  - https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf

### Retrieval practice / testing effect
- Roediger & Karpicke (2006), *Test-Enhanced Learning* — testing > restudy for long-term retention; students predict the opposite.
  - https://journals.sagepub.com/doi/pdf/10.1111/j.1467-9280.2006.01693.x

### What works, ranked
- Dunlosky et al. (2013) — practice testing + distributed practice = high utility; rereading/highlighting = low.
  - https://www.academia.edu/13564364/Improving_Students_Learning_With_Effective_Learning_Techniques
- Pashler et al. (2008), IES Practice Guide — spacing + interleaving + quizzing by evidence strength.
  - https://ies.ed.gov/ncee/wwc/practiceguide/1

### Knowledge vs generic skills / cognitive load
- Willingham (2007), *Critical Thinking: Why Is It So Hard to Teach?* — "memory is the residue of thought"; critical thinking is domain-specific.
  - https://www.aft.org/sites/default/files/media/2014/Crit_Thinking.pdf
- Sweller (1988) / Kirschner, Sweller & Clark (2006) — cognitive load; explicit guidance beats discovery for novices.

---

## 3b. Readiness predictiveness + calibration methodology

### How predictive are practice tests? (for the readiness point estimate + range)
- **AAMC Full-Lengths are the gold standard.** Chen & Corridon (2020): **median AAMC practice score ↔ real MCAT r = 0.92** (most-recent r=0.79, max r=0.60). Small n (~19), single institution — strong but limited.
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC7780194/ ; https://journals.sagepub.com/doi/10.1177/2382120520981979
- Practitioner consensus on error band: **typical error ≈ ±2–3 pts**, ~70–80% within ±3, >90% within ±5, near-zero bias. Best anchor = **average of last two AAMC FLs** (max/single-test inflate).
- **Third-party FLs systematically UNDERPREDICT** (use with bias correction + wider uncertainty): Blueprint ~+2–5, Kaplan ~+5–10, Princeton Review ~+8–15. (Joel Harris crowdsourced n=844: PR 503 → real ~518.)
  - https://joel.vg/converting-3rd-party-mcat-scores-to-actual-scores/ ; https://www.trevorkleetutor.com/how-accurate-are-aamc-next-step-kaplan-and-princeton-review-mcat-exams/
- ⚠️ Crowdsourced (Reddit/SDN) data is self-selection biased upward (sample means ~515 vs population ~500) → reinforces the "abstain / don't trust thin data" stance.

### Calibration & uncertainty methods (for the honest-score machinery)
- **Calibration of probabilities:** reliability diagrams, Expected Calibration Error (ECE), **Brier score** + log loss (proper scoring rules). Modern models tend to be overconfident; temperature scaling is a cheap fix. (Guo et al. 2017) https://arxiv.org/abs/1706.04599
  - (The project requires a calibration chart + Brier/log loss on held-out reviews — §6 Sunday.)
- **Uncertainty for a score regression (472–528):** prefer **conformal prediction** (distribution-free, guaranteed coverage) and **Conformalized Quantile Regression (CQR)** for adaptive interval widths (narrow with many AAMC FLs, wide with sparse/third-party data).
  - Angelopoulos & Bates, Gentle Intro to Conformal Prediction: https://arxiv.org/abs/2107.07511
  - Romano, Patterson & Candès (CQR) 2019: https://arxiv.org/abs/1905.03222
- **Abstention / "give-up rule" (selective prediction):** risk–coverage trade-off; set a threshold guaranteeing target selective risk. (Geifman & El-Yaniv 2017 https://proceedings.neurips.cc/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf ; SelectiveNet 2019 https://arxiv.org/abs/1901.09192)
  - Maps directly to the project's required give-up rule (abstain when <2 recent AAMC FLs, stale data, OOD inputs, or interval too wide).

### Design recipe (honest readiness score)
- Point estimate: regression anchored on last-2 AAMC FL average (+ provider-bias correction for third-party).
- Range: CQR/split-conformal ~90% interval; width = the "how sure" indicator (bucket Low/Med/High).
- Monitor: empirical interval coverage + Brier/ECE if also emitting categorical probs (e.g., P(≥510)).
- Abstain when data insufficient/stale/OOD.

---

## 4. Anki engine (architecture facts for pedagogy→code mapping)

Cloned: `ankitects/anki` (desktop + shared Rust engine) and `ankidroid/Anki-Android` (phone).

- `repos/anki/rslib/` — Rust backend. `rslib/src/scheduler/` has `queue/`, `states/`, `answering/`, `fsrs/`, `service/`.
- **Queue builder (where our interleaving order lives):** `rslib/src/scheduler/queue/builder/`
  - `gathering.rs` — gathers due/new cards
  - `sorting.rs` — orders the gathered cards (our topic×weakness / interleaving order hooks here)
  - `intersperser.rs` — **Anki ALREADY interleaves new vs. review cards here, but NOT by discipline/topic.** Our change extends this to topic/discipline-aware interleaving — building on the existing mechanism, not bolting on.
  - `sized_chain.rs`, `burying.rs`, `mod.rs`, `entry.rs`, `main.rs`, `learning.rs`, `undo.rs` (undo support — must keep working per §7a).
- **Protobuf:** `proto/anki/scheduler.proto` — add the new message for our queue/mastery call (called from Python per §7a). `proto/anki/ankidroid.proto` exists → AnkiDroid-specific backend messaging is already a pattern.
- `repos/anki/pylib/` (Python bindings), `qt/` (desktop UI), `ts/` (TS UI).
- AnkiDroid consumes the same Rust backend via `rsdroid` → our Rust change ships to the phone through the shared engine (satisfies "two apps, one engine"; rewriting the scheduler in Swift/JS does not count).
