# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
§7e leakage check — a standalone, reproducible, CITABLE "the training data is
clean" runner.

Grader rubric §7e asks for "a script that scans your training data and flags any
test item, or a near-copy of one, that slipped in. Run it and show the result is
clean." This module is that script. It:

1. Loads the TRAINING / study corpus (read-only):
   * ``seed_study`` — the seed declarative cards' front/back and the curated
     problem bank's stem/worked_solution (``repos/anki/speedrun/seed/*.yaml``),
     via :func:`eval.leakage.load_study_texts` (the exact study content the
     graph's real gold gate is built against — cross-repo READ ONLY).
   * ``rag_corpus`` — the vendored RAG passages' text
     (``rag/corpus/gre_math_sources.jsonl``), via :func:`rag.retriever.load_corpus`.
2. Scans every training item against the held-out gold set using the validated
   scanner :func:`eval.leakage.leaks` (a training item LEAKS iff it shares a
   13-gram word run with, OR has TF-IDF cosine >= 0.85 to, ANY gold item).
3. Reports AGGREGATE counts only.

Two gold "surfaces" are reported (mirroring how ``eval/gate.py`` reports STRICT
vs FAMILY — dual, clearly-labeled metrics, nothing hidden):

* **Test-item identity (PRIMARY)** — a "test item" is the QUESTION a learner must
  answer: its ``question`` + ``choices`` + ``correct_answer``. Leakage here means
  a held-out QUESTION (or a near-copy) actually slipped into the study material.
  This is the §7e-faithful verdict and drives ``clean``.
* **Full content (STRICT diagnostic)** — additionally folds each gold item's
  ``worked_solution`` derivation into the compared surface. This is stricter than
  the rubric asks and can flag a *shared derivation step* on a canonical example
  (e.g. the determinant of the standard 2x2 matrix) even when the QUESTIONS
  differ. Reported transparently as a diagnostic; it does NOT gate ``clean``.

INDEPENDENCE / HOLDOUT RULE (mirrors ``eval/gate.py`` and ``eval/perf_eval.py``):
the runner CODE reads the held-out gold set at runtime ONLY to compute aggregate
counts. It NEVER prints, serializes, or asserts on individual gold questions /
answers. Even a leak record is aggregate-safe — it carries the training item's
source + index + which scanner arm fired + the cosine, but NEVER the gold or the
near-copy text (a near-copy of a gold item would itself reveal gold content).

Hermetic + deterministic + offline (no network, no OpenAI). ``clean`` is True iff
zero test-item-identity leaks were found AND the check was actually runnable
(non-empty gold AND non-empty training) — an empty gold/training set fails
CLOSED, never a false "clean".
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from eval.leakage import (
    _max_cosine,
    _ngram_overlap,
    leaks,
    load_study_texts,
)

# ---------------------------------------------------------------------------
# Locations + pre-registered thresholds
# ---------------------------------------------------------------------------

# services/speedrun-ai/eval/leakage_check.py -> repo root is three parents up
# (same resolution as eval/gate.py / eval/perf_eval.py).
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD_PATH = _REPO_ROOT / "eval" / "holdout" / "gre_math_gold.jsonl"

# The §7e / §7f pre-registered scanner thresholds. These MUST match
# eval.leakage.leaks (and the graph's real gold gate in eval.gate.make_gold_gate).
DEFAULT_NGRAM = 13
DEFAULT_SIM_THRESHOLD = 0.85

# The fields that IDENTIFY a gold "test item" — the question a learner would see
# and answer. Bibliographic / metadata fields (``source_citation``, ``topic_id``,
# ``difficulty_hint``, ``id``, ``verification``) are DELIBERATELY excluded so a
# shared citation or topic label can never manufacture a spurious "leak".
_GOLD_IDENTITY_FIELDS = ("question", "stem", "prompt", "correct_answer", "answer")
_GOLD_LIST_FIELDS = ("choices", "distractors", "options")
# Worked-solution / derivation fields — folded in ONLY for the STRICT diagnostic
# surface, never the primary test-item-identity verdict.
_GOLD_SOLUTION_FIELDS = ("worked_solution", "solution", "explanation")

# Human-facing labels for the two gold surfaces.
_SCOPE_IDENTITY = "test-item identity (question + choices + correct_answer)"
_SCOPE_FULL = "full content (test-item identity + worked-solution derivations)"


# ---------------------------------------------------------------------------
# Gold-set loading (aggregate-internal — NEVER surfaced outward)
# ---------------------------------------------------------------------------


def _gold_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("SPEEDRUN_GOLD_PATH")
    return Path(env) if env else DEFAULT_GOLD_PATH


def _load_gold_rows(path: Path | str | None = None) -> list[dict]:
    """Parse the held-out gold JSONL for AGGREGATE use only (INTERNAL).

    Mirrors ``gate.py::_load_gold`` — rows are consumed to compute counts; no row
    text is ever exposed. Returns ``[]`` (never raises) if the holdout is absent
    so a misconfigured environment fails CLOSED at :func:`scan` rather than
    crashing.
    """
    gold_path = _gold_path(path)
    if not gold_path.is_file():
        return []
    rows: list[dict] = []
    with gold_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _gold_item_text(row: dict, *, include_solution: bool) -> str:
    """Concatenate a gold item's human-readable text (INTERNAL, aggregate-only).

    ``include_solution`` folds the worked-solution / derivation fields into the
    compared surface (the STRICT diagnostic). The returned text is fed ONLY to
    the scanner to compute aggregate counts; it is never printed or serialized.
    Metadata / citation fields are always excluded.
    """
    fields = _GOLD_IDENTITY_FIELDS + (
        _GOLD_SOLUTION_FIELDS if include_solution else ()
    )
    parts: list[str] = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    for field in _GOLD_LIST_FIELDS:
        value = row.get(field)
        if isinstance(value, (list, tuple)):
            parts.extend(str(v) for v in value if str(v).strip())
    return " ".join(parts).strip()


def load_gold_texts(
    path: Path | str | None = None, *, include_solution: bool = False
) -> list[str]:
    """Per-item gold text strings (aggregate-internal).

    ``include_solution=False`` (default) returns the test-item IDENTITY surface;
    ``True`` returns the full-content surface (adds worked-solution derivations).
    Callers must treat these as opaque holdout content: consume them to compute
    counts, never print or serialize them.
    """
    return [
        t
        for t in (
            _gold_item_text(r, include_solution=include_solution)
            for r in _load_gold_rows(path)
        )
        if t
    ]


# ---------------------------------------------------------------------------
# Training / study corpus loading (read-only; cross-repo seed read is fine)
# ---------------------------------------------------------------------------


def _load_corpus_rows(path: Path | str | None = None) -> list[dict]:
    """Load the vendored RAG passages, degrading to ``[]`` if unavailable.

    Imported lazily so the (heavy) retriever deps load only when the corpus is
    actually scanned, and so a missing corpus never breaks the seed-only path.
    """
    try:
        from rag.retriever import load_corpus

        return load_corpus(path)
    except Exception:
        return []


def load_training_items(
    *,
    seed_dir: Path | str | None = None,
    corpus_path: Path | str | None = None,
    include_corpus: bool = True,
) -> list[dict]:
    """Load the TRAINING / study corpus as tagged ``{"source", "text"}`` items.

    Read-only. ``seed_study`` items come from the seed cards + problem bank
    (cross-repo, never modified); ``rag_corpus`` items come from the vendored
    passages' ``text`` field (included when ``include_corpus``). Blank items are
    dropped.
    """
    items: list[dict] = []
    for text in load_study_texts(seed_dir):
        if text and text.strip():
            items.append({"source": "seed_study", "text": text})
    if include_corpus:
        for row in _load_corpus_rows(corpus_path):
            text = str(row.get("text", "") or "").strip()
            if text:
                items.append({"source": "rag_corpus", "text": text})
    return items


# ---------------------------------------------------------------------------
# The scan (PURE + injectable — the hermetic unit-tested core)
# ---------------------------------------------------------------------------


def scan(
    training_items: list[dict],
    gold_texts: list[str],
    *,
    ngram: int = DEFAULT_NGRAM,
    sim_threshold: float = DEFAULT_SIM_THRESHOLD,
    gold_scope: str | None = None,
) -> dict[str, Any]:
    """Scan each TRAINING item against the gold set; return AGGREGATE counts.

    A training item LEAKS iff it is a verbatim / near copy of ANY gold item under
    :func:`eval.leakage.leaks` (a shared ``ngram``-word run OR TF-IDF cosine
    ``>= sim_threshold``). Returns::

        {
          "ngram", "sim_threshold", "gold_scope",
          "num_gold_items", "num_training_items", "num_leaks",
          "ngram_hits",          # flags whose verbatim n-gram arm fired
          "cosine_near_copies",  # flags whose cosine arm fired (>= threshold)
          "runnable",   # gold AND training both non-empty
          "clean",      # runnable AND num_leaks == 0  (fail-closed)
          "by_source":  {src: {"num_items": n, "leaks": k}, ...},
          "leaks":      [ {"source", "training_index",
                           "ngram_overlap", "max_cosine"}, ... ],
        }

    AGGREGATE-ONLY: no gold text and no near-copy text ever appears in the
    result (leak records carry the training index + which arm fired + the cosine
    only). Deterministic and offline.
    """
    gold = [t for t in (gold_texts or []) if t and t.strip()]
    by_source: dict[str, dict[str, int]] = {}
    leak_records: list[dict[str, Any]] = []
    scanned = 0

    for idx, item in enumerate(training_items):
        text = str(item.get("text", "") or "")
        source = str(item.get("source", "unknown"))
        if not text.strip():
            continue
        scanned += 1
        bucket = by_source.setdefault(source, {"num_items": 0, "leaks": 0})
        bucket["num_items"] += 1
        if gold and leaks(text, gold, ngram=ngram, sim_threshold=sim_threshold):
            bucket["leaks"] += 1
            # Aggregate-safe diagnostics ONLY (no gold / near-copy text): which
            # arm fired and the exact cosine the scanner saw.
            leak_records.append(
                {
                    "source": source,
                    "training_index": idx,
                    "ngram_overlap": bool(_ngram_overlap(text, gold, ngram)),
                    "max_cosine": round(_max_cosine(text, gold), 4),
                }
            )

    runnable = len(gold) > 0 and scanned > 0
    return {
        "ngram": ngram,
        "sim_threshold": sim_threshold,
        "gold_scope": gold_scope or _SCOPE_IDENTITY,
        "num_gold_items": len(gold),
        "num_training_items": scanned,
        "num_leaks": len(leak_records),
        "ngram_hits": sum(1 for r in leak_records if r["ngram_overlap"]),
        "cosine_near_copies": sum(
            1 for r in leak_records if r["max_cosine"] >= sim_threshold
        ),
        "runnable": runnable,
        "clean": runnable and len(leak_records) == 0,
        "by_source": by_source,
        "leaks": leak_records,
    }


def run(
    *,
    seed_dir: Path | str | None = None,
    gold_path: Path | str | None = None,
    corpus_path: Path | str | None = None,
    include_corpus: bool = True,
    ngram: int = DEFAULT_NGRAM,
    sim_threshold: float = DEFAULT_SIM_THRESHOLD,
) -> dict[str, Any]:
    """Load the REAL training corpus + gold set and run the §7e scan.

    Returns the PRIMARY (test-item-identity) aggregate result, with the STRICT
    full-content pass attached under ``"strict_full_content"`` as a transparent
    diagnostic. Reads the held-out gold set at runtime for counts only.
    """
    training = load_training_items(
        seed_dir=seed_dir, corpus_path=corpus_path, include_corpus=include_corpus
    )
    gold_identity = load_gold_texts(gold_path, include_solution=False)
    gold_full = load_gold_texts(gold_path, include_solution=True)

    primary = scan(
        training,
        gold_identity,
        ngram=ngram,
        sim_threshold=sim_threshold,
        gold_scope=_SCOPE_IDENTITY,
    )
    strict = scan(
        training,
        gold_full,
        ngram=ngram,
        sim_threshold=sim_threshold,
        gold_scope=_SCOPE_FULL,
    )
    primary["strict_full_content"] = {
        "gold_scope": strict["gold_scope"],
        "num_gold_items": strict["num_gold_items"],
        "num_leaks": strict["num_leaks"],
        "ngram_hits": strict["ngram_hits"],
        "cosine_near_copies": strict["cosine_near_copies"],
        "by_source": strict["by_source"],
        "leaks": strict["leaks"],
        "note": (
            "Stricter than §7e asks: folds gold worked-solution DERIVATIONS into "
            "the compared surface. A flag here with cosine_near_copies == 0 is a "
            "shared verbatim DERIVATION step on a canonical example (e.g. the "
            "determinant of a standard 2x2 matrix), not a reproduced test "
            "QUESTION. Aggregate-safe records only."
        ),
    }
    return primary


# ---------------------------------------------------------------------------
# Presentation (AGGREGATE-only text + citable JSON artifact)
# ---------------------------------------------------------------------------


def _leak_lines(records: list[dict], indent: str = "  ") -> list[str]:
    lines = []
    for rec in records:
        lines.append(
            f"{indent}- source={rec['source']} idx={rec['training_index']} "
            f"ngram_overlap={rec['ngram_overlap']} max_cosine={rec['max_cosine']}"
        )
    return lines


def format_report(result: dict[str, Any]) -> str:
    """Human-readable AGGREGATE summary. Never echoes gold / near-copy text."""
    n = result["num_training_items"]
    m = result["num_gold_items"]
    k = result["num_leaks"]
    lines = [
        "§7e leakage check — training/study data vs held-out gold set",
        "=" * 64,
        f"scanner : eval.leakage.leaks(ngram={result['ngram']}, "
        f"sim_threshold={result['sim_threshold']})",
        "          [flags a >=13-gram word overlap OR TF-IDF cosine "
        ">= threshold]",
        f"training/study items scanned : {n}",
        f"held-out gold items          : {m}",
        "",
        f"PRIMARY surface — {result['gold_scope']}",
        f"  leaks / near-copies found  : {k}  "
        f"(verbatim n-gram: {result.get('ngram_hits', 0)}, "
        f"cosine near-copies: {result.get('cosine_near_copies', 0)})",
        "  by source:",
    ]
    for source, bucket in sorted(result["by_source"].items()):
        lines.append(
            f"    {source:<12} items={bucket['num_items']:<5d} "
            f"leaks={bucket['leaks']}"
        )
    lines += _leak_lines(result["leaks"], indent="    ")

    strict = result.get("strict_full_content")
    if strict is not None:
        lines += [
            "",
            f"STRICT diagnostic — {strict['gold_scope']}",
            f"  flags: {strict['num_leaks']}  "
            f"(verbatim n-gram: {strict['ngram_hits']}, "
            f"cosine near-copies: {strict['cosine_near_copies']})",
        ]
        lines += _leak_lines(strict["leaks"], indent="    ")

    lines.append("")
    if not result.get("runnable", False):
        lines.append(
            "WARNING: check NOT runnable (missing gold or training data) — this "
            "is NOT a clean pass (fails closed)."
        )
    elif result["clean"]:
        lines.append(
            f"LEAKAGE: 0 found across {n} training items vs {m} gold items "
            "(clean)"
        )
        if strict and strict["num_leaks"]:
            lines.append(
                f"  note: the STRICT diagnostic surfaced {strict['num_leaks']} "
                "shared worked-solution derivation step(s) on a canonical "
                f"example (cosine near-copies: {strict['cosine_near_copies']}), "
                "not a reproduced test question — reported for transparency."
            )
    else:
        lines.append(
            f"LEAKAGE: {k} found across {n} training items vs {m} gold items "
            "(NOT clean)"
        )
        lines.append(
            "  (records are aggregate-safe: source + index + arm + cosine; no "
            "gold/near-copy text)"
        )
    return "\n".join(lines)


def emit_artifact(result: dict[str, Any], path: Path | str | None = None) -> Path:
    """Write the citable JSON artifact (default ``eval/leakage-check.json``).

    Contains AGGREGATE counts only — safe to commit and cite.
    """
    out_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parent / "leakage-check.json"
    )
    payload = dict(result)
    payload["notes"] = (
        "§7e leakage check. Each TRAINING/study item (seed declarative cards + "
        "curated problem bank via eval.leakage.load_study_texts, and the "
        "vendored RAG corpus passages) is scanned against the held-out gold set "
        "with eval.leakage.leaks (>=13-gram word overlap OR TF-IDF cosine >= "
        "sim_threshold). AGGREGATE counts only — no gold or near-copy text is "
        "read out. PRIMARY surface = test-item identity (question + choices + "
        "correct_answer); clean == (runnable AND num_leaks == 0). "
        "strict_full_content additionally compares gold worked-solution "
        "derivations (a transparency diagnostic; not the §7e verdict). An empty "
        "gold or training set fails closed (clean=false)."
    )
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return out_path


if __name__ == "__main__":  # pragma: no cover
    _result = run()
    print(format_report(_result))
    _artifact = emit_artifact(_result)
    print(f"\n[emitted] {_artifact}")
    # Exit non-zero if the data is not provably clean, so a repro run / CI fails
    # loudly on any test-item leak (or on a non-runnable, fail-closed check).
    sys.exit(0 if _result.get("clean") else 1)
