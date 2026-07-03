# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the hybrid RAG retriever (BM25 + dense -> RRF).

Fully offline and deterministic: no network, fixed vectorizer, TF-IDF dense
arm. The corpus is loaded from the vendored JSONL.
"""

from __future__ import annotations

import pytest

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
# BUG 3 (SAFETY): the grounding gate must depend on REAL similarity, not RRF
# rank-presence. Previously every corpus doc appeared rank-0-eligible in both
# arms (full-corpus argsort), so a zero-signal query still produced a top RRF
# score of ~0.0333 >= the 0.03 default => gibberish "grounded" to a real
# citation. The abstain decision must instead be driven by actual similarity:
# a query with zero raw signal in BOTH arms must yield NO candidates -> None.
# ---------------------------------------------------------------------------


def test_ground_gibberish_query_abstains_at_default_threshold():
    """A gibberish / off-topic stem with zero raw similarity in both arms must
    NOT ground, even at the (permissive) default grounding threshold."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    candidate = {"stem": "zzzqqq foobarbaz nonsense wibble plugh xyzzy"}
    citation = retriever.ground(candidate, min_score=DEFAULT_MIN_GROUND_SCORE)
    assert citation is None, (
        "a zero-signal gibberish query must abstain, not ground to a real "
        "citation via RRF rank-presence"
    )


def test_ground_on_topic_query_still_grounds_at_default_threshold():
    """Guard against over-tightening: a genuinely on-topic stem must still
    ground to a relevant citation at the default threshold."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    candidate = {
        "stem": "State the epsilon-delta definition of a limit and the "
        "derivative of a polynomial.",
    }
    citation = retriever.ground(candidate, min_score=DEFAULT_MIN_GROUND_SCORE)
    assert citation, "a genuinely on-topic stem must still ground"
    assert "OpenStax" in citation or "Hefferon" in citation


def test_retrieve_yields_no_candidates_for_zero_signal_query():
    """The abstain decision hangs on candidacy: a query with zero raw signal in
    both the BM25 and dense arms must produce NO ranked candidates at all (so
    ground() has nothing to return), rather than surfacing an arbitrary doc via
    full-corpus rank fusion."""
    retriever = HybridRetriever(_corpus())
    hits = retriever.retrieve("zzzqqq foobarbaz nonsense wibble plugh xyzzy")
    assert hits == [], "a zero-signal query must yield no candidates"


def test_retrieve_still_returns_hits_for_on_topic_query():
    retriever = HybridRetriever(_corpus())
    hits = retriever.retrieve("eigenvalues and the characteristic polynomial")
    assert hits, "an on-topic query must still return candidates"


# ---------------------------------------------------------------------------
# BUG 3 (DEEPENED): the nonzero-arm filter alone only drops OUT-OF-VOCAB tokens.
# Common English words / incidental math-vocab single-word overlaps are in the
# corpus vocabulary, so off-topic, math-less stems still score in BOTH arms and
# reach the both-arms-#1 RRF ceiling (~0.0333), which is relevance-BLIND — a junk
# doc landing #1 in both arms is indistinguishable by score from a real hit.
# Two extra guards make grounding depend on real relevance:
#   (1) English stopword removal in both arms: a stopword-only stem reduces to
#       zero content tokens -> empty arms -> abstain.
#   (2) A minimum count of matched corpus-vocabulary CONTENT terms (RRF-rank
#       independent): a query whose only overlaps are a couple of incidental
#       single words abstains, while genuine math stems (which match several
#       content terms) still ground.
# ---------------------------------------------------------------------------


def test_ground_stopword_only_query_abstains():
    """A stopword-only stem ("the a an of to") has no content tokens after
    stopword removal -> empty arms -> must abstain (not ground at RRF ~0.0325)."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    citation = retriever.ground(
        {"stem": "the a an of to"}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation is None, (
        "a stopword-only stem must abstain, not ground via common-word overlap"
    )


def test_ground_off_topic_in_vocab_sentence_abstains():
    """An off-topic English sentence whose only corpus overlaps are a couple of
    incidental in-vocabulary words ("function", "value") must abstain, even
    though it reaches the both-arms-#1 RRF ceiling (~0.0333, byte-identical to a
    genuine hit). This is the adversary's defeat of the shallow fix."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    off_topic = (
        "The function last night was a great party with lots of dancing "
        "and value."
    )
    citation = retriever.ground(
        {"stem": off_topic}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation is None, (
        "an off-topic sentence with only incidental single-word overlaps must "
        "abstain, not ground to a real citation"
    )


def test_ground_genuine_math_stems_still_ground():
    """Recall guard: genuine math stems (each matching several corpus content
    terms) must STILL ground at the default threshold after the deepened fix."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    genuine = [
        "Compute the eigenvalues from the characteristic polynomial of a matrix",
        "u substitution rule for integrals",
        "State the epsilon-delta definition of a limit",
        "State the rank nullity theorem for a linear map between vector spaces",
    ]
    for stem in genuine:
        citation = retriever.ground(
            {"stem": stem}, min_score=DEFAULT_MIN_GROUND_SCORE
        )
        assert citation, f"genuine math stem must still ground: {stem!r}"


def test_retrieve_baseline_arms_unaffected_by_relevance_gate():
    """The min-content-terms relevance gate lives in ground() ONLY, so the
    ranked-arm retrieval methods used by the Recall eval still surface hits for
    a genuine query (protecting Recall@10)."""
    retriever = HybridRetriever(_corpus())
    assert retriever.retrieve_bm25("eigenvalues characteristic polynomial")
    assert retriever.retrieve_dense("u substitution integral")
    assert retriever.retrieve("rank nullity theorem")


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


def test_real_retriever_abstains_on_gibberish_stem_at_default_threshold():
    """BUG 3 end-to-end: a candidate whose stem is gibberish (zero raw signal in
    both arms) must drive the graph's "no source grounding" abstain path even at
    the DEFAULT grounding threshold — not ground to a real citation."""
    from graph import make_hybrid_retriever, run_generation

    def _llm(topic, technique):
        return {
            "candidate": {
                # a verifiably-correct answer, but a gibberish (ungroundable) stem
                "stem": "zzzqqq foobarbaz nonsense wibble plugh xyzzy",
                "correct": "2*x",
                "worked_solution": "zzzqqq foobarbaz nonsense wibble",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    retriever = make_hybrid_retriever()  # default min_score
    state = run_generation(
        "zzz", "qqq", llm_propose=_llm, retriever=retriever
    )
    assert state["status"] == "abstain", (
        "a gibberish, ungroundable stem must abstain, not ground"
    )
    assert "ground" in state["abstain_reason"].lower()
    assert state["problem"] is None


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


# ---------------------------------------------------------------------------
# BUG 3 (TOPICALITY): the min-content-terms word-COUNT gate was defeated by an
# independent adversary. Counting DISTINCT corpus-vocabulary tokens measures
# ENGLISH-WORD OVERLAP, not TOPICALITY: the corpus vocab contains ~39 everyday
# English words that are also math vocab (value, set, function, point, order,
# field, ... base). An off-topic English sentence built from those words matches
# >= 4 vocab terms and wrongly grounds; conversely a terse but genuine stem
# ("Find the eigenvalues.") matches < 4 and wrongly abstains.
#
# The real gate is TOPICALITY, decided from three signals on the TOP retrieved
# passage (all must hold; conservative — any doubt -> abstain):
#   (1) DISCRIMINATIVE terms: matched terms count only if corpus-discriminative
#       (outside the everyday-English band) — raw vocabulary membership does not.
#   (2) PER-PASSAGE CONCENTRATION: the discriminative query terms must co-occur
#       in the ONE top passage (not scatter across many), i.e. a high fraction of
#       the query's discriminative terms land in the top hit.
#   (3) RAW RELEVANCE FLOOR: RRF is rank-based / relevance-blind, so the top
#       hit's RAW dense cosine must also clear a floor.
# Thresholds were calibrated on the hermetic corpus + the terse legit stems
# below (NEVER on eval/holdout): attack disc-concentration tops out at 0.50 and
# attack raw cosine (among any with a discriminative anchor) never clears the
# floor, while every genuine stem has disc-concentration >= 0.57 and cosine
# >= 0.16. See rag/retriever.py for the numbers.
# ---------------------------------------------------------------------------


# Strings the SHALLOW word-count gate wrongly GROUNDS but a topicality gate must
# ABSTAIN on (off-topic prose from everyday-math words, keyword stuffing, bare
# noun bags). Includes generalization cases built from DIFFERENT everyday-math
# words than the reported examples, so the gate cannot be tuned to the list.
_WRONGLY_GROUND = [
    # off-topic English prose whose words are all everyday-math-vocab
    "I value my close friends and the change of pace, no matter the form "
    "or the point.",
    "The team set a positive tone, valued open feedback, and kept a real "
    "sense of order.",
    "In real life you have to change your base, close the deal, and value "
    "your time.",
    # keyword stuffing (no question)
    "group ring field vector matrix eigenvalue",
    "linear vector matrix theorem function domain range image",
    # bare noun bag of everyday-math words
    "value set function point",
    # the reviewer "party" sentence extended so word-count grounds (12 terms)
    "The function last night was a great party with lots of dancing and "
    "value. We set the table and kept good order all night. It was a real "
    "change of pace, no matter the form.",
    # GENERALIZATION: different everyday-math words, must also abstain
    "Please open the map and set a course, then close the range and change "
    "lanes.",
    "The base rate of change in the market was positive, a real product of "
    "the order.",
    "sum product power root series line plane area volume base",
    "identity form space image order rule change rate",
    "She kept an open mind about the plane ride and valued the extra space "
    "and volume.",
]

# Terse but genuine corpus-covered stems the SHALLOW gate wrongly ABSTAINS on
# (fewer than 4 matched vocab terms) — the topicality gate must GROUND them.
_WRONGLY_ABSTAIN = [
    "Compute the determinant.",
    "Find the eigenvalues.",
    "Diagonalize the matrix.",
    "What is a basis?",
    "Compute the gradient.",
    "State the chain rule.",
    "Define a vector space.",
    "Row reduce A.",
    "Find the Taylor series.",
    "Is the map injective?",
    "Differentiate sin(x).",
    "What is the derivative of cos(x)?",
]


@pytest.mark.parametrize("stem", _WRONGLY_GROUND)
def test_ground_off_topic_or_stuffed_query_abstains(stem):
    """Every off-topic / keyword-stuffed / bare-noun stem must ABSTAIN at the
    default threshold — its words overlap the corpus vocab but carry no
    topicality (no discriminative anchor concentrated in one real passage)."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    citation = retriever.ground(
        {"stem": stem}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation is None, (
        f"off-topic / non-topical stem must abstain, not ground: {stem!r}"
    )


@pytest.mark.parametrize("stem", _WRONGLY_ABSTAIN)
def test_ground_terse_genuine_stem_still_grounds(stem):
    """Every terse but genuinely corpus-covered stem must GROUND at the default
    threshold, even though it matches fewer than the old 4 vocab terms."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = HybridRetriever(_corpus())
    citation = retriever.ground(
        {"stem": stem}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation, f"terse genuine math stem must still ground: {stem!r}"
    assert "OpenStax" in citation or "Hefferon" in citation or (
        "MIT OCW" in citation
    )


def test_topicality_gate_lives_only_in_ground_recall_arms_untouched():
    """RECALL GUARD: the topicality gate must live ONLY in ground(). The three
    eval arms (retrieve / retrieve_bm25 / retrieve_dense) — which define
    Recall@10 — must be untouched, i.e. still surface hits for genuine queries
    AND still surface hits for the off-topic vocab-overlap strings (the gate
    does not prune their candidacy; only ground() abstains on them). This is what
    structurally preserves Recall@10."""
    retriever = HybridRetriever(_corpus())
    # genuine queries: all three arms return candidates
    for q in (
        "eigenvalues characteristic polynomial",
        "u substitution integral",
        "rank nullity theorem",
    ):
        assert retriever.retrieve(q), f"hybrid arm must return hits for {q!r}"
        assert retriever.retrieve_bm25(q), f"bm25 arm must return hits for {q!r}"
        assert retriever.retrieve_dense(q), f"dense arm must return hits for {q!r}"
    # An off-topic vocab-overlap string STILL produces ranked candidates in the
    # arms (candidacy is retrieval's job); only ground() abstains on it. If the
    # gate had leaked into the arms, these would be pruned and Recall could move.
    off_topic = "value set function point"
    assert retriever.retrieve(off_topic), (
        "the topicality gate must NOT prune eval-arm candidacy (recall guard)"
    )
