# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
In-house retrieval eval for the hybrid RAG retriever.

We author our OWN ``(query, expected_id)`` pairs here (NOT the §7f gold set,
which lives under ``eval/holdout/`` and is never read by this stage). For each
configuration — BM25-only, dense-only, and the full hybrid — we compute
Recall@k: the fraction of pairs whose ``expected_id`` appears in the top-``k``.

The purpose is a fast, hermetic sanity gate that the fusion does not REGRESS
below either single arm. The formal "beat baseline by >= 5 points on the 50
gold pairs" gate is Task 4.4.

Run standalone to print a small report::

    uv run python -m rag.eval_inhouse
"""

from __future__ import annotations

from rag.retriever import HybridRetriever, load_corpus

# ---------------------------------------------------------------------------
# Author-written eval pairs (18 pairs; 2 per scored leaf topic).
# Queries are paraphrases a student might type — NOT copied from any passage
# verbatim and NOT drawn from eval/holdout/.
# ---------------------------------------------------------------------------

EVAL_PAIRS: list[dict] = [
    # calc::limits
    {
        "query": "formal definition of a limit with epsilon and delta",
        "expected_id": "calc-limits-epsilon-delta",
        "topic_id": "calc::limits",
    },
    {
        "query": "rule for zero over zero indeterminate limits using derivatives",
        "expected_id": "calc-limits-lhopital",
        "topic_id": "calc::limits",
    },
    # calc::single_var::differentiation
    {
        "query": "how to differentiate x to the power n",
        "expected_id": "calc-diff-power-rule",
        "topic_id": "calc::single_var::differentiation",
    },
    {
        "query": "derivative of a composition of functions",
        "expected_id": "calc-diff-chain-rule",
        "topic_id": "calc::single_var::differentiation",
    },
    # calc::single_var::integration
    {
        "query": "u substitution to reverse the chain rule when integrating",
        "expected_id": "calc-int-usub",
        "topic_id": "calc::single_var::integration",
    },
    {
        "query": "theorem linking definite integral to an antiderivative",
        "expected_id": "calc-int-ftc",
        "topic_id": "calc::single_var::integration",
    },
    # calc::sequences_series
    {
        "query": "when does the sum a r to the n converge and to what value",
        "expected_id": "calc-series-geometric",
        "topic_id": "calc::sequences_series",
    },
    {
        "query": "test using the limit of consecutive term ratios for factorials",
        "expected_id": "calc-series-ratio-test",
        "topic_id": "calc::sequences_series",
    },
    # calc::multivar
    {
        "query": "vector of partial derivatives pointing in steepest ascent",
        "expected_id": "calc-multivar-gradient",
        "topic_id": "calc::multivar",
    },
    {
        "query": "optimize a function subject to a constraint using a multiplier",
        "expected_id": "calc-multivar-lagrange",
        "topic_id": "calc::multivar",
    },
    # linear_algebra::vector_spaces
    {
        "query": "linearly independent set that spans the whole space",
        "expected_id": "la-vs-basis",
        "topic_id": "linear_algebra::vector_spaces",
    },
    {
        "query": "number of vectors in a basis is the dimension",
        "expected_id": "la-vs-dimension",
        "topic_id": "linear_algebra::vector_spaces",
    },
    # linear_algebra::matrices
    {
        "query": "a square matrix is invertible when its determinant is nonzero",
        "expected_id": "la-mat-determinant-2x2",
        "topic_id": "linear_algebra::matrices",
    },
    {
        "query": "row reduce to find the rank of a matrix",
        "expected_id": "la-mat-rank",
        "topic_id": "linear_algebra::matrices",
    },
    # linear_algebra::eigen
    {
        "query": "roots of det of A minus lambda I give the eigenvalues",
        "expected_id": "la-eigen-char-poly",
        "topic_id": "linear_algebra::eigen",
    },
    {
        "query": "write A as P D P inverse with eigenvectors as columns",
        "expected_id": "la-eigen-diagonalization",
        "topic_id": "linear_algebra::eigen",
    },
    # linear_algebra::linear_maps
    {
        "query": "dimension of kernel plus dimension of image equals domain dim",
        "expected_id": "la-maps-rank-nullity",
        "topic_id": "linear_algebra::linear_maps",
    },
    {
        "query": "set of vectors that a linear map sends to zero",
        "expected_id": "la-maps-kernel",
        "topic_id": "linear_algebra::linear_maps",
    },
]


# ---------------------------------------------------------------------------
# Recall@k
# ---------------------------------------------------------------------------


def _recall_at_k(rank_fn, k: int) -> tuple[float, int]:
    """Return (recall@k, num_hits) for a ranking function over EVAL_PAIRS.

    ``rank_fn(query, k) -> list[row]`` returns the top-k rows (each with an
    ``id``); a pair is a hit if its ``expected_id`` is among those ids.
    """
    hits = 0
    for pair in EVAL_PAIRS:
        ids = [row["id"] for row in rank_fn(pair["query"], k)]
        if pair["expected_id"] in ids:
            hits += 1
    return hits / len(EVAL_PAIRS), hits


def run_eval(k: int = 10) -> dict:
    """Compute Recall@k for BM25-only, dense-only, and the hybrid.

    Deterministic and offline. Returns a nested report dict.
    """
    corpus = load_corpus()
    retriever = HybridRetriever(corpus)

    bm25_recall, bm25_hits = _recall_at_k(retriever.retrieve_bm25, k)
    dense_recall, dense_hits = _recall_at_k(retriever.retrieve_dense, k)
    hybrid_recall, hybrid_hits = _recall_at_k(retriever.retrieve, k)

    total = len(EVAL_PAIRS)
    return {
        "k": k,
        "num_pairs": total,
        "dense_arm": retriever.dense_arm,
        "bm25_only": {"recall_at_k": bm25_recall, "hits": bm25_hits},
        "dense_only": {"recall_at_k": dense_recall, "hits": dense_hits},
        "hybrid": {"recall_at_k": hybrid_recall, "hits": hybrid_hits},
    }


def _format_report(report: dict) -> str:
    lines = [
        f"In-house RAG eval (k={report['k']}, "
        f"{report['num_pairs']} pairs, dense_arm={report['dense_arm']})",
        "-" * 60,
    ]
    for name in ("bm25_only", "dense_only", "hybrid"):
        entry = report[name]
        lines.append(
            f"  {name:<12} Recall@{report['k']} = "
            f"{entry['recall_at_k']:.3f} "
            f"({entry['hits']}/{report['num_pairs']})"
        )
    best_single = max(
        report["bm25_only"]["recall_at_k"],
        report["dense_only"]["recall_at_k"],
    )
    verdict = (
        "PASS: hybrid >= each baseline"
        if report["hybrid"]["recall_at_k"] >= best_single
        else "FAIL: hybrid regressed below a baseline"
    )
    lines.append("-" * 60)
    lines.append(f"  {verdict}")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print(_format_report(run_eval(k=10)))
