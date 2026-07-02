# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
§7f leakage scanner.

A generated problem must not be a verbatim copy or near-duplicate of the
curated study content the learner is being tested on. This module provides a
single reusable predicate :func:`leaks`, plus a loader for the "study content"
(the seed declarative cards + the curated problem bank) it is checked against.

The scanner is deterministic and offline. Two independent arms — a candidate
leaks if EITHER fires:

1. **Verbatim n-gram overlap** — any shared word-level ``ngram``-gram (default
   13) between the candidate and a study text. This catches copy/paste even
   when the surrounding wording differs.
2. **TF-IDF cosine similarity** — cosine similarity ``>= sim_threshold``
   (default 0.85) against any study text. This catches heavy paraphrase /
   reordering that slips past the exact-n-gram check.

§7f target: **leakage = 0**. The gate treats ANY leak as an auto-fail for that
card (see :func:`eval.gate.make_gold_gate`).

Study-content source
--------------------
The study texts are loaded from the Anki seed YAML at
``repos/anki/speedrun/seed/*.yaml`` (declarative cards' front/back + the
problem bank's stem/worked_solution). That path lives in a DIFFERENT repo and
is not reachable from this git worktree, so :func:`load_study_texts` takes a
configurable ``seed_dir`` defaulting to the absolute umbrella location and
returns ``[]`` gracefully if the path is absent (documented in eval/README.md).
The YAML is parsed with a tiny dependency-free reader (no PyYAML needed).
"""

from __future__ import annotations

import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Default location of the curated study content (a different repo; see module
# docstring). Configurable via the ``seed_dir`` argument / SPEEDRUN_SEED_DIR.
DEFAULT_SEED_DIR = Path(
    r"C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki\speedrun\seed"
)

_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _words(text: str) -> list[str]:
    """Lowercased word tokens. Deterministic."""
    return _WORD_RE.findall(text.lower())


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _ngram_overlap(candidate: str, study_texts: list[str], n: int) -> bool:
    cand_grams = _ngrams(_words(candidate), n)
    if not cand_grams:
        return False
    for text in study_texts:
        if cand_grams & _ngrams(_words(text), n):
            return True
    return False


def _max_cosine(candidate: str, study_texts: list[str]) -> float:
    """Max TF-IDF cosine similarity of ``candidate`` vs any study text.

    The vectorizer is fit on the study texts + candidate together so the shared
    vocabulary is represented. Deterministic (no randomness in TF-IDF).
    """
    corpus = [*study_texts, candidate]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        token_pattern=r"[A-Za-z0-9]+",
        ngram_range=(1, 2),
    )
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (e.g. candidate had no word chars).
        return 0.0
    cand_vec = matrix[-1]
    study_matrix = matrix[:-1]
    sims = cosine_similarity(cand_vec, study_matrix).ravel()
    return float(sims.max()) if sims.size else 0.0


def leaks(
    candidate_text: str,
    corpus_texts: list[str],
    *,
    ngram: int = 13,
    sim_threshold: float = 0.85,
) -> bool:
    """Return True iff ``candidate_text`` leaks the study ``corpus_texts``.

    Leaks if EITHER a shared word-level ``ngram``-gram exists OR TF-IDF cosine
    similarity ``>= sim_threshold`` against any study text. Deterministic and
    offline. An empty candidate or empty corpus never leaks.
    """
    candidate_text = (candidate_text or "").strip()
    study_texts = [t for t in (corpus_texts or []) if t and t.strip()]
    if not candidate_text or not study_texts:
        return False
    if _ngram_overlap(candidate_text, study_texts, ngram):
        return True
    return _max_cosine(candidate_text, study_texts) >= sim_threshold


# ---------------------------------------------------------------------------
# Study-content loader (dependency-free YAML reader for the seed files)
# ---------------------------------------------------------------------------

# The seed YAML is a flat list of blocks; each block is a run of
# ``key: "value"`` lines. We only need a handful of string fields, so a small
# line-based reader avoids adding PyYAML to this service's deps.
_STUDY_FIELDS = ("front", "back", "stem", "worked_solution")
_KV_RE = re.compile(r'^\s*([A-Za-z_]+):\s*"(.*)"\s*$')


def _unescape(value: str) -> str:
    # Minimal YAML double-quoted unescaping for the escapes our seed uses.
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _extract_study_strings(yaml_text: str) -> list[str]:
    """Pull the study-relevant string fields out of a seed YAML file.

    Deliberately simple: matches ``field: "…"`` lines for the fields we care
    about. Values our seed spreads across quoted single-line entries; any line
    that does not match is ignored. Never raises on malformed input.
    """
    out: list[str] = []
    for line in yaml_text.splitlines():
        match = _KV_RE.match(line)
        if not match:
            continue
        field, value = match.group(1), match.group(2)
        if field in _STUDY_FIELDS and value.strip():
            out.append(_unescape(value))
    return out


def load_study_texts(seed_dir: Path | str | None = None) -> list[str]:
    """Load the study content (seed cards + problem bank) as plain strings.

    Reads every ``*.yaml`` under ``seed_dir`` (default :data:`DEFAULT_SEED_DIR`,
    overridable via the ``SPEEDRUN_SEED_DIR`` env var) and extracts the
    front/back/stem/worked_solution string fields. Returns ``[]`` (never
    raises) if the directory is missing — the caller documents this fallback.
    Read-only; the seed files are never modified.
    """
    import os

    if seed_dir is None:
        seed_dir = os.environ.get("SPEEDRUN_SEED_DIR") or DEFAULT_SEED_DIR
    directory = Path(seed_dir)
    if not directory.is_dir():
        return []
    texts: list[str] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            texts.extend(_extract_study_strings(path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return texts
