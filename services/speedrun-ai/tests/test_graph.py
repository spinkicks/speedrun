# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the LangGraph verify/retry/abstain pipeline.

All LLM/retriever/gate collaborators are STUBBED here — no network, no OpenAI.
The verify node uses the REAL SymPy verifier from ``verify/sympy_verifier.py``.
"""

from __future__ import annotations

import pytest

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


def test_verified_answer_diverges_from_emitted_correct_abstains():
    """BUG 1 (verify/emit divergence): the verifier validates
    ``spec.claimed_answer`` but the emit path builds the shipped ``correct``
    from ``candidate.correct``. If the two disagree, the SHIPPED answer was
    never the one that passed verification — a wrong answer could ship even
    though "verify passed". The pipeline MUST abstain on that divergence.
    """

    def _divergent_proposal():
        return {
            "candidate": {
                "stem": "Find the derivative of f(x) = x**2.",
                # candidate.correct is WRONG (3*x) ...
                "correct": "3*x",
                "choices": ["3*x"],
                "worked_solution": "(candidate ships a different answer)",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                # ... but the verifier only ever sees the CORRECT claimed_answer.
                "claimed_answer": "2*x",
            },
        }

    llm = _counting_llm([_divergent_proposal])
    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, max_retries=0
    )

    # verify() passes (2*x is the true derivative), but the emitted correct
    # answer (3*x) was NOT the verified one → must NOT emit.
    assert state["status"] == "abstain", (
        "a candidate whose emitted correct answer diverges from the verified "
        "claimed_answer must abstain, not ship the unverified answer"
    )
    assert state["problem"] is None


def test_verified_answer_matches_emitted_correct_still_emits():
    """Guard against over-tightening BUG 1's fix: when candidate.correct and
    the verified claimed_answer agree (modulo formatting), the happy path must
    still emit."""

    def _agreeing_proposal():
        return {
            "candidate": {
                "stem": "Find the derivative of f(x) = x**2.",
                # equal to claimed_answer up to whitespace/formatting only
                "correct": "2 * x",
                "choices": ["2 * x"],
                "worked_solution": "power rule",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    llm = _counting_llm([_agreeing_proposal])
    state = run_generation(
        "calculus", "power_rule", llm_propose=llm, max_retries=0
    )
    assert state["status"] == "emit"
    assert state["problem"] is not None


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


# ---------------------------------------------------------------------------
# BUG 4 (SAFETY): the gold_gate node must scan the DISTRACTORS / assembled
# choices, not just the raw proposed candidate. Distractors live in a separate
# state key (produced by the distractors node) and choices are assembled only in
# emit_node — both AFTER the gate. If the gate only ever sees the raw candidate,
# a leak buried solely in a distractor is never scanned and ships. Using the
# REAL leakage gate, a clean stem/solution/correct with a leaking distractor
# must FAIL the gate → abstain.
# ---------------------------------------------------------------------------


def test_gold_gate_scans_distractors_for_leaks():
    from eval.gate import make_gold_gate

    # A study passage; the leak is a verbatim >=13-word run copied into a
    # distractor below. (Authored here — no gold-set content.)
    study = [
        "A square matrix is invertible if and only if its determinant is "
        "nonzero and its columns are linearly independent vectors."
    ]

    def _clean_llm(topic, technique):
        return {
            "candidate": {
                # stem / solution / correct are all CLEAN (no leak)
                "stem": "Find the derivative of f(x) = x**2.",
                "correct": "2*x",
                "worked_solution": "By the power rule, d/dx(x^2) = 2x.",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    def _leaking_distractors(candidate):
        # The leak is buried ONLY in a distractor (a verbatim >=13-gram run
        # from the study passage), not in the stem/solution/correct.
        return [
            "A square matrix is invertible if and only if its determinant is "
            "nonzero and its columns are linearly independent vectors.",
            "1*x",
        ]

    gate = make_gold_gate(study)
    state = run_generation(
        "calculus",
        "power_rule",
        llm_propose=_clean_llm,
        make_distractors=_leaking_distractors,
        gate=gate,
    )

    assert state["status"] == "abstain", (
        "a leak present only in a distractor must be scanned by the gold_gate "
        "and abstain, not ship"
    )
    assert "gate" in state["abstain_reason"].lower()
    assert state["problem"] is None


def test_gold_gate_still_emits_when_distractors_are_clean():
    """Guard against over-tightening BUG 4's fix: when the candidate AND the
    distractors are all leak-free, the real gate must still let the problem
    emit."""
    from eval.gate import make_gold_gate

    study = [
        "A square matrix is invertible if and only if its determinant is "
        "nonzero and its columns are linearly independent vectors."
    ]

    def _clean_llm(topic, technique):
        return {
            "candidate": {
                "stem": "Find the derivative of f(x) = x**2.",
                "correct": "2*x",
                "worked_solution": "By the power rule, d/dx(x^2) = 2x.",
            },
            "spec": {
                "answer_type": "derivative",
                "expression": "x**2",
                "variable": "x",
                "claimed_answer": "2*x",
            },
        }

    def _clean_distractors(candidate):
        return ["3*x", "x/2", "1"]

    gate = make_gold_gate(study)
    state = run_generation(
        "calculus",
        "power_rule",
        llm_propose=_clean_llm,
        make_distractors=_clean_distractors,
        gate=gate,
    )
    assert state["status"] == "emit"
    assert state["problem"] is not None
    # the clean distractors made it into the emitted choices
    assert "3*x" in state["problem"]["choices"]


# ---------------------------------------------------------------------------
# AI bug #3 (SAFETY): FAIL-CLOSED syllabus scoping.
#
# The corpus covers exactly nine leaf topics. A GENUINE math question on an
# UNCOVERED topic (ODEs, arc length, partial-fraction integration, PCA) grounds
# to a near-neighbour-but-unsupporting passage → a misleading citation the
# semantic cosine gate cannot separate. Fail-closed scoping fixes it in normal
# operation: when ``covered_topics`` is supplied, the graph refuses to even
# PROPOSE for a topic the corpus does not cover — it abstains up front.
#
# ``covered_topics`` is OPT-IN (default None = current behaviour) so every
# existing test above stays green.
# ---------------------------------------------------------------------------

# The nine covered leaf topic_ids (as the corpus reports them).
_COVERED = {
    "calc::limits",
    "calc::single_var::differentiation",
    "calc::single_var::integration",
    "calc::sequences_series",
    "calc::multivar",
    "linear_algebra::vector_spaces",
    "linear_algebra::matrices",
    "linear_algebra::eigen",
    "linear_algebra::linear_maps",
}


def _tracking_llm():
    """A proposer that records whether it was ever called. Used to prove the
    scoping guard fires BEFORE proposing on an uncovered topic."""
    calls = {"n": 0}

    def _llm(topic, technique):
        calls["n"] += 1
        return _correct_derivative_proposal()

    _llm.calls = calls
    return _llm


def test_scoping_guard_default_none_is_current_behavior():
    # Opt-in: with covered_topics unset, an arbitrary free-text topic still
    # reaches the normal path and emits (no guard, backward compatible).
    llm = _counting_llm([_correct_derivative_proposal])
    state = run_generation("anything at all", "power_rule", llm_propose=llm)
    assert state["status"] == "emit"


@pytest.mark.parametrize(
    "topic",
    [
        "calc::limits",  # exact topic_id
        "calculus limits",
        "eigenvalues",
        "row reduce the matrix",
    ],
)
def test_covered_topic_reaches_normal_path(topic):
    # A covered topic must NOT be abstained by the scoping guard: the proposer
    # is reached and the problem emits normally.
    llm = _tracking_llm()
    state = run_generation(
        topic, "power_rule", llm_propose=llm, covered_topics=_COVERED
    )
    assert llm.calls["n"] >= 1, "covered topic must reach the proposer"
    assert state["status"] == "emit"
    assert (state.get("abstain_reason") or "") == ""


@pytest.mark.parametrize(
    "topic",
    [
        "solve the differential equation dy/dx=y",
        "compute the arc length of the curve",
        "integrate the rational function by partial fractions",
        "principal component analysis",
    ],
)
def test_uncovered_topic_abstains_before_proposing(topic):
    # A genuine question on an UNCOVERED topic must abstain with the
    # topic-not-covered reason, and the guard must fire BEFORE the proposer runs
    # (no propose, no mis-citation).
    llm = _tracking_llm()
    state = run_generation(
        topic, "power_rule", llm_propose=llm, covered_topics=_COVERED
    )
    assert state["status"] == "abstain"
    assert state["problem"] is None
    assert "topic" in state["abstain_reason"].lower()
    assert "corpus" in state["abstain_reason"].lower()
    assert llm.calls["n"] == 0, (
        "the scoping guard must abstain BEFORE proposing on an uncovered topic"
    )


# ---------------------------------------------------------------------------
# BUG P1-C: option order must VARY per problem (correct not always index 0).
# ``_assemble_choices`` used to build ``[correct, *distractors]`` unconditionally,
# so the correct answer was ALWAYS choices[0] → always letter 'A' → trivially
# gameable. It must now shuffle DETERMINISTICALLY per problem (stable seed) while
# keeping the correct value present exactly once.
# ---------------------------------------------------------------------------


def test_assemble_choices_keeps_correct_exactly_once():
    from graph import _assemble_choices

    choices = _assemble_choices("1", ["2", "3", "4"], seed="some stem")
    assert sorted(choices) == sorted(["1", "2", "3", "4"])
    assert choices.count("1") == 1


def test_assemble_choices_is_deterministic_for_same_seed():
    """Same (correct, distractors, seed) → identical order every time (stable
    tests, reproducible generation — no nondeterminism)."""
    from graph import _assemble_choices

    a = _assemble_choices("1", ["2", "3", "4", "5"], seed="stable-key")
    b = _assemble_choices("1", ["2", "3", "4", "5"], seed="stable-key")
    assert a == b


def test_assemble_choices_position_varies_across_problems():
    """Across problems with distinct correct values / seeds the correct answer's
    index is NOT constant 0 — i.e. the option order actually varies."""
    from graph import _assemble_choices

    positions = set()
    for i in range(20):
        correct = str(i)
        distractors = [str(i + 100 + d) for d in range(4)]
        choices = _assemble_choices(correct, distractors, seed=f"stem-{i}")
        assert choices.count(correct) == 1
        positions.add(choices.index(correct))
    assert positions != {0}, (
        "correct answer is always index 0 — options are not being shuffled"
    )
    assert len(positions) > 1, "correct-answer position never varies across problems"
