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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

CORPUS_PATH = Path(__file__).with_name("corpus") / "gre_math_sources.jsonl"

_REQUIRED_FIELDS = ("id", "topic_id", "title", "text", "source_citation")


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


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization. Deterministic and offline."""
    return _TOKEN_RE.findall(text.lower())


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
        else:
            self.dense_arm = "tfidf"
            # Deterministic offline vectorizer: unigrams + bigrams, sublinear tf.
            self._tfidf = TfidfVectorizer(
                lowercase=True,
                token_pattern=r"[A-Za-z0-9]+",
                ngram_range=(1, 2),
                sublinear_tf=True,
            )
            self._tfidf_matrix = self._tfidf.fit_transform(self._docs)
            self._doc_embeddings = None

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

    def ground(self, candidate: dict, *, min_score: float) -> Optional[str]:
        """Return the top hit's ``source_citation`` if it clears ``min_score``.

        Builds a query from the candidate's stem (and worked solution / topic
        when present). If the top fused hit's score is below ``min_score`` — or
        the candidate has no usable text — returns ``None`` so the generation
        graph takes its "no source grounding" abstain path.
        """
        query = " ".join(
            str(candidate.get(key, ""))
            for key in ("stem", "worked_solution", "topic", "technique")
        ).strip()
        if not query:
            return None
        hits = self.retrieve(query, k=1)
        if not hits:
            return None
        top = hits[0]
        if top["score"] < min_score:
            return None
        return top["source_citation"]

    def as_graph_retriever(self, *, min_score: float):
        """Adapt to the graph's ``Retriever = Callable[[dict], Optional[str]]``.

        Returns a closure ``retriever(candidate) -> citation | None`` suitable
        for injection into :func:`graph.build_graph` / :func:`graph.run_generation`.
        """

        def _retriever(candidate: dict) -> Optional[str]:
            return self.ground(candidate, min_score=min_score)

        return _retriever
