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

# Minimum count of DISTINCT corpus-vocabulary content terms a query must match
# before ground() will consider it grounded (BUG 3, deepened). This is the
# RRF-rank-INDEPENDENT relevance signal: RRF score alone is relevance-blind (a
# junk doc landing #1 in both arms scores the same ~0.0333 as a real hit), and
# raw dense similarity alone does NOT separate off-topic from genuine (an
# off-topic "party" sentence scores ~0.245, inside the genuine gold band whose
# floor is ~0.10). What DOES separate them cleanly is how many distinct corpus
# content terms the query overlaps. Chosen from the in-house gold set: ALL 50
# gold questions match >= 4 distinct content terms (min observed 4), while the
# adversarial off-topic stems match at most 3 (incidental ambiguous words like
# "function"/"set"/"value" that are common English AND math vocab). A floor of 4
# sits exactly at the genuine minimum (so Recall@10 is not regressed — verified)
# and above the incidental-overlap band, so every off-topic / stopword-laden
# stem — including the end-to-end "party" attack — abstains. Conservative by
# design (any doubt -> abstain).
DEFAULT_MIN_CONTENT_TERMS = 4


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

    def _dense_ranked_ids(self, query: str) -> list[str]:
        if self.dense_arm == "sentence-transformers":  # pragma: no cover
            q_emb = self._st_model.encode([query], normalize_embeddings=True)
            sims = (self._doc_embeddings @ q_emb.T).ravel()
        else:
            q_vec = self._tfidf.transform([query])
            sims = cosine_similarity(q_vec, self._tfidf_matrix).ravel()
        return self._ranked_ids_from_scores(np.asarray(sims, dtype=float))

    # -- relevance signal (RRF-rank independent) ---------------------------

    def _matched_terms(self, query: str) -> int:
        """Count DISTINCT corpus-vocabulary content terms the query matches.

        Stopwords are already dropped by :func:`_tokenize`; a term counts only if
        it is in the corpus content-vocabulary. This is independent of RRF rank
        and of raw similarity magnitude, so it distinguishes a genuinely on-topic
        stem (many matched content terms) from an off-topic sentence whose only
        overlaps are a couple of incidental words.
        """
        return len({tok for tok in _tokenize(query) if tok in self._content_vocab})

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
        min_content_terms: int = DEFAULT_MIN_CONTENT_TERMS,
    ) -> Optional[str]:
        """Return the top hit's ``source_citation`` if the candidate is grounded.

        Builds a query from the candidate's stem (and worked solution / topic
        when present). Returns ``None`` — driving the graph's "no source
        grounding" abstain path — unless ALL of the following hold:

        * the candidate has usable text, and
        * the query matches at least ``min_content_terms`` distinct corpus
          content terms (the RRF-rank-independent relevance signal: an off-topic
          stem whose only overlaps are a couple of incidental words abstains even
          though its fused score can reach the relevance-blind both-arms ceiling),
          and
        * a fused hit exists whose RRF score clears ``min_score``.

        The relevance-term check is applied first so an off-topic query never
        grounds regardless of its RRF score.
        """
        query = " ".join(
            str(candidate.get(key, ""))
            for key in ("stem", "worked_solution", "topic", "technique")
        ).strip()
        if not query:
            return None
        # RRF-rank-independent relevance gate: require enough matched content
        # terms before any citation can be returned.
        if self._matched_terms(query) < min_content_terms:
            return None
        hits = self.retrieve(query, k=1)
        if not hits:
            return None
        top = hits[0]
        if top["score"] < min_score:
            return None
        return top["source_citation"]

    def as_graph_retriever(
        self,
        *,
        min_score: float,
        min_content_terms: int = DEFAULT_MIN_CONTENT_TERMS,
    ):
        """Adapt to the graph's ``Retriever = Callable[[dict], Optional[str]]``.

        Returns a closure ``retriever(candidate) -> citation | None`` suitable
        for injection into :func:`graph.build_graph` / :func:`graph.run_generation`.
        """

        def _retriever(candidate: dict) -> Optional[str]:
            return self.ground(
                candidate,
                min_score=min_score,
                min_content_terms=min_content_terms,
            )

        return _retriever
