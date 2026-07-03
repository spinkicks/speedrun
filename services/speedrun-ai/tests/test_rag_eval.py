# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
In-house RAG eval: the hybrid retriever must beat (>=) each single-arm baseline
on Recall@10 over our own author-written (query, expected_source_id) pairs.

These pairs are authored HERE and are NOT the §7f gold set under eval/holdout/
(that formal 50-pair gate runs in Task 4.4 and is never read here).
"""

from __future__ import annotations

from rag.eval_inhouse import EVAL_PAIRS, run_eval


def test_eval_pairs_are_self_authored_and_cover_topics():
    # 15-20 author-written pairs across the nine scored leaf topics.
    assert 15 <= len(EVAL_PAIRS) <= 40
    topics = {pair["topic_id"] for pair in EVAL_PAIRS}
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


def test_expected_ids_exist_in_corpus():
    from rag.retriever import load_corpus

    ids = {row["id"] for row in load_corpus()}
    for pair in EVAL_PAIRS:
        assert pair["expected_id"] in ids, pair["expected_id"]


def test_hybrid_recall_at_10_meets_or_beats_each_baseline():
    report = run_eval(k=10)
    bm25 = report["bm25_only"]["recall_at_k"]
    dense = report["dense_only"]["recall_at_k"]
    hybrid = report["hybrid"]["recall_at_k"]
    # The hybrid must be at least as good as EACH single arm.
    assert hybrid >= bm25, (hybrid, bm25)
    assert hybrid >= dense, (hybrid, dense)
    # And it should be a strong retriever in absolute terms.
    assert hybrid >= 0.8


def test_hybrid_no_worse_than_best_single_arm_at_k10():
    # The task REQUIRES hybrid >= each baseline (>=, not strictly >). On this
    # small, well-separated corpus all three arms saturate Recall@10 = 1.0 on
    # realistic queries, so the honest outcome is a TIE at the top. We assert
    # the hybrid never REGRESSES below the best single arm (the real risk with
    # RRF), and we do NOT fabricate a strict win that isn't robustly present.
    report = run_eval(k=10)
    best_single = max(
        report["bm25_only"]["recall_at_k"],
        report["dense_only"]["recall_at_k"],
    )
    assert report["hybrid"]["recall_at_k"] >= best_single


def test_eval_is_deterministic():
    assert run_eval(k=10) == run_eval(k=10)
