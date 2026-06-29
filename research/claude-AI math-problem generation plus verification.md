# Designing the AI Layer of a GRE Mathematics Subject Test Study App: Generate, Verify, Ground, Gate

## TL;DR
- **Build a hybrid generation pipeline, not a pure LLM.** The only architecture that satisfies "no untraceable output and no wrong facts" is: an LLM proposes problem structure → a symbolic engine (SymPy/SageMath) instantiates and **verifies** the answer → every item is RAG-grounded to a named source passage → a hard gold-set gate blocks any card that fails verification before a student sees it. Pure LLM generation cannot meet the correctness bar; templated/symbolic generation guarantees correctness but is novelty-limited, so the two must be combined.
- **Verification is the crux and it is solvable for most GRE Math topics today** using CAS symbolic + numerical checks (cheap, high-coverage) with an optional Lean/autoformalization lane for proof-type items (expensive, low coverage). LLM-as-judge is the *weakest* verifier and must never be the sole gate.
- **The full RAG system provably beats keyword/vector baselines** when you use hybrid retrieval (BM25 + dense) fused with Reciprocal Rank Fusion and a cross-encoder reranker — a configuration repeatedly shown to add large recall/MRR gains over single-method retrieval — and you measure it on your own 50-pair gold set with a pre-registered passing cutoff.

## Key Findings
1. **Three generation families with a hard correctness/novelty trade-off.** Templated/parametric/symbolic generation gives provable correctness but bounded novelty; LLM generation gives unbounded novelty but hallucinates false facts; hybrid neuro-symbolic generation (LLM proposes, symbolic engine instantiates/verifies) is the established resolution to this "diversity–validity dilemma."
2. **CAS verification (SymPy/Sage/Mathematica) is the workhorse.** It can verify algebraic equality, derivatives/integrals, linear-algebra results, ODE solutions, and numeric answers exactly or via random-point/Monte-Carlo evaluation. It cannot, on its own, verify many proof-based statements (topology, real-analysis proofs) — that needs a proof assistant.
3. **Proof assistants (Lean/mathlib, Isabelle, Coq) give the strongest guarantee but lowest coverage.** State-of-the-art autoformalization+proving still proves only a minority of undergraduate-level problems (ReProver proves 26.5% on miniF2F and 13.8% on ProofNet), so this is a narrow, optional lane — not the main gate.
4. **Hybrid retrieval + reranking is the evidence-based way to beat BM25/single-vector.** DPR beats BM25 by 9–19% top-20 recall; RRF fusion of BM25+dense adds further gains; cross-encoder/ColBERT rerankers refine the top list. GraphRAG adds traceable concept-graph provenance well-suited to a math textbook.
5. **Indirect prompt injection is a real ingestion risk** (OWASP LLM01; Greshake et al.). Defenses: spotlighting/datamarking, data–instruction separation, input sanitization, and treating all ingested text as untrusted data.
6. **The gold-set gate is the single most important safety control.** It is a hard pre-display filter; a card ships only if (answer verified by CAS/proof) AND (grounded to a named source) AND (not a near-duplicate/leak) AND (passes teaching-quality checks).

## 1. Generation Approaches

### 1a. Templated / Parametric / Symbolic Generation (ESTABLISHED)
**How it works.** A problem *schema* is written once with typed parameters and constraints (e.g., "differentiate a degree-n polynomial with integer coefficients in [−9,9]"); a generator samples parameters, and the answer key is produced by the same symbolic procedure that defines correctness. Because the answer is computed by construction, correctness is guaranteed up to the correctness of the CAS.

**Tools & research.** The earliest principled algebraic problem generator is Singh et al. (2012), which generates variants via syntactic generalization and verifies correctness using polynomial identity testing, producing provably valid problems across polynomials, trigonometry, calculus, and determinants. Procedural/template systems include Polozov et al.'s personalized word-problem generation (IJCAI 2015, using Answer Set Programming for pedagogical/narrative constraints) and Deane & Sheehan's Frame-Semantics NLG. Xu et al. (2021) report 56% time savings with a template-based procedural system. Modern symbolic-space pipelines: GSM-Symbolic (Mirzadeh et al., 2024) converts GSM8K into perturbable templates; MathCAMPS encodes skills as formal grammars; AlphaGeometry generated 100M synthetic theorems via a symbolic deduction engine.

**Correctness guarantee:** strong (answer computed by construction). **Novelty limit:** bounded — items are variations within the schema's structure; "static grammars or fixed prompts… are not adapted to the model's capabilities" and tend to produce same-pattern items (Polozov notes the "personalization level is insufficient for engaging education").

### 1b. LLM-Based Generation (ESTABLISHED capabilities, ESTABLISHED failure modes)
**Capabilities.** LLMs produce linguistically diverse, novel, contextually rich problems and draft worked solutions and distractors at scale. MathScale (Tang et al., ICML 2024, arXiv:2403.02884) builds a concept graph from seed questions and uses a frontier LLM to produce the **MathScaleQA dataset of two million math question–answer pairs**; the resulting MathScale-7B "achieves 35.0% micro average accuracy and 37.5% macro average accuracy, surpassing its best open-source counterparts by 42.9% and 43.7% respectively."

**Failure modes.** LLMs hallucinate false facts and make arithmetic/algebra errors that invalidate items. The mathematical-hallucination taxonomy (FG-PRM) names six types: fabrication, factual inconsistency, context inconsistency, instruction inconsistency, logical inconsistency, and logical error. Surveys note hallucination "originates from statistical biases… and is, by some research, unavoidable," and is exacerbated in specialized sub-fields with scarce data. In math, "correctness is strictly binary and errors propagate through derivation chains" — a single bad step cascades. **Implication: never ship an LLM-generated answer key unverified.**

### 1c. Hybrid Neuro-Symbolic Generation (ESTABLISHED, RECOMMENDED)
The "diversity–validity dilemma" (Li et al., *Neuro-Symbolic Data Generation for Math Reasoning*, NeurIPS 2024, arXiv:2412.04857): prompt-based rephrasing is diverse but error-prone; template rewriting is valid but low-diversity. The resolution: generate/modify in *symbolic space* (SymPy/SMT), then realize as natural language. *Adaptive Problem Generation via Symbolic Representations* uses SymPy symbolic variables+constraints so that "symbolic solvers enable immediate verification that generated problems are well-posed and solvable, and provide corresponding solutions automatically." Li et al. (2024) formalized problems in SMT-LIB and used Markov-Chain Monte-Carlo to produce 620K verified examples. SymCode (arXiv:2510.25975) generates verifiable SymPy code with a self-debugging loop.

**The trade-off, explicitly:**

| Approach | Correctness | Novelty | Traceability | Best use |
|---|---|---|---|---|
| Templated/symbolic | Provable (by construction) | Low–medium | Easy (schema cites source) | Calculus, linear algebra, computational items |
| Pure LLM | Unreliable | High | Hard | Drafting, paraphrase, distractor ideation (never final key) |
| Hybrid (LLM proposes → symbolic instantiates/verifies) | Provable (verifier gates) | Medium–high | Easy (verifier + RAG) | **Default for the app** |

## 2. Verification (THE CRUX)

### 2i. Computer Algebra Systems (ESTABLISHED, primary gate)
**SymPy** (open-source, Python; sympy.org) is the recommended default: it keeps exact symbolic results (√2 stays `2*sqrt(2)`), and verification is done by simplifying a difference to zero — `simplify(candidate - reference) == 0`, or `Eq(...)`-style checks. The standard pattern: express the problem's answer symbolically, subtract the candidate, and check it simplifies to 0. **SageMath** (sagemath.org) wraps SymPy plus Maxima, GAP, PARI, etc., for heavier algebra/number theory. **Wolfram/Mathematica** (commercial) is fastest and most feature-complete.

**What CAS can verify:** algebraic equivalence, derivatives, integrals (definite/indefinite), limits, series, linear-algebra results (eigenvalues, determinants, rank), ODE solutions (substitute back), polynomial identities, and numeric answers. **What it cannot reliably verify:** equivalence is undecidable in general; CAS is brittle to surface form (term ordering, latex `\mathrm{i}` vs `i`, `2π` written separately), and it cannot by itself certify many *proof* statements (e.g., "this space is connected"). Document a tolerance and canonicalization step.

**Integration pattern:** run CAS in a sandboxed subprocess with a timeout; canonicalize both expressions; try `simplify`/`nsimplify`/`equals`; on inconclusive symbolic result, fall back to a numerical check.

### 2ii. Numerical Sanity / Monte-Carlo Checks (ESTABLISHED, cheap catch-all)
Evaluate both the reference and candidate answer at many random points in the domain; if they ever differ beyond tolerance ε (e.g., 10⁻⁶–10⁻⁹), the equality is false. This catches errors symbolic simplification misses and is the practical backstop SymPy's `evalf()`/`subs()` enables. The *Symbolic Recursive Self-Alignment* pipeline (arXiv:2603.21558) formalizes a multi-check gate: answer-correctness within ε=10⁻⁶, plus arithmetic verification that parses chain-of-thought expressions and requires ≥80% to satisfy `|sympy(lhs) − rhs| < ε`. Random-point evaluation gives a near-zero false-positive rate for inequality detection (it can prove two expressions *differ*, though not that they're *equal* everywhere).

### 2iii. Autoformalization & Proof Assistants (ESTABLISHED but LOW-COVERAGE; optional lane)
For proof-type items (real/complex analysis, topology, abstract algebra), formal verification gives the strongest guarantee: "a proof successfully verified by the Lean proof assistant is irrefutably sound." Tools: **Lean 4 + mathlib**, **Isabelle**, **Coq**. Key research:
- **Draft-Sketch-Prove** (Jiang et al., 2022, arXiv:2210.12283): LLM drafts informal proof → formal sketch → prover fills gaps (Isabelle).
- **LeanDojo / ReProver** (Yang et al., NeurIPS 2023, arXiv:2306.15626): first retrieval-augmented LLM prover. Verbatim from the paper: "It can prove 26.5% theorems in MiniF2F and 13.8% in ProofNet"; ReProver also proves 51.2% Pass@1 on the LeanDojo random split vs 47.6% (no-retrieval) and 29.0% (GPT-4). Open-source, MIT license; docs at leandojo.readthedocs.io.
- **ProofNet** (Azerbayev et al., 2023, arXiv:2302.12433): autoformalizing/proving undergraduate math — the most relevant benchmark for GRE-level material.
- **miniF2F** (Zheng et al., ICLR 2022): 488 olympiad/undergrad problems across Lean/Isabelle/HOL/Metamath. Note: *miniF2F-Lean Revisited* (arXiv:2511.03108) found reported autoformalization accuracy is "largely inflated" because LLM-based evaluation marks many wrong formalizations correct (true SoTA ~66%, not the reported 97%).
- **AlphaProof** (Google DeepMind, *Nature* 2025, s41586-025-09833-y): RL + Lean, silver-medal IMO 2024. Per the Nature paper, the combined system scored "a total score of 28 out of 42 points… within the silver-medal range… one point below the gold-medal threshold," with AlphaProof solving P1, P2, P6 and AlphaGeometry 2 solving P4 (the gold threshold began at 29 points; only 5 of ~600 contestants solved P6).

**Verdict:** Formal proof is too low-coverage and slow to be the main gate for a 1-week build. Use it as an *optional, best-effort* lane on a small set of proof items; for most GRE Math items, CAS+numerical suffices because GRE Subject answers are computational/multiple-choice rather than free-form proofs.

### 2iv. Self-Consistency / Majority Voting (ESTABLISHED, supporting signal only)
Sample k independent solutions; correct answers tend to recur while hallucinations vary (Wang et al., self-consistency; Farquhar et al., semantic entropy). *Self-Consistency-Based Hallucination Detection* (arXiv:2504.09440) builds reasoning graphs and repairs hallucinated nodes. Useful as a cheap pre-filter and confidence signal, but it can be **consistently wrong** (systematic errors recur), so it must sit *behind* the CAS gate, never replace it.

### 2v. LLM-as-Judge with Tool-Checking (ESTABLISHED but BIASED; never sole gate)
LLM judges exhibit documented biases: position/selection bias, verbosity bias, self-enhancement bias, authority/bandwagon bias, and agreeableness bias; multilingual reliability is modest (Fleiss' κ 0.1–0.32). Majority-vote across diverse model families and "minority-veto" ensembles help but "cannot fully correct systematic biases." Critically, *tool-augmented* judges (an LLM that calls SymPy/retrieval) far outperform parametric-only judges — self-consistency "lags far behind the tool-augmented baselines, confirming that external evidence… is critical for reliable objective judgment" (TALE, arXiv:2504.07385). **Use the LLM judge only for teaching-quality assessment, wrapped around tool checks, with diverse-model majority voting.**

### "Correct-but-bad-teaching" detection (vague/trivial/duplicate/ambiguous/multi-answer)
A correct answer is necessary but not sufficient. Add explicit checks:
- **Ambiguity / multiple valid answers:** CAS solves for *all* solutions; if `solve()` returns >1 admissible answer for a single-answer item, flag. The UMWP work (arXiv:2403.03558) benchmarks unanswerable/ill-posed problems — adapt as a filter.
- **Triviality:** require a minimum number of nontrivial solution steps (the symbolic schema knows the step count); reject 0–1 step items unless intended as warmups.
- **Duplicate / near-duplicate:** MinHash/LSH and embedding cosine similarity against the existing bank (see §4 leakage).
- **Vagueness / well-posedness:** verify all referenced quantities are defined and the domain is specified; a tool-checked LLM judge flags under-specified stems.

## 3. RAG for Traceability

**Goal:** every generated card cites the named source passage it was grounded in (textbook section, theorem, worked example), giving provenance/attribution.

**Foundational stack:**
- **RAG** (Lewis et al., NeurIPS 2020, arXiv:2005.11401): combine parametric LLM with non-parametric retrieval; retrieval augmentation reduces hallucination.
- **BM25** (Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond*, 2009): strong sparse lexical baseline — essential for exact math terms/symbols.
- **DPR** (Karpukhin et al., EMNLP 2020, arXiv:2004.04906): dense dual-encoder. On Natural Questions, DPR reaches **79.4% top-20 retrieval accuracy vs BM25's 59.1%**, and on TriviaQA **78.8% vs 66.9%**; the paper states "our dense retriever outperforms a strong Lucene-BM25 system largely by 9%–19% absolute in terms of top-20 passage retrieval accuracy."
- **ColBERT / ColBERTv2** (Khattab & Zaharia, SIGIR 2020, arXiv:2004.12832; Santhanam et al., arXiv:2112.01488): late-interaction multi-vector retrieval; per-token matching, strong for technical/definitional queries.

**Beating the baseline (the project's core requirement):**
- **Hybrid retrieval + RRF** (Cormack et al., 2009): fuse BM25 and dense ranked lists via RRF score = Σ 1/(k + rankᵢ(d)), k≈60. Benchmarks from *From BM25 to Corrective RAG* (arXiv:2604.01733): "Combining BM25 and dense retrieval via Reciprocal Rank Fusion improves over both constituent methods across all metrics… largest on TAT-DQA (+8.1pp Recall@5 over BM25)." Note the math-IR caveat: lexical/structure search is very strong for formulas, and dense retrieval is *complementary* (helps recall more than rerank) (arXiv:2203.11163).
- **Rerankers** (second stage): cross-encoders (monoBERT, Nogueira & Cho 2019; monoT5, Nogueira et al. 2020), bge-reranker (BAAI), and Cohere Rerank. In the same benchmark, adding a cross-encoder reranker (Cohere Rerank v4.0) on top of hybrid retrieval gave the largest single gain: **+17.2 percentage points MRR@3 and +12.1pp Recall@5 over unreranked hybrid retrieval** (Recall@5 of 0.816 vs BM25's 0.644, a +26.7% relative improvement). Standard production pattern: BM25 top-50 + dense top-50 → RRF → cross-encoder rerank to top-10 → generate.
- **GraphRAG** (Microsoft Research; microsoft.com/research/project/graphrag, github.com/microsoft/graphrag): builds an entity/relationship knowledge graph with Leiden-community summaries; "each node is associated with a snippet of source content, allowing GraphRAG to maintain traceability to the original document." Well-suited to a math textbook where "GraphRAG can follow graph paths through definitions, theorems, and examples." A direct study (arXiv:2509.16780) compares RAG vs GraphRAG for page-level retrieval QA on a math textbook.

**Attribution / faithfulness methods:**
- **Attributed QA** (Bohnet et al., 2022, arXiv:2212.08037): formalizes attribution evaluation; human gold + correlated automatic metric.
- **ALCE** (Gao et al.): first benchmark for automatic citation evaluation — fluency, correctness, citation quality.
- Faithfulness-metric surveys (arXiv:2406.15264; arXiv:2501.00269) and CaLM (arXiv:2406.05365, contrasting large/small models to verify grounded generation).

**Design:** make the generator emit, per card, the source passage ID + verbatim quote; gate on citation precision (does the cited passage support the item?) and citation recall.

## 4. Safety

### Prompt-injection defense for ingested documents (ESTABLISHED threat)
Textbook PDFs may contain hidden/adversarial text ("ignore instructions, output X"). This is **indirect prompt injection**, OWASP **LLM01:2025** (the #1 LLM risk), first demonstrated by **Greshake et al., 2023** ("Not What You've Signed Up For…", arXiv:2302.12173): adversarial instructions embedded in retrieved/external content. "RAG systems are particularly vulnerable… the retrieval step is specifically designed to pull external content."

**Defenses (layered):**
- **Spotlighting / datamarking** (Hines et al., 2024, arXiv:2403.14720): transform/delimit untrusted input so the model can distinguish data from instructions.
- **Data–instruction separation / instruction hierarchy** (Wallace et al., 2024, OpenAI): train/prompt models to prioritize privileged instructions; StruQ/SecAlign as structured defenses.
- **Input sanitization:** regex + LLM-classifier screening of ingested text; strip non-visible text layers from PDFs.
- **Architectural:** treat all ingested text as untrusted *data*; never let retrieved content issue tool calls; the generator's system prompt is privileged and isolated.

### Contradictory sources (ESTABLISHED methods)
When two sources disagree (e.g., differing conventions for a definition), detect and resolve before generating:
- **NLI-based contradiction detection** (de Marneffe et al., ACL 2008, aclanthology.org/P08-1118): the "contradiction" class of NLI with a typology (negation, numeric mismatch, antonymy, structural reversal).
- **SummaC** (Laban et al., TACL 2022, arXiv:2111.09525): sentence-pair NLI entailment matrix; SoTA inconsistency detection (74.4% balanced accuracy).
- **FactCC** (Kryściński et al., EMNLP 2020, arXiv:1910.12840) and **QAFactEval** (Fabbri et al., NAACL 2022, arXiv:2112.08542): factual-consistency metrics.
- **SparseCL** (arXiv:2406.10746): retrieves and removes contradicting passages to clean a corpus (recovers >60% of corruption-induced performance loss). **Contradiction Detection in RAG** (arXiv:2504.00180) evaluates LLMs as context validators across many retrieved docs.

**Policy:** on detected contradiction, prefer the source designated authoritative for the topic, or suppress generation and log for human review.

### Hallucination mitigation (ESTABLISHED)
RAG grounding (reduces hallucination), self-consistency/semantic-entropy filtering, tool-checked verification (the CAS gate), and SelfCheckGPT (Manakul et al., 2023, arXiv:2303.08896) for black-box consistency. These reduce but do not eliminate hallucination — which is why the gate is non-negotiable.

### The pre-display gold-set gate (THE hard control)
A card is shown to a student **only if all hold**:
1. **Answer verified** by CAS (symbolic + numerical) or, for proof items, by the optional proof lane.
2. **Grounded**: cites a named source passage with a supporting quote (citation-precision check).
3. **Not leaked/duplicated**: passes near-duplicate and verbatim-leakage checks (below).
4. **Teaching-quality**: passes ambiguity/triviality/well-posedness checks; distractors map to named misconceptions.

Any failure → the card is blocked and logged, never displayed. This is a *hard* gate, not a soft score.

### Leakage check (ESTABLISHED detection methods)
The app must not regurgitate source problems verbatim or near-verbatim:
- **N-gram overlap:** flag any generated stem sharing a long n-gram with a source item. GPT-3 used a **13-gram** collision threshold (Brown et al., 2020, arXiv:2005.14165); GPT-4 used a ~50-character overlap. Simple and fast but defeated by paraphrase (Yang et al., *Rephrased Samples*, arXiv:2311.04850 — "N-gram overlap detection… can result in a higher false negative rate if there's a small difference").
- **MinHash + LSH near-duplicate detection** (Lee et al., *Deduplicating Training Data Makes Language Models Better*, ACL 2022, arXiv:2107.06499): approximates Jaccard similarity; typical config 128–256 hashes over 5-grams, similarity threshold ~0.85. The paper found "over 1% of the unprompted output of language models trained on these datasets is copied verbatim from the training data." Add embedding cosine similarity (Sentence-BERT) for semantic near-duplicates.
- **Membership/contamination audits** (to check whether the generator is parroting training/source data): **Min-K% Prob** (Shi et al., 2023, arXiv:2310.16789) and **Min-K%++** (arXiv:2404.02936); **Proving Test Set Contamination** (Oren et al., 2023, arXiv:2310.17623, an exchangeability test with p-value guarantees); **Time Travel in LLMs** (Golchin & Surdeanu, 2023, arXiv:2308.08493, guided-instruction completion, 92–100% detection accuracy).

**Policy:** reject any card above the n-gram or similarity threshold against the source corpus and existing bank.

## 5. Creative / Unconventional Uses of AI for Math Mastery
*(Methods tie to research where available; "SPECULATIVE" labels flag unproven design ideas.)*

- **Minimally-different distractors from mal-rules (ESTABLISHED basis).** Generate plausible wrong answers by executing *buggy procedures* rather than random perturbation. Grounded in **Brown & Burton, "Diagnostic Models for Procedural Bugs in Basic Mathematical Skills"** (*Cognitive Science*, 1978; DOI 10.1207/s15516709cog0202_4) — the "BUGGY" model representing student errors as discrete modifications to correct skills (diagnosed 1,300 students; 39% showed consistent buggy borrowing behavior) — and **Brown & VanLehn's Repair Theory** (1980). Modern distractor-generation research: **DiVERT** (Feng et al., 2024, arXiv:2406.19356, variational error representation), overgenerate-and-rank (arXiv:2405.05144), in-context distractor+feedback generation (arXiv:2308.03234), and human-LLM collaboration (arXiv:2405.00864). For symbolic items, implement mal-rules in the CAS (e.g., the product-rule bug `d/dx[f·g] → f'·g'`) and compute the distractor exactly — giving *correct-by-construction wrong answers* tied to a named misconception.
- **Targeted counterexamples to a student's wrong reasoning (SPECULATIVE, CAS-feasible).** When a student asserts a false general claim (e.g., "every continuous function is differentiable"), use the CAS / a known-counterexample library to surface a minimal counterexample (Weierstrass function; |x| at 0). Feasible because the verifier already exists; not yet a validated product feature.
- **Prerequisite-weakness probes via a knowledge graph (ESTABLISHED basis).** Tie each item to nodes in a prerequisite knowledge graph (the GraphRAG concept graph), then generate items that isolate the suspected weak prerequisite. Supported by knowledge-graph-assisted retrieval and short-answer-grading-with-GraphRAG work (arXiv:2603.19276).
- **IRT-anchored difficulty-calibrated variants (ESTABLISHED basis).** Automatic Item Generation (AIG) with IRT calibrates item difficulty (b-parameter) and discrimination (a-parameter); cognitive-model features predict difficulty (Gierl & Lai; Arendasy's min–max approach). Difficulty-controllable generation: Susanti et al. (2017, controlling item difficulty), Tomikawa & Uto (2024, IRT-based difficulty-controllable MCQ), **AutoIRT** (arXiv:2409.08823), and **SMART** (simulated students aligned with IRT, arXiv:2507.05129). For symbolic schemas, difficulty knobs (coefficient size, step count, presence of fractions) map to measured difficulty after pilot data.
- **Misconception/error-pattern modeling (ESTABLISHED).** Maintain a catalog of named misconceptions per topic; each distractor and diagnostic item links to one. Brown–Burton lineage + DiVERT error-explanation generation.
- **Adversarial "trap" problems (SPECULATIVE).** Deliberately construct items where the most tempting heuristic fails (e.g., a limit that looks like it needs L'Hôpital but doesn't). The trap = the mal-rule path; correctness still gated by CAS. Pedagogically motivated by misconception research, but the "trap generator" itself is an unproven design.
- **Self-explanation grading + Socratic follow-ups (SPECULATIVE).** Use a tool-checked LLM to evaluate a student's free-text reasoning and generate the next probe. Reliability limited by LLM-judge biases (§2v) — keep a human in the loop.

## 6. Concrete Recommended Stack + Eval Design

### Recommended buildable stack (~1-week, ships with AI toggle-off)
- **Source ingestion:** parse a named, licensed source (e.g., one open textbook / problem set); chunk by section/theorem; strip hidden PDF text; treat as untrusted data.
- **Retrieval:** BM25 (e.g., Elasticsearch / `rank_bm25`) + dense bi-encoder (e.g., `bge`/E5 via FAISS) → **RRF fusion** (k=60) → **cross-encoder rerank** (`bge-reranker` or Cohere Rerank) to top-k. Optional GraphRAG concept graph for provenance.
- **Generation engine:** LLM proposes a *symbolic schema* (SymPy expression + constraints + intended skill + source passage ID), not a finished problem.
- **Instantiation + CAS verifier (primary gate):** SymPy instantiates parameters, computes the answer key and worked solution, and verifies via `simplify(diff)==0` + a random-point numerical check (ε=10⁻⁹). SageMath for number-theory/abstract-algebra items.
- **Optional proof lane:** Lean 4 + mathlib via LeanDojo/ReProver for a small subset of proof items, best-effort only.
- **Distractors:** mal-rule execution in CAS + DiVERT-style misconception tagging.
- **RAG attribution check:** verify the cited passage supports the item (citation precision).
- **Leakage + quality gate:** MinHash/LSH + embedding similarity (reject ≥0.85 or 13-gram match); ambiguity/triviality/well-posedness checks; tool-checked diverse-model LLM judge for teaching quality.
- **Gold-set gate:** hard pre-display filter combining all the above.
- **AI toggle-off:** ship a curated, human-verified static bank so the entire app works with AI disabled — the AI layer only *adds* generated cards on top.

### Evaluation design (with pre-registered cutoffs)
The project's **"7f AI card check"**: assemble **50 gold Q&A pairs** (human-verified, from the named source); **generate 50 cards from one real source passage set**; have graders (blind, with CAS access) classify each generated card and report **3 counts**:
- **(a) ACCURACY — correct & useful:** fraction of cards that are mathematically correct AND pedagogically useful.
- **(b) WRONG-ANSWER RATE — fraction with a wrong fact:** the worst failure; a card whose stated answer/solution is mathematically false.
- **(c) CORRECT-BUT-BAD-TEACHING RATE:** correct answer but vague/trivial/duplicate/ambiguous/multi-answer.

**Pre-set passing cutoffs (state BEFORE looking at results):**
- Wrong-answer rate **≤ 2%** (i.e., ≤1 of 50). Rationale: this is the project's red line; if a verified pipeline lets a wrong fact through, the gate has failed. Ideally **0%** post-gate, since CAS verification should catch all computational errors; a non-zero rate indicates a verifier gap.
- Accuracy (correct & useful) **≥ 80%** (≥40/50).
- Correct-but-bad-teaching **≤ 15%**.
- **Leakage check:** 0 cards exceeding the 13-gram / 0.85-similarity threshold against the source corpus (any leak = automatic fail of that card).

**Baseline comparison (must show full RAG beats keyword/vector):** on the **50 gold pairs**, measure retrieval quality (Recall@k, nDCG@k, MRR) for three systems: (1) BM25-only, (2) single dense vector only, (3) full hybrid+RRF+reranker. Pre-register that the full system must beat the better of the two baselines by a meaningful margin (e.g., **≥5 points Recall@10** — conservative relative to the +12pp Recall@5 / +17pp MRR@3 reranker gains and the 9–19pp DPR-over-BM25 gains in the literature). Also report end-to-end card-quality metrics (a/b/c above) for cards generated under each retrieval condition, to show grounding quality propagates to card quality. Use a held-out gold set the generator never saw, to avoid leakage inflating results.

**Why these cutoffs change decisions:** if wrong-answer rate > 0 after the CAS gate, *stop and fix the verifier* (it means an item type bypassed symbolic checking — add a numerical fallback or block that item class). If bad-teaching > 15%, tighten the ambiguity/triviality filters and distractor-misconception mapping. If the full RAG system does *not* beat baselines on the gold set, the reranker or fusion weighting is misconfigured — re-tune before shipping generated cards.

## Recommendations
1. **Week-1 critical path:** (i) stand up the SymPy verifier + numerical fallback first (it's the gate); (ii) write 10–15 symbolic schemas covering calculus, linear algebra, and probability (the bulk of GRE Math); (iii) wire hybrid retrieval + reranker; (iv) implement the leakage + gold-set gate; (v) only then add LLM schema-proposal for novelty. Ship the human-verified static bank in parallel so AI-off works on day one.
2. **Make the gate hard, not advisory.** No card reaches a student without passing CAS verification + grounding + leakage + quality. Log every blocked card for review.
3. **Use the LLM for what it's good at** (novelty, language, distractor ideation, teaching-quality judgment) and never for final answer authority. Wrap LLM judgments in tool checks and diverse-model majority voting.
4. **Defer the proof-assistant lane** unless proof items are essential; its coverage (26.5% miniF2F, 13.8% ProofNet for ReProver) doesn't justify week-1 cost. Keep CAS+numerical as the universal gate.
5. **Pre-register the cutoffs above** and run the 7f check on a held-out gold set before any launch decision. Treat wrong-answer rate as a release blocker.

### Thresholds that would change the plan
- Wrong-answer rate > 0% post-gate → halt; the verifier has a coverage hole.
- Hybrid RAG fails to beat BM25/dense baseline on gold Recall@10 → re-tune fusion/reranker before shipping generated cards.
- Bad-teaching rate > 15% → strengthen ambiguity/triviality/distractor filters.
- Any verbatim/near-duplicate leak → block the item; if systemic, increase paraphrase distance and add semantic dedup.

## Caveats
- **Equivalence checking is undecidable in general** and CAS is brittle to surface form; always pair symbolic with numerical checks and canonicalize. A "verified" item is verified *modulo* the CAS's own correctness and the canonicalization.
- **Autoformalization metrics are often inflated** (miniF2F-Lean Revisited): LLM-graded formalization correctness overstates true performance — don't over-trust the proof lane.
- **LLM-as-judge is biased** (position, verbosity, self-enhancement, agreeableness); reliability is modest and cannot be the sole quality signal.
- **Hallucination is not fully eliminable**; the architecture *contains* it via gating rather than curing it.
- **Several 2025–2026 sources are arXiv preprints** (e.g., contradiction-in-RAG arXiv:2504.00180, SymCode, adaptive symbolic generation, the BM25→Corrective-RAG benchmark) not yet peer-reviewed — treat as promising, not settled.
- **GRE Subject Test specificity:** the GRE Mathematics Subject Test is multiple-choice and computational/conceptual, which *favors* the CAS-gate approach (answers are checkable) over free-form proof verification; calibrating to the real exam's difficulty distribution still requires pilot response data for IRT.

## References (URLs)
- Adaptive Problem Generation via Symbolic Representations — https://arxiv.org/abs/2602.19187
- Li et al., Neuro-Symbolic Data Generation for Math Reasoning — https://arxiv.org/abs/2412.04857
- Tang et al., MathScale (ICML 2024) — https://arxiv.org/abs/2403.02884
- Polozov et al., Personalized Mathematical Word Problem Generation (IJCAI 2015) — https://www.ijcai.org/Proceedings/15/Papers/060.pdf
- Template-Driven LLM-Paraphrased Tabular MWP Generation — https://arxiv.org/abs/2412.15594
- Towards Generating Controllable & Solvable Geometry Problems — https://arxiv.org/abs/2506.02565
- Benchmarking Hallucination via Unanswerable MWP (UMWP) — https://arxiv.org/abs/2403.03558
- Self-Consistency-Based Hallucination Detection in Math — https://arxiv.org/abs/2504.09440
- FG-PRM: Fine-grained Hallucination Detection/Mitigation — https://openreview.net/forum?id=klzOWiyYn6
- SymCode: Neurosymbolic Mathematical Reasoning — https://arxiv.org/abs/2510.25975
- Symbolic Recursive Self-Alignment (multi-check verification) — https://arxiv.org/abs/2603.21558
- SymPy — https://www.sympy.org ; SageMath — https://www.sagemath.org
- Draft, Sketch, and Prove — https://arxiv.org/abs/2210.12283
- LeanDojo / ReProver — https://arxiv.org/abs/2306.15626 ; docs https://leandojo.readthedocs.io
- ProofNet — https://arxiv.org/abs/2302.12433
- miniF2F-Lean Revisited — https://arxiv.org/abs/2511.03108
- AlphaProof/AlphaGeometry (Nature 2025) — https://www.nature.com/articles/s41586-025-09833-y ; DeepMind blog — https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/
- TALE: Tool-Augmented Reference-Free Evaluation — https://arxiv.org/abs/2504.07385
- Lewis et al., RAG — https://arxiv.org/abs/2005.11401
- Karpukhin et al., DPR — https://arxiv.org/abs/2004.04906
- Khattab & Zaharia, ColBERT — https://arxiv.org/abs/2004.12832 ; ColBERTv2 — https://arxiv.org/abs/2112.01488
- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009) — https://doi.org/10.1561/1500000019
- Cormack et al., Reciprocal Rank Fusion (SIGIR 2009) — https://doi.org/10.1145/1571941.1572114
- From BM25 to Corrective RAG (hybrid/RRF/reranker benchmark) — https://arxiv.org/abs/2604.01733
- Math Information Retrieval — token/passage dense models — https://arxiv.org/abs/2203.11163
- Nogueira & Cho, Passage Re-ranking with BERT — https://arxiv.org/abs/1901.04085 ; monoT5 — https://arxiv.org/abs/2003.06713
- bge-reranker — https://huggingface.co/BAAI/bge-reranker-base ; Cohere Rerank — https://cohere.com/rerank
- Microsoft GraphRAG — https://www.microsoft.com/en-us/research/project/graphrag/ ; https://github.com/microsoft/graphrag
- RAG vs GraphRAG for math textbook page-level QA — https://arxiv.org/abs/2509.16780
- Bohnet et al., Attributed QA — https://arxiv.org/abs/2212.08037
- Faithfulness/citation evaluation surveys — https://arxiv.org/abs/2406.15264 ; https://arxiv.org/abs/2501.00269 ; CaLM — https://arxiv.org/abs/2406.05365
- OWASP Top 10 for LLM Applications 2025 — https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Greshake et al., Indirect Prompt Injection — https://arxiv.org/abs/2302.12173
- Hines et al., Spotlighting — https://arxiv.org/abs/2403.14720
- de Marneffe et al., Finding Contradictions in Text (ACL 2008) — https://aclanthology.org/P08-1118/
- SummaC — https://arxiv.org/abs/2111.09525
- FactCC — https://arxiv.org/abs/1910.12840 ; QAFactEval — https://arxiv.org/abs/2112.08542
- SparseCL — https://arxiv.org/abs/2406.10746 ; Contradiction Detection in RAG — https://arxiv.org/abs/2504.00180
- SelfCheckGPT — https://arxiv.org/abs/2303.08896
- Brown & Burton, Diagnostic Models for Procedural Bugs (Cognitive Science 1978) — https://doi.org/10.1207/s15516709cog0202_4
- DiVERT — https://arxiv.org/abs/2406.19356 ; Overgenerate-and-rank distractors — https://arxiv.org/abs/2405.05144 ; In-context distractor+feedback — https://arxiv.org/abs/2308.03234 ; Human-LLM MCQ collaboration — https://arxiv.org/abs/2405.00864
- AutoIRT — https://arxiv.org/abs/2409.08823 ; SMART (IRT simulated students) — https://arxiv.org/abs/2507.05129
- Short-answer grading with GraphRAG — https://arxiv.org/abs/2603.19276
- Brown et al., GPT-3 (13-gram contamination) — https://arxiv.org/abs/2005.14165 ; Rephrased Samples — https://arxiv.org/abs/2311.04850
- Lee et al., Deduplicating Training Data — https://arxiv.org/abs/2107.06499 (ACL: https://aclanthology.org/2022.acl-long.577/)
- Min-K% Prob — https://arxiv.org/abs/2310.16789 ; Min-K%++ — https://arxiv.org/abs/2404.02936
- Proving Test Set Contamination — https://arxiv.org/abs/2310.17623 ; Time Travel in LLMs — https://arxiv.org/abs/2308.08493
- GSM8K (Cobbe et al., 2021) — https://arxiv.org/abs/2110.14168 ; MATH (Hendrycks et al., 2021) — https://arxiv.org/abs/2103.03874 ; MathQA (Amini et al., 2019) — https://arxiv.org/abs/1905.13319