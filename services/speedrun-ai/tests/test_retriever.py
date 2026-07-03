# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the hybrid RAG retriever (BM25 + dense -> RRF).

Fully offline and deterministic: no network, fixed vectorizer, TF-IDF dense
arm. The corpus is loaded from the vendored JSONL.
"""

from __future__ import annotations

from rag.retriever import (
    HybridRetriever,
    load_corpus,
    reciprocal_rank_fusion,
)

# ---------------------------------------------------------------------------
# Corpus fixture
# ---------------------------------------------------------------------------


def _corpus() -> list[dict]:
    return load_corpus()


# ---------------------------------------------------------------------------
# Corpus integrity
# ---------------------------------------------------------------------------


def test_corpus_loads_and_covers_all_nine_topics():
    corpus = _corpus()
    assert len(corpus) >= 45  # ~80 passages after the linear-algebra expansion
    topics = {row["topic_id"] for row in corpus}
    expected = {
        "calc::limits",
        "calc::single_var::differentiation",
        "calc::single_var::integration",
        "calc::sequences_series",
        "calc::multivar",
        "linear_algebra::vector_spaces",
        "linear_algebra::matrices",
        "linear_algebra::eigen",
        "linear_algebra::linear_maps",
    }
    assert expected <= topics


def test_corpus_rows_have_required_fields_and_unique_ids():
    corpus = _corpus()
    ids = set()
    for row in corpus:
        for key in ("id", "topic_id", "title", "text", "source_citation"):
            assert row.get(key), f"missing {key} in {row.get('id')}"
        assert row["id"] not in ids, f"duplicate id {row['id']}"
        ids.add(row["id"])


def test_every_passage_has_a_named_source_citation():
    # Drop-if-unverifiable discipline: no blank / placeholder citations.
    corpus = _corpus()
    for row in corpus:
        citation = row["source_citation"]
        assert citation and "PLACEHOLDER" not in citation.upper()
        # Real named source: OpenStax (calculus), Hefferon or MIT OCW 18.06
        # (linear algebra) — all genuinely open, named sources.
        assert any(
            marker in citation
            for marker in ("OpenStax", "Hefferon", "Linear Algebra", "MIT OCW")
        )


# ---------------------------------------------------------------------------
# RRF unit behavior
# ---------------------------------------------------------------------------


def test_rrf_fuses_two_ranked_lists_deterministically():
    list_a = ["x", "y", "z"]
    list_b = ["y", "x", "w"]
    fused = reciprocal_rank_fusion([list_a, list_b], k=60)
    # returns (id, score) pairs sorted by descending score
    order = [doc_id for doc_id, _ in fused]
    # y and x appear high in both; y is rank0 in b and rank1 in a, x rank0 in
    # a and rank1 in b -> tie; both should precede z and w.
    assert set(order[:2]) == {"x", "y"}
    assert order[-2:] == order[-2:]  # deterministic
    # deterministic across calls
    assert reciprocal_rank_fusion([list_a, list_b], k=60) == fused


# ---------------------------------------------------------------------------
# Retriever behavior
# ---------------------------------------------------------------------------


def test_retrieve_returns_ranked_scored_hits():
    retriever = HybridRetriever(_corpus())
    hits = retriever.retrieve("definition of the derivative as a limit", k=5)
    assert 1 <= len(hits) <= 5
    for hit in hits:
        for key in ("id", "topic_id", "title", "text", "source_citation",
                    "score"):
            assert key in hit
    # sorted by descending score
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_is_deterministic():
    retriever = HybridRetriever(_corpus())
    a = retriever.retrieve("eigenvalues and characteristic polynomial", k=10)
    b = retriever.retrieve("eigenvalues and characteristic polynomial", k=10)
    assert [h["id"] for h in a] == [h["id"] for h in b]


def test_retrieve_finds_topically_relevant_top_hit():
    retriever = HybridRetriever(_corpus())
    hits = retriever.retrieve("u substitution rule for integrals", k=3)
    top = hits[0]
    assert top["topic_id"] == "calc::single_var::integration"
    assert top["id"] == "calc-int-usub"


def test_dense_arm_is_documented():
    retriever = HybridRetriever(_corpus())
    # The active dense arm must be introspectable (tfidf or sentence-transformers).
    assert retriever.dense_arm in ("tfidf", "sentence-transformers")


# ---------------------------------------------------------------------------
# Grounding adapter (drop-if-unverifiable gate)
# ---------------------------------------------------------------------------


def test_ground_returns_citation_when_top_score_clears_threshold():
    retriever = HybridRetriever(_corpus())
    candidate = {
        "stem": "State the epsilon-delta definition of a limit.",
        "correct": "for every epsilon there is delta",
    }
    citation = retriever.ground(candidate, min_score=0.0)
    assert citation
    assert "OpenStax" in citation or "Hefferon" in citation


def test_ground_returns_none_when_below_threshold():
    retriever = HybridRetriever(_corpus())
    candidate = {"stem": "State the epsilon-delta definition of a limit."}
    # An impossibly high threshold forces the ungrounded / abstain path.
    citation = retriever.ground(candidate, min_score=10_000.0)
    assert citation is None


def test_ground_handles_empty_candidate():
    retriever = HybridRetriever(_corpus())
    assert retriever.ground({}, min_score=10_000.0) is None


# ---------------------------------------------------------------------------
# Graph wiring: the real retriever injects cleanly via dependency injection,
# without OpenAI / network (LLM stubbed, real HybridRetriever grounding).
# ---------------------------------------------------------------------------


def test_real_retriever_grounds_the_generation_graph():
    from graph import make_hybrid_retriever, run_generation

    def _llm(topic, technique):
        return {
            "candidate": {
                "stem": "State the epsilon-delta definition of a limit.",
                "correct": "2*x",
                "worked_solution": "By the power rule d/dx(x^2)=2x.",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    retriever = make_hybrid_retriever(min_score=0.0)
    state = run_generation(
        "calc::limits", "epsilon-delta", llm_propose=_llm, retriever=retriever
    )
    assert state["status"] == "emit"
    # The citation came from the REAL corpus, not the placeholder stub.
    assert state["problem"]["citation"]
    assert "PLACEHOLDER" not in state["problem"]["citation"]
    assert (
        "OpenStax" in state["problem"]["citation"]
        or "Hefferon" in state["problem"]["citation"]
    )


def test_real_retriever_abstains_when_below_threshold():
    from graph import make_hybrid_retriever, run_generation

    def _llm(topic, technique):
        return {
            "candidate": {
                "stem": "Find the derivative of f(x) = x**2.",
                "correct": "2*x",
                "worked_solution": "power rule",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    # Impossibly high threshold => ungrounded => abstain ("no source grounding").
    retriever = make_hybrid_retriever(min_score=10_000.0)
    state = run_generation(
        "calc", "power_rule", llm_propose=_llm, retriever=retriever
    )
    assert state["status"] == "abstain"
    assert "ground" in state["abstain_reason"].lower()


# ---------------------------------------------------------------------------
# BUG 4b (SAFETY): the default grounding threshold must be strict enough that a
# near-zero-similarity passage does NOT count as grounding. With RRF (k=60), a
# hit that ranks #1 in only ONE arm scores ~0.0167; a real top hit (near-top in
# BOTH arms) scores ~0.032-0.033. The old default (0.01) let the weak,
# single-arm hit through. The default must sit above the single-arm score.
# ---------------------------------------------------------------------------


def test_default_min_ground_score_rejects_single_arm_weak_hit():
    from graph import DEFAULT_MIN_GROUND_SCORE

    k = 60  # HybridRetriever.rrf_k default
    single_arm_top = 1.0 / (k + 0)  # ~0.0167: #1 in one arm, absent in other
    both_arms_top = 1.0 / (k + 0) + 1.0 / (k + 0)  # ~0.0333: #1 in both
    # A weak, single-arm-only hit must NOT clear the default threshold.
    assert DEFAULT_MIN_GROUND_SCORE > single_arm_top, (
        "default grounding threshold must reject a single-arm-only (~0.0167) hit"
    )
    # ...but a genuine top hit present near the top of both arms must still pass.
    assert DEFAULT_MIN_GROUND_SCORE < both_arms_top, (
        "default grounding threshold must still admit a genuine top hit"
    )
