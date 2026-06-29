# Speedrun — A GRE Mathematics Subject Test Study App on Anki/FSRS
### Competitive Intelligence (Part A, cited), Radical Ideation (Part B, speculation), and Architecture Theorizing (Part C, speculation)

> **How to read this report.** Part A is evidence-based and cited with URLs; each claim is flagged as **[company/marketing]**, **[third-party/review]**, or **[peer-reviewed/primary]**. Parts B and C are explicitly **SPECULATION / IDEATION** — they are design proposals, not findings, though they cite real learning science where it applies.

---

## TL;DR
- **The exact product Speedrun describes does not exist anywhere.** No competitor combines GRE-Math-Subject specificity + an open/AGPL Anki+FSRS memory chassis + three separately calibrated scores (Memory/Performance/Readiness) with uncertainty intervals and an abstention rule + one engine across desktop/mobile + engine-level topic-aware, points-at-stake interleaving. Math Academy owns the knowledge-graph + spaced-repetition idea but has no exam product, no uncertainty display, and is closed-source; the GRE-Math-Subject tool market itself is nearly empty (static books and one forum).
- **The single biggest, most defensible bet is "weaponized honesty."** Abstention + calibrated intervals (selective prediction, conformalized quantile regression, temperature scaling/ECE, Brier) are well-established in ML but essentially absent from ed-tech, which universally shows single confident numbers and gamified streaks. This is both a trust differentiator and a genuinely novel engagement loop.
- **Only one proposed feature truly requires touching Anki's Rust core** (`rslib/src/scheduler/queue/builder/`): topic-aware, points-at-stake **interleaving**, because ordering runs in the Rust backend and add-ons can only modify the Python layer. Almost everything else (performance engine, calibration, abstention, RAG generation) lives cleanly in an added Python/application layer plus a separate LLM service.

---

## PART A — Competitive Intelligence (EVIDENCE)

### A.0 Market context (the "why this is white space" baseline)

The GRE Mathematics Subject Test is a **small, high-stakes, prerequisite-structured** market:

- **Volume:** ETS's *GRE Subject Test Interpretive Data* reports **5,180** Mathematics test-takers for July 1, 2021–June 30, 2024 (**mean 680, SD 161**; 22% female, 77% male). An earlier window (2019–2023) listed 7,452. So the addressable annual pool is roughly **~5,000–7,500/year**. *(ets.org — peer-reviewed/primary org data: https://www.ets.org/pdfs/gre/interpreting-gre-scores.pdf and https://www.ets.org/content/dam/ets-india/pdfs/gre/interpreting-gre-scores.pdf)*
- **Structure:** ~66 multiple-choice questions in 2h50m; **~50% calculus**, ~25% algebra (incl. linear/abstract algebra, number theory), ~25% other (real analysis, point-set topology, probability/stats, complex analysis, numerical analysis, etc.). Scored 200–990. Computer-delivered since September 2023. *(ets.org — primary: https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html; Wikipedia corroboration: https://en.wikipedia.org/wiki/GRE_Mathematics_Test)*
- **Prerequisite reality:** calculus genuinely gates analysis, complex analysis, and ODEs — so a DAG/taxonomy is not cosmetic; it reflects the subject. The ETS practice book confirms calculus is "assumed to be common to the backgrounds of almost all mathematics majors." *(ets.org primary: https://www.ets.org/pdfs/gre/practice-book-math.pdf)*

**Finding:** the small, motivated, technically sophisticated taker pool is ideal for a paid, honest, rigorous tool — and is too small to attract the big incumbents, which is precisely why the niche is unoccupied.

---

### A.1 Math Academy — DEEP DIVE (the closest analog)

Math Academy (mathacademy.com) is the most important comparable: it is the existing realization of "knowledge-graph + spaced repetition for math." Founders Sandy & Jason Roberts; **Justin Skycak** is Chief Quant / Director of Analytics; Alex Smith leads curriculum. It grew out of the Eurisko program at Pasadena High School (2020–2023). *(beginnersinai.org third-party profile: https://beginnersinai.org/mathacademy-explained/; Skycak LinkedIn: https://www.linkedin.com/in/justinskycak/)*

**Pricing:** **$49/month or $500/year, no free tier, 30-day refund.** This is a recurring point of contention; Frank Hecker's independent review notes "$49 a month is a pretty substantial sum for most people." *([company] mathacademy.com; [third-party] https://frankhecker.com/2025/02/16/math-academy-part-9/; https://biggo.com/news/202508150714_Math_Academy_Price_Debate)*

#### The knowledge graph
- ~**2,500 topics**, each with **3–4 "knowledge points,"** each linked to one or more prerequisites. The full graph spans 4th grade → university math. A course is a subgraph. *([company] https://www.mathacademy.com/how-our-ai-works)*
- Crucially, edges carry **"encompassing weights"** — "what fraction of the prerequisite topic is encompassed, on average, by solving a problem in the post-requisite topic." Skycak reports hand-encoding these "about 8 hours per day… for a month," calling the connectivity "right at the edge of human scale." *([company/founder] https://www.justinmath.com/how-math-academy-creates-its-knowledge-graph/)*

#### The mastery model
- **Mastery learning + "layering":** students must demonstrate proficiency on prerequisites, then are pushed forward "as soon as they demonstrate mastery of prerequisites," so existing knowledge becomes "more ingrained, organized, and deeply understood." *([company] how-our-ai-works)*
- **XP system:** every task earns XP scaled by performance; ~1 XP ≈ 1 minute of focused effort; quizzes are tuned so students average ~80%. *([company] https://www.mathacademy.com/how-it-works)*

#### Spaced repetition — "Fractional Implicit Repetition" (FIRe) — the secret sauce
This is Math Academy's genuine technical novelty. Standard SRS (Anki/SuperMemo) treats flashcards as independent; Skycak argues this fails for hierarchical math:
- **Trickle-down / implicit repetitions:** "repetitions on advanced topics should 'trickle down' the knowledge graph to update the repetition schedules of simpler topics that are implicitly practiced." *([company] how-our-ai-works)*
- **Encompassings, not raw prerequisites:** reps trickle to "encompassed" topics (component skills actually practiced), not all prerequisites; implicit reps are **discounted** ("too early to count for full credit") and can be **fractional/partial** (e.g., integration-by-parts only partly exercises trig-integral skills). *([company/founder] https://www.justinmath.com/individualized-spaced-repetition-in-hierarchical-knowledge-structures/)*
- **Repetition compression:** a single well-chosen task "knocks out" many due reviews — "toppling an entire arrangement of dominoes with the fewest number of pushes." Skycak: "raw spaced repetition just doesn't work out… students will get absolutely crushed by a tsunami of review unless we… cut down the amount of review (i.e., fractional implicit repetition + repetition compression)." *([company/founder] justinmath.com; how-our-ai-works)*
- **Student-topic learning speed:** each (student, topic) pair gets a speed multiplier (e.g., 2× easy, 0.5× hard) controlling rep value. *([company] how-our-ai-works)*

#### The diagnostic / placement exam
- Adaptive, leverages the graph to estimate the **"knowledge frontier"** (boundary of known/unknown). **20–60 questions** depending on level (vs a naïve 500–1,000). Compresses the graph, then greedily selects the most informative topic; weighs positive vs negative evidence; down-weights correct-but-slow answers; marks borderline topics "conditionally completed" and "falls backwards" if the student then struggles. *([company] how-our-ai-works; [third-party] https://frankhecker.com/2025/02/14/math-academy-part-7/)*

#### Skycak's primary writings (cite these)
- **The Math Academy Way: Using the Power of Science to Supercharge Student Learning** (Skycak, advised by Roberts) — ~400-page self-published working draft, "peppered with hundreds of scientific references." Free PDF: https://www.justinmath.com/files/the-math-academy-way.pdf ; book hub: https://www.justinmath.com/books/ ; Amazon ISBN 9798339129745; ResearchGate mirror: https://www.researchgate.net/publication/381225724. Covers Bloom's two-sigma, neuromyths, active learning, deliberate practice, mastery, cognitive load, automaticity, layering, non-interference, spacing, interleaving, the testing effect, and technical deep dives on spaced repetition/diagnostics. *([company/founder])*
- Blog posts on FIRe and the knowledge graph (justinmath.com, above).
- Podcast/interviews: Chalk & Talk Ep. 42 (Anna Stokke, https://www.annastokke.com/ep-42-resources), CS Primer; Hacker News founder AMA (https://news.ycombinator.com/item?id=35515627). *([third-party])*

#### What Math Academy does NOT do — gaps, limits, weaknesses (critical for Speedrun)
- **No GRE Mathematics Subject Test product** and no exam-specific readiness scoring at all. It optimizes course mastery, not a fixed exam's points-at-stake.
- **Thin proof coverage.** As of Sept 2024 Skycak confirmed "our only proof-based course out is Methods of Proof"; advanced/abstract courses are roadmap-only. Independent reviewers are harsh on this: Andy Matuschak — "proof-oriented lessons are rote templates… at no point do I need to decide what proof strategy to use—which is the skill I really need"; Oz Nova — "it overstates the value of procedural fluency"; Michael Pershan calls it "fundamentally broken"; Dan Meyer questions illusory learning. *([founder] https://www.justinmath.com/the-future-of-proof-based-courses-on-math-academy/; [third-party] https://notes.andymatuschak.org/Math_Academy ; https://newsletter.ozwrites.com/p/a-balanced-review-of-math-academy ; https://frankhecker.com/2025/02/18/math-academy-part-11/)*
- **No uncertainty, no calibration, no abstention.** It shows single XP/mastery/progress numbers. There is no reported interval, no Brier/ECE calibration, no "we refuse to score you" rule. This is the open lane.
- **Not open source, not built on Anki.** Fully proprietary. The graph is human-curated IP (and, reviewers note, scrapeable).
- **"AI" is classical ML, not LLM, no RAG generation.** Diagnostic questions are hand-written; reviewers and Hecker criticize the "AI-powered" marketing as overstated. *([third-party] https://frankhecker.com/2025/02/16/math-academy-part-9/; https://beginnersinai.org/mathacademy-explained/)*
- **UX austere; no human in loop; text/equation only (no video); reviewers note SRS feels "too conservative."** *([third-party] Matuschak; beginnersinai)*

---

### A.2 Competitor matrix — signal modeled, pricing, key limitation

| Product | Learning signal(s) modeled | Pricing | Key limitation(s) for this niche |
|---|---|---|---|
| **ALEKS** (McGraw Hill) | **Knowledge Space Theory** — combinatorial *knowledge states* (not memory decay); Algebra ≈ 350–500 problem types → trillions of feasible states; probabilistic placement + periodic re-assessment | **$19.95/mo, $49.95/3 mo, $99.95/6 mo, $179.95/yr** | Placement-prep oriented; **not** an LLM; no GRE-subject content; no spaced-repetition *memory* model; no uncertainty/abstention. *([company] aleks.com/about_aleks/knowledge_space_theory; [peer-reviewed] Doble et al., *J. Math. Psych.*, https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134; pricing [third-party] beginnersinai.org/aleks-explained + Ohio JEOC brief)* |
| **Khan Academy + Khanmigo** | Mastery practice + **GPT-4 Socratic tutoring** (guides, won't give answers) | **Khanmigo $4/mo or $44/yr; free for teachers** | Not GRE-subject specific; weaker outside math; guidance-only, no calibrated readiness; an efficacy RCT is *claimed* (Harvard/Stanford collaboration) but no precise public effect size was locatable — treat as **company claim**. *([company] khanmigo.ai/pricing; [third-party] aiforcause.org/stories/khanmigo-ai-tutor)* |
| **Korbit (Korbi)** | Dialogue-based ITS using ML/NLP/RL; free-text answer classification + pedagogical-intervention selection (RL); ~20,000 learners | Not publicly listed (B2C + B2B); pivoting toward code-review | Domain = data science/ML only; not math-exam, not GRE; no memory/SRS chassis. *([peer-reviewed] arXiv:2005.02431, arXiv:2203.03724; [third-party] betakit.com, crunchbase.com/organization/korbit-ai)* |
| **RevisionDojo (Jojo AI)** | IB question bank (**35,000+** items) + AI mark-scheme grading + flashcards with spaced repetition | **Plus ~$17/mo, Pro ~$19/mo; free question bank; tutors $29/hr**; YC-backed | **IB only**, not GRE Math; AI grading "not official"; no calibrated readiness/abstention; no engine-level interleaving. *([company] revisiondojo.com/pricing; llms.revisiondojo.com/pricing-feature-map)* |
| **Riiid / Santa (now Socra.ai)** | **Knowledge tracing + score prediction** on TOEIC/TOEFL; **EdNet** dataset = **131,441,538 interactions from 784,309 students** (13,169 problems, 1,021 lectures, 293 skills) | Subscription (criticized as "insane"/paywalled in app reviews) | English tests only; no math/proofs; closed; aggressive monetization complaints; no open engine. *([peer-reviewed] Choi et al., "EdNet," arXiv:1912.03072; [third-party] play.google.com Santa reviews; prnewswire/Qualson)* |
| **Duolingo Max** | Gamified SRS + **GPT-4 Video Call/Roleplay**; curriculum-aware AI | **$168/yr ($14/mo annual), $29.99/mo; family ~$240/yr**; some AI features became free Jan 2026 | Language only; conversations scripted/short; energy system widely disliked; no calibrated mastery/abstention. *([company] duolingo.com/help/what-is-duolingo-max, blog.duolingo.com/duolingo-max; [third-party] copycatcafe.com, myengineeringbuddy.com)* |
| **GRE-Math-Subject tools** | **Essentially none adaptive.** Static books: Princeton Review/Leduc *Cracking the GRE Mathematics Subject Test*; Charles Rambo *Practice for the GRE Math Subject Test*; mathsub.com, subjectmath.com; ETS official practice book; mathematicsgre.com forum; Rutgers prep notes | Books ~$20–40; ETS PDF free | **No adaptive app, no spaced-repetition engine, no readiness model, no calibration.** *([third-party/primary] amazon.com Leduc/Rambo listings; https://www.mathsub.com/resources/; ets.org practice book; https://mathematicsgre.com/viewtopic.php?t=6037)* |

**Knowledge-tracing reality check (informs the modeling stance):** Gervet et al. (2020), *When is Deep Learning the Best Approach to Knowledge Tracing?* — across nine datasets, simple logistic-regression/IRT-style models (e.g., "Best-LR") and well-specified BKT are competitive with or beat deep KT, and BKT/BKT+ are slow and "not competitive" only on the largest sets. Khajah et al. (2016) showed relaxed-assumption BKT can outperform DKT; Xiong et al. (2016) compared DKT to weak baselines. **Implication: with a ~5k/yr, sparse-data niche, a calibrated IRT/BKT-flavored readiness model is the right call — deep KT would be over-engineered.** *([peer-reviewed] https://theophilegervet.github.io/assets/pdf/gervet2020deep.pdf; arXiv:2112.15072; Piech et al. DKT, stanford.edu/~cpiech)*

---

### A.3 White-space analysis — where Speedrun is first/only

No product offers any of these *combinations*, let alone all five:

1. **GRE-Math-Subject specificity** — owned by *no one* in software (only static books). Math Academy, ALEKS, Khan = general math; Riiid/Duolingo = language; RevisionDojo = IB.
2. **GRE-Math + open/AGPL Anki+FSRS memory chassis** — *no one*. Math Academy reinvented SRS (FIRe) proprietarily; nobody builds the exam tool *on Anki's proven engine* with sync.
3. **Three separately calibrated scores (Memory vs Performance vs Readiness), each with intervals + an abstention rule** — *no one*. Every competitor shows single, confident numbers (XP, mastery %, predicted score). Calibration/abstention is standard in ML and absent in ed-tech.
4. **One engine, desktop + mobile, with sync** — Anki already does this; competitors are web or mobile silos (Duolingo Max can't even upgrade on web).
5. **Engine-level topic-aware interleaving + points-at-stake sequencing** — *no one*. ALEKS sequences by knowledge state; Math Academy interleaves to reduce interference but not by *exam point value*; Anki interleaves only by deck/due date.

**Verdict:** Speedrun's intersection — **(GRE Math Subject) × (open Anki/FSRS) × (calibrated three-number honesty + abstention) × (cross-platform one-engine) × (points-at-stake DAG interleaving)** — is genuinely unoccupied. The nearest neighbor (Math Academy) is missing four of the five and is closed.

---

## PART B — Radical Ideation (SPECULATION / IDEATION)

> Everything below is **proposed design**, not established fact. Learning-science citations are real; the *features* are unbuilt hypotheses. Labels: **[PR]** peer-reviewed, **[T]** third-party/company.

**Evidence base referenced throughout:**
- **Interleaving RCT:** Rohrer, Dedrick, Hartwig & Cheung (2020), *J. Educational Psychology* 112(1):40–52 — **interleaved 61% vs blocked 37%** on an unannounced test one month later, **Cohen's d = 0.83, 95% CI [0.68, 0.97]**, 787 seventh-graders in 54 classes; IES What Works Clearinghouse rates it "meets WWC standards without reservations." (Some summaries round blocked to 38%; the journal table states 37%.) **[PR]** *(https://ies.ed.gov/use-work/awards/efficacy-study-interleaved-mathematics-practice; gwern.net/doc/.../2019-rohrer.pdf)*
- **Desirable difficulties, fluency illusion, generation effect, errorful learning:** Bjork & Bjork (1992, 2011, 2020). **[PR]** *(https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf)*
- **Calibration:** Guo, Pleiss, Sun & Weinberger (2017), *On Calibration of Modern Neural Networks*, ICML — "modern neural networks… are poorly calibrated"; **temperature scaling** "is surprisingly effective"; defines **ECE** (binned |accuracy − confidence|). **[PR]** *(arXiv:1706.04599; proceedings.mlr.press/v70/guo17a)*
- **Selective prediction / abstention:** Geifman & El-Yaniv (2017), *Selective Classification for Deep Neural Networks*, NeurIPS — "reduce the error rate by abstaining from prediction when in doubt, while keeping coverage as high as possible"; learn a classifier–rejection pair **(f, g)**; the **risk–coverage** tradeoff. **[PR]** *(arXiv:1705.08500)*
- **Conformalized Quantile Regression (CQR):** Romano, Patterson & Candès (2019), NeurIPS — distribution-free, finite-sample, heteroscedasticity-adaptive prediction intervals. **[PR]** *(arXiv:1905.03222)*
- **Brier score:** Brier (1950), *Monthly Weather Review* 78(1):1–3 — mean squared error of probabilistic forecasts; strictly proper. **[PR]** *(DOI 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2)*
- **Worked-example effect; testing effect; metacognition.** **[PR]**

### The 18 ideas

**1. Abstention as the headline UX — "We refuse to lie to you."**
(a) *Insight:* refusing to display a score below a data threshold is a costly, credible trust signal in a market drowning in confident fake numbers. (b) *Rationale:* selective prediction's (f,g) reject option; calibration. (c) *Mechanics:* the Readiness panel shows **"INSUFFICIENT DATA — answer 12 more calculus items to unlock"** rather than a number; coverage rises as data accrues. (d) *Risk/novelty:* medium novelty, **high impact**, very feasible (1-wk MVP = threshold + gated UI).

**2. The three-number honesty dashboard with intervals.**
(a) Memory ≠ Performance ≠ Readiness; conflating them is the core lie of test prep. (b) CQR intervals; Brier/ECE for honesty about the honesty. (c) Three calibrated bars each with a CI; Readiness = a predicted exam-score *distribution*, not a point. (d) **High impact**, medium feasibility (needs the performance store + interval fit).

**3. Memory→Performance gap meter — "you remember it but can't use it."**
(a) Recall of a theorem ≠ deploying it under time pressure; the fluency illusion lives in this gap. (b) Testing effect, fluency illusion (Bjork). (c) Same topic, two probes: flashcard recall vs timed multi-step solve; surface the delta explicitly per topic. (d) **High novelty**, high impact, medium feasibility.

**4. Counterexample gauntlet (auto-generated).**
(a) Mathematical maturity = knowing *where claims break*, not reciting them. (b) Generation effect + errorful learning (Bjork). (c) A RAG/LLM service emits "Is this always true?" statements (some true, some false-with-counterexample) drawn from the topic; the user must accept/reject and, when rejecting, *produce or pick* a counterexample. (d) **High novelty**, high impact, medium feasibility (LLM service + verification).

**5. Proof/derivation scaffolding with fading hints.**
(a) Beginners need worked steps; experts need to struggle. (b) Worked-example effect + desirable difficulty; fade scaffolds as mastery grows. (c) Reveal step *k+1* only after an attempt at step *k*; progressively remove revealed steps over successive reps. (d) Medium novelty, medium feasibility.

**6. "Productively dumb" mode (desirable-difficulty dial).**
(a) Lower immediate accuracy can mean better exam-day retention. (b) Rohrer 2020 (interleaving lowers practice-time accuracy, raises delayed test scores). (c) A user-set dial increases interleaving/spacing intensity, with an honest banner: "your in-session accuracy will drop ~20 pts; your exam score should rise." (d) **High novelty** (anti-best-practice), risky for retention/engagement, feasible.

**7. Points-at-stake, topic-aware interleaving (engine-level).** *(core to project)*
(a) Not all topics are worth equal study; sequence by **exam point value × prerequisite centrality × current weakness**, interleaved to avoid blocking. (b) Interleaving RCT + IRT item information. (c) The queue builder mixes topics so "no two consecutive problems require the same strategy" *and* front-loads high-yield, high-centrality nodes. (d) Medium novelty, **high impact**, the one true Rust-core change (see Part C).

**8. Prerequisite-DAG "blast radius" view.**
(a) A weak prereq silently poisons everything downstream. (b) Knowledge-graph trickle-down (Math Academy's FIRe logic, generalized). (c) Tap a weak node → highlight all downstream topics whose readiness it caps. (d) Medium.

**9. Diagnostic interrogation / Socratic wrong-answer drilldown.**
(a) *Which* sub-step failed matters more than the wrong final answer. (b) Metacognition; targeted remediation. (c) On error, ask the learner to localize the failure (algebra slip? wrong theorem? setup?); route remediation to that node. (d) Medium.

**10. Anti-streak / honest-effort metric.**
(a) Streaks reward showing up, not learning, and punish principled rest days. (b) Anti-gamification; spacing > cramming. (c) Replace the streak with a *calibrated growth* number that **penalizes cramming** (massed practice yields diminishing readiness credit). (d) **High novelty**, **risky** (may hurt engagement), feasible.

**11. Calibration self-bet — "rate your confidence."**
(a) Overconfidence is the GRE killer; make it visible and scored. (b) Brier (1950) + Guo et al. ECE; metacognition. (c) Before revealing correctness, the user states P(correct); the app scores them with Brier/ECE and shows an "overconfidence tax." (d) **High novelty**, high impact, very feasible (capture one slider + score it).

**12. Adversarial sibling problems.**
(a) Pattern-matching ("this looks like the integration-by-parts one") collapses on the real exam. (b) Interleaving + errorful learning. (c) Generate near-identical twins with one changed condition (sign, bound, hypothesis) that flips the method. (d) **High novelty**, medium feasibility.

**13. Readiness conformal countdown.**
(a) The only question that matters: "what will I score on the date I sit it?" (b) CQR (Romano 2019) gives calibrated, adaptive intervals. (c) "80% chance your score is in [X, Y] on <exam date>," updated daily as data and forgetting evolve. (d) **High impact**, medium feasibility.

**14. Exam-simulation under modeled decay.**
(a) Test day is weeks out; today's mastery isn't test-day mastery. (b) FSRS retrievability projects forward. (c) Simulate a full mock at *projected* retrievability on the exam date, not now. (d) Medium.

**15. "Teach-back" generation tasks.**
(a) Explaining forces encoding far more than recognizing. (b) Generation effect. (c) The user writes a derivation/justification; the LLM service grades against a rubric and flags missing steps. (d) Medium.

**16. Topic-frontier abstention map.**
(a) Make the unknown visible and motivating. (b) Selective prediction at the node level. (c) Graph view greys out nodes where data is insufficient for a calibrated score; clearing fog is the progress loop. (d) Medium.

**17. Interference-aware scheduling.**
(a) Confusable topics taught back-to-back create lasting errors (e.g., the convergence tests; sin/cos integral patterns). (b) Associative interference (Math Academy's "non-interference"). (c) Spacer rules in the scheduler forbid adjacent confusable nodes. (d) Medium.

**18. Honest leaderboard of uncertainty.**
(a) Ranking by raw score rewards luck and cramming; rank by *calibration*. (b) Anti-gamification; Brier/ECE. (c) Leaderboard sorted by interval tightness + calibration quality, not point score. (d) **Risky**, niche-appealing, feasible.

### Ranking (novelty × impact × feasibility-in-1-week-MVP)
**1 ▸ 2 ▸ 11 ▸ 4 ▸ 3 ▸ 7 ▸ 13 ▸ 6 ▸ 5 ▸ 12 ▸ 9 ▸ 15 ▸ 14 ▸ 8 ▸ 16 ▸ 17 ▸ 10 ▸ 18**

**Top 5 (deepened) — high-novelty × high-impact for *this* project:**
- **#1 Abstention UX** — cheapest, most differentiating; nobody in ed-tech does it; directly operationalizes "three-number honesty."
- **#2 Three-number dashboard with intervals** — the product's thesis made visible; the thing no competitor has.
- **#11 Calibration self-bet** — converts the calibration machinery into a daily *engagement loop* (the "weaponized honesty" growth flywheel) while measuring the exact failure mode (overconfidence) the GRE punishes.
- **#4 Counterexample gauntlet** — uniquely *mathematical*; exploits RAG generation; trains the maturity static books can't.
- **#3 Memory→Performance gap meter** — directly measures and weaponizes the memory→performance→readiness gap that defines the architecture.

These five also stack into one narrative: *measure honestly (2), refuse to fake it (1), make the user bet against their own overconfidence (11), expose the recall-vs-use gap (3), and harden understanding with counterexamples (4).*

---

## PART C — Architecture Theorizing (SPECULATION, high-level)

> Speculative sketch only. Anki's relevant cores: memory state in **`rslib/src/scheduler/fsrs/`**, ordering in **`rslib/src/scheduler/queue/builder/`**, review logging in the Rust backend + `pylib/anki`. **A documented constraint:** add-ons can only modify the **Python** layer; "the sorting function is implemented in Anki's Rust backend… impossible to modify the order of reviews" without backend changes. *([third-party] FSRS Helper notes, ankiweb.net/shared/info/759844606; [third-party] deepwiki.com/ankitects/anki)*

**Layering principle:** keep the proven FSRS memory chassis in Rust; add Performance + Readiness as a Python/application layer reading the revlog plus a new performance store; isolate LLM/RAG in a separate service. Only interleaving justifies a Rust-core change.

- **#1 / #2 / #13 — Abstention, three-number dashboard, conformal countdown.**
 *Where:* **Memory** already computed in the Rust FSRS core (retrievability/stability). **Performance** and **Readiness** models live in an **added Python/application layer** that reads `revlog` + a new performance table (per-attempt correctness, time, hint usage, points-at-stake). **CQR intervals + abstention thresholds** computed there. **Display** in the existing desktop/mobile UI (TS/Svelte). **Sync** via Anki's existing sync of the collection DB (extend schema, not the sync protocol). No Rust change required.

- **#11 — Calibration self-bet.**
 *Where:* capture a confidence value at answer time. Cleanest as a **small revlog/schema extension** (a confidence field) — a minor Rust touch to persist it — with **Brier/ECE scoring + temperature scaling** entirely in the Python layer. If avoiding Rust, store confidence in a side table keyed by review id.

- **#4 / #15 — Counterexample gauntlet & teach-back.**
 *Where:* a **separate RAG/LLM microservice** for generation + rubric grading (kept out of the client for cost, safety, and AGPL-cleanliness). New **card type(s)** surfaced through the Python layer and injected into the normal queue. No Rust scheduler change beyond recognizing the new note type.

- **#3 — Memory→Performance gap meter.**
 *Where:* pure **Python/application analytics** joining the FSRS memory state (Rust-exposed) against the performance store; rendered in UI. No backend change.

- **#7 — Points-at-stake, topic-aware interleaving.** *(the genuine Rust-core change)*
 *Where:* **`rslib/src/scheduler/queue/builder/`**. The `QueueBuilder` ordering must become **topic-DAG-aware and point-weighted** — interleaving so consecutive items use different strategies while front-loading high-yield, high-centrality, currently-weak nodes. Because ordering executes in the Rust backend and add-ons cannot reorder reviews, this **must** be implemented in `rslib` (the project's stated "real change to Anki's Rust backend"). Inputs (DAG, point weights, weakness) can be precomputed in the Python layer and passed into the builder; the *decision logic* lives in Rust.

**Net architecture:** Rust core = memory + (new) interleaving ordering + a tiny confidence field; Python/application layer = performance engine, IRT/calibrated readiness, CQR intervals, abstention, analytics, dashboards; separate service = RAG/LLM generation & grading. This keeps the AGPL Anki engine intact, confines novelty to one well-scoped Rust change, and puts the differentiating "honesty" math where it's easiest to iterate.

---

### Source-quality flags (summary)
- **Primary/peer-reviewed:** ETS data & test specs; Rohrer 2020 (IES/JEP); Bjork (UCLA); Guo 2017 (ICML); Geifman & El-Yaniv 2017 (NeurIPS); Romano 2019 (NeurIPS); Brier 1950 (AMS); Gervet 2020; Choi 2020 EdNet; ALEKS KST (J. Math. Psych.).
- **Company/marketing:** mathacademy.com, justinmath.com (Skycak), aleks.com, khanmigo.ai, revisiondojo.com, duolingo.com — used for *what they claim to do* and pricing; flagged inline.
- **Third-party/review:** frankhecker.com, Andy Matuschak notes, Oz Nova, beginnersinai.org, app-store reviews, DeepWiki/Anki forums — used for limitations, independent pricing corroboration, and Anki internals.
- **Unverified company claim:** the Khanmigo Harvard/Stanford RCT "significant gains" — no public effect size located; treat with caution.