# Speedrun — Canonical Core Sources (load-bearing only)

The ~24 sources that actually drive our SPOVs and design decisions. The fuller body (≈900 across the Claude reports + `research-notes.md`) stays as the audit trail; **this is the curated set we synthesize from** to keep the BrainLift clear and un-jumbled. Tags: [PR]=peer-reviewed/primary, [ORG]=official org data, [PRAC]=practitioner/expert (non-peer-reviewed).

## 1. The exam (ground truth)
1. **ETS — GRE Math Subject Test, Content & Structure** [ORG] — ~66 Q / 170 min, 200–990, Calc 50% / Algebra 25% / Additional 25%. https://www.ets.org/gre/test-takers/subject-tests/about/content-structure.html
2. **ETS — Math fact sheet** [ORG] — official content weights. https://www.ets.org/content/dam/ets-india/pdfs/gre/fact-sheet-math.pdf
3. **ETS — Interpretive Data (percentiles)** [ORG] — mean 680, SD 161; 680≈50th, 880≈88th. https://www.ets.org/pdfs/gre/interpreting-gre-scores.pdf

## 2. Learning science (the pedagogy)
4. **Soderstrom & Bjork (2015), Learning vs Performance** [PR] — in-the-moment performance ≠ durable learning. (SPOV 1)
5. **Bjork & Bjork (2011), Desirable Difficulties** [PR] — effortful practice builds durable, transferable skill. (SPOV 1, 3)
6. **Rohrer, Dedrick, Hartwig & Cheung (2020), Interleaved Math Practice RCT** [PR] — 61% vs 38%, d≈0.83. (SPOV 3) https://doi.org/10.1037/edu0000367
7. **Rohrer & Taylor (2007), Shuffling Mathematics Problems** [PR] — the native interleaving result. (SPOV 3)
8. **Sweller & Cooper (1985), Worked Examples** [PR] — worked examples halve time / cut errors for novices. (Pedagogy, Insight 9)
9. **Sweller (1988), Cognitive Load Theory** [PR] — working-memory limits → guidance for novices.
10. **Willingham (2007), Critical Thinking / knowledge vs skills** [PR] — "memory is the residue of thought." (SPOV 6)
11. **Huang et al. (2023), Retrieval practice may not benefit math problem-solving** [PR] — the key caveat: testing effect ≠ procedural transfer. (Insight 9) https://doi.org/10.3389/fpsyg.2023.1093653
12. **Dunlosky et al. (2013)** [PR] + **Pashler et al. (2008), IES Practice Guide** [ORG] — practice testing + spacing + interleaving rank highest.

## 3. Honest readiness (the measurement machinery)
13. **Guo et al. (2017), Calibration of Modern NNs** [PR] — ECE, temperature scaling. (SPOV 2)
14. **Angelopoulos & Bates (2023), Conformal Prediction** [PR] — distribution-free intervals. (SPOV 2)
15. **Romano, Patterson & Candès (2019), CQR** [PR] — intervals that widen under sparse data. (SPOV 2)
16. **Geifman & El-Yaniv (2017), Selective Classification** [PR] — the abstention/give-up rule. (SPOV 2)
17. **Embretson & Reise (2000), IRT for Psychologists** [PR] — ability θ → scaled score; the flat baseline.

## 4. Knowledge modeling (graph vs flat — the honest case)
18. **Gervet et al. (2020), When is Deep Learning Best for KT?** [PR] — flat IRT/BKT competitive with deep/graph, esp. sparse data. (SPOV 4, Insight 10)
19. **Doignon & Falmagne (1985) / Sun et al. (2021) ALEKS meta-analysis** [PR] — knowledge-space structure works as a *supplement* (g=0.43). (SPOV 4)

## 5. Competitive north star
20. **Skycak, *The Math Academy Way* + FIRe writings** [PRAC] — closest analog (knowledge graph + SRS); our differentiation target. https://www.justinmath.com/files/the-math-academy-way.pdf

## 6. High-scorer strategy (encode the playbook; treat as biased sample)
21. **mathematicsgre.com top-scorer threads** (ylyoo 970; boredmathguy 90th) [PRAC] — calc+LA first, speed, stereotyped tail, conserve mocks, error logs.
22. **UChicago GRE guide (DeWitt & Neaton)** + **mathsub.com** [PRAC] — expert prep regimen + resource evaluation + raw→scaled charts.

## 7. AI pipeline (generation + verification + grounding)
23. **Li et al. (2024), Neuro-Symbolic Data Generation for Math** [PR] + **SymPy** — LLM proposes → CAS verifies (the correctness gate). (SPOV 6)
24. **Lewis et al. (2020) RAG** + **Karpukhin et al. (2020) DPR** + **Cormack et al. (2009) RRF** [PR] — hybrid retrieval that beats keyword/vector (traceability). Plus **Brown & Burton (1978) BUGGY** [PR] for mal-rule distractors and **Greshake et al. (2023)** [PR] for prompt-injection defense.

---
**Rule:** when the BrainLift makes a claim, it should trace to one of these 24. New claims require either a core source or a clearly-flagged hypothesis. Everything else in `research/` is supporting/audit material.
