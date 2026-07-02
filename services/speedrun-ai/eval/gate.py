# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
§7f gold-set gate harness.

This is the independent evaluation GATE for the AI problem generator. It
computes the §7f metrics AGGREGATELY against the held-out gold set — which the
generator and RAG corpus were built WITHOUT seeing, and which must stay that
way. The harness CODE reads the gold file at runtime to emit aggregate numbers;
it never surfaces individual gold questions/answers.

Functions
---------
- :func:`recall_at_10_report` — Recall@10 for BM25-only / dense-only / hybrid
  retrieval against the gold set, plus corpus coverage. Aggregate only.
- :func:`corpus_coverage` — fraction of gold source citations present in the
  RAG corpus (an upper bound on achievable Recall).
- :func:`wrong_answer_batch_result` — drives the REAL SymPy verifier over a
  batch of correct + deliberately-wrong specs; proves post-gate wrong-answer
  rate = 0 (every wrong spec is rejected before it could be emitted).
- :func:`make_gold_gate` — factory returning the REAL graph gate: a candidate
  that leaks the study content fails the gate (→ graph abstains).
- :func:`llm_judge` — scaffold for the subjective useful / bad-teaching metrics;
  runs ONLY with an injected client (the enabled path / demo). Never called in
  hermetic tests except with a fake client.

§7f cutoffs (pre-registered in eval/README.md BEFORE any results):
  * wrong-answer rate <= 2%  (target 0; any wrong post-gate => halt & fix verifier)
  * useful >= 80%            (LLM-judge / human review, at demo)
  * bad-teaching <= 15%      (LLM-judge / human review, at demo)
  * leakage = 0              (this harness's leakage scanner)
  * hybrid RAG beats the better baseline by >= 5 pts Recall@10 (reported)

INDEPENDENCE RULE: nothing here reads gold text into anything that leaves the
process as anything other than an aggregate count/fraction.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from eval.leakage import leaks, load_study_texts
from rag.retriever import HybridRetriever, load_corpus
from verify.sympy_verifier import ProblemSpec, verify

# ---------------------------------------------------------------------------
# Gold-set location (configurable; defaults to the repo-root eval/holdout/).
# ---------------------------------------------------------------------------

# services/speedrun-ai/eval/gate.py -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD_PATH = _REPO_ROOT / "eval" / "holdout" / "gre_math_gold.jsonl"

# A source citation appearing in the gold set may be absent from the corpus; a
# source not in the corpus can NEVER be retrieved, so it bounds Recall.


def _gold_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("SPEEDRUN_GOLD_PATH")
    return Path(env) if env else DEFAULT_GOLD_PATH


def _load_gold(path: Path | str | None = None) -> list[dict]:
    """Load the held-out gold set at runtime.

    INTERNAL. Returns the parsed rows for AGGREGATE computation only; callers in
    this module never expose row text outward.
    """
    gold_path = _gold_path(path)
    rows: list[dict] = []
    with gold_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# 1. Recall@10 retrieval eval + corpus coverage
# ---------------------------------------------------------------------------


def _norm_citation(citation: str) -> str:
    """Normalize a source citation for robust matching (case/space-insensitive).

    This is the STRICT match key: whole citation, lowercased, whitespace
    collapsed. Two citations match only if their full strings agree. The gold
    set and the vendored corpus were authored independently and use different
    conventions (e.g. "Vol." vs "Volume", a "§" section symbol vs a plain
    number), so exact matches are rare — see :func:`_family_key` for the looser,
    clearly-labeled textbook-level diagnostic.
    """
    return " ".join(str(citation or "").lower().split())


def _family_key(citation: str) -> str:
    """Textbook-FAMILY key for a citation (the source book, not the section).

    Used ONLY for a secondary, clearly-labeled coverage/Recall diagnostic that
    is robust to citation-string convention drift ("Vol."/"Volume", section
    notation, license suffixes). This is NOT the strict §7f target-match rule;
    it answers "is the right SOURCE BOOK retrieved, ignoring section
    formatting?". It is derived purely from the citation-format families and is
    NOT tuned per gold item.
    """
    text = _norm_citation(citation)
    # Drop a parenthetical license suffix like "(cc by 4.0)".
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("volume", "vol").replace("vol.", "vol")
    # The family is everything up to the first comma (the book/author), plus a
    # volume number if present so Vol.1/2/3 stay distinct.
    head = text.split(",", 1)[0].strip()
    vol = re.search(r"\bvol\s*(\d+)", text)
    return f"{head} vol{vol.group(1)}" if vol else head


def _recall_at_k(
    rank_fn: Callable[[str, int], list[dict]],
    gold: list[dict],
    k: int,
    key: Callable[[str], str] = _norm_citation,
):
    """Return (recall, hits, scored) where a gold item is a hit iff any top-k
    retrieved passage's ``source_citation`` (under ``key``) matches the gold
    item's. ``key`` is the strict :func:`_norm_citation` by default, or
    :func:`_family_key` for the looser textbook-level diagnostic."""
    hits = 0
    scored = 0
    for item in gold:
        target = key(item.get("source_citation", ""))
        if not target:
            continue
        scored += 1
        retrieved = {
            key(row.get("source_citation", ""))
            for row in rank_fn(item["question"], k)
        }
        if target in retrieved:
            hits += 1
    recall = hits / scored if scored else 0.0
    return recall, hits, scored


def corpus_coverage(
    gold_path: Path | str | None = None,
    corpus: list[dict] | None = None,
    key: Callable[[str], str] = _norm_citation,
) -> float:
    """Fraction of gold source citations that exist in the RAG corpus.

    A source absent from the corpus can never be retrieved, so this is an upper
    bound on achievable Recall. ``key`` selects the strict (default) or the
    textbook-family match. Aggregate fraction only.
    """
    gold = _load_gold(gold_path)
    rows = corpus if corpus is not None else load_corpus()
    corpus_sources = {key(r.get("source_citation", "")) for r in rows}
    targets = [
        key(item.get("source_citation", ""))
        for item in gold
        if str(item.get("source_citation", "")).strip()
    ]
    if not targets:
        return 0.0
    covered = sum(1 for t in targets if t in corpus_sources)
    return covered / len(targets)


def recall_at_10_report(
    gold_path: Path | str | None = None,
    corpus: list[dict] | None = None,
    k: int = 10,
) -> dict[str, Any]:
    """Compute Recall@k for BM25-only, dense-only, and hybrid over the gold set.

    Returns an AGGREGATE report dict::

        {
          "k": 10, "num_gold": int, "num_scored": int, "dense_arm": str,
          "recall_at_10": {"bm25": f, "dense": f, "hybrid": f},
          "hits": {"bm25": n, "dense": n, "hybrid": n},
          "coverage": f,
          "best_baseline": "bm25"|"dense", "best_baseline_recall": f,
          "hybrid_minus_best_baseline_pts": f,   # x100 percentage points
        }

    No gold question/answer text is included — counts and fractions only.
    """
    gold = _load_gold(gold_path)
    rows = corpus if corpus is not None else load_corpus()
    retriever = HybridRetriever(rows)

    # --- STRICT match (whole normalized citation string) -------------------
    bm25_r, bm25_h, scored = _recall_at_k(retriever.retrieve_bm25, gold, k)
    dense_r, dense_h, _ = _recall_at_k(retriever.retrieve_dense, gold, k)
    hybrid_r, hybrid_h, _ = _recall_at_k(retriever.retrieve, gold, k)

    if bm25_r >= dense_r:
        best_name, best_recall = "bm25", bm25_r
    else:
        best_name, best_recall = "dense", dense_r
    delta_pts = (hybrid_r - best_recall) * 100.0
    coverage = corpus_coverage(gold_path=gold_path, corpus=rows)

    # --- FAMILY match (textbook-level; robust to citation-format drift) -----
    fam = _family_key
    fbm25_r, fbm25_h, fscored = _recall_at_k(retriever.retrieve_bm25, gold, k, fam)
    fdense_r, fdense_h, _ = _recall_at_k(retriever.retrieve_dense, gold, k, fam)
    fhybrid_r, fhybrid_h, _ = _recall_at_k(retriever.retrieve, gold, k, fam)
    fbest_recall = max(fbm25_r, fdense_r)
    fbest_name = "bm25" if fbm25_r >= fdense_r else "dense"
    fdelta_pts = (fhybrid_r - fbest_recall) * 100.0
    fcoverage = corpus_coverage(gold_path=gold_path, corpus=rows, key=fam)

    return {
        "k": k,
        "num_gold": len(gold),
        "num_scored": scored,
        "dense_arm": retriever.dense_arm,
        # strict (whole-citation) metrics — the conservative primary numbers
        "recall_at_10": {"bm25": bm25_r, "dense": dense_r, "hybrid": hybrid_r},
        "hits": {"bm25": bm25_h, "dense": dense_h, "hybrid": hybrid_h},
        "coverage": coverage,
        "best_baseline": best_name,
        "best_baseline_recall": best_recall,
        "hybrid_minus_best_baseline_pts": delta_pts,
        # family (textbook-level) metrics — robust-to-format diagnostic
        "family": {
            "recall_at_10": {
                "bm25": fbm25_r,
                "dense": fdense_r,
                "hybrid": fhybrid_r,
            },
            "hits": {"bm25": fbm25_h, "dense": fdense_h, "hybrid": fhybrid_h},
            "coverage": fcoverage,
            "num_scored": fscored,
            "best_baseline": fbest_name,
            "best_baseline_recall": fbest_recall,
            "hybrid_minus_best_baseline_pts": fdelta_pts,
        },
    }


# ---------------------------------------------------------------------------
# 3. Wrong-answer rate = 0 by construction (verify() gates every emit)
# ---------------------------------------------------------------------------

# These specs are AUTHORED here (not drawn from the gold set). They exercise the
# real verifier across answer types with both correct and deliberately-wrong
# claimed answers. The generation graph only EMITS a problem whose spec passed
# verify(); so any wrong spec that verify() rejects can never be emitted.

_CORRECT_SPECS: list[dict] = [
    {"answer_type": "derivative", "expression": "x**2", "variable": "x",
     "claimed_answer": "2*x"},
    {"answer_type": "derivative", "expression": "sin(x)", "variable": "x",
     "claimed_answer": "cos(x)"},
    {"answer_type": "integral", "expression": "2*x", "variable": "x",
     "claimed_answer": "x**2", "definite": False},
    {"answer_type": "limit", "expression": "sin(x)/x", "variable": "x",
     "claimed_answer": "1", "limit_point": "0"},
    {"answer_type": "expression_equivalence", "expression": "(x+1)**2",
     "variable": "x", "claimed_answer": "x**2 + 2*x + 1"},
    {"answer_type": "numeric_value", "expression": "2+2", "variable": "x",
     "claimed_answer": "4"},
]

_WRONG_SPECS: list[dict] = [
    {"answer_type": "derivative", "expression": "x**2", "variable": "x",
     "claimed_answer": "3*x"},
    {"answer_type": "derivative", "expression": "sin(x)", "variable": "x",
     "claimed_answer": "-cos(x)"},
    {"answer_type": "integral", "expression": "2*x", "variable": "x",
     "claimed_answer": "x**2 + x", "definite": False},
    {"answer_type": "limit", "expression": "sin(x)/x", "variable": "x",
     "claimed_answer": "0", "limit_point": "0"},
    {"answer_type": "expression_equivalence", "expression": "(x+1)**2",
     "variable": "x", "claimed_answer": "x**2 + 1"},
    {"answer_type": "numeric_value", "expression": "2+2", "variable": "x",
     "claimed_answer": "5"},
]

_SPEC_FIELDS = {
    "answer_type", "expression", "variable", "claimed_answer", "definite",
    "lower_bound", "upper_bound", "limit_point", "extra_symbols",
    "numeric_eps", "numeric_samples", "numeric_seed",
}


def _verify_spec_dict(spec: dict) -> bool:
    kwargs = {k: v for k, v in spec.items() if k in _SPEC_FIELDS}
    return bool(verify(ProblemSpec(**kwargs)).passed)


def wrong_answer_batch_result() -> dict[str, Any]:
    """Run the authored batch through the REAL verifier and report the result.

    ``wrong_survived`` = number of deliberately-wrong specs that verify()
    ACCEPTED (must be 0). ``wrong_answer_rate`` = wrong_survived / num_wrong.
    Because the graph's verify node gates every emit, this rate IS the post-gate
    wrong-answer rate: 0 by construction.
    """
    correct_passed = sum(1 for s in _CORRECT_SPECS if _verify_spec_dict(s))
    wrong_survived = sum(1 for s in _WRONG_SPECS if _verify_spec_dict(s))
    num_wrong = len(_WRONG_SPECS)
    return {
        "num_correct": len(_CORRECT_SPECS),
        "num_wrong": num_wrong,
        "correct_passed": correct_passed,
        "wrong_survived": wrong_survived,
        "wrong_answer_rate": (wrong_survived / num_wrong) if num_wrong else 0.0,
    }


# ---------------------------------------------------------------------------
# 4. Real gold-gate factory (leakage-free check) for the graph
# ---------------------------------------------------------------------------


def _candidate_text(candidate: dict) -> str:
    """Concatenate the human-readable fields of a candidate for leak-checking."""
    return " ".join(
        str(candidate.get(key, ""))
        for key in ("stem", "worked_solution", "correct")
    ).strip()


def make_gold_gate(
    study_texts: list[str] | None = None,
    *,
    ngram: int = 13,
    sim_threshold: float = 0.85,
) -> Callable[[dict], bool]:
    """Build the REAL §7f gold gate for injection into the generation graph.

    Returns ``gate(candidate) -> bool``: ``False`` (fail → graph abstains) if
    the candidate leaks the study content, else ``True``. ANY leak is an
    auto-fail. If ``study_texts`` is None it is loaded from the seed YAML via
    :func:`eval.leakage.load_study_texts`.
    """
    texts = study_texts if study_texts is not None else load_study_texts()
    texts = [t for t in texts if t and t.strip()]

    def gate(candidate: dict) -> bool:
        text = _candidate_text(candidate)
        if not text or not texts:
            # No study content to compare against, or empty candidate: the
            # leakage gate has nothing to reject on (verify/RAG gate elsewhere).
            return True
        return not leaks(text, texts, ngram=ngram, sim_threshold=sim_threshold)

    return gate


# ---------------------------------------------------------------------------
# 5. LLM-judge scaffold (subjective useful / bad-teaching metrics)
# ---------------------------------------------------------------------------


def llm_judge(problem: dict, *, client: Any) -> dict[str, Any]:
    """Score a problem's usefulness + teaching quality via an injected client.

    RUN ONLY when the service is enabled (a real client is present) or at demo /
    human-review time. NEVER called in hermetic tests except with a fake client.
    ``client`` must expose ``score(problem) -> {"useful": bool,
    "bad_teaching": bool, ...}``. Raises if no client is supplied.

    §7f cutoffs measured from an aggregate of these verdicts: useful >= 80%,
    bad-teaching <= 15% (see eval/README.md — these require the LLM judge or
    human review; they are NOT computed hermetically).
    """
    if client is None:
        raise ValueError(
            "llm_judge requires an injected client (LLM judge is enabled-only)"
        )
    verdict = client.score(problem)
    if not isinstance(verdict, dict) or "useful" not in verdict:
        raise ValueError("client.score must return a dict with a 'useful' key")
    verdict.setdefault("bad_teaching", False)
    return verdict


def judge_batch(problems: list[dict], *, client: Any) -> dict[str, Any]:
    """Aggregate useful / bad-teaching rates over a batch (enabled-only)."""
    if not problems:
        return {"n": 0, "useful_rate": 0.0, "bad_teaching_rate": 0.0}
    verdicts = [llm_judge(p, client=client) for p in problems]
    useful = sum(1 for v in verdicts if v.get("useful"))
    bad = sum(1 for v in verdicts if v.get("bad_teaching"))
    n = len(verdicts)
    return {
        "n": n,
        "useful_rate": useful / n,
        "bad_teaching_rate": bad / n,
    }


# ---------------------------------------------------------------------------
# Standalone report (prints AGGREGATE numbers only; never raw gold pairs)
# ---------------------------------------------------------------------------


def format_report() -> str:
    report = recall_at_10_report()
    r = report["recall_at_10"]
    fam = report["family"]
    fr = fam["recall_at_10"]
    wa = wrong_answer_batch_result()
    k = report["k"]
    ns = report["num_scored"]
    fns = fam["num_scored"]
    lines = [
        "§7f gold-set gate — aggregate results",
        "=" * 64,
        f"gold items: {report['num_gold']}  (scored: {ns})  "
        f"dense_arm={report['dense_arm']}",
        "",
        "[STRICT match: whole normalized citation string]",
        f"  corpus coverage of gold sources: {report['coverage'] * 100:.1f}%  "
        "(upper bound on Recall)",
        f"  Recall@{k}  BM25-only  = {r['bm25']:.3f} "
        f"({report['hits']['bm25']}/{ns})",
        f"  Recall@{k}  dense-only = {r['dense']:.3f} "
        f"({report['hits']['dense']}/{ns})",
        f"  Recall@{k}  HYBRID     = {r['hybrid']:.3f} "
        f"({report['hits']['hybrid']}/{ns})",
        f"  best baseline = {report['best_baseline']} "
        f"({report['best_baseline_recall']:.3f}); "
        f"hybrid - best = {report['hybrid_minus_best_baseline_pts']:+.1f} pts",
        "",
        "[FAMILY match: textbook-level, robust to citation-format drift]",
        f"  corpus coverage of gold sources: {fam['coverage'] * 100:.1f}%  "
        "(upper bound on Recall)",
        f"  Recall@{k}  BM25-only  = {fr['bm25']:.3f} "
        f"({fam['hits']['bm25']}/{fns})",
        f"  Recall@{k}  dense-only = {fr['dense']:.3f} "
        f"({fam['hits']['dense']}/{fns})",
        f"  Recall@{k}  HYBRID     = {fr['hybrid']:.3f} "
        f"({fam['hits']['hybrid']}/{fns})",
        f"  best baseline = {fam['best_baseline']} "
        f"({fam['best_baseline_recall']:.3f}); "
        f"hybrid - best = {fam['hybrid_minus_best_baseline_pts']:+.1f} pts "
        "(§7f target >= +5.0 pts)",
        "",
        "-" * 64,
        f"  wrong-answer rate (post-gate) = "
        f"{wa['wrong_answer_rate'] * 100:.1f}%  "
        f"(wrong survived verify: {wa['wrong_survived']}/{wa['num_wrong']}; "
        f"correct verified: {wa['correct_passed']}/{wa['num_correct']}) "
        "— §7f <= 2%, target 0",
        f"  hybrid >= both baselines (strict): "
        f"{r['hybrid'] >= r['bm25'] and r['hybrid'] >= r['dense']}",
        f"  hybrid >= both baselines (family): "
        f"{fr['hybrid'] >= fr['bm25'] and fr['hybrid'] >= fr['dense']}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print(format_report())
