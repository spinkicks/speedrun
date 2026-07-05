# Speedrun BrainLift: An Honest GRE Math App Built on Anki

## Owners
- David Ordonez
- AI collaborator (research + drafting)

---

## Purpose

To articulate why **Speedrun**, though built on Anki's spaced-repetition engine, is a fundamentally different species of study product for the **GRE Mathematics Subject Test**. Anki (and every tool built on it) optimizes one thing: the **retrievability of an isolated fact**. Speedrun treats that as the *cheapest, weakest* signal of exam readiness and adds, on top of Anki's memory chassis, the layers the entire GRE-math market is missing:

1. **Memory → Performance:** memorizing a theorem, formula, or technique ≠ solving a *novel* multi-step problem under time pressure. Speedrun measures that gap instead of hiding it.
2. **Prerequisite-aware Readiness:** math is cumulative, so mastery (and weakness) must **propagate through a topic dependency graph**. A calibrated projection on the 200–990 scale, with a range and a rule for when to abstain.

This does to Anki what Blazing Audio did to Brilliant: concede and build on the proven chassis (spaced repetition / FSRS), then add new integrations (a practice-problem engine, a prerequisite knowledge graph, and an honest readiness model) so the platform is optimized for *actually doing well on the exam*, not just feeling like you remember.

### Why the GRE Math Subject Test (vs. MCAT / GRE General Quant)
- **An almost empty market.** There is no adaptive tool, no calibrated readiness predictor, and **no knowledge-graph product** for this exam, only aging books, free PDFs, and one modest flashcard app. Maximum room to be innovative (a stated project goal).
- **A real prerequisite structure.** Calculus is 50% of the exam *and* the prerequisite for much of the other 50% (real analysis, complex variables, differential equations). This makes a dependency-graph engine genuinely valuable, unlike the flat topic lists of MCAT/General Quant.
- **The headline learning-science feature has native evidence.** The foundational interleaving study (Rohrer & Taylor 2007) is literally about *shuffling mathematics problems*.
- **Objective answers.** Math problems have verifiable correct answers and worked solutions, making AI-card checking and gold sets cleaner than fuzzy fact cards.

### In Scope
- Spiky, defensible points of view on why memorizing math ≠ GRE-math readiness, grounded in Speedrun's actual mechanics (prerequisite-aware/points-at-stake scheduling in the Rust engine, topic interleaving, a practice-problem/transfer bridge, and a calibrated, abstaining readiness model).
- The **pedagogy → engine mapping**: each learning-science principle operationalized in a specific Anki/Rust file or feature.
- A curated knowledge tree of (a) the GRE Math Subject Test's structure/scoring/official content weights, (b) the cognitive-science evidence base, and (c) the (thin) competitive landscape that proves the gap is unfilled.
- **Source-grounded AI via RAG**: practice-problem generation and tutoring where every AI output cites a named source, is checked against a gold set (objective answers + worked solutions), and must beat a keyword/vector baseline. RAG here is a *traceability and honesty* commitment, not a model-benchmark brag.

### Out of Scope
- Whether spaced repetition works at all (the premise of Anki/FSRS is conceded and built upon).
- The "biggest problem bank" race. The argument is about *measurement and sequencing architecture*, not problem count.
- Generic "AI tutor" hype and leaderboard bragging. AI must produce traceable, checked, transfer-building output or it's removed.
- Real efficacy trials / external score-validation that has not been measured. Report only what can be backed up (the project's honesty rule); where data is thin, abstain.

---

## DOK 4: Spiky Points of View

### SPOV 1: Memorizing the math doesn't mean you can do the math; on a problem-solving exam, recognition is counterfeit readiness.
The intuitive study loop is "review until the theorems and formulas feel familiar." But the GRE Math Subject Test is ~66 multi-step problems in 170 minutes (~2.5 min each): it scores *execution on novel problems*, not recall of named results. Knowing the statement of the residue theorem, the conditions for a subgroup, or the formula for arc length is necessary and worthless alone; the score comes from *deploying* them fast under time pressure. Soderstrom & Bjork (2015) explain the trap: in-the-moment recall fluency is a *treacherous* index of durable, transferable skill. High scorers say the same thing in plainer words: a self-reported 970 scorer (*"most of your score will be correlated to your ability to solve calculus and linear algebra problems **fast**"*) and another (*"the test doesn't actually test your maths ability, but rather your ability to do the test."*). In other words, for the GRE specifically, **performance = fast, pattern-recognition execution under a ~2.5-min/question clock**, not depth or proof. So Speedrun separates the two signals on purpose: Anki/FSRS tracks **memory** of theorems/definitions/conditions and "problem-pattern → technique" triggers, while a **timed practice-problem engine** tests whether that remembered technique transfers to a novel problem fast enough to count. Speedrun reports the *gap* between the two. If recall and problem accuracy move together, the app has built nothing; when they diverge (and for math they will), that gap is the most honest readiness signal available.

### SPOV 2: A readiness "score" as one confident number is dishonest; the only honest unit is a calibrated range that abstains when it can't see enough, and on this exam that humility is the whole edge.
Across the entire GRE-math market, no tool outputs a calibrated readiness estimate with uncertainty; "readiness" is at best a raw score on a single official practice test. Speedrun's readiness output is: point estimate + range + % coverage of the official content map + percentile (200–990 scale; any percentile shown only against a **cited** ETS table — we removed unsourced population figures for honesty) + a "how sure" indicator + the single best next action, and **no number at all** below a stated data threshold. This exam *forces* the honesty issue: with only a handful of official practice forms and a small public dataset, naïve point predictions would be guesses in a nice font. So Speedrun leans in: a calibrated point estimate, a **conformal** prediction interval (Romano et al. 2019) that automatically *widens* when data is sparse, and a **selective-prediction abstention rule** (Geifman & El-Yaniv 2017) that returns "insufficient data: here's what to do to unlock a score." Thin data becomes a feature: a system that knows when it doesn't know. Competitive research confirms this is genuinely unoccupied: *every* tool in the space (Math Academy, ALEKS, Khanmigo, Riiid/Santa, the GRE-Math books) shows single confident numbers (XP, mastery %, a predicted score), and **none** report a calibration metric, an interval, or an abstention rule. This is "weaponized honesty": the abstention/calibration machinery (selective prediction, conformalized quantile regression, ECE/Brier, temperature scaling) is standard in ML and essentially absent from ed-tech, making it both a trust differentiator *and* a novel engagement loop (see the calibration self-bet in Flagship Features).

### SPOV 3: Interleaving is not a scheduling tweak; it's the only part of a flashcard app that trains the skill this exam actually tests (choosing the right technique), and for math the evidence is native.
A mixed, 66-question math test punishes the student who can execute a method once told which one to use but can't *recognize* which method a novel problem demands. Blocked practice (all integration, then all linear algebra) trains execution; **interleaved** practice trains *selection and discrimination*. The foundational evidence, Rohrer & Taylor (2007), is literally "the shuffling of *mathematics* problems improves learning," reinforced by Rohrer (2012) on distinguishing similar concepts. Interleaving feels worse in the moment (a desirable difficulty; Bjork & Bjork 2011), which is exactly why students avoid it. Anki already interleaves new vs. review cards (`queue/builder/intersperser.rs`) but is blind to topic; Speedrun extends that mechanism into **topic-aware interleaving in the Rust scheduler**, ships it to desktop and phone via the shared engine, and proves it with the three-build ablation (on / off / plain Anki) at equal study time. A null result is still a real result.

### SPOV 4: A few foundational topics carry most of the score *and* unlock the rest of the curriculum, so study order should follow the prerequisite graph; but the score itself is a weighted sum, not a gate, and the graph is a scaffold, not a prediction silver bullet.
Math is cumulative: single-variable calculus underpins multivariable/vector calculus, sequences/series, ODEs, and real analysis; linear algebra underpins abstract algebra and numerical methods; real analysis underpins complex analysis and topology. Calculus is the dominant root, and it is ~**50%** of the exam, so a weak calculus foundation genuinely caps a large fraction of achievable score. That much is well-supported. But this POV carries three deliberate honesty corrections that the evidence forces (and that make it *more* defensible than the typical "knowledge-graph" pitch):

1. **The concentration is real but "20% → 80%" is an overstatement.** Across released forms, roughly **~30% of topics account for ~70% of questions**. Calculus ≈ 50%; **calculus + all algebra ≈ 70–75%**; **calculus + linear algebra specifically ≈ 55–60%** (not the 65–70% first assumed). The long tail (point-set topology, complex analysis, numerical analysis) is ~0–3 questions each, and "50% calculus" is itself partly a bucketing artifact (analysis-flavored items get folded into calculus). All subtopic counts are *estimates* with high per-form variance.
2. **Score is a topic-weighted sum, not a min() over prerequisites.** Every item is equally weighted and number-right scored, so a weak *tail* topic costs only 1–2 points; only weak *calculus* caps a large share. Speedrun therefore models expected score as a **topic-weighted sum with calculus mastery as a strong multiplier**, and reserves the prerequisite graph for **study sequencing** (where Gagné learning hierarchies and the KLI framework support it), not for score-gating.
3. **A graph model is a scaffold, not a prediction silver bullet.** The knowledge-tracing literature repeatedly shows graph/deep models only *modestly* beat well-tuned flat models (IRT, BKT+), with gains that are data-hungry and often vanish under sparse data (Khajah et al. 2016; Xiong et al. 2016; Gervet et al. 2020); and the high-yield core (calc/LA) is *shallow* in the graph, while the deep chains live in the low-yield tail. So Speedrun ships a **calibrated flat IRT/mastery model first**, and treats the knowledge graph as a **falsifiable v2 experiment that must beat that flat baseline on held-out *score* prediction** before it earns its place. This is exactly the discipline the project's §13 bonus demands ("prove the graph beats keyword/vector search": *prove*, not draw), and it maps onto the Rust change (topic-aware / points-at-stake *sequencing*). The graph's honest value is sequencing, pedagogy, and robustness under sparse data.

### SPOV 5: The best study app is minimal and honest, not feature-rich. Trust is the product.
Students preparing for a high-stakes exam don't need animations, streaks, or a hundred features; they need a crisp tool that tells the truth: here's what you can recall, here's whether it transfers to a real problem, here's your weakest prerequisite, here's your defensible score range, here's the one thing to study next, and here's where there isn't yet enough data to say. Most ed-tech competes on dopamine and feature count; for an exam this consequential, **honesty and clarity are the differentiator, and minimalism is what makes the honesty legible.** A simple app that does exactly what it needs to, and admits what it can't, beats a flashy one that fakes confidence. Distinctive, trustworthy substance out-competes polished sameness.

### SPOV 6: Most AI study tools quietly ship wrong cards; on a math exam (where every answer is CAS-checkable) that is inexcusable, so an unverified AI card simply doesn't exist in Speedrun.
The default "AI for studying" is summarize-and-answer, which strips out the retrieval and reasoning that *cause* learning ("memory is the residue of thought," Willingham). Speedrun inverts this: AI **generates retrieval and transfer opportunities** (novel practice problems targeting a student's weakest prerequisite, variants of missed problems) and every AI output is **grounded in a named source via RAG**, checked against a gold set with a *known correct answer and worked solution*, and must beat a keyword/vector baseline before a student sees it. Math is the ideal domain for this discipline: a generated problem either has the stated answer or it doesn't. AI that can't show its source, can't be verified, or does the thinking for the learner is removed.

### SPOV 7: Maybe train *above* the exam, under the clock, so test day feels slow and easy.
The way I (David) actually got good at math is iteration on problems, specifically grinding problems *harder* than what the test throws, on a timer, until the real thing feels easy by comparison. Most prep does the opposite: it drills at-or-below exam difficulty until in-session accuracy *looks* reassuring (the exact fluency illusion SPOV 1 warns about). For a **timed** exam (the GRE Math Subject Test is ~2.5 min/question, and *timing is the dominant failure mode high scorers report*), I believe that's backwards. So Speedrun includes an **"overtrain" mode**: above-exam-difficulty, strictly-timed sets layered on top of normal practice. **Honesty caveat (this is my belief, not settled science):** training under harder/timed conditions is supported by desirable-difficulties research, but pure *overlearning* has weak long-term evidence (Rohrer & Taylor 2006), so this is an explicit **Tier-2 experiment**, validated by ablation (overtrain on/off at equal study time, scored on *real*-difficulty held-out problems) before the claim is made.

### SPOV 8: Motivation is a *product* of success, not its prerequisite, so the app engineers competence, not hype.
The seductive story is "motivate the student and learning follows." The evidence runs the other way. Garon-Carrier et al. (2016, *Child Development*, n=1,478, grades 1–4) found math **achievement predicted later intrinsic motivation, but motivation did not predict later achievement**; as Kirschner, Hendrick & Heal put it in *Instructional Illusions* (p.52), "we have the causal arrow the wrong way round"; motivation is a developmental construct "progressively crystallized through experiences of achievement." So Speedrun does **not** chase motivation with streaks, badges, or hype (consistent with SPOV 5's anti-features); it manufactures the thing that *actually* produces motivation, repeated and visible **experiences of competence**: calibrated practice the student gets right more and more, an honest readiness number that visibly climbs, and a clear single "next best thing" that keeps success within reach. The loop is *succeed → feel competent → want more → succeed more.* And there's a meta-motivator unique to an *honest* tool: a student who genuinely trusts the app is measuring and improving their real score will use it more than a flashier app they don't believe: **trust is itself motivating.**

### SPOV 9: The knowledge to ace this exam is already free and everywhere; the real problem is that it's *scattered*, and fragmentation taxes working memory, so coherent consolidation is genuine value, not mere convenience.
Every theorem, technique, and practice problem for the GRE Math Subject Test already exists across textbooks, PDFs, forums, and videos, so why build anything? Because *scattered* knowledge imposes **extraneous cognitive load**: jumping between mismatched sources, notations, and formats fragments attention (the **split-attention effect**; Sweller's Cognitive Load Theory), and working memory spent reconciling sources is working memory *not* spent learning math. Speedrun's value isn't new information; it's **coherence**: one consistent notation, one prerequisite-ordered path, one place where memory, practice, and readiness live together, so extraneous load drops and the student's limited working memory goes to actual problem-solving. (This *complements* the core thesis: consolidation lowers load, while the honest memory→performance→readiness engine is still the differentiator, not the aggregation itself.)

---

## Experts

### Robert & Elizabeth Bjork
- **Who:** UCLA Learning & Forgetting Lab; originators of "desirable difficulties" and storage-vs-retrieval-strength.
- **Focus:** Why effortful, error-prone practice (spacing, interleaving, testing) yields durable, transferable skill; learning ≠ performance.
- **Why follow:** Theoretical engine for SPOV 1, 2, 3: distrusting fluency and making practice harder is the point.
- **Where:** https://bjorklab.psych.ucla.edu

### Doug Rohrer
- **Who:** Cognitive psychologist (Univ. of South Florida); leading interleaving researcher *in mathematics*.
- **Focus:** Interleaved problem practice improves discrimination, technique selection, and transfer.
- **Why follow:** The native empirical backbone of SPOV 3 (headline feature + Rust change).
- **Where:** Rohrer & Taylor (2007), *The shuffling of mathematics problems improves learning*; Rohrer (2012).

### Henry Roediger III & Jeffrey Karpicke
- **Who:** Memory researchers (Washington University); *Make It Stick* (Roediger).
- **Focus:** The testing effect: retrieval is a more potent learning event than restudy.
- **Why follow:** Justifies the retrieval-first loop and the practice-problem engine (SPOV 1, 6).
- **Where:** Roediger & Karpicke (2006), *Psychological Science*.

### Yana Weinstein & Megan Sumeracki (The Learning Scientists)
- **Who:** Cognitive psychologists; *Understanding How We Learn*.
- **Focus:** Operationalizing the six core strategies (retrieval, spacing, interleaving, elaboration, dual coding, concrete examples).
- **Why follow:** Practitioner-ready translation of the strategies built into the engine.
- **Where:** https://www.learningscientists.org

### Daniel Willingham
- **Who:** Cognitive scientist (UVA); *Why Don't Students Like School?*
- **Focus:** Knowledge vs. generic skills; "memory is the residue of thought"; expertise is domain-specific.
- **Why follow:** Grounds SPOV 6 (AI should make students think) and the "content is prerequisite, but must be applied" framing.
- **Where:** Willingham (2007), *Critical Thinking: Why Is It So Hard to Teach?*

### John Sweller & Paul Kirschner
- **Who:** Originator of Cognitive Load Theory (Sweller); co-author of the case against minimal guidance (Kirschner), and co-author of *Instructional Illusions*.
- **Focus:** Working-memory limits; the split-attention effect; why explicit, worked-example-based instruction beats discovery for novices, directly relevant to learning math procedures.
- **Why follow:** The mechanism beneath worked examples and scaffolding (how problems are presented), and beneath SPOV 9 (scattered sources raise extraneous load).
- **Where:** Sweller (1988); Kirschner, Sweller & Clark (2006); Kirschner, Hendrick & Heal, *Instructional Illusions*.

### Anastasios Angelopoulos & Stephen Bates / Chuan Guo et al.
- **Who:** Conformal-prediction educators; calibration researchers.
- **Focus:** Distribution-free uncertainty intervals; calibration (ECE, Brier, temperature scaling); selective prediction.
- **Why follow:** The machinery behind SPOV 2's honest, abstaining readiness model, essential given thin GRE-math data.
- **Where:** Angelopoulos & Bates (2023), arXiv:2107.07511; Guo et al. (2017), arXiv:1706.04599; Geifman & El-Yaniv (2017).

### ETS (the exam-maker)
- **Who:** Educational Testing Service.
- **Focus:** Official GRE Math Subject Test structure, scoring/equating, percentile interpretive data, and (uniquely for this exam) an **official content-weight breakdown** (Calculus 50% / Algebra 25% / Additional Topics 25%).
- **Why follow:** Ground truth for the readiness scale, the coverage map, and the prerequisite/Pareto structure the thesis rests on.
- **Where:** https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html ; https://www.ets.org/content/dam/ets-india/pdfs/gre/fact-sheet-math.pdf

### Justin Skycak (Math Academy): the closest analog, to learn from *and* differentiate against
- **Who:** Chief Quant / Director of Analytics at Math Academy; author of *The Math Academy Way* (~400 pp, heavily referenced).
- **Focus:** A hand-built **knowledge graph** (~2,500 topics with "encompassing weights") + **mastery learning/layering** + **"Fractional Implicit Repetition" (FIRe)**: spaced repetition where reps "trickle down" the graph to implicitly-practiced prerequisites, with repetition compression. The existing realization of "knowledge graph + SRS for math."
- **Why follow:** Proves the pedagogy works at scale and is the design north star for the graph/sequencing, but it has **no exam product, no uncertainty/calibration/abstention, is closed-source, not on Anki, and uses classical ML (no LLM/RAG)**. Those four gaps are precisely Speedrun's white space.
- **Where:** https://www.justinmath.com/files/the-math-academy-way.pdf ; https://www.mathacademy.com/how-our-ai-works ; https://www.justinmath.com/individualized-spaced-repetition-in-hierarchical-knowledge-structures/

---

## DOK 3: Insights

- **Insight 1: The "I remember this theorem" feeling is an anti-signal for problem readiness.** Recall fluency is exactly the variable that fails to predict whether a student can execute a novel multi-step problem in 2.5 minutes. The app should de-emphasize the signal students find most reassuring.

- **Insight 2: Memory and performance are different objects, and on math the gap is unusually wide.** Anki/FSRS handles memory of declarative content (theorem hypotheses, definitions, named results, standard integrals); a separate problem engine must handle procedural transfer. Conflating them is the design error this app exploits.

- **Insight 3: Prerequisites govern study *order*, but the score is a weighted sum, not a gate.** Number-right scoring means a weak tail topic costs 1–2 points while weak calculus caps a large share, so model expected score as a calculus-weighted topic sum, and use the prerequisite graph for sequencing (Gagné/KLI), not for score-gating.

- **Insight 4: The Pareto is real but moderate, and partly definitional.** ~30% of topics ≈ ~70% of questions; calculus ≈ 50% (its dominant root), calculus + all algebra ≈ 70–75%, calculus + linear algebra ≈ 55–60%. "50% calculus" is partly a bucketing artifact (analysis folded into calculus). The honest pitch is "a handful of foundational topics carry ~70% of the score *and* unlock the rest", not a literal 80/20.

- **Insight 9: Lead with worked examples; don't assume the testing effect transfers to math procedures.** Worked examples (Sweller & Cooper 1985) and interleaving (Rohrer et al. 2020, d≈0.83) have strong math-native evidence, but retrieval-practice gains do *not* cleanly transfer to math problem-solving (Huang et al. 2023). So the pedagogy is worked-examples → interleaved + spaced practice, with retrieval used for the declarative layer, not as the sole driver of procedural skill.

- **Insight 10: The knowledge graph must earn its place against a flat baseline.** The KT literature shows flat IRT/BKT often matches graph/deep models, especially under sparse data. Treating the graph as a falsifiable hypothesis benchmarked against a tuned flat model isn't a hedge; it's exactly the rigor the project rewards (and the only honest way to claim §13's "graph beats keyword/vector").

- **Insight 5: Interleaving is a discrimination trainer, and this exam is a discrimination test.** A 66-problem mixed exam rewards recognizing *which* technique applies. Interleaving builds exactly that competence, and the evidence base is math-native.

- **Insight 6: Thin external data makes abstention a feature, not an apology.** With few official practice forms and a small public dataset, the honest move is calibrated uncertainty + a give-up rule. Supplementing with generated/curated problems widens the anchor without faking precision.

- **Insight 7: Objective answers make AI verifiable.** Unlike fuzzy fact cards, a generated math problem has a checkable answer and a worked solution, so the RAG-grounded generator can be held to a hard, measurable gold-set bar.

- **Insight 8: Productive struggle is a feature, but not a spiky one.** Difficulty that feels bad in the moment (free recall, novel problems, interleaving) predicts better outcomes; well-established, so the app builds it in without claiming it as contrarian.

- **Insight 11: "Weaponized honesty" is an unoccupied position *and* a growth loop.** Competitive research confirms no ed-tech tool shows calibration/abstention; turning that machinery into a daily *calibration self-bet* converts the honesty thesis from a defensive virtue into the engagement flywheel, while measuring overconfidence, the exact failure mode the timed GRE punishes.

- **Insight 12: Distractors should be correct-by-construction wrong answers tied to named misconceptions.** Generating wrong options by executing *buggy rules* in the CAS (Brown & Burton's BUGGY/Repair Theory) makes every distractor diagnostic (it tells *which* misconception a student holds) rather than a random foil. This turns the AI layer into a misconception detector, not just a problem printer.

---

## Flagship Features (the creative payload)

The bold, mostly-novel mechanics that make Speedrun unlike anything in the market. They stack into one narrative: **measure honestly → refuse to fake it → make the user bet against their own overconfidence → expose the recall-vs-use gap → harden understanding with counterexamples.** Each maps to a SPOV and to where it lives (per `docs/ARCHITECTURE.md`). Ranked by novelty × impact × 1-week-MVP feasibility.

1. **Three-number honesty dashboard** *(SPOV 1, 2)*: Memory / Performance / Readiness shown **separately**, each with a calibrated interval (not a blended number). The thesis made visible; no competitor has it. *App layer + read RPC.* — ✅ *now has a live **readiness gauge** on Home (pure-SVG, both platforms, honest abstain).*
2. **Abstention UX** *(SPOV 2)*: below the data threshold, the Readiness panel shows **"INSUFFICIENT DATA: answer 12 more calculus items to unlock"**, not a fake score. Cheapest, most differentiating trust signal. *App layer.*
3. **Calibration self-bet** *(SPOV 2, 5)*: before each reveal, the user states P(correct); the app scores it with Brier/ECE and shows an "overconfidence tax." The honesty machinery becomes the daily engagement loop. *App layer + tiny confidence field.* — ✅ *now has a live **calibration reliability diagram** on Memory (pure-SVG, both platforms).*
4. **Memory→Performance gap meter** *(SPOV 1)*: per topic, the explicit delta between flashcard recall and timed novel-problem accuracy ("you remember it but can't use it yet"). *App-layer analytics.* — ✅ *now has a live **gap slope chart** on Memory (pure-SVG, both platforms).*
5. **Counterexample gauntlet** *(SPOV 6)*: auto-generated "Is this always true?" claims; on rejecting, the user must produce/pick a counterexample. CAS-verifiable; trains the maturity static books can't. *RAG/LLM service + CAS.*
6. **Points-at-stake, topic-aware interleaving** *(SPOV 3, 4; the Rust change)*: the queue orders by exam point-value × prerequisite centrality × current weakness, interleaved so consecutive items need different strategies. *Rust core (`scheduler/queue/builder/`).*
7. **Prerequisite-DAG "blast radius" diagnosis** *(SPOV 4)*: tap a weak node → see every downstream topic it caps. The graph used for *diagnosis/sequencing* (its defensible strength), not score-gating. *App layer + read RPC.* — ✅ **SHIPPED 2026-07-03 as The Map (`/speedrun-map`)** — interactive tap→blast-radius, pure-SVG, both platforms.
8. **Adversarial sibling problems + mal-rule distractors** *(SPOV 3, 6, Insight 12)*: near-identical twins where one changed condition flips the method; wrong options computed from buggy rules (Brown & Burton). Defeats pattern-matching; diagnoses misconceptions. *RAG/LLM + CAS.*
9. **The encoded 99th-percentile playbook** *(SPOV 4, 5)*: defaults distilled from top-scorer accounts: calculus-first weighted plan; **stereotyped-pattern decks** for the low-yield tail (complex analysis = Cauchy-Riemann + residue; etc.); timed **"mock-pace" interleaving at ~2.5 min/q**; auto **error-log → spaced review**; **conserved-mock** readiness (don't burn the ~6 released forms early); a **formula/shortcut card type**; and a **coverage/triage dashboard** that warns against over-studying low-yield topics. *App layer + content.*
10. **Overtrain mode** *(Tier-2, SPOV 7)*: above-exam-difficulty, strictly-timed problem sets layered on normal practice, so test day feels slow and easy; validated by ablation before the claim is made. *App layer + content.*

> Anti-features (deliberate omissions, per SPOV 5): no vanity streaks, no dopamine gamification, no single confident "you're 87% ready" number. Replace the streak with a *calibrated growth* signal and rank by calibration quality, not raw score.

---

## DOK 2: Knowledge Tree

### Category 1: The GRE Math Subject Test as a measurement target
**Subcategory 1.1: Structure & scoring**
- Source: ETS, Subject Test content & structure; Math fact sheet; interpretive data (Table 2B)
  - DOK 1, Facts: **~66 multiple-choice questions, 170 minutes**, one continuous block, 5 choices each; number-right scoring then equated. **Scale 200–990 (10-pt increments).** Median ≈ **680 = 50th percentile**; **~880 = 90th**; mean ≈ 680, SD ≈ 161. Computer-delivered, offered 3×/yr, **5-year** validity. **~5,000 takers/year** (vs. ~930k General Quant).
  - DOK 2, Summary: A numeric-scale, fixed-form exam with a published score→percentile mapping (so a calibrated readiness *range* is meaningful), but a small population and few official forms (so external validation is thin → abstention matters).
  - Links: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html ; https://www.ets.org/content/dam/ets-india/pdfs/gre/fact-sheet-math.pdf ; https://en.wikipedia.org/wiki/GRE_Mathematics_Test

**Subcategory 1.2: Official content weights (the coverage map + Pareto core)**
- Source: ETS Math fact sheet (official category weights)
  - DOK 1, Facts: **Calculus 50%** (single/multivariable differential & integral calc + applications, coordinate geometry, trig, ODEs). **Algebra 25%** (elementary, **linear algebra**, **abstract algebra**: groups/rings/fields, **number theory**). **Additional Topics 25%** (intro **real analysis**; **discrete math**: logic, set theory, combinatorics, graph theory, algorithms; plus topology, geometry, complex variables, probability/statistics, numerical analysis).
  - DOK 2, Summary: Official weights give a real coverage map and a defensible high-yield core (calc + linear algebra ≈ 55–60%; calc + all algebra ≈ 70–75%). The coverage map drives the abstain-below-the-line rule.
  - Link: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html

**Subcategory 1.3: Prerequisite (dependency-graph) structure**
- Source: ETS content map + standard math curriculum dependencies
  - DOK 1, Facts: single-var calc → multivar/vector calc; calc + limits/sequences → real analysis; linear algebra → abstract algebra + numerical analysis; calc → complex variables + ODEs; set theory/logic → discrete math + topology.
  - DOK 2, Summary: A genuine prerequisite DAG, with calculus as the dominant root node. Foundation for the readiness graph and points-at-stake scheduling (SPOV 4).

### Category 2: The competitive landscape & the empty market
- Source: Tool-landscape research (see `research/research-notes.md` + `research/claude-innovation landscape plus bold ideation.md`)
  - DOK 1, Facts: GRE *General* Quant market is saturated (ETS PowerPrep, Magoosh, Manhattan, GregMat, Khan). The **Subject Test** market is nearly empty: ETS Math Practice Book (1 full test PDF), historical released forms (GR0568/GR1768), dated books (Princeton Review; REA, widely criticized), academic PDFs (Ian Coley bootcamp, Charles Rambo, mathsub.com), and one modest non-adaptive app (Varsity Tutors). No comprehensive maintained Anki deck.
  - DOK 2, Facts: **No adaptive engine, no calibrated readiness predictor, and no knowledge-graph/prerequisite tool exists for the Subject Test.** Largest unmet need in the landscape; Speedrun's wedge.
  - Links: https://www.mathsub.com/resources/ ; https://sites.math.rutgers.edu/~iacoley/gre/lecture-notes.pdf ; https://www.rambotutoring.com/GREpractice.pdf
- Source: Math Academy (Skycak), the closest analog
  - DOK 1, Facts: ~2,500-topic hand-built knowledge graph with "encompassing weights"; mastery learning + layering; **Fractional Implicit Repetition (FIRe)** = reps trickle down the graph to implicitly-practiced prerequisites + repetition compression; adaptive diagnostic estimating a "knowledge frontier." $49/mo, no free tier. Closed-source; classical ML (no LLM/RAG); thin proof coverage (criticized by Matuschak, Nova, Pershan).
  - DOK 2, Summary: Proves "knowledge graph + SRS for math" works and is the design north star, but has **no exam product, no uncertainty/calibration/abstention, isn't open/Anki-based, and uses no LLM/RAG**. Those four gaps are Speedrun's white space.
  - Links: https://www.mathacademy.com/how-our-ai-works ; https://www.justinmath.com/individualized-spaced-repetition-in-hierarchical-knowledge-structures/
- Source: Broader competitor matrix (ALEKS, Khanmigo, Korbit, RevisionDojo, Riiid/Santa, Duolingo Max)
  - DOK 1, Facts: ALEKS (Knowledge Space Theory; math/chem/stats; no GRE-subject, no SRS memory model, no uncertainty); Khanmigo (GPT-4 Socratic tutor; not GRE-subject; guidance-only); Riiid/Santa (knowledge tracing + score prediction, but English tests only, closed); Duolingo Max (gamified SRS + GPT-4; language only). KT reality check: simple IRT/BKT+ are competitive with deep KT, esp. on small data (Gervet 2020) → flat readiness model is right for a ~5k/yr niche.
  - DOK 2, Summary: **Verdict: the intersection (GRE-Math-Subject × open Anki/FSRS × three calibrated scores with abstention × one engine desktop+mobile × points-at-stake DAG interleaving) is genuinely unoccupied.** The nearest neighbor (Math Academy) is missing four of the five.
  - Links: https://www.aleks.com/about_aleks/knowledge_space_theory ; https://theophilegervet.github.io/assets/pdf/gervet2020deep.pdf

### Category 3: Why effortful learning works
- Source: Sweller (1988), CLT; Kirschner, Sweller & Clark (2006)
  - DOK 1, Facts: Working memory is capacity/duration-limited; long-term memory is effectively unlimited. **Worked examples** reduce extraneous load for novices; minimally-guided/discovery instruction is consistently beaten by explicit guidance (faded as expertise grows).
  - DOK 2, Summary: Teach procedures with worked examples and scaffolding, then fade; directly applicable to how math techniques are presented.
  - Links: https://onlinelibrary.wiley.com/doi/10.1207/s15516709cog1202_4 ; https://research.ou.nl/ws/files/1015152/Why%20minimal%20guidance%20during%20instruction%20does%20not%20work.pdf

### Category 4: Retrieval, spacing, desirable difficulties
- Source: Roediger & Karpicke (2006); Bjork & Bjork (2011); Soderstrom & Bjork (2015); Dunlosky et al. (2013); Pashler et al. (2008)
  - DOK 1, Facts: Testing >> restudy for retention (students predict the opposite). Spacing/interleaving/testing slow apparent acquisition but improve retention/transfer; performance during practice is a poor predictor of durable learning. Practice testing + distributed practice = highest-utility techniques; IES recommends spacing + interleaving + quizzing.
  - DOK 2, Summary: The effortful, unpleasant-feeling techniques win and underpin SPOV 1–3.
  - Links: https://journals.sagepub.com/doi/pdf/10.1111/j.1467-9280.2006.01693.x ; https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/11/soderstorm_ra_learningvsperformance.pdf ; https://ies.ed.gov/ncee/wwc/practiceguide/1

### Category 5: Interleaving & transfer (the headline feature; native math evidence, incl. RCT)
- Source: Rohrer & Taylor (2007); Rohrer (2012); Rohrer, Dedrick & Stershic (2015); Rohrer, Dedrick, Hartwig & Cheung (2020)
  - DOK 1, Facts: Interleaving (shuffling) *mathematics* problems improves delayed-test learning and helps students *choose the correct strategy* and *distinguish similar concepts*. Rohrer et al. (2015): heavier interleaving → higher delayed scores; mechanism = better discrimination **and** stronger problem→strategy association. **Rohrer et al. (2020), preregistered cluster RCT (787 students): interleaved practice 61% vs. 38% blocked on an unannounced test one month later, d ≈ 0.83** (meets WWC standards). Caveat: interleaving was confounded with spacing (synergistic).
  - DOK 2, Summary: The strongest, math-native, causal evidence for the headline feature: interleaving = a discrimination/strategy-selection trainer. Maps to topic-aware interleaving in the Rust queue; pair with spacing.
  - Links: https://doi.org/10.1037/edu0000367 ; https://www.learningscientists.org/blog/2016/8/11-1

### Category 6: Knowledge vs. generic skills / why math compounds
- Source: Willingham (2007)
  - DOK 1, Facts: Reasoning depends on domain knowledge in long-term memory; automated background knowledge frees working memory ("memory is the residue of thought").
  - DOK 2, Summary: Automaticity on foundational procedures (calculus!) frees working memory for the hard, novel parts: the cognitive basis of the prerequisite-graph thesis (SPOV 4) and SPOV 6.
  - Link: https://www.aft.org/sites/default/files/media/2014/Crit_Thinking.pdf

### Category 6b: Motivation follows achievement
- Source: Garon-Carrier et al. (2016), *Child Development*; Kirschner, Hendrick & Heal, *Instructional Illusions* (p.52)
  - DOK 1, Facts: Longitudinal study (n=1,478, grades 1–4): math achievement predicted later intrinsic motivation, but motivation did not predict later achievement. Motivation is "progressively crystallized through experiences of achievement"; "the causal arrow [is] the wrong way round."
  - DOK 2, Summary: Engineer *success experiences*, not hype; competence generates the motivation, not vice versa. Grounds SPOV 8 and the anti-gamification stance.

### Category 7: Honest readiness, score estimation, calibration & abstention (under thin data)
- Source: Lord (1980); Hambleton et al. (1991); Embretson & Reise (2000); IRT/equating
  - DOK 1, Facts: GRE math is **number-right scored then equated** to 200–990 (released forms include raw→scaled tables; identical raw scores map to different scaled scores across forms). IRT estimates ability θ from item responses: 1PL/Rasch (difficulty), 2PL (+discrimination), **3PL (+guessing c≈0.2, apt for 5-choice MC)**. Mean ≈ 680, SD ≈ 161 (2021–24); 880 ≈ 88th pct (90th ≈ 890).
  - DOK 2, Summary: A principled point-estimate path: fit an IRT/mastery model, map θ→scaled score via equating-style conversion. This is the flat baseline the graph must beat.
- Source: Guo et al. (2017); Angelopoulos & Bates (2023); Romano et al. (2019); Geifman & El-Yaniv (2017); El-Yaniv & Wiener (2010)
  - DOK 1, Facts: Calibration via reliability diagrams, ECE, **Brier**/log loss; models are often overconfident (temperature scaling helps). Uncertainty via **conformal prediction** (distribution-free coverage) and **CQR** (adaptive widths). Selective prediction sets an abstention threshold via the risk–coverage trade-off.
  - DOK 2, Summary: The machinery for SPOV 2: calibrated estimate + conformal range that widens with sparse data + principled give-up rule. With ~66-item forms and sparse per-user data, intervals will be **wide and abstention frequent**; that's honest, and the UI must communicate it, not hide it. The anchor is also *supplemented* with curated/generated problems.
  - Links: https://arxiv.org/abs/1706.04599 ; https://arxiv.org/abs/2107.07511 ; https://arxiv.org/abs/1905.03222 ; https://proceedings.neurips.cc/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf

### Category 7b: Prerequisite modeling & knowledge tracing, graph vs flat (the honest case)
- Source: Doignon & Falmagne (1985) / Sun et al. (2021) ALEKS meta-analysis; Corbett & Anderson (1995) BKT; Piech et al. (2015) DKT; Nakagawa et al. (2019) GKT; Chen et al. (2018) PDKT; Koedinger et al. (2012) KLI; Gagné (1968)
  - DOK 1, Facts: Knowledge Space Theory underpins ALEKS; meta-analysis (56 effect sizes, 9,238 students): ALEKS ≈ traditional instruction standalone (g=0.05) but strong as a **supplement** (g=0.43). Graph-based KT (GKT) beats DKT by ~6.25% relative AUC with ~10× fewer params, but on within-system *next-item* prediction with large data. **Disconfirming:** Khajah et al. (2016) "how deep is knowledge tracing?" (BKT+ matches DKT); Xiong et al. (2016) found dataset duplication inflated DKT's edge; Wilson et al. (2016) Bayesian IRT can beat DKT; Gervet et al. (2020) deep models win only with large, richly-structured data.
  - DOK 2, Summary: Prerequisite/graph structure is well-supported as a **pedagogical/sequencing scaffold** (esp. as a supplement, this regime) but **only modestly, and unreliably, better for raw prediction**. → Ship a calibrated flat IRT/BKT model first; treat the graph as a falsifiable v2 experiment benchmarked against it on held-out *score* prediction (SPOV 4, Insight 10).
  - Links: https://doi.org/10.1080/19477503.2021.1926194 ; https://arxiv.org/abs/1604.02416

### Category 8: Anki/SRS fit for math (honest assessment)
- Source: Math-Anki practitioner write-ups (see research notes §E)
  - DOK 1, Facts: Anki is a memorization/retention engine, not a problem-solving trainer. Strong card targets: theorem statements **with hypotheses/conditions**, definitions, named results, standard derivatives/integrals, Taylor series, residue theorem, counterexamples (LaTeX/MathJax, cloze). Weak target: memorizing whole problems (long reviews, false mastery). Calculus (50%) is largely procedural → must be trained with timed problems.
  - DOK 2, Summary: Use Anki for the declarative layer; wrap it in a problem engine for the procedural layer. Validates the "build on top of Anki" architecture.
  - Links: https://leananki.com/remember-formulas-using-anki/ ; https://unisium.io/guides/how-study-physics-math-anki
- Source: Sweller & Cooper (1985); Huang et al. (2023); Leahy, Hanham & Sweller (2015)
  - DOK 1, Facts: Worked examples halve solving time and cut errors ~5× vs. conventional problem-solving for algebra novices (transfer to varied problems is muted). The **testing/retrieval effect does NOT cleanly transfer to math problem-solving**: Huang et al. (2023) found example–test pairs did not beat restudy on delayed problem-solving; high element-interactivity material can fail to show a testing effect (Leahy et al. 2015).
  - DOK 2, Summary: For the *procedural* layer, lead with **worked examples → interleaved + spaced practice**; use retrieval/Anki for the *declarative* layer, not as the sole driver of problem-solving skill (corrects a naïve "just drill retrieval" assumption).
  - Links: https://doi.org/10.1207/s1532690xci0201_3 ; https://doi.org/10.3389/fpsyg.2023.1093653

### Category 8b: Cognitive load & consolidation
- Source: Sweller, split-attention effect / extraneous load (Sweller 1988; Sweller, Ayres & Kalyuga 2011)
  - DOK 1, Facts: Splitting attention across multiple, mutually-referring sources imposes extraneous cognitive load; integrating sources (one coherent presentation) reduces it and improves learning for novices.
  - DOK 2, Summary: Scattered GRE-math resources fragment working memory; consolidating into one coherent notation/path lowers extraneous load. Grounds SPOV 9 (consolidation is genuine value, complementing the measurement thesis).

### Category 9: Our engine (pedagogy → code)
- **9.1 Prerequisite-aware *sequencing* / points-at-stake → Rust scheduler.** `repos/anki/rslib/src/scheduler/queue/builder/`: extend `sorting.rs`/`gathering.rs` to order due cards by **topic centrality (graph leverage) × student weakness**, and extend `intersperser.rs` for **topic-aware interleaving**; add a new message in `proto/anki/scheduler.proto` called from Python; preserve `undo.rs`. (The graph drives study *order*, where Gagné/KLI support it.) Ships to phone via the shared Rust backend (AnkiDroid `rsdroid`).
- **9.2 Memory model (honest) → FSRS layer.** FSRS retrievability over theorem/definition/technique cards; surfaced with a range + give-up rule (never as "readiness").
- **9.3 Memory→performance bridge → practice-problem engine.** Serve novel problems mapped to the technique each card trains; lead with worked examples; compare card recall vs. problem accuracy; report the gap (the §7d paraphrase/transfer test, math version).
- **9.4 Readiness → FLAT calibrated model first, graph as falsifiable v2.** Ship a calibrated **flat IRT/mastery model** (expected score = calculus-weighted topic sum, *not* a min() gate) with conformal intervals on 200–990 + Brier/calibration monitoring + selective abstention; anchor supplemented with curated/generated problems. The **prerequisite-graph readiness model is a v2 experiment that must beat the flat baseline on held-out *score* prediction** before adoption (Insight 10).
- **9.5 Coverage map → ETS official weights.** Mark covered vs. uncovered topics against Calc 50% / Algebra 25% / Additional 25%; abstain below the coverage line.
- **9.6 Source-grounded AI → hybrid neuro-symbolic pipeline (external service).** **LLM proposes a symbolic schema → SymPy instantiates + verifies the answer (symbolic `simplify(diff)==0` + random-point numerical backstop, ε≈10⁻⁹) → RAG-grounds to a named source (hybrid BM25+dense → RRF; a cross-encoder rerank was scoped but skipped) → hard gold-set gate before display.** Distractors computed from **mal-rules** (Brown & Burton BUGGY) so each is a diagnostic, correct-by-construction wrong answer. Safety: prompt-injection defense (spotlighting/data-instruction separation), contradiction detection, leakage check (MinHash/LSH + 13-gram). Generated cards import as notes and sync down; **AI-off ships a curated human-verified bank** so the app works with AI disabled. Lean/proof-assistant lane optional/best-effort only.
  - **Eval (pre-registered §7f cutoffs):** 50 gold pairs; wrong-answer rate ≤2% (target 0 post-gate), correct-&-useful ≥80%, correct-but-bad-teaching ≤15%, leakage 0; full RAG must beat the better baseline by ≥5 pts Recall@10. Wrong-answer >0 post-gate ⇒ halt and fix the verifier. **Honest outcome (2026-07-05):** wrong-answer **0%** and leakage **0** met; the **≥5-pt RAG margin was NOT met — hybrid ties the baselines at 0.900 Recall@10** (small curated corpus saturates), so we report non-regression + the SymPy-verifier safety win, not a retrieval beat. See `docs/RESULTS.md`.

### Category 10: Multi-exam extensibility (exam-profile abstraction), groundwork for GRE Physics
- Source: GRE Physics + extensibility research (`research/claude-GRE Physics plus multi-exam extensibility.md`)
  - DOK 1, Facts: GRE Physics is a viable second module (post-2023: ~70 Q, 120 min, 200–990, rights-only, computer-delivered; CM 20% / E&M 18% / QM 13% / …; mean 724, SD 167). It shares heavy **math machinery** with GRE Math (single/multivariable calc, linear algebra, ODEs/PDEs, vector calc, Fourier); only the *physics content* differs. ⚠️ Never hard-code structural numbers (the spec's "100 q / 170 min / ¼-penalty" for Physics is stale): read from config.
  - DOK 2, Summary: Adopt an **"exam profile"** split now: **exam-specific data** (topic taxonomy, prerequisite DAG, content weights, scoring/percentile tables, item pools, timing, scoring rule, abstention thresholds) vs. **shared engine** (scheduler, FSRS, IRT/calibration, interleaving, readiness display, sync, RAG). A **shared math-node layer** lets a math node mastered in the Math module satisfy the same prerequisite in Physics (transfer credit). Adding Physics later = ship new data files + an `ExamProfile` record, no engine change. Caveat: worked examples in physics must integrate diagram+equation+text (Sweller 2023 split-attention).
  - Links: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html ; https://link.springer.com/article/10.1007/s10648-023-09817-2

---

## Appendix: How this BrainLift maps to the project rubric
- **Rust change (20%)** ← SPOV 4 / KT 9.1 (prerequisite-aware points-at-stake + topic interleaving queue).
- **Score accuracy + honest uncertainty (20%)** ← SPOV 2 / KT 7 + 9.4 (flat IRT + conformal range + abstention; supplemented anchor).
- **Study feature on learning science (15%)** ← SPOV 3 (interleaving ablation, math-native RCT evidence, d≈0.83).
- **AI checking & safety (15%)** ← SPOV 6 / KT 9.6 (RAG traceability + gold-set checker + baseline; objective math answers).
- **Fair re-runnable tests (12%)** ← the ablation + held-out evals + leakage check + flat-vs-graph benchmark.
- **Two apps, one engine + sync (10%)** ← KT 9.1 (shared Rust backend to AnkiDroid).
- **Useful product & clean UX (8%)** ← SPOV 5 (minimal + honest).
- **Bonus: knowledge graph beats keyword/vector (§13)** ← SPOV 4 / KT 7b + 9.4 (graph as falsifiable v2, benchmarked against a flat baseline; proven, not just drawn).
