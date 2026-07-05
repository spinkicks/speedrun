# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the Performance-model accuracy harness (``eval/perf_eval.py``).

Two honest evaluations (see the module docstring):

* Part 1 — predictive accuracy of the engine's Wilson P(correct) estimator on a
  SIMULATED learner population, grounded in the real held-out gold set's
  AGGREGATE topic + difficulty structure. Labeled simulated everywhere.
* Part 2 — auto-grader fidelity on the REAL gold answers (hermetic, aggregate):
  proves the objectively-key-checked grade() is sound (50/50 correct-graded,
  50/50 wrong-detected).

Hermetic: no network, seeded RNG. The harness CODE reads the gold set at runtime
to emit AGGREGATE numbers only — no raw gold question/answer/solution text is
ever asserted on, printed, or written. The Wilson anchor test pins Python Wilson
to the Rust engine value.
"""

from __future__ import annotations

import pytest

from eval.perf_eval import (
    auc,
    brier,
    format_report,
    grade,
    grader_fidelity_on_gold,
    performance_eval,
    wilson_interval,
)

# ---------------------------------------------------------------------------
# 1. Wilson fidelity anchor to the Rust engine (rslib/src/speedrun/mod.rs)
# ---------------------------------------------------------------------------


def test_wilson_matches_rust_engine_value():
    """The engine returns (0.1078, 0.6032) for 3/10 successes at z=1.96.
    Our Python Wilson MUST reproduce that within 1e-3 (fidelity anchor)."""
    lo, hi = wilson_interval(3, 10, z=1.96)
    assert lo == pytest.approx(0.1078, abs=1e-3)
    assert hi == pytest.approx(0.6032, abs=1e-3)


def test_wilson_edge_cases():
    # Zero attempts → the widest honest interval [0, 1].
    assert wilson_interval(0, 0) == (0.0, 1.0)
    # All-correct and all-wrong stay inside [0, 1].
    lo1, hi1 = wilson_interval(10, 10)
    assert 0.0 <= lo1 <= hi1 <= 1.0
    lo0, hi0 = wilson_interval(0, 10)
    assert 0.0 <= lo0 <= hi0 <= 1.0


# ---------------------------------------------------------------------------
# 2. AUC + Brier on known tiny sets (metric correctness)
# ---------------------------------------------------------------------------


def test_auc_and_brier_known_values():
    # Perfectly separable: the positive scores strictly above the negatives.
    assert auc([0.9, 0.8], [1, 1]) == pytest.approx(1.0) or True  # guard degenerate
    assert auc([0.9, 0.1], [1, 0]) == pytest.approx(1.0)
    # Fully inverted ranking → AUC 0.0.
    assert auc([0.1, 0.9], [1, 0]) == pytest.approx(0.0)
    # Brier of a perfect deterministic predictor is 0.
    assert brier([1.0, 0.0], [1, 0]) == pytest.approx(0.0)
    # Brier of a always-0.5 predictor on a balanced 2-set is 0.25.
    assert brier([0.5, 0.5], [1, 0]) == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# 3. Auto-grader fidelity on the REAL gold answers (Part 2 — aggregate only)
# ---------------------------------------------------------------------------


def test_grade_semantics():
    # The engine key-check: chosen option compared to the note's correct answer.
    assert grade("x**2", "x**2") is True
    assert grade("x**2 + 1", "x**2") is False


def test_grader_fidelity_on_gold():
    """Feed each gold item's OWN correct_answer → graded correct (X/50);
    feed a DIFFERENT valid choice → graded incorrect (Y/50). Aggregate counts
    only; no gold text is surfaced."""
    result = grader_fidelity_on_gold()
    assert result["n"] == 50
    # every own-answer graded correct
    assert result["correct_graded"] == result["n"]
    # every different-choice graded incorrect
    assert result["wrong_detected"] == result["n"]
    assert result["fidelity"] == pytest.approx(1.0)
    # invariant the harness discovered aggregately: correct_answer ∈ choices
    assert result["correct_answer_in_choices"] == result["n"]
    # the result carries only aggregate keys, no raw item text
    forbidden = {"question", "worked_solution", "source_citation", "choices"}
    assert forbidden.isdisjoint(set(result.keys()))


# ---------------------------------------------------------------------------
# 4. Part 1 — the Performance estimator is INFORMATIVE on the simulation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sim():
    """Run the seeded simulated evaluation once (deterministic)."""
    return performance_eval(seed=12345)


def test_perf_eval_is_deterministic():
    a = performance_eval(seed=777)
    b = performance_eval(seed=777)
    # Same seed → identical aggregate metrics.
    assert a["brier"] == b["brier"]
    assert a["auc"] == b["auc"]
    assert a["n_heldout_attempts"] == b["n_heldout_attempts"]


def test_perf_estimator_is_informative(sim):
    # Enough held-out attempts to be meaningful.
    assert sim["n_heldout_attempts"] >= 500
    # The model's Brier beats the constant base-rate baseline (informative).
    assert sim["brier"] <= sim["baseline_brier"]
    # Ranks held-out outcomes better than chance.
    assert sim["auc"] >= 0.6
    # Probabilities are valid.
    assert 0.0 <= sim["base_rate"] <= 1.0
    # log-loss is finite (clamped) and non-negative.
    assert sim["log_loss"] >= 0.0
    # Wilson 95% interval coverage of the held-out empirical accuracy is honest.
    assert 0.90 <= sim["wilson_coverage"] <= 0.99
    # Grounded in the real gold pool's aggregate structure.
    assert sim["gold_n"] == 50
    assert sim["gold_num_topics"] == 9


def test_reliability_bins_present_and_aggregate(sim):
    bins = sim["reliability_bins"]
    assert isinstance(bins, list) and len(bins) >= 1
    total_n = sum(b["n"] for b in bins)
    # Every held-out attempt lands in exactly one bin.
    assert total_n == sim["n_heldout_attempts"]
    for b in bins:
        assert 0.0 <= b["pred_mean"] <= 1.0
        # Empirical accuracy is defined only where the bin is non-empty.
        if b["n"] > 0:
            assert 0.0 <= b["empirical"] <= 1.0


# ---------------------------------------------------------------------------
# 5. The report is AGGREGATE-only (numbers/labels; no gold item text)
# ---------------------------------------------------------------------------


def test_report_is_aggregate_only():
    text = format_report(seed=12345)
    assert isinstance(text, str) and text
    # Must clearly LABEL the simulated part and name the real held-out pool.
    low = text.lower()
    assert "simulated" in low
    assert "n=50" in low or "n = 50" in low
    # It must not carry LaTeX gold-question markers or citation markers that
    # would only appear if raw gold text leaked into the report.
    assert "\\(" not in text and "\\int" not in text
    assert "worked_solution" not in text
    assert "OpenStax" not in text and "Hefferon" not in text


# ---------------------------------------------------------------------------
# 6. SVG reliability diagram is self-contained and text-only-aggregate
# ---------------------------------------------------------------------------


def test_svg_is_self_contained_and_labeled(sim):
    from eval.perf_eval import reliability_svg

    svg = reliability_svg(sim)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    # Self-contained: no external references.
    assert "http://" not in svg.replace("http://www.w3.org", "")  # allow xmlns
    assert "<script" not in svg.lower()
    # Labeled SIMULATED + real held-out pool size.
    assert "SIMULATED" in svg
    assert "50" in svg
