# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the SymPy verifier (Phase 4, Task 4.1).

These tests are written FIRST (TDD) and must fail before the implementation
exists. They cover the full contract: correct answers PASS, wrong answers FAIL,
coincidence traps FAIL, ill-posed inputs FAIL (never raise).
"""

import pytest

from verify.sympy_verifier import ProblemSpec, verify


# ---------------------------------------------------------------------------
# 1. Derivative — correct
# ---------------------------------------------------------------------------
def test_derivative_correct():
    """d/dx of x**2 = 2*x → PASS."""
    spec = ProblemSpec(
        answer_type="derivative",
        expression="x**2",
        variable="x",
        claimed_answer="2*x",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 2. Derivative — wrong
# ---------------------------------------------------------------------------
def test_derivative_wrong():
    """d/dx of x**2 ≠ 3*x → FAIL."""
    spec = ProblemSpec(
        answer_type="derivative",
        expression="x**2",
        variable="x",
        claimed_answer="3*x",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ---------------------------------------------------------------------------
# 3. Expression equivalence — symbolically non-trivial identity (Pythagorean)
# ---------------------------------------------------------------------------
def test_expression_pythagorean_identity():
    """sin(x)**2 + cos(x)**2 == 1 → PASS (trigsimp needed)."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="sin(x)**2 + cos(x)**2",
        variable="x",
        claimed_answer="1",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 4. Coincidence trap — Abs(x) vs x
# ---------------------------------------------------------------------------
def test_coincidence_abs_vs_x():
    """Abs(x) != x globally (fails at negative x) → FAIL."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="Abs(x)",
        variable="x",
        claimed_answer="x",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL (coincidence trap) but got PASS"


# ---------------------------------------------------------------------------
# 5a. Indefinite integral — correct up to constant
# ---------------------------------------------------------------------------
def test_indefinite_integral_correct():
    """∫2x dx = x**2 + 5 (up to +C) → PASS."""
    spec = ProblemSpec(
        answer_type="integral",
        expression="2*x",
        variable="x",
        claimed_answer="x**2 + 5",
        definite=False,
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 5b. Indefinite integral — wrong antiderivative
# ---------------------------------------------------------------------------
def test_indefinite_integral_wrong():
    """∫2x dx ≠ x**2 + x → FAIL."""
    spec = ProblemSpec(
        answer_type="integral",
        expression="2*x",
        variable="x",
        claimed_answer="x**2 + x",
        definite=False,
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ---------------------------------------------------------------------------
# 6a. Definite integral — correct
# ---------------------------------------------------------------------------
def test_definite_integral_correct():
    """∫_0^1 x dx = 1/2 → PASS."""
    spec = ProblemSpec(
        answer_type="integral",
        expression="x",
        variable="x",
        claimed_answer="1/2",
        definite=True,
        lower_bound="0",
        upper_bound="1",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 6b. Definite integral — wrong
# ---------------------------------------------------------------------------
def test_definite_integral_wrong():
    """∫_0^1 x dx ≠ 1 → FAIL."""
    spec = ProblemSpec(
        answer_type="integral",
        expression="x",
        variable="x",
        claimed_answer="1",
        definite=True,
        lower_bound="0",
        upper_bound="1",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ---------------------------------------------------------------------------
# 7a. Equation solution set — correct (complete)
# ---------------------------------------------------------------------------
def test_solution_set_correct():
    """x**2 - 1 = 0 → solutions {-1, 1} → PASS."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 - 1",
        variable="x",
        claimed_answer="{-1, 1}",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 7b. Equation solution set — incomplete
# ---------------------------------------------------------------------------
def test_solution_set_incomplete():
    """x**2 - 1 = 0 claimed {1} only → FAIL (missing -1)."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 - 1",
        variable="x",
        claimed_answer="{1}",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL (incomplete solution set) but got PASS"


# ---------------------------------------------------------------------------
# 8a. Ill-posed — unparseable expression
# ---------------------------------------------------------------------------
def test_ill_posed_unparseable():
    """'x +* 2' is not valid SymPy syntax → FAIL, no exception."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="x +* 2",
        variable="x",
        claimed_answer="x",
    )
    # Must not raise
    result = verify(spec)
    assert not result.passed, "Expected FAIL for unparseable input"
    assert result.reason  # should have an explanatory reason


# ---------------------------------------------------------------------------
# 8b. Ill-posed — undeclared free symbol in claimed answer
# ---------------------------------------------------------------------------
def test_ill_posed_free_symbol():
    """Claimed answer introduces undeclared symbol 'y' → FAIL."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="x**2",
        variable="x",
        claimed_answer="x**2 + y",  # 'y' not declared
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL for undeclared free symbol"


# ---------------------------------------------------------------------------
# 9. Limit — correct
# ---------------------------------------------------------------------------
def test_limit_correct():
    """lim_{x→0} sin(x)/x = 1 → PASS."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="sin(x)/x",
        variable="x",
        limit_point="0",
        claimed_answer="1",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


# ---------------------------------------------------------------------------
# 9b. Limit — wrong
# ---------------------------------------------------------------------------
def test_limit_wrong():
    """lim_{x→0} sin(x)/x ≠ 0 → FAIL."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="sin(x)/x",
        variable="x",
        limit_point="0",
        claimed_answer="0",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ---------------------------------------------------------------------------
# 10. numeric_value answer type
# ---------------------------------------------------------------------------
def test_numeric_value_correct():
    """Numeric value: sqrt(4) claimed 2 → PASS."""
    spec = ProblemSpec(
        answer_type="numeric_value",
        expression="sqrt(4)",
        variable="x",
        claimed_answer="2",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


def test_numeric_value_wrong():
    """Numeric value: sqrt(4) claimed 3 → FAIL."""
    spec = ProblemSpec(
        answer_type="numeric_value",
        expression="sqrt(4)",
        variable="x",
        claimed_answer="3",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ---------------------------------------------------------------------------
# 11. Never raises — garbage input
# ---------------------------------------------------------------------------
def test_never_raises_on_garbage():
    """Even with completely garbage input, verify() must not raise."""
    spec = ProblemSpec(
        answer_type="derivative",
        expression="!!!! not math !!!!",
        variable="x",
        claimed_answer="???",
    )
    try:
        result = verify(spec)
        assert not result.passed, "Garbage input should FAIL"
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"verify() raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# 12. Expression equivalence — basic algebra
# ---------------------------------------------------------------------------
def test_expression_equivalence_algebra():
    """(x+1)**2 == x**2 + 2*x + 1 → PASS."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="(x+1)**2",
        variable="x",
        claimed_answer="x**2 + 2*x + 1",
    )
    result = verify(spec)
    assert result.passed, f"Expected PASS but got FAIL: {result.reason}"


def test_expression_equivalence_wrong():
    """(x+1)**2 ≠ x**2 + 1 → FAIL."""
    spec = ProblemSpec(
        answer_type="expression_equivalence",
        expression="(x+1)**2",
        variable="x",
        claimed_answer="x**2 + 1",
    )
    result = verify(spec)
    assert not result.passed, "Expected FAIL but got PASS"


# ===========================================================================
# REGRESSION — BUG 1 (SAFETY): transcendental/periodic equations have infinite
# solution sets. A finite claimed set can never be complete → must FAIL.
# solve() used to return only a partial sample, causing false PASSes.
# ===========================================================================
def test_solution_set_transcendental_sin_incomplete():
    """sin(x)=0 has infinite solutions n·π; claimed {0, pi} is incomplete → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="sin(x)",
        variable="x",
        claimed_answer="{0, pi}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL (infinite sol set) got PASS: {result.reason}"


def test_solution_set_transcendental_cos_incomplete():
    """cos(x)-1=0 has infinite solutions 2n·π; claimed {0, 2*pi} incomplete → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="cos(x)-1",
        variable="x",
        claimed_answer="{0, 2*pi}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"


def test_solution_set_transcendental_tan_incomplete():
    """tan(x)=0 has infinite solutions n·π; claimed {0} incomplete → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="tan(x)",
        variable="x",
        claimed_answer="{0}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"


def test_solution_set_transcendental_sin_squared_incomplete():
    """sin(x)**2 - 1/4 = 0 has infinite solutions; claimed 4 roots incomplete → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="sin(x)**2 - 1/4",
        variable="x",
        claimed_answer="{-pi/6, pi/6, 5*pi/6, 7*pi/6}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"


def test_solution_set_transcendental_cos2x_incomplete():
    """cos(2*x)-1=0 has infinite solutions n·π; claimed {0, pi} incomplete → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="cos(2*x)-1",
        variable="x",
        claimed_answer="{0, pi}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"


def test_solution_set_polynomial_still_passes():
    """Regression guard: pure polynomial x**2-1=0 claimed {-1,1} still PASS."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 - 1",
        variable="x",
        claimed_answer="{-1, 1}",
    )
    result = verify(spec)
    assert result.passed is True, f"Expected PASS got FAIL: {result.reason}"


def test_solution_set_polynomial_incomplete_still_fails():
    """Regression guard: x**2-1=0 claimed {1} only → FAIL (missing -1)."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 - 1",
        variable="x",
        claimed_answer="{1}",
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"


def test_solution_set_spurious_root_fails():
    """Claimed set adds a spurious root that does not satisfy the equation → FAIL."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 - 1",
        variable="x",
        claimed_answer="{-1, 1, 2}",  # 2 is spurious
    )
    result = verify(spec)
    assert result.passed is False, f"Expected FAIL (spurious root) got PASS: {result.reason}"


def test_solution_set_empty_over_reals_deterministic_fail():
    """x**2+1=0 over Reals has no real solutions; claimed {} → deterministic FAIL, no crash."""
    spec = ProblemSpec(
        answer_type="equation_solution_set",
        expression="x**2 + 1",
        variable="x",
        claimed_answer="{}",
    )
    try:
        result = verify(spec)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"verify() raised on empty-set claim: {exc}")
    assert result.passed is False, f"Expected deterministic FAIL got PASS: {result.reason}"


# ===========================================================================
# REGRESSION — BUG 2: infinite limits were wrongly rejected because
# simplify(oo - oo) = nan. These CORRECT answers must now PASS.
# ===========================================================================
def test_limit_infinite_x_to_oo():
    """lim_{x→oo} x = oo → PASS."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="x",
        variable="x",
        limit_point="oo",
        claimed_answer="oo",
    )
    result = verify(spec)
    assert result.passed is True, f"Expected PASS got FAIL: {result.reason}"


def test_limit_infinite_one_over_x():
    """lim_{x→0+} 1/x = oo (SymPy default dir='+') → PASS."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="1/x",
        variable="x",
        limit_point="0",
        claimed_answer="oo",
    )
    result = verify(spec)
    assert result.passed is True, f"Expected PASS got FAIL: {result.reason}"


def test_limit_infinite_x_squared_to_oo():
    """lim_{x→oo} x**2 = oo → PASS."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="x**2",
        variable="x",
        limit_point="oo",
        claimed_answer="oo",
    )
    result = verify(spec)
    assert result.passed is True, f"Expected PASS got FAIL: {result.reason}"


def test_limit_infinite_wrong_still_fails():
    """lim_{x→oo} x = oo, but claimed a finite value → FAIL (no crash feeding oo to complex)."""
    spec = ProblemSpec(
        answer_type="limit",
        expression="x",
        variable="x",
        limit_point="oo",
        claimed_answer="5",
    )
    try:
        result = verify(spec)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"verify() raised on infinite-vs-finite limit: {exc}")
    assert result.passed is False, f"Expected FAIL got PASS: {result.reason}"
