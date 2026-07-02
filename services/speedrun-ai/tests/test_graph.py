# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the LangGraph verify/retry/abstain pipeline.

All LLM/retriever/gate collaborators are STUBBED here — no network, no OpenAI.
The verify node uses the REAL SymPy verifier from ``verify/sympy_verifier.py``.
"""

from __future__ import annotations

from graph import run_generation

# ---------------------------------------------------------------------------
# Stub problem builders
# ---------------------------------------------------------------------------


def _correct_derivative_proposal() -> dict:
    """A CORRECT problem: d/dx(x**2) = 2*x. Passes the real SymPy verifier."""
    return {
        "candidate": {
            "stem": "Find the derivative of f(x) = x**2.",
            "correct": "2*x",
            "choices": ["2*x"],
            "worked_solution": "By the power rule, d/dx(x^2) = 2x.",
        },
        "spec": {
            "answer_type": "derivative",
            "expression": "x**2",
            "variable": "x",
            "claimed_answer": "2*x",
        },
    }


def _wrong_derivative_proposal() -> dict:
    """A WRONG problem: claims d/dx(x**2) = 3*x. Fails the real SymPy verifier."""
    return {
        "candidate": {
            "stem": "Find the derivative of f(x) = x**2.",
            "correct": "3*x",
            "choices": ["3*x"],
            "worked_solution": "(intentionally wrong)",
        },
        "spec": {
            "answer_type": "derivative",
            "expression": "x**2",
            "variable": "x",
            "claimed_answer": "3*x",
        },
    }


def _counting_llm(sequence):
    """Return an llm_propose stub that yields proposals from ``sequence`` in
    order (repeating the last one once exhausted) and records call count."""
    calls = {"n": 0}

    def _llm(topic, technique):
        idx = min(calls["n"], len(sequence) - 1)
        calls["n"] += 1
        return sequence[idx]()

    _llm.calls = calls
    return _llm


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_emits_packaged_problem():
    llm = _counting_llm([_correct_derivative_proposal])
    state = run_generation("calculus", "power_rule", llm_propose=llm)

    assert state["status"] == "emit"
    assert state["abstain_reason"] in (None, "")
    # verification passed
    assert state["verification"]["passed"] is True
    # citation present (default stub returns a placeholder)
    assert state["citation"]
    # distractors present
    assert state["distractors"]
    # gate passed
    assert state["gate_result"] is True
    # a packaged problem dict is present and carries the essentials
    problem = state["problem"]
    assert problem is not None
    assert problem["stem"]
    assert problem["correct"] == "2*x"
    assert problem["citation"]
    assert problem["choices"]
    # exactly one LLM call on the happy path
    assert llm.calls["n"] == 1


def test_emit_distractors_present_and_no_dup_of_correct():
    llm = _counting_llm([_correct_derivative_proposal])
    state = run_generation("calculus", "power_rule", llm_propose=llm)

    assert state["status"] == "emit"
    distractors = state["problem"]["distractors"]
    assert len(distractors) >= 1
    # no distractor duplicates the correct answer
    correct = state["problem"]["correct"]
    assert correct not in distractors
    # choices contain the correct answer + distractors, correct appears once
    choices = state["problem"]["choices"]
    assert correct in choices
    assert choices.count(correct) == 1


# ---------------------------------------------------------------------------
# verify-fail → retry → abstain
# ---------------------------------------------------------------------------


def test_verify_fail_retries_then_abstains():
    # Always wrong; with max_retries=2, that is 1 initial + 2 retries = 3 calls.
    llm = _counting_llm([_wrong_derivative_proposal])
    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, max_retries=2
    )

    assert state["status"] == "abstain"
    assert "verif" in state["abstain_reason"].lower()
    assert state["problem"] is None
    # 1 initial proposal + 2 retries = 3 total proposals
    assert llm.calls["n"] == 3
    assert state["retries"] == 2


# ---------------------------------------------------------------------------
# verify-fail → retry → SUCCESS
# ---------------------------------------------------------------------------


def test_verify_fail_then_success_on_retry():
    # Wrong first, correct second.
    llm = _counting_llm(
        [_wrong_derivative_proposal, _correct_derivative_proposal]
    )
    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, max_retries=2
    )

    assert state["status"] == "emit"
    assert state["verification"]["passed"] is True
    # 1 wrong + 1 correct = 2 proposals, exactly one retry consumed
    assert llm.calls["n"] == 2
    assert state["retries"] == 1


# ---------------------------------------------------------------------------
# ungrounded → abstain
# ---------------------------------------------------------------------------


def test_ungrounded_abstains():
    llm = _counting_llm([_correct_derivative_proposal])

    def _no_citation(candidate):
        return None

    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, retriever=_no_citation
    )

    assert state["status"] == "abstain"
    assert "ground" in state["abstain_reason"].lower()
    assert state["problem"] is None


def test_empty_citation_abstains():
    llm = _counting_llm([_correct_derivative_proposal])

    def _empty_citation(candidate):
        return ""

    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, retriever=_empty_citation
    )

    assert state["status"] == "abstain"
    assert "ground" in state["abstain_reason"].lower()


# ---------------------------------------------------------------------------
# gold-gate fail → abstain
# ---------------------------------------------------------------------------


def test_gold_gate_fail_abstains():
    llm = _counting_llm([_correct_derivative_proposal])

    def _reject_gate(candidate):
        return False

    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, gate=_reject_gate
    )

    assert state["status"] == "abstain"
    assert "gate" in state["abstain_reason"].lower()
    assert state["problem"] is None


# ---------------------------------------------------------------------------
# verify node uses the REAL verifier (sanity: a subtly wrong answer is caught)
# ---------------------------------------------------------------------------


def test_verify_node_uses_real_sympy_verifier():
    # Claimed antiderivative missing a factor — only the real verifier catches it.
    def _wrong_integral():
        return {
            "candidate": {
                "stem": "Integrate 2*x dx.",
                "correct": "x**2 + x",  # wrong: d/dx = 2x + 1, not 2x
                "choices": ["x**2 + x"],
                "worked_solution": "(wrong)",
            },
            "spec": {
                "answer_type": "integral",
                "expression": "2*x",
                "variable": "x",
                "claimed_answer": "x**2 + x",
                "definite": False,
            },
        }

    llm = _counting_llm([_wrong_integral])
    state = run_generation(
        "calculus", "integration", llm_propose=llm, max_retries=0
    )
    assert state["status"] == "abstain"
    assert state["verification"]["passed"] is False
