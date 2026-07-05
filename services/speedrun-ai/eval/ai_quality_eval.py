# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
§7f AI-card 3-count quality harness (the "AI checking & safety" deliverable).

Generate N cards from ONE covered source, run them through the REAL generation
graph (verified-only, exactly as ``POST /generate_batch`` / ``run_generation``
does — we reuse that code, never reimplement verify), judge each surviving emit
with the LLM judge, sort them into three buckets, apply the PRE-REGISTERED §7f
cutoffs, and BLOCK (drop) any card that fails.

The 3-count and its pre-registered cutoffs (see eval/README.md, fixed BEFORE
any results):

  * correct-&-useful          >= 80 %
  * wrong                      <= 2 %  (target 0; wrong is 0 by construction
                                        because the SymPy verify() node gates
                                        every emit — no unverified answer can be
                                        generated at all)
  * correct-but-bad-teaching   <= 15 %

Two entry points
----------------
- :func:`run_ai_quality_eval` — the pure harness. Injected ``generate`` (the
  real ``app.generate_problem`` in the live path; a fake in tests) and
  ``judge_client`` (a real OpenAI-backed judge live; a fake in tests). Returns
  AGGREGATE counts + rates + cutoff pass/fail; never surfaces raw card text.
  Optionally emits ``eval/ai-quality.json`` when ``SPEEDRUN_EVAL_EMIT=1``.
- :func:`main` (``python -m eval.ai_quality_eval``) — the LIVE, key-gated run.
  Builds the real generator + real LLM judge from the environment, runs the
  eval over ONE covered source, and reports the 3-count vs cutoffs. If the key
  is missing / unreachable it DOES NOT fabricate numbers: it writes the N
  generated cards to a file for HUMAN REVIEW and reports the subjective cutoffs
  as PENDING, clearly labeled.

HERMETIC RULE: the harness itself never touches the network. Generation and
judging are injected. The LIVE run (``main``) is the only place a real client
is constructed, and it is gated on ``OPENAI_API_KEY`` + ``SPEEDRUN_AI_ENABLED``.

HONESTY RULE: this module reports REAL numbers against the pre-registered
cutoffs. It never fabricates a subjective verdict — if the LLM judge cannot run,
the subjective cutoffs are reported PENDING (human-review fallback), never as a
pass.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

# The subjective verdicts come from the SAME injected judge client that backs
# eval.gate.llm_judge / judge_batch (a ``client.score(problem) -> verdict``
# collaborator). We score per-card here (rather than calling judge_batch) because
# the 3-count needs each card's individual bucket, not just aggregate rates.

# ---------------------------------------------------------------------------
# Pre-registered §7f cutoffs (see eval/README.md — fixed before any results)
# ---------------------------------------------------------------------------

CUTOFF_USEFUL = 0.80          # correct-&-useful rate must be >= this
CUTOFF_WRONG = 0.02           # wrong rate must be <= this (target 0)
CUTOFF_BAD_TEACHING = 0.15    # correct-but-bad-teaching rate must be <= this

# The default source to generate all cards from. ONE genuinely-open, covered
# leaf topic in the RAG corpus (OpenStax Calculus, CC BY 4.0). Documented in the
# §7f RESULTS paragraph. Overridable on the CLI.
DEFAULT_TOPIC = "calc::single_var::differentiation"
DEFAULT_SOURCE = "OpenStax Calculus Vol. 1, differentiation (3.x) (CC BY 4.0)"
DEFAULT_N = 50

# Where the aggregate artifact is written (gated behind SPEEDRUN_EVAL_EMIT=1).
_HERE = Path(__file__).resolve().parent
DEFAULT_ARTIFACT_PATH = _HERE / "ai-quality.json"
# Where generated cards are dumped for HUMAN REVIEW when the judge can't run.
DEFAULT_REVIEW_PATH = _HERE / "ai-quality-cards-for-review.jsonl"

# A generator is generate(topic, technique) -> graph result dict (the shape
# run_generation returns: {"status": "emit"|"abstain", "problem": {...}|None,...}).
Generator = Callable[[str, str], dict]


# ---------------------------------------------------------------------------
# The 3-bucket classifier
# ---------------------------------------------------------------------------


def classify(verdict: dict) -> str:
    """Sort a judge verdict into exactly one of the three §7f buckets.

    Priority: a WRONG card is "wrong" regardless of anything else (a wrong answer
    is the worst outcome and must be counted/blocked first). Otherwise a correct
    card with bad teaching is "bad_teaching". A correct, well-teaching, USEFUL
    card is "correct_useful". A correct card that is neither useful nor
    bad-teaching falls through to "correct_not_useful" — it is NOT
    correct-&-useful (it fails the useful bar) and is blocked.

    ``verdict`` keys (from the LLM judge): ``correct`` (bool), ``useful`` (bool),
    ``bad_teaching`` (bool). Missing keys default conservatively: ``correct``
    defaults True (the verifier already proved it), ``useful`` False,
    ``bad_teaching`` False.
    """
    correct = bool(verdict.get("correct", True))
    if not correct:
        return "wrong"
    if bool(verdict.get("bad_teaching", False)):
        return "bad_teaching"
    if bool(verdict.get("useful", False)):
        return "correct_useful"
    return "correct_not_useful"


# Buckets that are KEPT (shippable) vs BLOCKED (dropped). Only correct-&-useful
# ships; wrong, bad-teaching, and correct-but-not-useful are all blocked.
_KEPT_BUCKETS = {"correct_useful"}


# ---------------------------------------------------------------------------
# The harness
# ---------------------------------------------------------------------------


def run_ai_quality_eval(
    topic: str,
    technique: str,
    *,
    n: int,
    source: str,
    generate: Generator,
    judge_client: Any,
    judge_model: str = "unknown",
    artifact_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Run the §7f AI-card 3-count over N generated cards from ONE source.

    Steps (honest, verified-only):

    1. Make ``n`` INDEPENDENT generation attempts via ``generate`` (the real
       verified/grounded/gold-gated graph in the live path). Keep only the
       verified emits — every abstain is dropped BEFORE judging (a card that
       never verified is never a "wrong" card; it simply was never generated).
    2. Judge each surviving emit with the injected ``judge_client`` (the same
       ``client.score(problem) -> verdict`` collaborator that backs
       :func:`eval.gate.llm_judge`; real LLM live, fake in tests). This is the
       ONLY place the subjective useful / bad-teaching verdicts come from.
    3. Sort each judged card into one of the three buckets (:func:`classify`),
       compute aggregate counts + rates.
    4. Apply the pre-registered cutoffs; BLOCK (drop) every card that is not
       correct-&-useful; report kept / blocked and overall pass/fail.

    Returns an AGGREGATE dict (counts, rates, cutoffs, kept/blocked, N, source,
    judge model). NO raw card text is included. When ``SPEEDRUN_EVAL_EMIT=1`` the
    same dict is written to ``artifact_path`` (default ``eval/ai-quality.json``).
    """
    # --- 1. Generate N attempts; keep verified emits only ------------------
    emits: list[dict] = []
    n_generated = 0
    n_abstained = 0
    for _ in range(max(0, int(n))):
        result = generate(topic, technique)
        n_generated += 1
        if isinstance(result, dict) and result.get("status") == "emit":
            problem = result.get("problem")
            if isinstance(problem, dict):
                emits.append(problem)
                continue
        n_abstained += 1

    # --- 2. Judge each verified emit (subjective useful / bad-teaching) -----
    # Score each card directly through the injected client (the same
    # collaborator eval.gate.llm_judge uses); the 3-count needs per-card buckets,
    # not just aggregate rates.
    verdicts = [judge_client.score(p) for p in emits]

    # --- 3. Bucket + count --------------------------------------------------
    counts = {
        "correct_useful": 0,
        "wrong": 0,
        "bad_teaching": 0,
        "correct_not_useful": 0,
    }
    for verdict in verdicts:
        counts[classify(verdict)] += 1

    n_judged = len(verdicts)

    def _rate(bucket: str) -> float:
        return counts[bucket] / n_judged if n_judged else 0.0

    rates = {
        "correct_useful": _rate("correct_useful"),
        "wrong": _rate("wrong"),
        "bad_teaching": _rate("bad_teaching"),
    }

    # --- 4. Cutoffs + block failures ---------------------------------------
    # With nothing judged there is nothing to certify -> every cutoff "fails"
    # (we never certify a pass on an empty batch).
    have_cards = n_judged > 0
    cutoffs = {
        "correct_useful": {
            "cutoff": CUTOFF_USEFUL,
            "direction": ">=",
            "value": rates["correct_useful"],
            "pass": have_cards and rates["correct_useful"] >= CUTOFF_USEFUL,
        },
        "wrong": {
            "cutoff": CUTOFF_WRONG,
            "direction": "<=",
            "value": rates["wrong"],
            "pass": have_cards and rates["wrong"] <= CUTOFF_WRONG,
        },
        "bad_teaching": {
            "cutoff": CUTOFF_BAD_TEACHING,
            "direction": "<=",
            "value": rates["bad_teaching"],
            "pass": have_cards and rates["bad_teaching"] <= CUTOFF_BAD_TEACHING,
        },
    }
    passed = all(c["pass"] for c in cutoffs.values())

    # Block (drop) any card that fails: only correct-&-useful is kept.
    kept = sum(1 for v in verdicts if classify(v) in _KEPT_BUCKETS)
    blocked = n_judged - kept

    report = {
        "spec": "§7f AI-card 3-count (AI checking & safety)",
        "source": source,
        "topic": topic,
        "judge_model": judge_model,
        "n_generated": n_generated,
        "n_abstained": n_abstained,
        "n_judged": n_judged,
        "kept": kept,
        "blocked": blocked,
        "counts": counts,
        "rates": rates,
        "cutoffs": cutoffs,
        "passed": passed,
    }

    if os.environ.get("SPEEDRUN_EVAL_EMIT") == "1":
        path = Path(artifact_path) if artifact_path is not None else DEFAULT_ARTIFACT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return report


# ---------------------------------------------------------------------------
# Real LLM judge client (constructed ONLY in the live path)
# ---------------------------------------------------------------------------


class OpenAIJudgeClient:
    """A real OpenAI-backed judge exposing ``score(problem) -> verdict``.

    Constructed ONLY in the live path (:func:`main`), never in hermetic tests.
    Returns ``{"correct": bool, "useful": bool, "bad_teaching": bool,
    "rationale": str}``. ``correct`` is a SECONDARY, independent check on top of
    the SymPy verifier (the primary, hard gate); the useful / bad-teaching
    verdicts are the subjective §7f metrics.
    """

    def __init__(self, *, api_key: str, model: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def score(self, problem: dict) -> dict:  # pragma: no cover - network path
        stem = problem.get("stem", "")
        correct = problem.get("correct", "")
        worked = problem.get("worked_solution", "")
        choices = problem.get("choices", [])
        prompt = (
            "You are an independent grader of GRE-Mathematics practice cards.\n"
            "Judge the card below on THREE independent axes and respond with "
            "STRICT JSON only:\n"
            '{"correct": bool, "useful": bool, "bad_teaching": bool, '
            '"rationale": str}\n\n'
            "- correct: is the stated correct answer actually correct for the "
            "stem? (The answer was already symbolically verified; flag it false "
            "ONLY if you are confident it is wrong.)\n"
            "- useful: is this a well-posed, on-topic, non-trivial GRE-level "
            "practice item a student would benefit from?\n"
            "- bad_teaching: does the card teach badly — misleading framing, a "
            "wrong/absent worked solution, ambiguous or duplicated choices, or a "
            "distractor that is actually also correct? (correct answer, bad "
            "pedagogy.)\n\n"
            f"STEM: {stem}\n"
            f"CORRECT ANSWER: {correct}\n"
            f"CHOICES: {choices}\n"
            f"WORKED SOLUTION: {worked}\n"
        )
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        verdict = json.loads(content)
        verdict.setdefault("correct", True)
        verdict.setdefault("useful", False)
        verdict.setdefault("bad_teaching", False)
        return verdict


# ---------------------------------------------------------------------------
# Human-review fallback (when the LLM judge cannot run)
# ---------------------------------------------------------------------------


def _generate_cards_only(
    generate: Generator, topic: str, technique: str, n: int
) -> tuple[list[dict], int, int]:
    """Run N generation attempts and return (emitted problems, n_generated,
    n_abstained). Used by the human-review fallback so we can still emit the
    generated cards for manual review even without a judge."""
    emits: list[dict] = []
    n_generated = 0
    n_abstained = 0
    for _ in range(max(0, int(n))):
        result = generate(topic, technique)
        n_generated += 1
        if isinstance(result, dict) and result.get("status") == "emit":
            problem = result.get("problem")
            if isinstance(problem, dict):
                emits.append(problem)
                continue
        n_abstained += 1
    return emits, n_generated, n_abstained


def write_human_review_fallback(
    emits: list[dict],
    *,
    source: str,
    topic: str,
    n_generated: int,
    n_abstained: int,
    review_path: Path | str = DEFAULT_REVIEW_PATH,
    artifact_path: Path | str = DEFAULT_ARTIFACT_PATH,
) -> dict[str, Any]:
    """Documented fallback when the LLM judge is unavailable (missing/unreachable
    key). Writes the N generated cards to ``review_path`` (JSONL) for HUMAN
    review, and an aggregate artifact marking the subjective cutoffs PENDING.

    We NEVER fabricate useful / bad-teaching numbers. The wrong-answer count is
    still 0 by construction (every emit passed the real SymPy verifier), and the
    generated cards are AI-generated (not holdout), so dumping them for review
    is fine.
    """
    review_path = Path(review_path)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    with review_path.open("w", encoding="utf-8") as handle:
        for problem in emits:
            handle.write(json.dumps(problem, ensure_ascii=False) + "\n")

    report = {
        "spec": "§7f AI-card 3-count (AI checking & safety) — PENDING (human review)",
        "source": source,
        "topic": topic,
        "judge_model": None,
        "n_generated": n_generated,
        "n_abstained": n_abstained,
        "n_judged": 0,
        "kept": 0,
        "blocked": 0,
        "counts": {"correct_useful": 0, "wrong": 0, "bad_teaching": 0,
                   "correct_not_useful": 0},
        "rates": {"correct_useful": None, "wrong": 0.0, "bad_teaching": None},
        "cutoffs": {
            "correct_useful": {"cutoff": CUTOFF_USEFUL, "direction": ">=",
                               "value": None, "pass": None, "status": "PENDING (LLM judge/human review)"},
            "wrong": {"cutoff": CUTOFF_WRONG, "direction": "<=",
                      "value": 0.0, "pass": True,
                      "status": "0 by construction (SymPy verify gates every emit)"},
            "bad_teaching": {"cutoff": CUTOFF_BAD_TEACHING, "direction": "<=",
                             "value": None, "pass": None, "status": "PENDING (LLM judge/human review)"},
        },
        "passed": None,
        "review_cards_path": str(review_path),
        "note": (
            "LLM judge unavailable (no/unreachable OPENAI_API_KEY). Subjective "
            "cutoffs (useful / bad-teaching) are PENDING human review of the "
            f"{len(emits)} cards emitted to {review_path}. Wrong-answer rate is "
            "0 by construction: every emitted card passed the real SymPy "
            "verify() gate."
        ),
    }
    if os.environ.get("SPEEDRUN_EVAL_EMIT") == "1":
        artifact_path = Path(artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report


# ---------------------------------------------------------------------------
# LIVE run (explicit, key-gated) — python -m eval.ai_quality_eval
# ---------------------------------------------------------------------------


def _format_report(report: dict[str, Any]) -> str:
    lines = [
        "§7f AI-card 3-count — AI checking & safety",
        "=" * 64,
        f"source : {report['source']}",
        f"topic  : {report['topic']}",
        f"judge  : {report['judge_model']}",
        f"N      : generated={report['n_generated']} "
        f"abstained={report['n_abstained']} judged={report['n_judged']} "
        f"kept={report['kept']} blocked={report['blocked']}",
        "",
    ]
    c = report["counts"]
    r = report["rates"]
    cut = report["cutoffs"]

    def _line(label: str, bucket: str) -> str:
        val = r.get(bucket)
        cinfo = cut[bucket]
        val_s = "PENDING" if val is None else f"{val * 100:5.1f}%"
        p = cinfo.get("pass")
        verdict = "PENDING" if p is None else ("PASS" if p else "FAIL")
        extra = f"  [{cinfo['status']}]" if cinfo.get("status") else ""
        return (
            f"  {label:<24} {c[bucket]:>3}/{report['n_judged']:<3} = {val_s}  "
            f"({cinfo['direction']} {cinfo['cutoff'] * 100:.0f}%)  -> {verdict}{extra}"
        )

    lines.append(_line("correct-&-useful", "correct_useful"))
    lines.append(_line("wrong", "wrong"))
    lines.append(_line("correct-but-bad-teach", "bad_teaching"))
    lines.append("")
    overall = report["passed"]
    lines.append(
        f"OVERALL: {'PASS' if overall else ('PENDING' if overall is None else 'FAIL')}"
    )
    if report.get("note"):
        lines.append("")
        lines.append(report["note"])
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:  # pragma: no cover - live path
    """LIVE, key-gated run. Reports the 3-count vs cutoffs from ONE source.

    Enabled only when ``SPEEDRUN_AI_ENABLED`` is truthy AND ``OPENAI_API_KEY`` is
    present (the same kill-switch as the service). If disabled/keyless, does NOT
    fabricate: runs the human-review fallback (emit cards + mark subjective
    cutoffs PENDING) if it can build a generator, else reports the gate.
    """
    import argparse

    parser = argparse.ArgumentParser(description="§7f AI-card 3-count eval")
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--technique", default="")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)

    from config import load_settings

    settings = load_settings()

    # Build the REAL generator (the app's verified/grounded/gold-gated wrapper).
    # Imported lazily so importing this module never pulls in the app / RAG deps.
    def _build_generator() -> Generator:
        import app as app_module

        return app_module.generate_problem

    if not settings.is_enabled():
        print(
            "[§7f] AI service DISABLED (SPEEDRUN_AI_ENABLED/OPENAI_API_KEY not "
            "set). Cannot run the live LLM judge.\n"
            "      Falling back to HUMAN REVIEW: generating cards for manual "
            "review; subjective cutoffs reported PENDING (never fabricated).",
            flush=True,
        )
        # Can we at least generate cards for review? Only if enabled enough to
        # construct the generator; if not, we truly cannot generate.
        # generate_problem itself requires a key, so with no key we cannot
        # generate either — report the gate honestly.
        report = write_human_review_fallback(
            [], source=args.source, topic=args.topic,
            n_generated=0, n_abstained=0,
        )
        report["note"] = (
            "AI service disabled: no key, so no cards could be generated and no "
            "judge could run. Enable the service (SPEEDRUN_AI_ENABLED=1 + "
            "OPENAI_API_KEY) to run the live 3-count, or supply pre-generated "
            "cards for human review."
        )
        print(_format_report(report), flush=True)
        return 2

    generate = _build_generator()

    # Try to build the real judge; if it fails (unreachable), fall back to human
    # review over the cards we DID generate — never fabricate the verdicts.
    try:
        judge = OpenAIJudgeClient(api_key=settings.api_key, model=settings.model)
        report = run_ai_quality_eval(
            args.topic, args.technique, n=args.n, source=args.source,
            generate=generate, judge_client=judge, judge_model=settings.model,
        )
        print(_format_report(report), flush=True)
        return 0 if report["passed"] else 1
    except Exception as exc:  # judge unreachable / errored mid-run
        print(f"[§7f] LLM judge unavailable/errored ({exc}). "
              "Falling back to human review of generated cards.", flush=True)
        emits, n_gen, n_abs = _generate_cards_only(
            generate, args.topic, args.technique, args.n
        )
        report = write_human_review_fallback(
            emits, source=args.source, topic=args.topic,
            n_generated=n_gen, n_abstained=n_abs,
        )
        print(_format_report(report), flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
