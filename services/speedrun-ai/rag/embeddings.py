# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Embedder abstraction for the SEMANTIC grounding gate.

The grounding gate's decisive signal is SEMANTIC relevance, not word overlap:
after RRF selects the top hit, :meth:`rag.retriever.HybridRetriever.ground`
requires the cosine of an embedding of the query against an embedding of that
top passage to clear a calibrated threshold. Word-overlap gates were repeatedly
defeated because "one incidental math word in off-topic prose" shares the same
anchor as a genuine terse stem; embeddings separate the two by MEANING.

Two paths, one interface ``embed(texts: list[str]) -> list[vector]``:

* **Real path** — :class:`OpenAIEmbedder`, ``text-embedding-3-small``, built
  LAZILY only when an API key is present (mirroring ``app._make_openai_propose``).
  Constructing this class does NOT touch the network; the client is only built
  when :meth:`OpenAIEmbedder.embed` is first called.
* **Test path** — tests inject their OWN deterministic stub embedder (no
  network), so the tracked suite is hermetic. Any object exposing
  ``embed(texts) -> list[vector]`` works (structural typing).

The API key is NEVER printed, logged, or serialized here.
"""

from __future__ import annotations

from typing import Protocol

# Sentinel model for the real semantic gate. Small, cheap, strong enough to
# separate genuine math stems from off-topic prose (see the calibration in
# rag/retriever.py).
OPENAI_EMBED_MODEL = "text-embedding-3-small"


class Embedder(Protocol):
    """Structural type for anything that can embed a batch of texts.

    ``embed`` returns one vector (list[float]) per input text, index-aligned.
    Vectors need not be pre-normalized; cosine consumers normalize.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...


class OpenAIEmbedder:
    """Lazily-constructed OpenAI embedder (``text-embedding-3-small``).

    The OpenAI client is built on first :meth:`embed` (not at construction), so
    importing / instantiating this never touches the network and never requires
    a key to be present at import time. The key is read from the injected
    settings-like object and is never logged.
    """

    def __init__(self, api_key: str, *, model: str = OPENAI_EMBED_MODEL) -> None:
        if not api_key:
            raise ValueError("OpenAIEmbedder requires a non-empty api_key")
        self._api_key = api_key
        self._model = model
        self._client = None  # built lazily

    def _ensure_client(self):  # pragma: no cover - exercised only in live runs
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        """Embed a batch of texts with ``text-embedding-3-small``.

        Returns one vector per input, index-aligned. Empty input -> empty list.
        """
        if not texts:
            return []
        client = self._ensure_client()
        resp = client.embeddings.create(model=self._model, input=list(texts))
        # The API guarantees output order matches input order.
        return [list(item.embedding) for item in resp.data]


def make_openai_embedder_if_key(settings) -> OpenAIEmbedder | None:
    """Build an :class:`OpenAIEmbedder` IFF the settings carry a key, else None.

    Mirrors the lazy ``_make_openai_propose`` gating in ``app.py``: no key ->
    no real embedder -> the retriever falls back to its lexical topicality gate
    (still safe, just without the semantic discriminator). Never logs the key.
    """
    key = getattr(settings, "api_key", None)
    if not key:
        return None
    model = getattr(settings, "embed_model", None) or OPENAI_EMBED_MODEL
    return OpenAIEmbedder(key, model=model)
