# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the §7f AI-card 3-count quality harness (``eval/ai_quality_eval.py``).

The §7f "AI checking & safety" deliverable is a 3-count over N generated cards
from ONE covered source, with pre-registered cutoffs:

  * correct-&-useful       >= 80 %
  * wrong                  <= 2 %   (target 0; wrong = 0 by construction since
                                     verify() gates every emit)
  * correct-but-bad-teaching <= 15 %

Hermetic: this drives the harness with a FAKE generator (returns canned graph
results — no OpenAI, no RAG index, no network) and a FAKE judge client (a
deterministic ``score(problem) -> {"correct", "useful", "bad_teaching"}``),
mirroring ``tests/test_gate.py``'s injected-fake-client pattern. NO network.
The LIVE run is a SEPARATE, explicit, key-gated step (not exercised here).
"""

from __future__ import annotations

import json

import pytest

from eval.ai_quality_eval import (
    CUTOFF_BAD_TEACHING,
    CUTOFF_USEFUL,
    CUTOFF_WRONG,
    classify,
    run_ai_quality_eval,
)

# ---------------------------------------------------------------------------
# Fake collaborators (deterministic, offline)
# ---------------------------------------------------------------------------


def _emit(correct: str = "2*x") -> dict:
    """A graph EMIT result (the shape run_generation returns for a verified,
    grounded, gold-gated problem)."""
    return {
        "status": "emit",
        "problem": {
            "stem": "Differentiate x**2 with respect to x.",
            "correct": correct,
            "choices": [correct, "x", "x**2"],
            "distractors": ["x", "x**2"],
            "worked_solution": "Apply the power rule.",
            "citation": "OpenStax Calculus Vol. 1, 3.3 (CC BY 4.0)",
            "topic": "calc::single_var::differentiation",
            "technique": "",
        },
        "abstain_reason": None,
    }


def _abstain(reason: str = "no source grounding") -> dict:
    return {"status": "abstain", "problem": None, "abstain_reason": reason}


class _FakeJudge:
    """Deterministic judge: verdict chosen by an explicit per-call script.

    ``verdicts`` is a list of dicts consumed in order; each is returned verbatim
    (with defaults filled) as the ``score(problem)`` result. No network.
    """

    def __init__(self, verdicts: list[dict]):
        self._verdicts = list(verdicts)
        self.calls = 0

    def score(self, problem: dict) -> dict:
        self.calls += 1
        verdict = dict(self._verdicts.pop(0))
        verdict.setdefault("correct", True)
        verdict.setdefault("useful", True)
        verdict.setdefault("bad_teaching", False)
        return verdict


def _fake_generator(results: list[dict]):
    """Return a ``generate(topic, technique) -> result`` consuming ``results``
    in order (one per attempt)."""
    seq = list(results)

    def generate(topic: str, technique: str) -> dict:
        return seq.pop(0)

    return generate


SOURCE = "OpenStax Calculus Vol. 1, 3.3 (CC BY 4.0)"
TOPIC = "calc::single_var::differentiation"


# ---------------------------------------------------------------------------
# 1. classify(): the 3-bucket rule
# ---------------------------------------------------------------------------


def test_classify_correct_and_useful():
    assert classify({"correct": True, "useful": True, "bad_teaching": False}) == (
        "correct_useful"
    )


def test_classify_wrong_takes_priority():
    # A wrong verdict is "wrong" regardless of useful/bad_teaching.
    assert (
        classify({"correct": False, "useful": True, "bad_teaching": False})
        == "wrong"
    )
    assert (
        classify({"correct": False, "useful": False, "bad_teaching": True})
        == "wrong"
    )


def test_classify_correct_but_bad_teaching():
    assert (
        classify({"correct": True, "useful": True, "bad_teaching": True})
        == "bad_teaching"
    )


def test_classify_correct_not_useful_is_not_correct_useful():
    # correct but not useful (and not bad-teaching) must NOT count as
    # correct-&-useful — it fails the useful bar and is blocked.
    bucket = classify({"correct": True, "useful": False, "bad_teaching": False})
    assert bucket != "correct_useful"


# ---------------------------------------------------------------------------
# 2. run_ai_quality_eval(): the 3-count math + cutoff logic
# ---------------------------------------------------------------------------


def test_all_correct_and_useful_passes_all_cutoffs():
    n = 10
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge([{"correct": True, "useful": True, "bad_teaching": False}] * n)

    result = run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge, judge_model="fake"
    )

    assert result["n_generated"] == n
    assert result["counts"]["correct_useful"] == n
    assert result["counts"]["wrong"] == 0
    assert result["counts"]["bad_teaching"] == 0
    assert result["rates"]["correct_useful"] == pytest.approx(1.0)
    assert result["rates"]["wrong"] == pytest.approx(0.0)
    assert result["rates"]["bad_teaching"] == pytest.approx(0.0)
    # every cutoff met
    assert result["cutoffs"]["correct_useful"]["pass"] is True
    assert result["cutoffs"]["wrong"]["pass"] is True
    assert result["cutoffs"]["bad_teaching"]["pass"] is True
    assert result["passed"] is True
    # blocked = wrong + bad_teaching; kept = correct_useful
    assert result["kept"] == n
    assert result["blocked"] == 0
    assert result["source"] == SOURCE
    assert result["judge_model"] == "fake"


def test_three_count_math_mixed_buckets():
    # 10 emits: 8 correct-&-useful, 2 bad-teaching, 0 wrong.
    verdicts = (
        [{"correct": True, "useful": True, "bad_teaching": False}] * 8
        + [{"correct": True, "useful": True, "bad_teaching": True}] * 2
    )
    n = 10
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge(verdicts)

    result = run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge
    )

    assert result["counts"]["correct_useful"] == 8
    assert result["counts"]["bad_teaching"] == 2
    assert result["counts"]["wrong"] == 0
    assert result["rates"]["correct_useful"] == pytest.approx(0.8)
    assert result["rates"]["bad_teaching"] == pytest.approx(0.2)
    # correct-&-useful 0.80 >= 0.80 cutoff -> pass; bad-teaching 0.20 > 0.15 -> FAIL
    assert result["cutoffs"]["correct_useful"]["pass"] is True
    assert result["cutoffs"]["bad_teaching"]["pass"] is False
    assert result["passed"] is False
    # blocked = the 2 bad-teaching cards; kept = 8 correct-&-useful
    assert result["kept"] == 8
    assert result["blocked"] == 2


def test_useful_cutoff_fails_when_below_80():
    # 10 emits: 7 correct-&-useful, 3 correct-but-not-useful -> useful rate 0.7 < 0.8
    verdicts = (
        [{"correct": True, "useful": True, "bad_teaching": False}] * 7
        + [{"correct": True, "useful": False, "bad_teaching": False}] * 3
    )
    n = 10
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge(verdicts)

    result = run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge
    )
    assert result["rates"]["correct_useful"] == pytest.approx(0.7)
    assert result["cutoffs"]["correct_useful"]["pass"] is False
    assert result["passed"] is False


# ---------------------------------------------------------------------------
# 3. Wrong cards are ALWAYS blocked (never kept), and drive the wrong cutoff
# ---------------------------------------------------------------------------


def test_wrong_cards_are_always_blocked():
    # A judge flags one card wrong. Even though wrong should be 0 by
    # construction (verify gates every emit), the harness must BLOCK it and
    # never count it as kept.
    verdicts = (
        [{"correct": True, "useful": True, "bad_teaching": False}] * 9
        + [{"correct": False, "useful": True, "bad_teaching": False}]
    )
    n = 10
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge(verdicts)

    result = run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge
    )
    assert result["counts"]["wrong"] == 1
    assert result["rates"]["wrong"] == pytest.approx(0.1)
    # 1/10 = 10% > 2% cutoff -> wrong cutoff FAILS
    assert result["cutoffs"]["wrong"]["pass"] is False
    assert result["passed"] is False
    # the wrong card is blocked, never kept
    assert result["blocked"] >= 1
    assert result["kept"] == 9
    # kept + blocked == number of judged (emitted) cards
    assert result["kept"] + result["blocked"] == result["n_judged"]


# ---------------------------------------------------------------------------
# 4. Only VERIFIED emits are judged; abstains are dropped before judging
# ---------------------------------------------------------------------------


def test_abstains_dropped_before_judging():
    # 6 attempts: 4 emit, 2 abstain. Only the 4 emits reach the judge.
    results = [_emit(), _abstain(), _emit(), _emit(), _abstain(), _emit()]
    gen = _fake_generator(results)
    judge = _FakeJudge(
        [{"correct": True, "useful": True, "bad_teaching": False}] * 4
    )

    result = run_ai_quality_eval(
        TOPIC, "", n=6, source=SOURCE, generate=gen, judge_client=judge
    )
    assert result["n_generated"] == 6  # attempts made
    assert result["n_judged"] == 4  # only the verified emits
    assert result["n_abstained"] == 2
    assert judge.calls == 4  # judge only saw the 4 emits
    assert result["counts"]["correct_useful"] == 4


# ---------------------------------------------------------------------------
# 5. JSON artifact emission is gated behind SPEEDRUN_EVAL_EMIT=1
# ---------------------------------------------------------------------------


def test_no_artifact_emitted_without_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("SPEEDRUN_EVAL_EMIT", raising=False)
    out = tmp_path / "ai-quality.json"
    n = 3
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge(
        [{"correct": True, "useful": True, "bad_teaching": False}] * n
    )
    run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge,
        artifact_path=out,
    )
    assert not out.exists(), "artifact must NOT be written without SPEEDRUN_EVAL_EMIT=1"


def test_artifact_emitted_with_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEEDRUN_EVAL_EMIT", "1")
    out = tmp_path / "ai-quality.json"
    n = 5
    gen = _fake_generator([_emit() for _ in range(n)])
    judge = _FakeJudge(
        [{"correct": True, "useful": True, "bad_teaching": False}] * n
    )
    result = run_ai_quality_eval(
        TOPIC, "", n=n, source=SOURCE, generate=gen, judge_client=judge,
        judge_model="fake-judge", artifact_path=out,
    )
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    # aggregate 3-count + rates + N + source + judge model — no raw card text
    assert payload["source"] == SOURCE
    assert payload["judge_model"] == "fake-judge"
    assert payload["n_judged"] == n
    assert payload["counts"]["correct_useful"] == n
    assert set(payload["rates"]) == {"correct_useful", "wrong", "bad_teaching"}
    # the artifact must not carry raw generated-card text (aggregate only)
    forbidden = {"problems", "cards", "stem", "worked_solution", "choices"}
    assert forbidden.isdisjoint(set(payload.keys()))
    assert payload == result  # what is returned is what is written


# ---------------------------------------------------------------------------
# 6. Cutoff constants are the pre-registered §7f values
# ---------------------------------------------------------------------------


def test_cutoff_constants_match_preregistration():
    assert CUTOFF_USEFUL == pytest.approx(0.80)
    assert CUTOFF_WRONG == pytest.approx(0.02)
    assert CUTOFF_BAD_TEACHING == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 7. Zero judged cards -> a clean, non-crashing failure (nothing to certify)
# ---------------------------------------------------------------------------


def test_all_abstain_yields_zero_judged_and_does_not_pass():
    results = [_abstain() for _ in range(4)]
    gen = _fake_generator(results)
    judge = _FakeJudge([])  # never called
    result = run_ai_quality_eval(
        TOPIC, "", n=4, source=SOURCE, generate=gen, judge_client=judge
    )
    assert result["n_judged"] == 0
    assert result["kept"] == 0
    assert result["blocked"] == 0
    # with nothing judged there is nothing to certify -> not a pass
    assert result["passed"] is False
