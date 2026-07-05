# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
SymPy-based correctness verifier — the AI generation safety gate.

This module is the hard gate that makes the "AI off" failsafe: before any
AI-generated GRE math problem is accepted, this verifier confirms that the
claimed correct answer is ACTUALLY correct using both a symbolic check and a
numeric random-point check. Anything malformed, ambiguous, ill-posed, or only
coincidentally equal returns a FAIL. It never raises to the caller.

Design decisions:
- Fixed random seed (42) → deterministic, reproducible gate.
- Both symbolic AND numeric checks must pass for a PASS verdict.
- Undeclared free symbols in claimed answers → FAIL (prevents scope creep).
- Indefinite integrals: checked by differentiating the claimed antiderivative
  (handles the +C ambiguity cleanly).
- 8 numeric sample points with up to 3× resampling on domain errors.
- Equation solution sets use ``solveset(..., domain=S.Reals)`` (the COMPLETE
  solution set) NOT ``solve`` (which returns only a partial sample for
  transcendental/periodic equations); any non-finite complete set makes a
  finite claimed set FAIL as incomplete.
- Infinite limits (±oo) are compared by structural equality only; the numeric
  check runs solely when both sides are finite numbers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import sympy
from sympy import (
    I,
    Rational,
    S,
    Symbol,
    diff,
    integrate,
    limit,
    oo,
    pi,
    ratsimp,
    simplify,
    solveset,
    trigsimp,
)
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)
from sympy.sets.sets import FiniteSet


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

ANSWER_TYPES = frozenset(
    {
        "expression_equivalence",
        "equation_solution_set",
        "derivative",
        "integral",
        "limit",
        "numeric_value",
    }
)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# ---------------------------------------------------------------------------
# FIXED server-side numeric-gate parameters (NOT LLM/spec overridable).
#
# The numeric agreement check is a hard safety gate. Its tolerance and sample
# count must be controlled by the server, never by the (LLM-authored) spec:
# otherwise a crafted spec could set numeric_eps huge (swallowing any error) or
# numeric_samples=0 (making the numeric loop run zero times and pass vacuously),
# neutering the check. We clamp both here and ignore the spec's tuning fields.
# ProblemSpec still carries numeric_eps / numeric_samples for backward compat,
# but the verifier deliberately does not honor them.
_FIXED_NUMERIC_EPS = 1e-9
_MIN_NUMERIC_SAMPLES = 8


@dataclass
class ProblemSpec:
    """
    Describes a math problem for verification.

    Parameters
    ----------
    answer_type : str
        One of the supported answer types (see ANSWER_TYPES).
    expression : str
        The mathematical expression / equation LHS (as a SymPy-parseable string).
        For 'equation_solution_set', this is the LHS of ``expr = 0``.
    variable : str
        The primary variable name (e.g. "x").
    claimed_answer : str
        The answer being verified.
    definite : bool, optional
        For 'integral': True → definite integral, False → indefinite. Default False.
    lower_bound : str, optional
        For definite integrals: the lower bound as a parseable string.
    upper_bound : str, optional
        For definite integrals: the upper bound as a parseable string.
    limit_point : str, optional
        For 'limit': the point at which the limit is evaluated (e.g. "0", "oo").
    extra_symbols : list[str], optional
        Additional symbol names beyond ``variable`` used in the expressions.
    numeric_eps : float
        Tolerance for numeric equality checks. Default 1e-9.
    numeric_samples : int
        Number of numeric sample points. Default 8.
    numeric_seed : int
        Fixed random seed for reproducibility. Default 42.
    """

    answer_type: str
    expression: str
    variable: str
    claimed_answer: str
    definite: bool = False
    lower_bound: Optional[str] = None
    upper_bound: Optional[str] = None
    limit_point: Optional[str] = None
    extra_symbols: list[str] = field(default_factory=list)
    numeric_eps: float = 1e-9
    numeric_samples: int = 8
    numeric_seed: int = 42


@dataclass
class VerificationResult:
    """
    Result of a verification attempt.

    Parameters
    ----------
    passed : bool
        True iff both applicable checks passed.
    reason : str
        Human-readable explanation of the verdict.
    symbolic_ran : bool
        Whether a symbolic check was attempted.
    numeric_ran : bool
        Whether a numeric check was attempted.
    """

    passed: bool
    reason: str
    symbolic_ran: bool = False
    numeric_ran: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fail(reason: str, symbolic_ran: bool = False, numeric_ran: bool = False) -> VerificationResult:
    return VerificationResult(passed=False, reason=reason, symbolic_ran=symbolic_ran, numeric_ran=numeric_ran)


def _pass(reason: str, symbolic_ran: bool = False, numeric_ran: bool = False) -> VerificationResult:
    return VerificationResult(passed=True, reason=reason, symbolic_ran=symbolic_ran, numeric_ran=numeric_ran)


def _build_local_dict(symbols: list[str]) -> dict:
    """Build a symbol table for parse_expr from a list of symbol name strings."""
    local_dict: dict = {}
    for name in symbols:
        local_dict[name] = Symbol(name)
    return local_dict


def _parse(expr_str: str, local_dict: dict):
    """
    Parse a SymPy expression string safely.

    Returns (sympy_expr, error_str_or_None).
    """
    try:
        result = parse_expr(
            expr_str,
            local_dict=local_dict,
            transformations=TRANSFORMATIONS,
            evaluate=True,
        )
        return result, None
    except Exception as exc:
        return None, f"Parse error for '{expr_str}': {exc}"


def _parse_set(set_str: str, local_dict: dict):
    """
    Parse a set literal like '{-1, 1}' into a SymPy FiniteSet.

    Returns (sympy_set, error_str_or_None).
    """
    stripped = set_str.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None, f"Expected a set literal like {{a, b, ...}}, got: {set_str!r}"
    inner = stripped[1:-1]
    if not inner.strip():
        # Empty-set literal '{}'. We treat this as a deterministic parse
        # rejection rather than an empty FiniteSet: verifying "no solutions"
        # is out of scope for the GRE finite-answer gate, so it FAILs cleanly.
        return None, "empty solution set '{}' is not accepted (a non-empty finite claimed set is required)"
    elements = []
    for token in inner.split(","):
        token = token.strip()
        if not token:
            return None, f"Empty element in set: {set_str!r}"
        expr, err = _parse(token, local_dict)
        if err:
            return None, err
        elements.append(expr)
    return FiniteSet(*elements), None


def _symbolic_equal(lhs, rhs) -> bool:
    """Return True if lhs and rhs are mathematically equal.

    A structural-equality fast-path (``lhs == rhs``) is checked first. This
    handles ``oo == oo`` / ``-oo == -oo`` (where ``simplify(oo - oo)`` yields
    ``nan`` and would spuriously report inequality) and is a harmless shortcut
    for all other cases before the ``simplify`` path runs.
    """
    try:
        if lhs == rhs:
            return True
        diff_expr = simplify(lhs - rhs)
        if diff_expr == S.Zero:
            return True
        # Try additional simplifiers
        if trigsimp(diff_expr) == S.Zero:
            return True
        if ratsimp(diff_expr) == S.Zero:
            return True
        return False
    except Exception:
        return False


def _free_symbols_names(expr) -> set[str]:
    """Return the set of free symbol names in a SymPy expression."""
    try:
        return {str(s) for s in expr.free_symbols}
    except Exception:
        return set()


def _normalize_answer_string(text: str) -> str:
    """Conservative, whitespace-insensitive string normalization fallback.

    Used only when symbolic parsing/comparison cannot decide. Lowercasing is
    deliberately NOT applied (case can be meaningful in some answers); we only
    collapse whitespace so trivial formatting differences do not cause a false
    ``abstain`` while never masking a genuine value difference.
    """
    return " ".join(str(text or "").split())


def answers_equivalent(
    a: str, b: str, *, extra_symbols: Optional[list[str]] = None
) -> bool:
    """Return True iff answer strings ``a`` and ``b`` denote the SAME answer.

    This is the cross-check used by the generation graph (BUG 1): the answer
    that gets SHIPPED (``candidate.correct``) must be the SAME one that the
    verifier actually validated (``spec.claimed_answer``). It is deliberately
    CONSERVATIVE — it returns True only when it can positively establish
    equivalence; ANY doubt (parse failure, ambiguity) yields False so the caller
    fails closed (abstains).

    Strategy, in order:
      1. Exact / whitespace-collapsed string match → True (cheap, unambiguous).
      2. Both parse as set literals ``{...}`` → compare as simplified finite
         sets (order-insensitive).
      3. Both parse as SymPy expressions with no *new* undeclared symbols →
         :func:`_symbolic_equal`.
      4. Otherwise → False (cannot confirm; caller abstains).
    """
    a_raw, b_raw = str(a or ""), str(b or "")
    if _normalize_answer_string(a_raw) == _normalize_answer_string(b_raw):
        return True

    syms = ["x", "y", "z", "t", "n", "k"]
    if extra_symbols:
        syms = list(dict.fromkeys(syms + list(extra_symbols)))
    local_dict = _build_local_dict(syms)
    local_dict["oo"] = oo
    local_dict["pi"] = pi
    local_dict["I"] = I

    a_is_set = a_raw.strip().startswith("{")
    b_is_set = b_raw.strip().startswith("{")
    try:
        if a_is_set or b_is_set:
            if not (a_is_set and b_is_set):
                return False  # one is a set, the other is not → not equivalent
            set_a, err_a = _parse_set(a_raw, local_dict)
            set_b, err_b = _parse_set(b_raw, local_dict)
            if err_a or err_b:
                return False
            try:
                norm_a = frozenset(simplify(e) for e in set_a)
                norm_b = frozenset(simplify(e) for e in set_b)
            except Exception:
                return set_a == set_b
            return (set_a == set_b) or (norm_a == norm_b)

        expr_a, err_a = _parse(a_raw, local_dict)
        expr_b, err_b = _parse(b_raw, local_dict)
        if err_a or err_b:
            return False
        return _symbolic_equal(expr_a, expr_b)
    except Exception:
        # Any failure to positively establish equivalence → conservative False.
        return False


def _numeric_check(lhs, rhs, symbols: list[Symbol], spec: ProblemSpec) -> tuple[bool, str]:
    """
    Numeric random-point check: substitute pseudo-random rational values and
    assert |lhs - rhs| < eps at all of them.

    Returns (passed, reason).
    """
    # Server-side clamps: the numeric gate's tolerance and sample count are
    # FIXED here and NOT taken from the (LLM-authored) spec — see the module
    # constants. This closes the "neuter the numeric gate" hole (a spec setting
    # numeric_eps huge or numeric_samples=0 must not weaken/skip this check).
    eps = _FIXED_NUMERIC_EPS
    needed = max(_MIN_NUMERIC_SAMPLES, int(spec.numeric_samples or 0))

    if not symbols:
        # No free symbols — try a direct numeric evaluation
        try:
            val = complex(lhs - rhs)
            if abs(val) < eps:
                return True, "numeric check passed (no free symbols)"
            return False, f"numeric check failed (no free symbols): |diff| = {abs(val)}"
        except Exception as exc:
            return False, f"numeric check error (no free symbols): {exc}"

    rng = random.Random(spec.numeric_seed)
    # Generate rational sample values (avoid 0 and 1 to prevent degenerate cases)
    sample_values_pool = [
        Rational(p, q)
        for p in range(-7, 8) if p != 0
        for q in [1, 2, 3]
    ]
    # Shuffle with the fixed seed
    rng.shuffle(sample_values_pool)

    success_count = 0
    skip_count = 0
    # ``needed`` is the server-clamped sample count computed above (>= the safe
    # minimum); the spec cannot drive it to 0.
    pool_idx = 0

    while success_count < needed and pool_idx + len(symbols) <= len(sample_values_pool) + 1:
        # Build a substitution dict
        subs = {}
        for sym in symbols:
            if pool_idx < len(sample_values_pool):
                subs[sym] = sample_values_pool[pool_idx]
                pool_idx += 1
            else:
                # Ran out of pool — use a fallback value
                subs[sym] = Rational(pool_idx + 1, 7)
                pool_idx += 1

        try:
            lhs_val = complex(lhs.subs(subs))
            rhs_val = complex(rhs.subs(subs))
            if abs(lhs_val - rhs_val) < eps:
                success_count += 1
            else:
                return (
                    False,
                    f"numeric check failed at {subs}: |lhs-rhs| = {abs(lhs_val - rhs_val):.2e}",
                )
        except (ZeroDivisionError, ValueError, TypeError, AttributeError):
            # Domain error — skip this point
            skip_count += 1
            if skip_count > needed * 3:
                return False, "too many domain errors during numeric sampling — ill-posed expression"

    if success_count < needed:
        return False, f"only {success_count}/{needed} numeric samples succeeded"

    return True, f"numeric check passed ({success_count} samples)"


# ---------------------------------------------------------------------------
# Answer-type handlers
# ---------------------------------------------------------------------------

def _verify_expression_equivalence(spec: ProblemSpec) -> VerificationResult:
    """Verify that two expressions are mathematically equal."""
    all_syms = [spec.variable] + spec.extra_symbols
    local_dict = _build_local_dict(all_syms)

    lhs_expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    rhs_expr, err = _parse(spec.claimed_answer, local_dict)
    if err:
        return _fail(err)

    # Check for undeclared free symbols in the claimed answer
    declared = set(all_syms)
    claimed_free = _free_symbols_names(rhs_expr)
    extra = claimed_free - declared
    if extra:
        return _fail(f"undeclared free symbol(s) in claimed answer: {extra}")

    # Symbolic check
    sym_ok = _symbolic_equal(lhs_expr, rhs_expr)

    # Numeric check
    syms = [Symbol(s) for s in all_syms]
    num_ok, num_reason = _numeric_check(lhs_expr, rhs_expr, syms, spec)

    if sym_ok and num_ok:
        return _pass("both symbolic and numeric checks passed", symbolic_ran=True, numeric_ran=True)
    if not sym_ok:
        return _fail("symbolic check failed (expressions not equal)", symbolic_ran=True, numeric_ran=num_ok)
    # sym_ok but not num_ok → coincidence trap (e.g. Abs(x) vs x)
    return _fail(f"numeric check failed (possible coincidence): {num_reason}", symbolic_ran=True, numeric_ran=True)


def _verify_derivative(spec: ProblemSpec) -> VerificationResult:
    """Verify that claimed_answer == d/d(variable) of expression."""
    all_syms = [spec.variable] + spec.extra_symbols
    local_dict = _build_local_dict(all_syms)
    var = Symbol(spec.variable)

    expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    claimed, err = _parse(spec.claimed_answer, local_dict)
    if err:
        return _fail(err)

    # Undeclared symbols
    declared = set(all_syms)
    extra = _free_symbols_names(claimed) - declared
    if extra:
        return _fail(f"undeclared free symbol(s) in claimed answer: {extra}")

    try:
        true_deriv = diff(expr, var)
    except Exception as exc:
        return _fail(f"failed to compute derivative: {exc}")

    sym_ok = _symbolic_equal(true_deriv, claimed)

    syms = [Symbol(s) for s in all_syms]
    num_ok, num_reason = _numeric_check(true_deriv, claimed, syms, spec)

    if sym_ok and num_ok:
        return _pass("derivative correct (both checks)", symbolic_ran=True, numeric_ran=True)
    if not sym_ok:
        return _fail("derivative is incorrect (symbolic check failed)", symbolic_ran=True, numeric_ran=num_ok)
    return _fail(f"derivative numerically inconsistent: {num_reason}", symbolic_ran=True, numeric_ran=True)


def _verify_integral(spec: ProblemSpec) -> VerificationResult:
    """Verify indefinite or definite integral."""
    all_syms = [spec.variable] + spec.extra_symbols
    local_dict = _build_local_dict(all_syms)
    var = Symbol(spec.variable)

    expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    claimed, err = _parse(spec.claimed_answer, local_dict)
    if err:
        return _fail(err)

    # Undeclared symbols
    declared = set(all_syms)
    extra = _free_symbols_names(claimed) - declared
    if extra:
        return _fail(f"undeclared free symbol(s) in claimed answer: {extra}")

    if spec.definite:
        # Definite integral: compute the true value and compare numerically
        if spec.lower_bound is None or spec.upper_bound is None:
            return _fail("definite integral requires lower_bound and upper_bound")

        lower, err = _parse(spec.lower_bound, local_dict)
        if err:
            return _fail(f"lower_bound parse error: {err}")
        upper, err = _parse(spec.upper_bound, local_dict)
        if err:
            return _fail(f"upper_bound parse error: {err}")

        try:
            true_val = integrate(expr, (var, lower, upper))
        except Exception as exc:
            return _fail(f"failed to compute definite integral: {exc}")

        sym_ok = _symbolic_equal(true_val, claimed)

        # Numeric check with no free symbols (bounds are concrete)
        num_ok, num_reason = _numeric_check(true_val, claimed, [], spec)

        if sym_ok and num_ok:
            return _pass("definite integral correct (both checks)", symbolic_ran=True, numeric_ran=True)
        if not sym_ok:
            return _fail("definite integral value incorrect (symbolic)", symbolic_ran=True, numeric_ran=num_ok)
        return _fail(f"definite integral numerically inconsistent: {num_reason}", symbolic_ran=True, numeric_ran=True)

    else:
        # Indefinite integral: differentiate the claimed antiderivative and check == integrand
        # This correctly handles the +C ambiguity.
        try:
            claimed_deriv = diff(claimed, var)
        except Exception as exc:
            return _fail(f"failed to differentiate claimed antiderivative: {exc}")

        sym_ok = _symbolic_equal(expr, claimed_deriv)

        syms = [Symbol(s) for s in all_syms]
        num_ok, num_reason = _numeric_check(expr, claimed_deriv, syms, spec)

        if sym_ok and num_ok:
            return _pass("indefinite integral correct via antiderivative differentiation", symbolic_ran=True, numeric_ran=True)
        if not sym_ok:
            return _fail("claimed antiderivative is incorrect (d/dx(claimed) ≠ integrand)", symbolic_ran=True, numeric_ran=num_ok)
        return _fail(f"antiderivative numerically inconsistent: {num_reason}", symbolic_ran=True, numeric_ran=True)


def _verify_limit(spec: ProblemSpec) -> VerificationResult:
    """Verify a limit computation."""
    if spec.limit_point is None:
        return _fail("limit answer_type requires limit_point")

    all_syms = [spec.variable] + spec.extra_symbols
    # Allow 'oo' and 'pi' in limit point parsing
    local_dict = _build_local_dict(all_syms)
    local_dict["oo"] = oo
    local_dict["pi"] = pi
    local_dict["I"] = I

    var = Symbol(spec.variable)

    expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    claimed, err = _parse(spec.claimed_answer, local_dict)
    if err:
        return _fail(err)

    point, err = _parse(spec.limit_point, local_dict)
    if err:
        return _fail(f"limit_point parse error: {err}")

    # BUG P1-D: SymPy's default ``limit(expr, var, point)`` is ONE-SIDED
    # (dir='+', the right-hand limit). Accepting on the right-hand limit alone
    # lets an ill-posed problem whose TWO-SIDED limit does NOT exist pass as
    # "verified" (e.g. floor(x), sign(x), Abs(x)/x, exp(1/x) at 0). The honesty
    # gate must require the two-sided limit to EXIST first: compute BOTH the
    # left- and right-hand limits and accept the existence only when
    #   (a) both are finite and equal, OR
    #   (b) both are infinite (the project's documented unsigned-infinite
    #       convention — see BUG 2 regression, e.g. 1/x @ 0 → oo).
    # Any other combination (finite but unequal, one finite / one infinite)
    # means the two-sided limit does not exist → reject (fail closed / abstain).
    # All finiteness reasoning is wrapped so any exception fails CLOSED rather
    # than granting a spurious PASS.
    try:
        left = limit(expr, var, point, "-")
        right = limit(expr, var, point, "+")
    except Exception as exc:
        return _fail(f"failed to compute limit: {exc}")

    try:
        left_finite = left.is_finite is True and left.is_number
        right_finite = right.is_finite is True and right.is_number
        left_infinite = left.is_infinite is True
        right_infinite = right.is_infinite is True
    except Exception as exc:
        # Fail CLOSED: if we cannot even classify the one-sided limits, refuse
        # rather than fall through to a symbolic-only PASS.
        return _fail(f"limit existence guard errored (failing closed): {exc}")

    if left_finite and right_finite and _symbolic_equal(left, right):
        # Genuine finite two-sided limit; compare the shared value to claimed.
        true_limit = left
    elif left_infinite and right_infinite:
        # Both sides diverge; documented unsigned-infinite convention accepts
        # this as an (unsigned) infinite limit.
        true_limit = oo
    else:
        return _fail(
            "two-sided limit does not exist "
            f"(left={left}, right={right}); ill-posed limit rejected",
            symbolic_ran=True,
        )

    sym_ok = _symbolic_equal(true_limit, claimed)

    # Numeric check: only run it when BOTH sides are FINITE numbers. Feeding
    # ±oo (or nan) into complex() raises/misbehaves, so infinite limits are
    # verified by the symbolic (structural-equality) path alone.
    numeric_ran = False
    try:
        both_finite_numbers = (
            true_limit.is_finite is True
            and true_limit.is_number
            and claimed.is_finite is True
            and claimed.is_number
        )
        if both_finite_numbers:
            num_ok, num_reason = _numeric_check(true_limit, claimed, [], spec)
            numeric_ran = True
        else:
            num_ok, num_reason = True, "numeric check skipped (non-finite or non-numeric limit)"
    except Exception as exc:
        # Fail CLOSED: an error while deciding/running the numeric guard must not
        # grant a free PASS off the symbolic arm alone. Any doubt → reject.
        num_ok, num_reason = False, f"limit numeric guard errored (failing closed): {exc}"

    if sym_ok and num_ok:
        detail = "both checks" if numeric_ran else "symbolic check; numeric skipped (infinite/non-numeric)"
        return _pass(f"limit correct ({detail})", symbolic_ran=True, numeric_ran=numeric_ran)
    if not sym_ok:
        return _fail(f"limit incorrect: true limit is {true_limit}, claimed {claimed}", symbolic_ran=True, numeric_ran=numeric_ran)
    return _fail(f"limit numerically inconsistent: {num_reason}", symbolic_ran=True, numeric_ran=numeric_ran)


def _verify_equation_solution_set(spec: ProblemSpec) -> VerificationResult:
    """Verify that claimed_answer is the COMPLETE solution set of ``expr = 0``.

    Gate rule (conservative — designed to never emit a false PASS):

    The true solution set is computed with ``sympy.solveset(expr, var,
    domain=S.Reals)``, which — unlike ``sympy.solve`` — returns the *complete*
    solution set (including infinite periodic families for transcendental
    equations). We then:

    1. If solveset returns a ``FiniteSet``: PASS only if it equals the claimed
       finite set (simplify-normalized comparison) AND every claimed root
       substituted back into ``expr`` evaluates to ~0 (numeric, ``eps``). This
       rejects spurious claimed roots.
    2. If solveset returns anything that is NOT a ``FiniteSet`` (an infinite
       ``ImageSet``/``Union`` of them, ``Interval``, ``ConditionSet``,
       ``Complement``, etc.): a finite claimed set can never be the complete
       solution → FAIL.
    3. On ``ConditionSet`` / any failure to solve → FAIL ("could not determine
       complete solution set").

    Domain defaults to the reals (``S.Reals``) — a reasonable, stated choice for
    GRE real-variable problems.
    """
    all_syms = [spec.variable] + spec.extra_symbols
    local_dict = _build_local_dict(all_syms)
    # Constants that legitimately appear in claimed root sets (e.g. {pi/6}).
    local_dict["oo"] = oo
    local_dict["pi"] = pi
    local_dict["I"] = I
    var = Symbol(spec.variable)

    expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    claimed_set, err = _parse_set(spec.claimed_answer, local_dict)
    if err:
        return _fail(f"could not parse solution set: {err}")

    # Compute the COMPLETE solution set over the reals.
    try:
        true_set = solveset(expr, var, domain=S.Reals)
    except Exception as exc:
        return _fail(f"could not determine complete solution set: {exc}", symbolic_ran=True)

    # A ConditionSet means solveset could not fully solve the equation.
    if isinstance(true_set, sympy.ConditionSet):
        return _fail(
            "could not determine complete solution set (solveset returned a ConditionSet)",
            symbolic_ran=True,
        )

    # If the complete solution set is NOT finite, a finite claimed set cannot
    # possibly be complete → FAIL. This closes the transcendental/periodic hole.
    if not isinstance(true_set, FiniteSet):
        return _fail(
            "equation has infinitely many or non-finite solutions; a finite "
            f"claimed set is incomplete (true solution set: {true_set})",
            symbolic_ran=True,
        )

    # --- true_set is a FiniteSet: compare against the claimed finite set. ---
    try:
        def _normalize_set(s) -> frozenset:
            return frozenset(simplify(e) for e in s)

        sets_equal = (true_set == claimed_set) or (
            _normalize_set(true_set) == _normalize_set(claimed_set)
        )
        if not sets_equal:
            return _fail(
                f"solution set incorrect: true={true_set}, claimed={claimed_set}",
                symbolic_ran=True,
            )
    except Exception as exc:
        return _fail(f"solution set comparison failed: {exc}", symbolic_ran=True)

    # Extra guard: substitute each claimed root back into expr and require ~0.
    # This rejects spurious claimed roots even if set comparison were fooled.
    try:
        for root in claimed_set:
            residual = expr.subs(var, root)
            try:
                residual_val = complex(residual)
            except (TypeError, ValueError):
                residual_val = complex(simplify(residual))
            # FIXED server-side eps (not spec-overridable) — same rationale as
            # _numeric_check: an LLM-supplied huge eps must not admit a spurious
            # root whose residual is large.
            if abs(residual_val) >= _FIXED_NUMERIC_EPS:
                return _fail(
                    f"claimed root {root} does not satisfy the equation "
                    f"(residual {abs(residual_val):.2e})",
                    symbolic_ran=True,
                    numeric_ran=True,
                )
    except Exception as exc:
        return _fail(f"root back-substitution failed: {exc}", symbolic_ran=True, numeric_ran=True)

    return _pass("solution set correct (complete and back-substitution verified)",
                 symbolic_ran=True, numeric_ran=True)


def _verify_numeric_value(spec: ProblemSpec) -> VerificationResult:
    """Verify that the claimed scalar value equals the true expression value."""
    all_syms = [spec.variable] + spec.extra_symbols
    local_dict = _build_local_dict(all_syms)

    expr, err = _parse(spec.expression, local_dict)
    if err:
        return _fail(err)

    claimed, err = _parse(spec.claimed_answer, local_dict)
    if err:
        return _fail(err)

    # Symbolic check first
    sym_ok = _symbolic_equal(expr, claimed)

    # Numeric check
    num_ok, num_reason = _numeric_check(expr, claimed, [], spec)

    if sym_ok and num_ok:
        return _pass("numeric value correct (both checks)", symbolic_ran=True, numeric_ran=True)
    if not sym_ok:
        return _fail("numeric value incorrect (symbolic check failed)", symbolic_ran=True, numeric_ran=num_ok)
    return _fail(f"numeric value inconsistent: {num_reason}", symbolic_ran=True, numeric_ran=True)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_HANDLERS = {
    "expression_equivalence": _verify_expression_equivalence,
    "derivative": _verify_derivative,
    "integral": _verify_integral,
    "limit": _verify_limit,
    "equation_solution_set": _verify_equation_solution_set,
    "numeric_value": _verify_numeric_value,
}


def verify(spec: ProblemSpec) -> VerificationResult:
    """
    Verify a math problem specification.

    This is the sole public entry point. It NEVER raises — all exceptions are
    caught and converted to a FAIL result with a descriptive reason.

    Parameters
    ----------
    spec : ProblemSpec
        The problem to verify.

    Returns
    -------
    VerificationResult
        passed=True only if both applicable checks passed.
    """
    try:
        if spec.answer_type not in ANSWER_TYPES:
            return _fail(f"unsupported answer_type: {spec.answer_type!r}. Supported: {sorted(ANSWER_TYPES)}")

        handler = _HANDLERS[spec.answer_type]
        return handler(spec)

    except Exception as exc:
        # Belt-and-suspenders: catch anything that slipped through a handler
        return _fail(f"unexpected internal error: {exc}")
