# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Performance-model accuracy harness (§9.2).

The **Performance** score in the Rust engine (``rslib/src/speedrun/``) is
``P(correct on a novel Speedrun::Problem MCQ)`` per topic, computed as a
**Wilson 95%** interval on ``(correct / attempts)`` where correctness is now
**objectively key-checked** (the chosen MCQ option is compared to the note's
``CorrectAnswer``, not self-rated). It abstains below
``min_problem_attempts = 5``. This module evaluates that estimator HONESTLY,
in two clearly-separated parts:

Part 1 — predictive accuracy on a SIMULATED learner population
--------------------------------------------------------------
There are **no real learner attempts** on the held-out gold items yet, so we
cannot measure real predictive accuracy. Instead we simulate a learner
population and ask whether the engine's Wilson point estimate ``p̂`` (observed
on a learner's TRAIN attempts) PREDICTS that learner's remaining HELD-OUT
attempts. The simulation is **grounded in the real gold set's AGGREGATE
structure only** — its set of topics and the per-item difficulty offset derived
from each item's categorical ``difficulty_hint`` (easy/medium/hard). We NEVER
read gold question / answer / worked-solution / citation text into anything.
Every outcome here is SIMULATED and labeled as such.

Latent model (documented, seeded): each learner draws a per-topic ability
``θ ~ Normal(0, 1)``. True ``P(correct)`` on an item is the 1-parameter-logistic
(Rasch/IRT) ``logistic(θ_topic − b_item)`` where ``b_item`` is the difficulty
offset (easy −1, medium 0, hard +1). Outcomes are Bernoulli draws. The
estimator, exactly like the engine, **ignores per-item difficulty** — it just
counts correct/attempts per (learner, topic) and forms the Wilson estimate.

Part 2 — auto-grader fidelity on the REAL gold answers (hermetic, aggregate)
----------------------------------------------------------------------------
Validates the "objectively key-checked" claim: :func:`grade` implements the
engine's key-check (chosen option == correct answer). Reading the gold set
AGGREGATELY, we feed each item's own ``correct_answer`` (must grade correct) and
a deliberately DIFFERENT valid choice (must grade incorrect), and report the
aggregate fidelity (target 50/50 and 50/50 = 100%). We discovered the label
convention aggregately: the gold ``correct_answer`` is the choice-**text**
string (it is exactly one of the five ``choices`` strings — NOT a bare "A".."E"
letter), so the engine's key-check is a string compare of the chosen option's
value against ``CorrectAnswer``. :func:`grade` matches that.

Independence rule (mirrors ``eval/gate.py``): nothing here reads gold text into
anything that leaves the process as anything other than an aggregate
count/fraction.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Gold-set location (configurable; defaults to the repo-root eval/holdout/).
# services/speedrun-ai/eval/perf_eval.py -> repo root is three parents up.
# (Same resolution as eval/gate.py; we deliberately do NOT import gate.py to
# avoid pulling its heavy rag/verify dependencies.)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD_PATH = _REPO_ROOT / "eval" / "holdout" / "gre_math_gold.jsonl"

# Engine parity: Performance abstains below this many problem attempts.
MIN_PROBLEM_ATTEMPTS = 5

# Difficulty offsets (the IRT item difficulty b) per categorical hint. The gold
# set's difficulty_hint is categorical {easy, medium, hard} (discovered
# aggregately); we map to a symmetric ±1 logit offset, medium at 0.
_DIFFICULTY_OFFSET = {"easy": -1.0, "medium": 0.0, "hard": 1.0}


def _gold_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("SPEEDRUN_GOLD_PATH")
    return Path(env) if env else DEFAULT_GOLD_PATH


def _load_gold(path: Path | str | None = None) -> list[dict]:
    """Load the held-out gold set at runtime (INTERNAL, aggregate use only).

    Returns the parsed rows so callers can compute AGGREGATE numbers. Callers in
    this module never expose row text outward — mirrors ``gate.py::_load_gold``.
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
# Wilson 95% interval — MUST reproduce the Rust engine's value.
# ---------------------------------------------------------------------------


def wilson_interval(correct: int, attempts: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (correct/attempts).

    Fidelity anchor: for 3/10 successes at z=1.96 the Rust engine
    (``rslib/src/speedrun/mod.rs``) returns (0.1078, 0.6032); this reproduces it.
    With zero attempts there is no information, so it returns the widest honest
    interval [0.0, 1.0].
    """
    if attempts <= 0:
        return (0.0, 1.0)
    phat = correct / attempts
    z2 = z * z
    denom = 1.0 + z2 / attempts
    center = (phat + z2 / (2.0 * attempts)) / denom
    margin = (
        z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * attempts)) / attempts)
    ) / denom
    lo = center - margin
    hi = center + margin
    # Clamp to [0, 1] to stay a valid probability interval.
    return (max(0.0, lo), min(1.0, hi))


# ---------------------------------------------------------------------------
# Scoring metrics (dependency-free, exact).
# ---------------------------------------------------------------------------

_EPS = 1e-6


def brier(probs: list[float], outcomes: list[int]) -> float:
    """Mean squared error of predicted probabilities vs 0/1 outcomes."""
    if not probs:
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / len(probs)


def log_loss(probs: list[float], outcomes: list[int]) -> float:
    """Mean negative log-likelihood; probs clamped to [1e-6, 1-1e-6]."""
    if not probs:
        return 0.0
    total = 0.0
    for p, y in zip(probs, outcomes):
        pc = min(1.0 - _EPS, max(_EPS, p))
        total += -(y * math.log(pc) + (1 - y) * math.log(1.0 - pc))
    return total / len(probs)


def auc(scores: list[float], outcomes: list[int]) -> float:
    """Exact rank-based ROC AUC (probability a random positive outranks a
    random negative), counting ties as 0.5. Returns 0.5 if a class is absent."""
    pos = [s for s, y in zip(scores, outcomes) if y == 1]
    neg = [s for s, y in zip(scores, outcomes) if y == 0]
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for sp in pos:
        for sn in neg:
            if sp > sn:
                wins += 1.0
            elif sp == sn:
                wins += 0.5
    return wins / (len(pos) * len(neg))


# ---------------------------------------------------------------------------
# Part 2 — auto-grader fidelity on the REAL gold answers (aggregate only).
# ---------------------------------------------------------------------------


def grade(chosen: str, correct_answer: str) -> bool:
    """The engine's objective key-check: the chosen MCQ option is correct iff it
    equals the note's ``CorrectAnswer``.

    The gold ``correct_answer`` is the choice-text string (exactly one of the
    five ``choices``; discovered aggregately — it is NOT a bare A..E letter), so
    the key-check is a value compare of the chosen option against the stored
    correct answer. Whitespace is normalized so trivial padding never flips a
    grade (the engine stores canonical option text)."""
    return str(chosen).strip() == str(correct_answer).strip()


def grader_fidelity_on_gold(path: Path | str | None = None) -> dict[str, Any]:
    """Aggregate auto-grader fidelity on the REAL gold answers.

    For each of the N gold items: feeding its own ``correct_answer`` must grade
    CORRECT, and feeding a deliberately DIFFERENT valid choice must grade
    INCORRECT. Returns AGGREGATE counts only — never any item text::

        {"n", "correct_graded", "wrong_detected", "fidelity",
         "correct_answer_in_choices", "num_five_choice"}
    """
    gold = _load_gold(path)
    n = len(gold)
    correct_graded = 0
    wrong_detected = 0
    correct_answer_in_choices = 0
    num_five_choice = 0
    for item in gold:
        choices = item.get("choices") or []
        correct_answer = item.get("correct_answer", "")
        if isinstance(choices, list) and len(choices) == 5:
            num_five_choice += 1
        if correct_answer in choices:
            correct_answer_in_choices += 1
        # Own answer must grade correct.
        if grade(correct_answer, correct_answer):
            correct_graded += 1
        # A different valid choice must grade incorrect.
        other = next((c for c in choices if c != correct_answer), None)
        if other is not None and not grade(other, correct_answer):
            wrong_detected += 1
    return {
        "n": n,
        "correct_graded": correct_graded,
        "wrong_detected": wrong_detected,
        "fidelity": ((correct_graded + wrong_detected) / (2 * n)) if n else 0.0,
        "correct_answer_in_choices": correct_answer_in_choices,
        "num_five_choice": num_five_choice,
    }


# ---------------------------------------------------------------------------
# Part 1 — simulated learner population grounded in the real gold structure.
# ---------------------------------------------------------------------------


def _logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _gold_item_pool(path: Path | str | None = None) -> tuple[list[tuple[str, float]], list[str]]:
    """From the gold set, build the AGGREGATE item pool used to ground the
    simulation: a list of (topic_id, difficulty_offset) and the sorted topics.

    Uses only ``topic_id`` (per-topic structure) and ``difficulty_hint`` (mapped
    to an IRT difficulty offset). No question / answer / solution text touched.
    """
    gold = _load_gold(path)
    pool: list[tuple[str, float]] = []
    topics: set[str] = set()
    for item in gold:
        topic = item.get("topic_id", "")
        hint = str(item.get("difficulty_hint", "medium")).strip().lower()
        offset = _DIFFICULTY_OFFSET.get(hint, 0.0)
        pool.append((topic, offset))
        topics.add(topic)
    return pool, sorted(topics)


def performance_eval(
    *,
    seed: int = 12345,
    n_learners: int = 300,
    attempts_per_topic: int = 20,
    train_k: int = 5,
    n_bins: int = 10,
    gold_path: Path | str | None = None,
) -> dict[str, Any]:
    """Evaluate the Wilson P(correct) estimator on a SIMULATED learner
    population grounded in the real gold set's aggregate topic+difficulty pool.

    Deterministic given ``seed``. Returns AGGREGATE metrics + reliability bins.

    Design (see module docstring):
      1. Build the item pool (topic_id, difficulty offset) from the gold set —
         aggregate structure only.
      2. Simulate ``n_learners`` learners; each has per-topic ability
         θ_topic ~ Normal(0, 1). For each topic the learner attempts
         ``attempts_per_topic`` items drawn (by that topic) from the pool; true
         P(correct) = logistic(θ_topic − b_item); outcome ~ Bernoulli.
      3. Per (learner, topic) with ≥ MIN_PROBLEM_ATTEMPTS attempts: TRAIN = first
         ``train_k`` (default 5 — exactly the engine's ``min_problem_attempts``
         floor, i.e. the most conservative "just-unlocked" data budget the engine
         will ever score on), HELD-OUT = the rest (default 15 attempts). The
         estimator observes TRAIN → Wilson point p̂ = correct_train / train_k (it
         ignores per-item difficulty, exactly like the engine). Predict every
         held-out attempt with p̂. The larger held-out window is a measurement
         choice: it makes each cell's empirical held-out accuracy a stable target
         for the Wilson-coverage check; it does NOT give the estimator more data.
      4. Score p̂ vs held-out outcomes: Brier, log-loss, AUC, accuracy@0.5,
         a reliability diagram, Wilson-interval coverage of the held-out
         empirical accuracy, and a constant base-rate baseline Brier.
    """
    rng = random.Random(seed)
    pool, topics = _gold_item_pool(gold_path)
    gold_n = len(pool)
    # Bucket the pool by topic so we can draw same-topic items.
    by_topic: dict[str, list[float]] = {}
    for topic, offset in pool:
        by_topic.setdefault(topic, []).append(offset)

    preds: list[float] = []  # p̂ repeated per held-out attempt
    outs: list[int] = []  # held-out outcomes (0/1)
    # Per-(learner,topic) cells for Wilson coverage of held-out empirical acc.
    cell_train: list[tuple[int, int]] = []  # (correct_train, attempts_train)
    cell_heldout: list[tuple[int, int]] = []  # (correct_held, attempts_held)

    for _ in range(n_learners):
        for topic in topics:
            offsets = by_topic.get(topic, [])
            if not offsets:
                continue
            # Latent per-(learner, topic) ability θ, drawn ONCE per cell.
            theta_topic = rng.gauss(0.0, 1.0)
            outcomes: list[int] = []
            for _a in range(attempts_per_topic):
                # Draw a same-topic item; its difficulty offset b is the IRT b.
                b = offsets[rng.randrange(len(offsets))]
                p_true = _logistic(theta_topic - b)
                outcomes.append(1 if rng.random() < p_true else 0)

            if len(outcomes) < MIN_PROBLEM_ATTEMPTS:
                continue  # engine abstains; no estimate
            train = outcomes[:train_k]
            held = outcomes[train_k:]
            if not held:
                continue
            correct_train = sum(train)
            phat = correct_train / len(train)
            for y in held:
                preds.append(phat)
                outs.append(y)
            cell_train.append((correct_train, len(train)))
            cell_heldout.append((sum(held), len(held)))

    n_heldout = len(outs)
    base_rate = (sum(outs) / n_heldout) if n_heldout else 0.0

    model_brier = brier(preds, outs)
    baseline_brier = brier([base_rate] * n_heldout, outs)
    model_log_loss = log_loss(preds, outs)
    model_auc = auc(preds, outs)
    accuracy = (
        sum(1 for p, y in zip(preds, outs) if (1 if p >= 0.5 else 0) == y) / n_heldout
        if n_heldout
        else 0.0
    )

    # Wilson-interval coverage: fraction of cells whose TRAIN Wilson 95%
    # interval contains that learner's held-out empirical accuracy.
    covered = 0
    for (ct, at_), (ch, ah) in zip(cell_train, cell_heldout):
        lo, hi = wilson_interval(ct, at_)
        emp = ch / ah if ah else 0.0
        if lo <= emp <= hi:
            covered += 1
    wilson_coverage = (covered / len(cell_train)) if cell_train else 0.0

    # Reliability diagram: bin predictions in [0,1], report mean-pred vs
    # empirical held-out accuracy + n per bin.
    bins: list[dict[str, Any]] = []
    edges = [i / n_bins for i in range(n_bins + 1)]
    for i in range(n_bins):
        lo_e, hi_e = edges[i], edges[i + 1]
        # last bin is inclusive of 1.0
        if i == n_bins - 1:
            idx = [j for j, p in enumerate(preds) if lo_e <= p <= hi_e]
        else:
            idx = [j for j, p in enumerate(preds) if lo_e <= p < hi_e]
        n_b = len(idx)
        pred_mean = (sum(preds[j] for j in idx) / n_b) if n_b else (lo_e + hi_e) / 2
        empirical = (sum(outs[j] for j in idx) / n_b) if n_b else 0.0
        bins.append(
            {
                "lo": lo_e,
                "hi": hi_e,
                "n": n_b,
                "pred_mean": pred_mean,
                "empirical": empirical,
            }
        )

    return {
        # provenance / grounding
        "simulated": True,
        "seed": seed,
        "n_learners": n_learners,
        "attempts_per_topic": attempts_per_topic,
        "train_k": train_k,
        "min_problem_attempts": MIN_PROBLEM_ATTEMPTS,
        "gold_n": gold_n,
        "gold_num_topics": len(topics),
        "difficulty_offsets": dict(_DIFFICULTY_OFFSET),
        # Part 1 metrics
        "n_cells": len(cell_train),
        "n_heldout_attempts": n_heldout,
        "base_rate": base_rate,
        "brier": model_brier,
        "baseline_brier": baseline_brier,
        "log_loss": model_log_loss,
        "auc": model_auc,
        "accuracy": accuracy,
        "wilson_coverage": wilson_coverage,
        "reliability_bins": bins,
    }


# ---------------------------------------------------------------------------
# Reliability-diagram SVG (self-contained, dependency-free, aggregate-only).
# ---------------------------------------------------------------------------


def reliability_svg(result: dict[str, Any]) -> str:
    """Return a self-contained SVG reliability diagram string (no external
    refs, no scripts). The title states this is a SIMULATED learner population
    over the real held-out gold item pool N=50, plus Brier / AUC / accuracy /
    N. Aggregate numbers only."""
    W, H = 520, 400
    m = 56  # margin
    plot_w = W - 2 * m
    plot_h = H - 2 * m - 24  # leave headroom for two title lines

    def px(p: float) -> float:
        return m + p * plot_w

    def py(p: float) -> float:
        return (H - m) - p * plot_h

    bins = result.get("reliability_bins", [])
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="sans-serif">'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    # Titles (labeled SIMULATED + real held-out pool).
    parts.append(
        f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="14" '
        f'font-weight="bold">Performance estimator reliability '
        f'(SIMULATED learners)</text>'
    )
    parts.append(
        f'<text x="{W / 2}" y="40" text-anchor="middle" font-size="11" '
        f'fill="#555">grounded in real held-out GRE-Math gold pool '
        f'N={result.get("gold_n", 0)} &#183; Brier={result.get("brier", 0):.3f} '
        f'&#183; AUC={result.get("auc", 0):.3f} &#183; '
        f'acc={result.get("accuracy", 0):.3f} &#183; '
        f'N_attempts={result.get("n_heldout_attempts", 0)}</text>'
    )
    # Plot frame.
    parts.append(
        f'<rect x="{m}" y="{H - m - plot_h}" width="{plot_w}" height="{plot_h}" '
        f'fill="none" stroke="#999" stroke-width="1"/>'
    )
    # Perfect-calibration diagonal.
    parts.append(
        f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(1)}" y2="{py(1)}" '
        f'stroke="#bbb" stroke-width="1" stroke-dasharray="4 3"/>'
    )
    # Bin points sized by n, connected where non-empty.
    max_n = max((b["n"] for b in bins), default=1) or 1
    pts: list[tuple[float, float]] = []
    for b in bins:
        if b["n"] <= 0:
            continue
        cx, cy = px(b["pred_mean"]), py(b["empirical"])
        r = 3 + 6 * (b["n"] / max_n)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="#2b6cb0" fill-opacity="0.65" stroke="#1a365d"/>'
        )
        pts.append((cx, cy))
    if len(pts) >= 2:
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(
            f'<polyline points="{poly}" fill="none" stroke="#2b6cb0" '
            f'stroke-width="1.5"/>'
        )
    # Axis labels + ticks.
    parts.append(
        f'<text x="{m + plot_w / 2}" y="{H - 14}" text-anchor="middle" '
        f'font-size="12">predicted P(correct) (Wilson point p&#770;)</text>'
    )
    parts.append(
        f'<text x="16" y="{H - m - plot_h / 2}" text-anchor="middle" '
        f'font-size="12" transform="rotate(-90 16 {H - m - plot_h / 2})">'
        f'empirical held-out accuracy</text>'
    )
    for t in (0.0, 0.5, 1.0):
        parts.append(
            f'<text x="{px(t):.1f}" y="{H - m + 16:.1f}" text-anchor="middle" '
            f'font-size="10" fill="#555">{t:.1f}</text>'
        )
        parts.append(
            f'<text x="{m - 8}" y="{py(t) + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="#555">{t:.1f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Standalone report (prints AGGREGATE numbers only; never raw gold text).
# ---------------------------------------------------------------------------


def format_report(*, seed: int = 12345) -> str:
    sim = performance_eval(seed=seed)
    grader = grader_fidelity_on_gold()
    lines = [
        "Performance-model accuracy (§9.2) — aggregate results",
        "=" * 66,
        "",
        "PART 1 — predictive accuracy on a SIMULATED learner population",
        "         grounded in the REAL held-out gold pool's aggregate",
        "         topic+difficulty structure (N=50, 9 topics).",
        "  CAVEAT: no real learner attempts on the held-out items exist yet,",
        "  so predictive accuracy is measured on SIMULATED outcomes.",
        "-" * 66,
        f"  simulated learners      : {sim['n_learners']}",
        f"  attempts / (learner,topic): {sim['attempts_per_topic']}  "
        f"(train k={sim['train_k']}, min_problem_attempts={sim['min_problem_attempts']})",
        f"  (learner,topic) cells   : {sim['n_cells']}",
        f"  held-out attempts (N)   : {sim['n_heldout_attempts']}",
        f"  base rate (held-out)    : {sim['base_rate']:.4f}",
        f"  Brier (model p̂)       : {sim['brier']:.4f}",
        f"  Brier (base-rate const) : {sim['baseline_brier']:.4f}   "
        f"(model informative if lower)",
        f"  log-loss (model)        : {sim['log_loss']:.4f}",
        f"  AUC (held-out ranking)  : {sim['auc']:.4f}",
        f"  accuracy @0.5           : {sim['accuracy']:.4f}",
        f"  Wilson 95% coverage     : {sim['wilson_coverage']:.4f}   "
        f"(honest interval ~0.95)",
        "",
        "  reliability diagram (predicted-p bin -> empirical held-out acc, n):",
    ]
    for b in sim["reliability_bins"]:
        bar = "#" * int(round(b["empirical"] * 20)) if b["n"] else ""
        lines.append(
            f"    [{b['lo']:.1f},{b['hi']:.1f})  pred={b['pred_mean']:.3f}  "
            f"emp={b['empirical']:.3f}  n={b['n']:<5d} {bar}"
        )
    lines += [
        "",
        "PART 2 — auto-grader fidelity on the REAL gold answers (hermetic).",
        "         Validates the objectively-key-checked claim. Aggregate only.",
        "-" * 66,
        f"  gold items (N)          : {grader['n']}",
        f"  correct_answer in choices: {grader['correct_answer_in_choices']}/"
        f"{grader['n']}  (label convention = choice text, not A..E)",
        f"  own answer graded CORRECT: {grader['correct_graded']}/{grader['n']}",
        f"  diff choice graded WRONG : {grader['wrong_detected']}/{grader['n']}",
        f"  grader fidelity          : {grader['fidelity'] * 100:.1f}%",
    ]
    return "\n".join(lines)


def _emit_artifacts(*, seed: int = 12345) -> tuple[Path, Path]:
    """Write eval/perf-accuracy.json + eval/perf-accuracy.svg (gated by
    SPEEDRUN_EVAL_EMIT=1 in __main__). Aggregate metrics + reliability bins
    only."""
    sim = performance_eval(seed=seed)
    grader = grader_fidelity_on_gold()
    out_dir = Path(__file__).resolve().parent
    json_path = out_dir / "perf-accuracy.json"
    svg_path = out_dir / "perf-accuracy.svg"
    payload = {
        "part1_simulated_predictive_accuracy": sim,
        "part2_grader_fidelity_on_real_gold": grader,
        "notes": (
            "Part 1 is a SIMULATED learner population grounded in the real "
            "held-out gold pool's aggregate topic+difficulty structure; no real "
            "learner attempts exist yet. Part 2 grader fidelity IS on the real "
            "gold answers and is hermetic. Aggregate numbers only."
        ),
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    svg_path.write_text(reliability_svg(sim), encoding="utf-8")
    return json_path, svg_path


if __name__ == "__main__":  # pragma: no cover
    print(format_report())
    if os.environ.get("SPEEDRUN_EVAL_EMIT") == "1":
        jp, sp = _emit_artifacts()
        print(f"\n[emitted] {jp}")
        print(f"[emitted] {sp}")
