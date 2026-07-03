# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Hybrid RAG retriever for the AI problem generator.

Two ranking arms are fused with Reciprocal Rank Fusion (RRF):

* **Sparse arm** — BM25 (``rank-bm25``), pure-Python, offline, deterministic.
* **Dense arm** — a bi-encoder (``sentence-transformers`` ``all-MiniLM-L6-v2``)
  IS PREFERRED, but ONLY if it imports AND the weights are already cached
  locally (so tests stay hermetic / no network). Otherwise the dense arm falls
  back to a deterministic offline TF-IDF cosine vectorizer (``scikit-learn``).
  The active arm is recorded on ``HybridRetriever.dense_arm``.

The retriever is a drop-if-unverifiable grounding source: :meth:`ground` returns
the top hit's ``source_citation`` only when the fused top score clears a
threshold, otherwise ``None`` (which drives the graph's "no source grounding"
abstain path). Every corpus passage cites a real named source — there are no
fabricated citations.

Determinism
-----------
BM25, TF-IDF and RRF are all pure functions of the corpus and query. No random
seeds are consumed at retrieval time; results are byte-stable across runs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

CORPUS_PATH = Path(__file__).with_name("corpus") / "gre_math_sources.jsonl"

_REQUIRED_FIELDS = ("id", "topic_id", "title", "text", "source_citation")

# ---------------------------------------------------------------------------
# TOPICALITY gate parameters (BUG 3, re-fixed against an adversarial defeat).
#
# The prior gate counted DISTINCT corpus-vocabulary tokens and required >= 4.
# That measures ENGLISH-WORD OVERLAP, not TOPICALITY: the corpus vocabulary
# contains ~39 everyday-English words that are also math vocab (value, set,
# function, point, order, field, ... base). So an off-topic English sentence
# built from those words matched >= 4 vocab terms and wrongly grounded, while a
# terse genuine stem ("Find the eigenvalues.") matched < 4 and wrongly abstained.
#
# The re-fix decides TOPICALITY from three signals on the TOP retrieved passage,
# ALL of which must hold (conservative — any doubt -> abstain):
#
#   (1) DISCRIMINATIVE-term overlap. A matched term counts only if it is
#       corpus-DISCRIMINATIVE, i.e. NOT in the everyday-English band
#       (:data:`_EVERYDAY_ENGLISH`). Raw vocabulary membership no longer counts.
#       The gate needs >= :data:`DEFAULT_MIN_DISCRIMINATIVE_TERMS` discriminative
#       query terms co-occurring in the top passage. This kills all off-topic
#       prose / bare-noun bags whose only overlaps are everyday words (disc == 0).
#
#   (2) PER-PASSAGE CONCENTRATION. Of the query's discriminative terms, the
#       fraction co-occurring in the ONE top passage must be
#       >= :data:`DEFAULT_MIN_DISC_CONCENTRATION`. A keyword-stuffed stem whose
#       discriminative terms scatter across many passages fails this (its top
#       passage covers only a minority of them), while a genuine stem's few
#       discriminative terms concentrate in the one relevant passage.
#
#   (3) RAW RELEVANCE FLOOR (defense-in-depth). RRF's fused score is rank-based
#       and relevance-blind (a junk doc landing #1 in both arms scores the same
#       ~0.0333 as a real hit), so the top passage's RAW dense cosine must ALSO
#       clear :data:`DEFAULT_MIN_TOP_COSINE`. In the current corpus signals (1)+(2)
#       already reject EVERY attack in the adversarial set on their own — no attack
#       reaches both a discriminative anchor AND >= 0.55 concentration — so this
#       floor is a conservative third barrier against future/unseen attacks that
#       might satisfy (1)+(2), set low enough not to reject thinly-covered but
#       genuine single-term stems.
#
# All three signals are measured on the SAME passage: the FUSED (RRF) top hit —
# the passage whose citation would be returned — so concentration and the cosine
# floor describe one coherent candidate, not a different raw-cosine argmax.
#
# Calibration (hermetic corpus + the terse legit stems only; NEVER eval/holdout):
# across the adversarial attack set (off-topic prose, keyword stuffing, bare-noun
# bags — including generalization strings built from DIFFERENT everyday words)
# the discriminative concentration tops out at 0.50, while every genuine stem
# (terse AND long, including graph-style queries carrying a worked-solution
# suffix) has concentration >= 0.67 and fused-top cosine >= 0.13. The thresholds
# below sit in those gaps with margin on both sides.
DEFAULT_MIN_DISCRIMINATIVE_TERMS = 1
DEFAULT_MIN_DISC_CONCENTRATION = 0.55
DEFAULT_MIN_TOP_COSINE = 0.12


def load_corpus(path: Path | str | None = None) -> list[dict]:
    """Load the vendored GRE-math corpus from JSONL.

    Each row must carry all of ``id, topic_id, title, text, source_citation``.
    Rows with a missing/blank field are dropped (drop-if-unverifiable). The
    returned order matches the file order, giving deterministic tie-breaks.
    """
    corpus_path = Path(path) if path is not None else CORPUS_PATH
    rows: list[dict] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if all(str(row.get(field, "")).strip() for field in _REQUIRED_FIELDS):
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Tokenization (shared by BM25 and used for query normalization)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# English stopwords are dropped in BOTH arms (BUG 3, deepened). Using sklearn's
# ENGLISH_STOP_WORDS keeps the BM25 arm consistent with the dense TF-IDF arm
# (which is built with stop_words="english"). Stopwords carry no topical signal;
# without this a stopword-laden, math-less stem (e.g. "the a an of to") would
# still score in both arms via common-word overlap and reach the relevance-blind
# both-arms-#1 RRF ceiling (~0.0333), grounding to an arbitrary citation.
_STOPWORDS = frozenset(ENGLISH_STOP_WORDS)

# Everyday-English CONTENT-word band (BUG 3 topicality re-fix). These are common
# general-English words that happen ALSO to be math vocabulary, so they carry no
# topical signal on their own — a term is corpus-DISCRIMINATIVE only if it lies
# OUTSIDE this band. This is a domain stoplist, NOT derived from the corpus's own
# document frequencies: df cannot separate these from genuine anchors (e.g.
# "matrix" df=35 and "space" df=21 are legit high-df anchors, while "field" df=1
# and "volume" df=1 are low-df everyday words), so the everyday/technical split
# is lexical, not frequency-based. Verified to contain NO genuine math anchor
# (see tests). Not tuned to any single attack string: it is the general band of
# words that are simultaneously ordinary English and incidental math vocabulary.
_EVERYDAY_ENGLISH = frozenset(
    """
    value set function point order field power space map root term series line
    plane area volume sum product number real close open image range domain
    identity change rate rule form positive negative solution matter base
    """.split()
)


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization with English stopwords removed.

    Deterministic and offline. Dropping stopwords means a stopword-only query
    reduces to zero content tokens, so its ranked arms are empty and it grounds
    nothing (drop-if-unverifiable).
    """
    return [
        tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS
    ]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse several ranked ID lists with Reciprocal Rank Fusion.

    RRF score of a document = sum over lists of 1 / (k + rank), where ``rank``
    is the 0-based position of the document in that list. Documents absent from
    a list contribute nothing from it. Returns ``(id, score)`` pairs sorted by
    descending score, with ties broken by first appearance (stable, so the
    result is fully deterministic).
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    counter = 0
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in first_seen:
                first_seen[doc_id] = counter
                counter += 1
    return sorted(
        scores.items(),
        key=lambda item: (-item[1], first_seen[item[0]]),
    )


# ---------------------------------------------------------------------------
# Optional real bi-encoder dense arm (only if cached; else TF-IDF fallback)
# ---------------------------------------------------------------------------


def _try_load_sentence_transformer():
    """Return a loaded ``all-MiniLM-L6-v2`` model IFF it can load with no
    network (weights already cached), else ``None``.

    We refuse any path that would trigger a download so tests stay hermetic.
    """
    try:  # pragma: no cover - depends on optional heavy dep being present
        import os

        # Force offline: any cache miss raises instead of hitting the network.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------


class HybridRetriever:
    """BM25 (sparse) + dense arm fused with RRF, with a grounding adapter.

    Parameters
    ----------
    corpus : list[dict]
        Rows with ``id, topic_id, title, text, source_citation``.
    rrf_k : int
        RRF constant (default 60, the standard value).
    prefer_sentence_transformers : bool
        If True, attempt the real bi-encoder dense arm; it is used only if the
        model loads with no network. Defaults to True but degrades gracefully.
    """

    def __init__(
        self,
        corpus: list[dict],
        *,
        rrf_k: int = 60,
        prefer_sentence_transformers: bool = True,
    ) -> None:
        if not corpus:
            raise ValueError("corpus must be non-empty")
        self.corpus = list(corpus)
        self.rrf_k = rrf_k
        self._ids = [row["id"] for row in self.corpus]
        self._by_id = {row["id"]: row for row in self.corpus}
        # A document's searchable text = title + body (title is high-signal).
        self._docs = [f"{row['title']}. {row['text']}" for row in self.corpus]

        # Per-document (stopword-stripped) content-token SETS. Used by the
        # topicality gate's per-passage concentration signal: which of a query's
        # discriminative terms co-occur in ONE specific passage (the top hit).
        # Aligned by index with ``self._ids`` / ``self._docs``.
        self._doc_token_sets = [set(_tokenize(doc)) for doc in self._docs]

        # --- Sparse arm: BM25 -------------------------------------------------
        self._bm25 = BM25Okapi([_tokenize(doc) for doc in self._docs])

        # --- Dense arm: real bi-encoder if cached, else TF-IDF ---------------
        self._st_model = (
            _try_load_sentence_transformer()
            if prefer_sentence_transformers
            else None
        )
        if self._st_model is not None:  # pragma: no cover - optional path
            self.dense_arm = "sentence-transformers"
            self._doc_embeddings = self._st_model.encode(
                self._docs, normalize_embeddings=True
            )
            self._tfidf = None
            self._tfidf_matrix = None
            # Content-vocabulary for the relevance signal (see _matched_terms);
            # built from the (stopword-stripped) corpus tokens since there is no
            # TF-IDF vocabulary in the sentence-transformers path.
            self._content_vocab = frozenset(
                tok for doc in self._docs for tok in _tokenize(doc)
            )
        else:
            self.dense_arm = "tfidf"
            # Deterministic offline vectorizer: unigrams + bigrams, sublinear tf.
            # stop_words="english" drops common English words so incidental
            # stopword overlap cannot manufacture dense signal for an off-topic
            # stem (BUG 3, deepened) — kept consistent with the BM25 arm, which
            # drops the same stopwords in _tokenize.
            self._tfidf = TfidfVectorizer(
                lowercase=True,
                token_pattern=r"[A-Za-z0-9]+",
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english",
            )
            self._tfidf_matrix = self._tfidf.fit_transform(self._docs)
            self._doc_embeddings = None
            # Corpus content-vocabulary (single tokens only) for the RRF-rank
            # independent relevance signal used by ground() — see _matched_terms.
            self._content_vocab = frozenset(
                term
                for term in self._tfidf.get_feature_names_out()
                if " " not in term
            )

    # -- ranking helpers ----------------------------------------------------

    # Raw-similarity floor below which a doc is treated as NO signal in an arm.
    # BUG 3: a ranked arm must contain ONLY docs the query actually matches, so
    # the abstain decision depends on real similarity — not on full-corpus rank
    # fusion (which otherwise makes every doc rank-0-eligible in both arms and
    # lets a zero-signal query "ground"). BM25 emits exact 0.0 for no term
    # overlap; TF-IDF/dense cosine can be a tiny positive float, so we use a
    # small epsilon rather than a strict > 0 test.
    _MIN_ARM_SIM = 1e-9

    def _ranked_ids_from_scores(self, scores: np.ndarray) -> list[str]:
        """Rank docs by descending raw similarity, DROPPING any with no signal.

        A doc whose raw score is at/below :data:`_MIN_ARM_SIM` did not match the
        query in this arm and must not appear as a candidate — otherwise a
        zero-signal query would still surface arbitrary docs via RRF.
        """
        order = np.argsort(-scores, kind="stable")
        return [
            self._ids[i] for i in order if scores[i] > self._MIN_ARM_SIM
        ]

    def _bm25_ranked_ids(self, query: str) -> list[str]:
        scores = np.asarray(self._bm25.get_scores(_tokenize(query)), dtype=float)
        return self._ranked_ids_from_scores(scores)

    def _dense_sims(self, query: str) -> np.ndarray:
        """Raw dense similarity of the query against every doc (index-aligned).

        Cosine in both the real bi-encoder path and the TF-IDF fallback. This is
        the RAW, relevance-BEARING score (unlike RRF, which is rank-based and
        relevance-blind), used both for ranking and for the topicality gate's
        raw-relevance floor.
        """
        if self.dense_arm == "sentence-transformers":  # pragma: no cover
            q_emb = self._st_model.encode([query], normalize_embeddings=True)
            sims = (self._doc_embeddings @ q_emb.T).ravel()
        else:
            q_vec = self._tfidf.transform([query])
            sims = cosine_similarity(q_vec, self._tfidf_matrix).ravel()
        return np.asarray(sims, dtype=float)

    def _dense_ranked_ids(self, query: str) -> list[str]:
        return self._ranked_ids_from_scores(self._dense_sims(query))

    # -- topicality signals (RRF-rank independent) -------------------------

    def _discriminative_query_terms(self, query: str) -> set[str]:
        """Distinct query terms that are corpus-DISCRIMINATIVE.

        A term is discriminative iff it is in the corpus content-vocabulary AND
        NOT in the everyday-English band (:data:`_EVERYDAY_ENGLISH`). Everyday
        words (value/set/function/point/...) are common English that merely
        happen to be math vocab, so they carry no topical signal; only the
        remaining terms distinguish a genuine math stem from off-topic prose.
        """
        return {
            tok
            for tok in _tokenize(query)
            if tok in self._content_vocab and tok not in _EVERYDAY_ENGLISH
        }

    def _topicality(self, query: str, doc_id: str) -> tuple[int, float, float]:
        """Return the three topicality signals for ``query`` against ``doc_id``.

        ``doc_id`` is the passage whose citation grounding would return — i.e. the
        FUSED (RRF) top hit — so all three signals describe the ONE coherent
        candidate passage, not scattered corpus statistics or a different
        raw-cosine argmax. ``(disc_in_top, disc_concentration, top_cosine)``:

        * ``disc_in_top`` — count of the query's discriminative terms that
          co-occur in that passage (per-passage overlap, NOT a corpus-global
          count).
        * ``disc_concentration`` — fraction of the query's discriminative terms
          that land in that passage (0.0 if the query has none). A keyword-stuffed
          or off-topic stem whose discriminative terms scatter across passages
          scores low; a focused genuine stem scores near 1.0.
        * ``top_cosine`` — that passage's RAW dense cosine (the relevance floor
          signal; RRF score is rank-based / relevance-blind so this is required
          too).
        """
        disc_terms = self._discriminative_query_terms(query)
        top_i = self._ids.index(doc_id)
        sims = self._dense_sims(query)
        top_cosine = float(sims[top_i]) if sims.size else 0.0
        top_tokens = self._doc_token_sets[top_i]
        disc_in_top = sum(1 for t in disc_terms if t in top_tokens)
        concentration = disc_in_top / len(disc_terms) if disc_terms else 0.0
        return disc_in_top, concentration, top_cosine

    # -- public API ---------------------------------------------------------

    def retrieve(self, query: str, k: int = 10) -> list[dict]:
        """Return the top-``k`` fused hits as ranked, scored corpus rows.

        Each hit is ``{id, topic_id, title, text, source_citation, score}``
        where ``score`` is the RRF score. Deterministic given the corpus.
        """
        bm25_ids = self._bm25_ranked_ids(query)
        dense_ids = self._dense_ranked_ids(query)
        fused = reciprocal_rank_fusion([bm25_ids, dense_ids], k=self.rrf_k)
        hits: list[dict] = []
        for doc_id, score in fused[:k]:
            row = self._by_id[doc_id]
            hits.append(
                {
                    "id": row["id"],
                    "topic_id": row["topic_id"],
                    "title": row["title"],
                    "text": row["text"],
                    "source_citation": row["source_citation"],
                    "score": float(score),
                }
            )
        return hits

    # -- single-arm rankings (used by the in-house baseline eval) -----------

    def retrieve_bm25(self, query: str, k: int = 10) -> list[dict]:
        """BM25-only ranking (baseline arm for the in-house eval)."""
        ranked = self._bm25_ranked_ids(query)[:k]
        return [dict(self._by_id[i]) for i in ranked]

    def retrieve_dense(self, query: str, k: int = 10) -> list[dict]:
        """Dense-only ranking (baseline arm for the in-house eval)."""
        ranked = self._dense_ranked_ids(query)[:k]
        return [dict(self._by_id[i]) for i in ranked]

    # -- grounding adapter (drop-if-unverifiable gate) ----------------------

    def ground(
        self,
        candidate: dict,
        *,
        min_score: float,
        min_discriminative_terms: int = DEFAULT_MIN_DISCRIMINATIVE_TERMS,
        min_disc_concentration: float = DEFAULT_MIN_DISC_CONCENTRATION,
        min_top_cosine: float = DEFAULT_MIN_TOP_COSINE,
    ) -> Optional[str]:
        """Return the top hit's ``source_citation`` if the candidate is grounded.

        Builds a query from the candidate's stem (and worked solution / topic /
        technique when present). Returns ``None`` — driving the graph's "no
        source grounding" abstain path — unless ALL of the following hold
        (TOPICALITY gate; conservative — any doubt -> abstain):

        * the candidate has usable text, and
        * a fused hit exists whose RRF score clears ``min_score``, and
        * (1) DISCRIMINATIVE overlap: the query has at least
          ``min_discriminative_terms`` discriminative terms (corpus vocabulary
          minus the everyday-English band) co-occurring in the top passage, and
        * (2) PER-PASSAGE CONCENTRATION: the fraction of the query's
          discriminative terms landing in that one top passage is
          >= ``min_disc_concentration``, and
        * (3) RAW RELEVANCE FLOOR: the top passage's raw dense cosine is
          >= ``min_top_cosine`` (RRF alone is relevance-blind).

        The topicality signals are evaluated before returning any citation, so an
        off-topic stem never grounds regardless of its (relevance-blind) RRF
        score. See the module-level parameter docs for calibration.
        """
        query = " ".join(
            str(candidate.get(key, ""))
            for key in ("stem", "worked_solution", "topic", "technique")
        ).strip()
        if not query:
            return None
        # A candidate hit must exist and clear the RRF floor first.
        hits = self.retrieve(query, k=1)
        if not hits:
            return None
        top = hits[0]
        if top["score"] < min_score:
            return None
        # TOPICALITY gate (RRF-rank independent): discriminative-term overlap,
        # per-passage concentration, and a raw-cosine relevance floor — all on
        # the SAME passage whose citation we would return (the fused top hit).
        # Any failure => abstain.
        disc_in_top, concentration, top_cosine = self._topicality(query, top["id"])
        if disc_in_top < min_discriminative_terms:
            return None
        if concentration < min_disc_concentration:
            return None
        if top_cosine < min_top_cosine:
            return None
        return top["source_citation"]

    def as_graph_retriever(
        self,
        *,
        min_score: float,
        min_discriminative_terms: int = DEFAULT_MIN_DISCRIMINATIVE_TERMS,
        min_disc_concentration: float = DEFAULT_MIN_DISC_CONCENTRATION,
        min_top_cosine: float = DEFAULT_MIN_TOP_COSINE,
    ):
        """Adapt to the graph's ``Retriever = Callable[[dict], Optional[str]]``.

        Returns a closure ``retriever(candidate) -> citation | None`` suitable
        for injection into :func:`graph.build_graph` / :func:`graph.run_generation`.
        """

        def _retriever(candidate: dict) -> Optional[str]:
            return self.ground(
                candidate,
                min_score=min_score,
                min_discriminative_terms=min_discriminative_terms,
                min_disc_concentration=min_disc_concentration,
                min_top_cosine=min_top_cosine,
            )

        return _retriever
