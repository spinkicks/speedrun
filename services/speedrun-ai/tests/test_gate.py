# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the §7f gold-set gate harness (``eval/gate.py``).

Hermetic: the Recall@10 eval reads the held-out gold set FROM DISK at runtime
(that is the harness's job) and emits AGGREGATE numbers only — no raw gold
pairs are ever asserted on or printed. The wrong-answer-by-construction test
drives the REAL SymPy verifier. No network, no OpenAI.
"""

from __future__ import annotations

import pytest

from eval.gate import (
    corpus_coverage,
    make_gold_gate,
    recall_at_10_report,
    wrong_answer_batch_result,
)

# ---------------------------------------------------------------------------
# 1. Recall@10 retrieval eval (reads the gold set at runtime)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def report():
    """Compute the Recall@10 report once (loads the gold set + builds index)."""
    return recall_at_10_report()


def test_report_has_all_three_methods(report):
    for method in ("bm25", "dense", "hybrid"):
        assert method in report["recall_at_10"]
        assert 0.0 <= report["recall_at_10"][method] <= 1.0


def test_report_counts_are_aggregate_only(report):
    # The report must expose counts/fractions, NOT raw gold items.
    assert isinstance(report["num_gold"], int)
    assert report["num_gold"] > 0
    assert "coverage" in report
    assert 0.0 <= report["coverage"] <= 1.0
    # No key should carry raw question/answer text.
    forbidden = {"question", "correct_answer", "worked_solution", "choices"}
    assert forbidden.isdisjoint(set(report.keys()))


def test_hybrid_at_least_matches_baselines(report):
    # The ONLY hard assertion on retrieval: hybrid must not regress below
    # either single arm. The >=5pt margin is reported, not hard-asserted.
    r = report["recall_at_10"]
    assert r["hybrid"] >= r["bm25"]
    assert r["hybrid"] >= r["dense"]


def test_coverage_matches_helper(report):
    # corpus_coverage() and the report agree (both aggregate).
    assert corpus_coverage() == pytest.approx(report["coverage"])


def test_family_diagnostic_present_and_hybrid_not_worse(report):
    # The looser textbook-family diagnostic is present and aggregate-only.
    fam = report["family"]
    fr = fam["recall_at_10"]
    for method in ("bm25", "dense", "hybrid"):
        assert 0.0 <= fr[method] <= 1.0
    assert 0.0 <= fam["coverage"] <= 1.0
    # hybrid must not regress below either baseline on the family metric either
    assert fr["hybrid"] >= fr["bm25"]
    assert fr["hybrid"] >= fr["dense"]
    # family coverage should be >= strict coverage (looser match)
    assert fam["coverage"] >= report["coverage"]


# ---------------------------------------------------------------------------
# 3. Wrong-answer rate = 0 by construction (verify() gates every emit)
# ---------------------------------------------------------------------------


def test_wrong_answers_all_rejected_by_verify():
    """A batch of (correct + deliberately-wrong) specs through verify():
    every wrong one must be rejected → post-gate wrong-answer rate = 0."""
    result = wrong_answer_batch_result()
    # sanity: the batch actually contains both kinds
    assert result["num_correct"] > 0
    assert result["num_wrong"] > 0
    # every correct spec verified
    assert result["correct_passed"] == result["num_correct"]
    # NOT ONE wrong spec survived verification
    assert result["wrong_survived"] == 0
    assert result["wrong_answer_rate"] == 0.0


# ---------------------------------------------------------------------------
# 4. Real gold-gate factory (leakage-free check) wired for the graph
# ---------------------------------------------------------------------------


def test_make_gold_gate_rejects_leaking_candidate():
    study = [
        "The derivative of x squared is two x by the power rule for polynomials."
    ]
    gate = make_gold_gate(study)
    leaking = {
        "stem": "Recall the derivative of x squared is two x by the power "
        "rule for polynomials as shown.",
        "correct": "2*x",
        "worked_solution": "",
    }
    assert gate(leaking) is False


def test_make_gold_gate_accepts_clean_candidate():
    study = [
        "The derivative of x squared is two x by the power rule for polynomials."
    ]
    gate = make_gold_gate(study)
    clean = {
        "stem": "A train leaves Boston at noon travelling west at sixty miles "
        "per hour toward a distant unrelated city.",
        "correct": "5",
        "worked_solution": "Distance equals rate times time.",
    }
    assert gate(clean) is True


def test_gold_gate_checks_worked_solution_too():
    study = [
        "A square matrix is invertible if and only if its determinant is nonzero."
    ]
    gate = make_gold_gate(study)
    candidate = {
        "stem": "Is this matrix invertible?",
        "correct": "yes",
        # leak hidden in the worked solution, not the stem
        "worked_solution": "A square matrix is invertible if and only if its "
        "determinant is nonzero, so we check the determinant.",
    }
    assert gate(candidate) is False


# ---------------------------------------------------------------------------
# 4b. BUG 3 (SAFETY): empty study corpus must FAIL CLOSED
# ---------------------------------------------------------------------------


def test_gold_gate_empty_corpus_fails_closed():
    """If the study corpus is empty/missing, the leakage check cannot run. The
    gate must then REFUSE (return False) — never silently disable the leakage
    guard and pass everything (fail-open)."""
    gate = make_gold_gate([])  # empty study corpus
    candidate = {
        "stem": "Compute the derivative of x**3.",
        "correct": "3*x**2",
        "worked_solution": "power rule",
    }
    assert gate(candidate) is False, (
        "an empty study corpus must fail CLOSED (leakage check cannot run)"
    )


def test_gold_gate_corpus_of_blanks_fails_closed():
    """A corpus that is only blank/whitespace strings is effectively empty and
    must also fail closed."""
    gate = make_gold_gate(["", "   ", "\n"])
    candidate = {"stem": "Compute the limit of sin(x)/x.", "correct": "1"}
    assert gate(candidate) is False


# ---------------------------------------------------------------------------
# 4c. BUG 4a (SAFETY): the leak scan must include the choices/distractor text
# ---------------------------------------------------------------------------


def test_gold_gate_scans_choices_for_leaks():
    """A leak hidden ONLY in the answer choices (not the stem/solution/correct)
    must still be caught. Previously the leak scan omitted the choices text."""
    study = [
        "A square matrix is invertible if and only if its determinant is nonzero."
    ]
    gate = make_gold_gate(study)
    candidate = {
        "stem": "Pick the true statement about this 3x3 matrix.",
        "correct": "42",
        "worked_solution": "See options.",
        # the leak is buried in a distractor / choice, not the other fields
        "choices": [
            "42",
            "A square matrix is invertible if and only if its determinant "
            "is nonzero, hence it is singular.",
        ],
    }
    assert gate(candidate) is False, (
        "a leak present only in the answer choices must still fail the gate"
    )


# ---------------------------------------------------------------------------
# 5. LLM-judge scaffold: never calls the network in tests
# ---------------------------------------------------------------------------


def test_llm_judge_uses_injected_client_only():
    from eval.gate import llm_judge

    class _FakeClient:
        """Records the call and returns a canned JSON verdict."""

        def __init__(self):
            self.called = False

        def score(self, problem):  # pragma: no cover - trivial
            self.called = True
            return {"useful": True, "bad_teaching": False}

    client = _FakeClient()
    problem = {"stem": "x?", "correct": "1", "worked_solution": "because"}
    verdict = llm_judge(problem, client=client)
    assert client.called is True
    assert set(verdict.keys()) >= {"useful", "bad_teaching"}


def test_llm_judge_requires_a_client():
    from eval.gate import llm_judge

    with pytest.raises((ValueError, TypeError)):
        llm_judge({"stem": "x?"}, client=None)


# ---------------------------------------------------------------------------
# 6. Kill-switch (structural): AI service is OFF by default
# ---------------------------------------------------------------------------


def test_ai_service_off_by_default(monkeypatch):
    # No flag, no key → disabled. (Mirrors the 4.2 /generate→503 behavior.)
    monkeypatch.delenv("SPEEDRUN_AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from config import load_settings

    assert load_settings().is_enabled() is False


def test_generate_returns_503_when_disabled(monkeypatch):
    monkeypatch.delenv("SPEEDRUN_AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from fastapi.testclient import TestClient

    import app as app_module

    client = TestClient(app_module.app)
    resp = client.post("/generate", json={"topic": "calc", "technique": "x"})
    assert resp.status_code == 503
