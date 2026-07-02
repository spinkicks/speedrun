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
| `corpus/gre_math_sources.jsonl` | Vendored corpus of 56 source passages (JSONL). |
| `retriever.py` | `HybridRetriever` (BM25 + dense → RRF) + `ground()` adapter. |
| `eval_inhouse.py` | In-house `(query, expected_id)` eval; Recall@k per arm. |

## Corpus provenance

- **56 passages**, covering all 9 scored leaf topics (5–7 each):
  `calc::limits` (6), `calc::single_var::differentiation` (7),
  `calc::single_var::integration` (7), `calc::sequences_series` (7),
  `calc::multivar` (7), `linear_algebra::vector_spaces` (6),
  `linear_algebra::matrices` (5), `linear_algebra::eigen` (5),
  `linear_algebra::linear_maps` (6).
- Each row: `{id, topic_id, title, text, source_citation}`. `text` is a faithful
  2–5 sentence summary of a real textbook section's key definitions / theorems /
  techniques.
- **Citations are real named sections**, reusing the style of
  `repos/anki/speedrun/seed/cards_calc.yaml`:
  **OpenStax Calculus Vol. 1/2/3** (CC BY 4.0) for calculus and
  **Hefferon, *Linear Algebra*** (free license) for linear algebra. No citation
  is fabricated or a placeholder — the corpus-integrity tests enforce this.
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

citation = r.ground(candidate, min_score=0.01)   # str | None (abstain gate)
graph_fn = r.as_graph_retriever(min_score=0.01)  # candidate -> citation|None
```

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
