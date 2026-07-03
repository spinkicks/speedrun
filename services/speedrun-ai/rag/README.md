<!--
Copyright: Speedrun contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
# RAG source-grounding (Phase 4, Task 4.3)

Hybrid retriever that grounds every AI-generated GRE-math problem in a **real,
named source**. If a candidate problem cannot be grounded above a threshold, the
generation graph takes its `abstain` ("no source grounding") path and the
problem is **dropped**. This is the drop-if-unverifiable gate.

## Files

| File | Purpose |
| --- | --- |
| `corpus/gre_math_sources.jsonl` | Vendored corpus of 82 source passages (JSONL). |
| `retriever.py` | `HybridRetriever` (BM25 + dense → RRF) + `ground()` adapter. |
| `eval_inhouse.py` | In-house `(query, expected_id)` eval; Recall@k per arm. |

## Corpus provenance

- **82 passages**, covering all 9 scored leaf topics:
  `calc::limits` (6), `calc::single_var::differentiation` (7),
  `calc::single_var::integration` (7), `calc::sequences_series` (7),
  `calc::multivar` (7), `linear_algebra::vector_spaces` (12),
  `linear_algebra::matrices` (12), `linear_algebra::eigen` (11),
  `linear_algebra::linear_maps` (13).
- The four linear-algebra leaves were **broadened** (from 5–6 to 11–13 passages
  each) on **domain grounds** — the §7f coverage diagnostic flagged that the
  original corpus was missing canonical open LA sources. The 26 added passages
  cover eigenvalues/eigenvectors/diagonalization, determinants/inverses/rank,
  vector spaces/subspaces/basis/dimension, and linear maps/rank-nullity, split
  between **Hefferon** (12) and **MIT OCW 18.06** (14). This expansion is
  **topic-driven, not gold-driven**: no `eval/holdout/` content was ever read.
- Each row: `{id, topic_id, title, text, source_citation}`. `text` is a faithful
  2–5 sentence summary of a real textbook section's key definitions / theorems /
  techniques.
- **Citations are real named sections**, reusing the style of
  `repos/anki/speedrun/seed/cards_calc.yaml`:
  **OpenStax Calculus Vol. 1/2/3** (CC BY 4.0) for calculus,
  **Hefferon, *Linear Algebra*** (free license, cited at chapter granularity),
  and **MIT OCW 18.06 *Linear Algebra* (Strang)** (MIT OpenCourseWare open
  license, cited at lecture granularity). No citation is fabricated or a
  placeholder — the corpus-integrity tests enforce this.
- Content is AI-authored (Friday permits it) but mathematically checked against
  the cited sources. It was **not** copied from `eval/holdout/` (the held-out
  gold set), which this stage never reads.

## Retriever design

Two ranking arms fused with **Reciprocal Rank Fusion (RRF)**:

- **Sparse arm — BM25** (`rank-bm25`, `BM25Okapi`). Pure-Python, offline,
  deterministic. Documents are `"{title}. {text}"`; lowercase alphanumeric
  tokenization.
- **Dense arm — TF-IDF cosine** (`scikit-learn` `TfidfVectorizer`, unigrams +
  bigrams, `sublinear_tf=True`) + cosine similarity.
  - A real bi-encoder (`sentence-transformers` `all-MiniLM-L6-v2`) is
    **preferred** and attempted first (`_try_load_sentence_transformer`, forced
    `HF_HUB_OFFLINE`), but it is used **only if the model loads with no
    network**. In this fresh worktree the weights are **not cached** and the
    heavyweight `torch`/model download is not hermetic, so the retriever falls
    back to the **TF-IDF dense arm**. The active arm is recorded on
    `HybridRetriever.dense_arm` (`"tfidf"` here) and asserted in tests. This
    keeps tests offline and deterministic.
- **Fusion — RRF, k = 60** (the standard constant). Score of a doc =
  Σ over arms of `1 / (k + rank)`; ties broken by first appearance (stable →
  fully deterministic).
- **Optional rerank — skipped.** A cross-encoder reranker is not trivially
  available offline in this environment, so no rerank stage runs. The code path
  is a clean extension point.

### API

```python
from rag.retriever import HybridRetriever, load_corpus

r = HybridRetriever(load_corpus())         # deterministic, offline
hits = r.retrieve("u substitution for integrals", k=10)
# -> [{id, topic_id, title, text, source_citation, score}, ...] desc by score

citation = r.ground(candidate, min_score=0.03)   # str | None (abstain gate)
graph_fn = r.as_graph_retriever(min_score=0.03)  # candidate -> citation|None
```

### Grounding gate: SEMANTIC relevance (embeddings)

`ground()` returns a citation only when the candidate is genuinely *on topic* for
some corpus passage. RRF's fused score is rank-based and relevance-blind (a junk
doc landing #1 in both arms scores the same as a real hit), so the **decisive**
signal is the **semantic cosine** between the query and its fused top passage,
computed with real OpenAI embeddings (`text-embedding-3-small`), which must clear
`SEMANTIC_GROUND_THRESHOLD` (default **0.33**, env-overridable). Two cheap lexical
guards flank it (>= 1 shared token; a discriminative-anchor concentration guard)
to also reject in-domain keyword-bags a pure cosine cannot. Conservative — any
doubt abstains.

- **Injectable embedder** (`rag/embeddings.py`): the real `OpenAIEmbedder` is
  built lazily only when a key is present (the enabled path); tests inject a
  deterministic stub, so CI stays offline. Corpus-passage embeddings are cached
  (computed once).
- **Calibration** (on real embeddings, never touching `eval/holdout/`): off-topic
  prose tops out at cosine ≈0.29; genuine covered stems sit at 0.37–0.71, so 0.33
  sits in the gap. Verified by **four independent adversarial passes**: off-topic
  prose — including topic-adjacent finance/physics/CS text and single-math-anchor
  sentences ("My cat is named Eigenvalue…") — abstains; genuine terse stems
  ("Compute the determinant.", "Does the series converge?") ground.
- The gate lives **only** in `ground()`; the eval arms (`retrieve`,
  `retrieve_bm25`, `retrieve_dense`) are untouched, so **Recall@10 is unchanged**.

This is the third iteration of the gate. Two earlier *lexical* gates were each
defeated by a fresh adversary: (1) a word-COUNT heuristic (>= 4 distinct corpus
tokens) fell to off-topic English built from everyday-words-that-are-also-math;
(2) a 3-signal topicality gate (discriminative overlap + per-passage
concentration + a raw 0.12 cosine floor) fell to a **single** math word in
off-topic prose (one anchor forces concentration → 1.0; the low floor can't
separate a 1-word math overlap from a 1-word off-topic one). Lexical overlap
fundamentally cannot separate "one math word in off-topic prose" from "a genuine
terse math stem"; the semantic embedding gate can.

#### Known limitation: coverage-gap mis-citation (honest disclosure)

A *genuine* math question on a topic the corpus does **not** cover (e.g. ODEs /
separation of variables, arc length, partial-fraction integration, PCA) can
ground to the nearest *in-domain but unsupporting* passage at cosine 0.35–0.43 —
a **misleading citation**. The covered-stem and uncovered-mis-cite cosine
distributions **overlap** (≈0.37 vs <= 0.43), so no single fixed threshold
separates "near-neighbor covered passage" from "actually-supported passage" when
the true source is simply absent (a *similarity ≠ entailment* problem).

- **Impact is bounded:** the AI service is **OFF by default**; the study app never
  depends on it; the hard safety gates (SymPy symbolic verification + gold-set
  leakage) are independent and unaffected. In normal use the proposer is asked for
  topics drawn from the exam syllabus, and covered topics ground correctly.
- **Robust fix (future work):** augment the cosine floor with an
  **entailment/support check** ("does this passage actually support this
  problem?") — an NLI or LLM-judge call — since the failure mode is an absent
  source, not an out-ranked one. Merely raising the floor toward ~0.45 would
  reject most mis-citations but trade recall on genuinely covered terse stems.

## In-house eval (NOT the §7f gold set)

`eval_inhouse.py` holds **18 author-written `(query, expected_id)` pairs**
(2 per scored leaf topic). These are our own paraphrase queries — **not** drawn
from `eval/holdout/`. Recall@k = fraction of pairs whose `expected_id` appears
in the top-k.

Run: `uv run python -m rag.eval_inhouse`

| Configuration | Recall@10 |
| --- | --- |
| BM25-only | 1.000 (18/18) |
| dense-only (TF-IDF) | 1.000 (18/18) |
| **hybrid (RRF)** | **1.000 (18/18)** |

**Required invariant met:** hybrid Recall@10 ≥ each single-arm baseline
(the test asserts this). On this small, well-separated corpus all three arms
saturate at 1.0 on realistic queries, so the honest result is a **tie at the
ceiling** — RRF does not *regress* below the better arm (the real risk it
guards against). We deliberately do **not** manufacture a strict win that isn't
robustly present; on adversarial hard-paraphrase probes RRF sometimes trails the
single best arm at strict low-k, which is expected behavior for rank fusion on a
tiny index.

## Honesty note

This in-house eval is a fast, hermetic sanity gate only. The **formal §7f gate**
— "beat the baseline by ≥ 5 points on the 50 gold pairs" — runs in **Task 4.4**
against `eval/holdout/`, which is intentionally never touched by this stage so
retriever construction stays independent of the held-out set.

## Determinism & offline guarantees

- No network at test time; no random seeds consumed at retrieval time.
- BM25, TF-IDF, and RRF are pure functions of the corpus + query → byte-stable
  results across runs (`test_retrieve_is_deterministic`, `test_eval_is_deterministic`).
- AGPL header on every `.py`.

## Graph wiring (dependency injection preserved)

`graph.make_hybrid_retriever(corpus=None, min_score=0.01)` builds the real
grounding closure and is injected by `app.generate_problem` (the enabled
OpenAI path). The graph's `default_retriever` remains a **stub**, so the 45
existing graph/app unit tests keep stubbing and never build an index or hit the
network. The real retriever is imported lazily inside `make_hybrid_retriever`.
