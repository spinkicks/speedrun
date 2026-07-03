# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the hybrid RAG retriever (BM25 + dense -> RRF).

Fully offline and deterministic: no network, fixed vectorizer, TF-IDF dense
arm. The corpus is loaded from the vendored JSONL.
"""

from __future__ import annotations

import math

import pytest

from rag.retriever import (
    DEFAULT_SEMANTIC_GROUND_THRESHOLD,
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


# ===========================================================================
# FIX 4 (DEFINITIVE): a REAL SEMANTIC relevance gate.
#
# Three prior LEXICAL fixes (arm-nonzero filter -> min-content-terms ->
# discriminative-concentration) were each defeated by a fresh adversary because
# word-OVERLAP can't distinguish "one incidental math word inside off-topic
# prose" ("My cat is named Eigenvalue and she loves the sofa.") from a genuine
# terse stem ("Find the eigenvalues."). Both carry the SAME single anchor.
#
# The definitive discriminator is SEMANTIC: after RRF selects the top hit (the
# passage whose citation would ship), we require the cosine of an EMBEDDING of
# the query against an EMBEDDING of that top passage to clear a calibrated
# threshold. Off-topic prose is semantically far from every math passage even
# when it shares an incidental token; a genuine stem is semantically close to
# its relevant passage.
#
# These tests are HERMETIC: they inject a DETERMINISTIC stub embedder (no
# network) that reproduces the semantic separation. The stub places a query /
# passage on the math-concept axis it genuinely talks about, and off-topic prose
# on an orthogonal "non-math" axis, so cosine cleanly separates the two classes.
# The threshold used here is the SAME config constant the real OpenAI embedder
# path uses; only the vectors differ (stub vs. text-embedding-3-small).
# ===========================================================================


# --- deterministic hermetic stub embedder ----------------------------------
#
# The stub reproduces REAL embedding GEOMETRY so it can exercise the gate LOGIC
# (cosine + threshold + abstain) without a network. Two ideas make it faithful:
#
#   1. MATH-CONCEPT SUBSPACE. A small set of concept axes (eigen, determinant,
#      integral, ...). Every math trigger word pushes on its concept axis. A
#      focused genuine stem ("Find the eigenvalues.") concentrates on ONE concept
#      axis; a SCATTERED math-keyword bag ("group ring field vector matrix
#      eigenvalue") spreads across MANY concept axes, so its cosine to any ONE
#      concentrated passage is low — exactly how real embeddings treat an
#      incoherent bag of terms.
#
#   2. NON-MATH SUBSPACE (many hashed dims). Every ordinary word hashes to one of
#      many "non-math" dims. Two different off-topic sentences therefore land on
#      DIFFERENT non-math dims (near-orthogonal), and all of them are orthogonal
#      to the concept axes. Off-topic prose with ONE incidental math word ("My
#      cat is named Eigenvalue and she loves the sofa.") puts most of its mass in
#      the non-math subspace -> LOW cosine to the eigen passage despite sharing
#      the token. This is the separation no lexical/word-overlap gate can make.
#
# Real math passages are math-dense (mostly triggers), so their mass sits on the
# concept axes; a genuine stem shares that concept -> HIGH cosine. The vector is
# L2-normalized, so cosine is a dot product. Ordinary stopwords carry no meaning
# and are dropped (they neither help nor pad), matching real de-weighting of
# function words.

_STUB_STOP = frozenset(
    """
    a an the and or of to in on for with is are was were be been being that this
    these those it its as at by from into over under out up down we you he she
    they i my her his their our your no not do does did has have had will would
    can could should than then so but if while about after before during between
    all near every there exists such whenever have has also using used use when
    what which who how why where find compute state define does do is are the0
    """.split()
)

_CONCEPTS: dict[str, tuple[str, ...]] = {
    "determinant": ("determinant", "det", "invertible", "nonzero"),
    "eigen": ("eigenvalue", "eigenvalues", "eigenvector", "eigenvectors",
              "characteristic", "lambda"),
    "diagonalize": ("diagonalize", "diagonalizable", "diagonalization", "pdp",
                    "diagonal"),
    "basis": ("basis", "span", "spans", "spanning", "independent", "dimension",
              "dimensions"),
    "gradient": ("gradient", "partial", "partials", "steepest", "ascent"),
    "chain": ("chain", "composition", "composite"),
    "vectorspace": ("vector", "vectors", "space", "spaces", "axioms",
                    "subspace"),
    "matrix": ("matrix", "matrices", "square"),
    "rowreduce": ("row", "reduce", "reduction", "echelon", "rank", "pivot",
                  "gauss", "jordan"),
    "taylor": ("taylor", "maclaurin", "series", "expansion"),
    "injective": ("injective", "surjective", "kernel", "map", "maps", "mapping",
                  "linear", "nullity"),
    "differentiate": ("differentiate", "differentiation", "derivative",
                      "sin", "cos", "tan", "power"),
    "converge": ("converge", "converges", "convergent", "convergence",
                 "diverge", "geometric", "alternating", "ratio"),
    "limit": ("limit", "limits", "epsilon", "delta", "lhopital", "squeeze"),
    "integral": ("integral", "integrals", "integrate", "substitution",
                 "antiderivative", "integration", "ftc"),
}

# Reverse index: trigger word -> concept index.
_CONCEPT_NAMES = list(_CONCEPTS)
_TRIGGER_TO_IDX: dict[str, int] = {}
for _i, _name in enumerate(_CONCEPT_NAMES):
    for _trig in _CONCEPTS[_name]:
        _TRIGGER_TO_IDX.setdefault(_trig, _i)

_N_CONCEPTS = len(_CONCEPT_NAMES)
# Many hashed non-math dims -> distinct off-topic texts are mutually orthogonal
# (collision-free for the small hermetic test set).
_N_NONMATH = 4096
_DIM = _N_CONCEPTS + _N_NONMATH

# A text resolves to genuine math (multi-hot concept vector) vs. the non-math
# subspace. A LONG math text (many trigger words — a real corpus passage) is
# always "about math". A SHORT text is about math only if its math words are a
# real presence (count OR density) AND FOCUS on one concept — this is what
# separates a genuine terse stem from a scattered keyword bag. See _stub_vector.
_STUB_MANY_MATH_WORDS = 5  # a rich math passage: about-math regardless of focus
_STUB_MIN_MATH_WORDS = 2   # a short stem needs >=2 math words ...
_STUB_MIN_DENSITY = 0.5    # ... or math words a majority of the content ...
_STUB_MIN_FOCUS = 0.5      # ... AND a plurality concept (rejects keyword bags)


def _nonmath_dim(token: str) -> int:
    # Deterministic, offline hash bucket in the non-math subspace.
    h = 0
    for ch in token:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return _N_CONCEPTS + (h % _N_NONMATH)


def _stub_vector(text: str) -> list[float]:
    """Deterministic, hand-designed embedding for the hermetic gate tests.

    Resolves each text to a UNIT vector: on its dominant math-CONCEPT axis when
    the text is genuinely about that concept, else on a whole-text-hashed
    NON-MATH axis. "Genuinely about a concept" = (>= ``_STUB_MIN_MATH_WORDS`` math
    trigger words OR math density >= ``_STUB_MIN_DENSITY``) AND the dominant
    concept is a plurality (focus >= ``_STUB_MIN_FOCUS``) of those math words.

    Consequences that mirror real embedding geometry (and defeat lexical gates):
      * a corpus passage (math-dense, title-anchored) -> its dominant concept;
      * a genuine terse stem ("Find the eigenvalues.", "Row reduce A.") ->
        the SAME concept -> cosine ~1 with its passage -> GROUND;
      * off-topic prose with ONE incidental math word ("My cat is named
        Eigenvalue...") -> too math-SPARSE -> non-math axis -> cosine ~0 -> ABSTAIN;
      * a scattered math-keyword bag ("group ring field vector matrix eigenvalue")
        -> no plurality concept (focus too low) -> non-math axis -> ABSTAIN.

    The TITLE (before the first period, per HybridRetriever's "{title}. {text}")
    is weighted so a passage resolves to what it is chiefly about. Clean,
    deterministic separation to exercise the gate's cosine + threshold + abstain
    path; the REAL embedder's separation is calibrated live. No network.
    """
    head, _, _ = text.partition(".")
    title_words = {w.strip(",;:!?()[]{}'\"") for w in head.lower().split()}
    words = [w.strip(".,;:!?()[]{}'\"") for w in text.lower().split()]
    words = [w for w in words if w and w not in _STUB_STOP]
    vec = [0.0] * _DIM
    if not words:
        vec[_N_CONCEPTS] = 1.0
        return vec
    concept = [0.0] * _N_CONCEPTS
    n_math = 0
    for w in words:
        idx = _TRIGGER_TO_IDX.get(w)
        if idx is not None:
            concept[idx] += 3.0 if w in title_words else 1.0
            n_math += 1
    density = n_math / len(words)
    focus = (max(concept) / sum(concept)) if n_math else 0.0
    about_math = n_math >= _STUB_MANY_MATH_WORDS or (
        (n_math >= _STUB_MIN_MATH_WORDS or density >= _STUB_MIN_DENSITY)
        and focus >= _STUB_MIN_FOCUS
    )
    if about_math:
        # Multi-hot over the text's concepts (title-weighted), unit-normalized.
        # A passage carries ALL its concepts, so a genuine query matching ANY of
        # them aligns; a focused stem shares its one concept -> high cosine.
        cn = math.sqrt(sum(c * c for c in concept)) or 1.0
        for i in range(_N_CONCEPTS):
            vec[i] = concept[i] / cn
    else:
        # off-topic / scattered -> a stable non-math axis keyed to the whole text.
        vec[_nonmath_dim("|".join(words))] = 1.0
    return vec


class _StubEmbedder:
    """Deterministic, offline embedder for hermetic gate tests."""

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [_stub_vector(t) for t in texts]


def _semantic_retriever() -> HybridRetriever:
    return HybridRetriever(_corpus(), embedder=_StubEmbedder())


# NEW single-math-anchor off-topic sentences (different anchors + incidental
# corpus words like "average"/"block"/"chosen") — proving GENERALIZATION beyond
# the reported adversary strings. Each contains exactly one math word buried in
# ordinary prose; a lexical gate that keys on the anchor would ground them.
_NEW_OFFTOPIC = [
    "My cat is named Eigenvalue and she loves the sofa.",
    "The determinant of my morning was a cup of coffee and toast.",
    "The matrix at the movie theater sold out before we arrived.",
    "The limit on my credit card ruined our vacation plans.",
    "The average rainfall this spring made the garden bloom.",
    "We chose the vector graphics for the birthday party invitations.",
    "The gradient of the sunset over the block was breathtaking.",
    "Her basis for the argument was simply that the dog looked guilty.",
    "The series finale of the show aired on the chosen Tuesday.",
    "A convergence of tourists blocked the average sidewalk downtown.",
    "The kernel of popcorn stuck between my teeth all afternoon.",
    "He set the power tools down and took a long, pleasant nap.",
]

_MUST_ABSTAIN_SEMANTIC = [
    "My cat is named Eigenvalue and she loves the sofa.",
    "The determinant of my morning was a cup of coffee and toast.",
    "The weather was average today and quite pleasant.",
    "The block party was cancelled due to rain.",
    "The matrix at the movie theater sold out before we arrived.",
    "The limit on my credit card ruined our vacation plans.",
    "I value my close friends and the change of pace, no matter the form "
    "or the point.",
    "group ring field vector matrix eigenvalue",
    "value set function point",
    *_NEW_OFFTOPIC,
]

_MUST_GROUND_SEMANTIC = [
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
    "Does the series converge?",
]


def test_semantic_threshold_constant_is_in_calibrated_range():
    # The gate's decisive constant must exist and sit in a plausible cosine band
    # (calibrated on REAL embeddings; see rag/retriever.py module docstring).
    assert 0.0 < DEFAULT_SEMANTIC_GROUND_THRESHOLD < 1.0


@pytest.mark.parametrize("stem", _MUST_ABSTAIN_SEMANTIC)
def test_semantic_gate_abstains_on_off_topic(stem):
    """Every off-topic sentence — including single-math-anchor prose and NEW
    generalization strings — must ABSTAIN under the semantic gate: its embedding
    is orthogonal to every math passage, so the top-hit cosine is far below the
    threshold."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = _semantic_retriever()
    citation = retriever.ground(
        {"stem": stem}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation is None, (
        f"off-topic stem must abstain under the semantic gate: {stem!r}"
    )


@pytest.mark.parametrize("stem", _MUST_GROUND_SEMANTIC)
def test_semantic_gate_grounds_genuine_stems(stem):
    """Every genuine, corpus-covered terse stem must GROUND under the semantic
    gate: its embedding is close to the relevant passage, so the top-hit cosine
    clears the threshold. Includes "Does the series converge?" which wrongly
    abstained before."""
    from graph import DEFAULT_MIN_GROUND_SCORE

    retriever = _semantic_retriever()
    citation = retriever.ground(
        {"stem": stem}, min_score=DEFAULT_MIN_GROUND_SCORE
    )
    assert citation, f"genuine stem must ground under the semantic gate: {stem!r}"
    assert "OpenStax" in citation or "Hefferon" in citation or (
        "MIT OCW" in citation
    )


def test_semantic_gate_corpus_embeddings_are_cached_once():
    """The embedder must embed the corpus passages EXACTLY once (at construction)
    and reuse them; per-query grounding embeds only the query."""
    embedder = _StubEmbedder()
    retriever = HybridRetriever(_corpus(), embedder=embedder)
    calls_after_build = embedder.calls
    assert calls_after_build >= 1, "corpus must be embedded at construction"
    retriever.ground(
        {"stem": "Find the eigenvalues."}, min_score=0.0
    )
    retriever.ground(
        {"stem": "Compute the determinant."}, min_score=0.0
    )
    # Two more ground() calls => at most two more embed() calls (one per query),
    # never a re-embed of the whole corpus.
    assert embedder.calls <= calls_after_build + 2


def test_semantic_gate_does_not_touch_eval_arms():
    """RECALL GUARD (definitive fix): injecting a semantic embedder must not
    change the eval retrieval arms. retrieve / retrieve_bm25 / retrieve_dense
    must be byte-identical WITH and WITHOUT the embedder, so Recall@10 is
    provably preserved — the semantic check lives ONLY in ground()."""
    plain = HybridRetriever(_corpus())
    semantic = HybridRetriever(_corpus(), embedder=_StubEmbedder())
    for q in (
        "eigenvalues characteristic polynomial",
        "u substitution integral",
        "rank nullity theorem",
        "value set function point",  # off-topic: still ranked in the arms
        "definition of the derivative as a limit",
    ):
        assert (
            [h["id"] for h in plain.retrieve(q)]
            == [h["id"] for h in semantic.retrieve(q)]
        ), f"hybrid arm drifted with embedder for {q!r}"
        assert (
            [r["id"] for r in plain.retrieve_bm25(q)]
            == [r["id"] for r in semantic.retrieve_bm25(q)]
        ), f"bm25 arm drifted with embedder for {q!r}"
        assert (
            [r["id"] for r in plain.retrieve_dense(q)]
            == [r["id"] for r in semantic.retrieve_dense(q)]
        ), f"dense arm drifted with embedder for {q!r}"


def test_semantic_gate_grounds_via_graph_injection():
    """End-to-end: a HybridRetriever WITH a stub embedder wires into the graph
    and grounds a genuine terse stem to a real citation."""
    from graph import DEFAULT_MIN_GROUND_SCORE, run_generation

    retriever = _semantic_retriever().as_graph_retriever(
        min_score=DEFAULT_MIN_GROUND_SCORE
    )

    def _llm(topic, technique):
        return {
            "candidate": {
                "stem": "Find the eigenvalues.",
                "correct": "2*x",
                "worked_solution": "characteristic polynomial",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    state = run_generation(
        "linear_algebra::eigen", "eigenvalues",
        llm_propose=_llm, retriever=retriever,
    )
    assert state["status"] == "emit"
    assert state["problem"]["citation"]


def test_semantic_gate_abstains_via_graph_injection():
    """End-to-end: a single-math-anchor off-topic stem drives the graph's
    "no source grounding" abstain path under the semantic gate."""
    from graph import DEFAULT_MIN_GROUND_SCORE, run_generation

    retriever = _semantic_retriever().as_graph_retriever(
        min_score=DEFAULT_MIN_GROUND_SCORE
    )

    def _llm(topic, technique):
        return {
            "candidate": {
                "stem": "My cat is named Eigenvalue and she loves the sofa.",
                "correct": "2*x",
                "worked_solution": "she also loves the average sunny window.",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    state = run_generation(
        "cat", "sofa", llm_propose=_llm, retriever=retriever,
    )
    assert state["status"] == "abstain"
    assert "ground" in state["abstain_reason"].lower()
