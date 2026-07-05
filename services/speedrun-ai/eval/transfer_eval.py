# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
§7d paraphrase / transfer harness — the "gap meter" (Performance != Memory).

Thesis (spec §7d): declarative flashcard *recall* is high while *transfer* —
solving a reworded, exam-style APPLICATION of the same concept under time — is
lower. The engine surfaces this as a per-topic gap Δ = recall − transfer. This
module demonstrates and QUANTIFIES that gap honestly.

What is REAL here
-----------------
* The declarative recall side is the SHIPPED seed deck: the hand-authored
  ``cards_*`` YAML in the primary anki checkout (``repos/anki/speedrun/seed/``).
  We read only the declarative ``cards_*`` files (the recall side) — NEVER the
  ``problems_*`` MCQs (that is the shipped exam deck) and NEVER the held-out gold
  set (``eval/holdout/`` is not touched by this module at all).
* The transfer side is an INDEPENDENTLY authored set (``eval/transfer_items.jsonl``):
  two exam-style application questions per seed card, written from the concept —
  never copied from the card front, never derived from the holdout. Each item
  carries a categorical ``difficulty`` (easy/medium/hard) reflecting its
  application load, and (where the answer is symbolic) a ``sympy_check``
  reference form.
* :func:`verify_sympy_items` is a REAL, non-simulated correctness check: it runs
  the project's own :func:`verify.sympy_verifier.answers_equivalent` to confirm
  each authored ``correct_answer`` equals its ``sympy_check`` reference form.

What is SIMULATED here (and clearly labeled)
--------------------------------------------
There are NO real learner attempts, so :func:`transfer_eval` reports the gap on a
seeded SIMULATED learner population — the same modelling approach as
``eval/perf_eval.py``. Every learner draws a per-topic latent ability
``θ ~ Normal(μ_ability, σ)``. Outcomes are Bernoulli draws from a 1-parameter
(Rasch/IRT) model ``logistic(θ − b_item)`` where the item difficulty ``b`` is:

* RECALL items (declarative cards): a low, near-constant difficulty — you have
  either memorized the fact or not, so recall is high. ``b_recall`` is small.
* TRANSFER items: the difficulty comes from the AUTHORED transfer set's own
  categorical difficulty {easy, medium, hard} → a POSITIVE logit offset on top
  of the concept's recall difficulty (application is strictly harder than
  restating the fact). This is the honest grounding: the gap is driven by the
  structural difference between "state the rule" and "use the rule under time",
  measured from the authored item mix, not from any real learner data.

The point is to demonstrate + quantify the gap the engine's §7d gap-meter
surfaces, honestly — NOT to claim a real learner result. The population and its
numbers are SIMULATED and labeled as such everywhere.
"""

from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths.
# ---------------------------------------------------------------------------
# services/speedrun-ai/eval/transfer_eval.py
#   -> services/speedrun-ai/eval  (this dir)
#   -> repo root is three parents up (same resolution as perf_eval.py/gate.py).
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parents[2]

# The declarative seed deck lives in the PRIMARY anki checkout (cross-repo,
# read-only). The umbrella repo root's sibling is the primary Speedrun checkout;
# but the canonical, documented location is repos/anki/speedrun/seed under the
# primary checkout. We resolve it relative to the primary checkout, allowing an
# override for hermetic testing.
_DEFAULT_SEED_DIR = Path(
    r"C:/Users/davir/Ultra/Alpha/Speedrun/repos/anki/speedrun/seed"
)

# Only the DECLARATIVE recall cards — never problems_* (exam deck) or holdout.
SEED_CARD_FILES: tuple[str, ...] = ("cards_calc.yaml", "cards_linear_algebra.yaml")

# Deterministic id prefix per seed file (stable across runs; matches the order
# build_seed_deck.load_notes() concatenates them).
_FILE_PREFIX = {"cards_calc.yaml": "calc", "cards_linear_algebra.yaml": "la"}

TRANSFER_ITEMS_PATH = _THIS_DIR / "transfer_items.jsonl"

# IRT difficulty (logit b) of the AUTHORED transfer items, by categorical hint.
# Positive => harder than recall. Grounded in the authored item mix.
_TRANSFER_DIFFICULTY_OFFSET = {"easy": 0.5, "medium": 1.2, "hard": 2.0}

# Recall (declarative) item difficulty: low and near-constant — a memorized fact
# is easy to restate. This is the "high-retention" recall assumption, labeled.
_RECALL_DIFFICULTY = -1.5

# Latent learner ability distribution (per topic). A capable-but-imperfect
# population: mean slightly positive so recall is high without being trivially 1.
_ABILITY_MEAN = 1.0
_ABILITY_STD = 0.8


def _seed_dir(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("SPEEDRUN_SEED_DIR")
    return Path(env) if env else _DEFAULT_SEED_DIR


# ---------------------------------------------------------------------------
# Loading — the declarative recall side (read-only cross-repo).
# ---------------------------------------------------------------------------


def load_seed_cards(seed_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """Load the shipped declarative GRE-math seed cards (the RECALL side).

    Reads only the ``cards_*`` YAML (never problems_* or holdout). Each returned
    card gets a deterministic, stable ``source_card_id`` (``<prefix>-<index>``)
    matching the file's own order, plus its ``front`` and ``topic``.
    """
    directory = _seed_dir(seed_dir)
    cards: list[dict[str, Any]] = []
    for name in SEED_CARD_FILES:
        prefix = _FILE_PREFIX[name]
        data = yaml.safe_load((directory / name).read_text(encoding="utf-8"))
        for idx, note in enumerate(data):
            cards.append(
                {
                    "source_card_id": f"{prefix}-{idx:02d}",
                    "front": str(note["front"]),
                    "topic": str(note["topic"]),
                }
            )
    return cards


def load_transfer_items(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load the INDEPENDENTLY authored transfer items (the APPLICATION side)."""
    items_path = Path(path) if path is not None else TRANSFER_ITEMS_PATH
    items: list[dict[str, Any]] = []
    with items_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ---------------------------------------------------------------------------
# REAL check — SymPy verification of the authored transfer answers.
# ---------------------------------------------------------------------------


def verify_sympy_items(path: Path | str | None = None) -> dict[str, Any]:
    """Verify every transfer item that carries a ``sympy_check`` reference form.

    REAL (not simulated): uses the project's own
    :func:`verify.sympy_verifier.answers_equivalent` to confirm the authored
    ``correct_answer`` denotes the SAME math answer as the ``sympy_check`` form.
    Returns AGGREGATE counts only::

        {"n_items", "n_checkable", "n_verified", "all_verified", "failures"}

    ``failures`` lists only the ``source_card_id`` + item index of any mismatch
    (no answer text), so a broken authored item is discoverable without leaking
    content into logs.
    """
    from verify.sympy_verifier import answers_equivalent

    items = load_transfer_items(path)
    n_checkable = 0
    n_verified = 0
    failures: list[str] = []
    per_card_index: dict[str, int] = {}
    for it in items:
        cid = it["source_card_id"]
        k = per_card_index.get(cid, 0)
        per_card_index[cid] = k + 1
        check = it.get("sympy_check")
        if not check:
            continue
        n_checkable += 1
        # Declare the extra free symbols our authored answers use beyond the
        # verifier defaults (x,y,z,t,n,k). Deliberately NOT "E" or "lambda":
        # "E" must stay SymPy's Euler number e (our answers use exp(1)/E for e),
        # and no authored answer uses a free symbol named lambda.
        extra = ["epsilon", "m", "a", "b", "c", "d"]
        if answers_equivalent(str(it["correct_answer"]), str(check), extra_symbols=extra):
            n_verified += 1
        else:
            failures.append(f"{cid}#{k}")
    return {
        "n_items": len(items),
        "n_checkable": n_checkable,
        "n_verified": n_verified,
        "all_verified": (n_checkable > 0 and n_verified == n_checkable),
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# SIMULATED learner population — the gap Δ = recall − transfer.
# ---------------------------------------------------------------------------


def _logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list (q in [0,1])."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def transfer_eval(
    *,
    seed: int = 12345,
    n_learners: int = 400,
    seed_dir: Path | str | None = None,
    items_path: Path | str | None = None,
) -> dict[str, Any]:
    """Quantify the §7d gap on a SIMULATED learner population.

    Deterministic given ``seed``. Returns AGGREGATE metrics only:

    * ``mean_recall`` / ``mean_transfer`` — population mean accuracy on the
      declarative recall cards vs the authored transfer items.
    * ``mean_gap`` = ``mean_recall - mean_transfer`` (the headline §7d Δ), plus
      the per-learner gap distribution (``gap_std``, ``gap_p10/p50/p90``).
    * ``per_topic`` — ``{topic: {recall, transfer, gap, n_cards, n_items}}``.

    Model (see module docstring; SIMULATED, labeled): each learner draws a
    per-topic ability θ ~ Normal(μ, σ). RECALL of a declarative card succeeds
    with P = logistic(θ − b_recall) (low b → high recall). TRANSFER of an
    authored item succeeds with P = logistic(θ − (b_recall + offset(difficulty)))
    where the offset is the authored item's categorical difficulty. The gap is
    driven purely by the authored recall-vs-application difficulty split.
    """
    rng = random.Random(seed)
    cards = load_seed_cards(seed_dir)
    items = load_transfer_items(items_path)

    topics = sorted({c["topic"] for c in cards})
    cards_by_topic: dict[str, list[dict]] = {}
    for c in cards:
        cards_by_topic.setdefault(c["topic"], []).append(c)
    items_by_topic: dict[str, list[dict]] = {}
    for it in items:
        items_by_topic.setdefault(it["topic"], []).append(it)

    # Per-topic accumulators (sum of per-learner topic means / count).
    topic_recall_sum: dict[str, float] = {t: 0.0 for t in topics}
    topic_transfer_sum: dict[str, float] = {t: 0.0 for t in topics}
    topic_learner_count: dict[str, int] = {t: 0 for t in topics}

    per_learner_gap: list[float] = []
    overall_recall_sum = 0.0
    overall_transfer_sum = 0.0
    overall_count = 0

    for _ in range(n_learners):
        learner_recall_vals: list[float] = []
        learner_transfer_vals: list[float] = []
        for topic in topics:
            topic_cards = cards_by_topic.get(topic, [])
            topic_items = items_by_topic.get(topic, [])
            if not topic_cards or not topic_items:
                continue
            theta = rng.gauss(_ABILITY_MEAN, _ABILITY_STD)

            # RECALL: one Bernoulli attempt per declarative card in the topic.
            recall_correct = 0
            for _card in topic_cards:
                p = _logistic(theta - _RECALL_DIFFICULTY)
                recall_correct += 1 if rng.random() < p else 0
            recall_acc = recall_correct / len(topic_cards)

            # TRANSFER: one Bernoulli attempt per authored item in the topic,
            # with the item's authored difficulty raising b above recall.
            transfer_correct = 0
            for it in topic_items:
                offset = _TRANSFER_DIFFICULTY_OFFSET.get(
                    str(it.get("difficulty", "medium")).strip().lower(), 1.2
                )
                b = _RECALL_DIFFICULTY + offset
                p = _logistic(theta - b)
                transfer_correct += 1 if rng.random() < p else 0
            transfer_acc = transfer_correct / len(topic_items)

            topic_recall_sum[topic] += recall_acc
            topic_transfer_sum[topic] += transfer_acc
            topic_learner_count[topic] += 1
            learner_recall_vals.append(recall_acc)
            learner_transfer_vals.append(transfer_acc)

        if learner_recall_vals:
            lr = sum(learner_recall_vals) / len(learner_recall_vals)
            lt = sum(learner_transfer_vals) / len(learner_transfer_vals)
            per_learner_gap.append(lr - lt)
            overall_recall_sum += lr
            overall_transfer_sum += lt
            overall_count += 1

    mean_recall = overall_recall_sum / overall_count if overall_count else 0.0
    mean_transfer = overall_transfer_sum / overall_count if overall_count else 0.0
    mean_gap = mean_recall - mean_transfer

    gaps_sorted = sorted(per_learner_gap)
    n_g = len(gaps_sorted)
    gap_mean_pl = sum(gaps_sorted) / n_g if n_g else 0.0
    gap_var = (
        sum((g - gap_mean_pl) ** 2 for g in gaps_sorted) / n_g if n_g else 0.0
    )
    gap_std = math.sqrt(gap_var)

    per_topic: dict[str, dict[str, Any]] = {}
    for topic in topics:
        n = topic_learner_count[topic]
        if n == 0:
            continue
        r = topic_recall_sum[topic] / n
        t = topic_transfer_sum[topic] / n
        per_topic[topic] = {
            "recall": r,
            "transfer": t,
            "gap": r - t,
            "n_cards": len(cards_by_topic.get(topic, [])),
            "n_items": len(items_by_topic.get(topic, [])),
        }

    return {
        "simulated": True,
        "seed": seed,
        "n_learners": n_learners,
        "n_cards": len(cards),
        "n_transfer_items": len(items),
        "n_topics": len(per_topic),
        "recall_difficulty_b": _RECALL_DIFFICULTY,
        "transfer_difficulty_offsets": dict(_TRANSFER_DIFFICULTY_OFFSET),
        "ability_mean": _ABILITY_MEAN,
        "ability_std": _ABILITY_STD,
        "mean_recall": mean_recall,
        "mean_transfer": mean_transfer,
        "mean_gap": mean_gap,
        "gap_std": gap_std,
        "gap_p10": _percentile(gaps_sorted, 0.10),
        "gap_p50": _percentile(gaps_sorted, 0.50),
        "gap_p90": _percentile(gaps_sorted, 0.90),
        "per_topic": per_topic,
    }


# ---------------------------------------------------------------------------
# SVG — self-contained, aggregate-only, LABELED simulated.
# ---------------------------------------------------------------------------


def transfer_gap_svg(result: dict[str, Any]) -> str:
    """Return a self-contained SVG bar chart of per-topic recall vs transfer
    (with the gap), LABELED as a SIMULATED learner population. Aggregate numbers
    only; no external refs, no scripts."""
    per_topic = result.get("per_topic", {})
    topics = list(per_topic.keys())
    W = 720
    row_h = 34
    top = 70
    H = top + row_h * max(1, len(topics)) + 40
    left = 250  # room for topic labels
    bar_w = W - left - 90

    def short(t: str) -> str:
        # Trim the longest common prefixes for readability; aggregate label only.
        return t.replace("linear_algebra::", "la::").replace("single_var::", "")

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="sans-serif">'
    )
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(
        f'<text x="{W / 2}" y="24" text-anchor="middle" font-size="15" '
        f'font-weight="bold">&#167;7d Performance vs Memory gap '
        f'(SIMULATED learners)</text>'
    )
    parts.append(
        f'<text x="{W / 2}" y="44" text-anchor="middle" font-size="11" '
        f'fill="#555">recall (green) vs transfer (orange) per topic &#183; '
        f'mean gap &#916;={result.get("mean_gap", 0):.3f} &#183; '
        f'N_cards={result.get("n_cards", 0)} &#183; '
        f'N_transfer={result.get("n_transfer_items", 0)} &#183; '
        f'learners={result.get("n_learners", 0)}</text>'
    )
    for i, topic in enumerate(topics):
        row = per_topic[topic]
        y = top + i * row_h
        parts.append(
            f'<text x="{left - 8}" y="{y + 13}" text-anchor="end" '
            f'font-size="10" fill="#333">{short(topic)}</text>'
        )
        # recall bar (green)
        rw = bar_w * float(row["recall"])
        parts.append(
            f'<rect x="{left}" y="{y}" width="{rw:.1f}" height="10" '
            f'fill="#2e7d32" fill-opacity="0.85"/>'
        )
        # transfer bar (orange), directly below
        tw = bar_w * float(row["transfer"])
        parts.append(
            f'<rect x="{left}" y="{y + 12}" width="{tw:.1f}" height="10" '
            f'fill="#e07b1a" fill-opacity="0.9"/>'
        )
        parts.append(
            f'<text x="{left + bar_w + 6}" y="{y + 17}" font-size="10" '
            f'fill="#333">&#916;={float(row["gap"]):.2f}</text>'
        )
    # axis note
    parts.append(
        f'<text x="{left}" y="{H - 14}" font-size="10" fill="#777">'
        f'bar length = mean accuracy in [0,1]; SIMULATED (no real learner '
        f'attempts) &#183; item difficulty from the authored transfer set</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Standalone report (aggregate numbers/labels only).
# ---------------------------------------------------------------------------


def format_report(*, seed: int = 12345) -> str:
    res = transfer_eval(seed=seed)
    ver = verify_sympy_items()
    lines = [
        "§7d Performance vs Memory gap meter — aggregate results",
        "=" * 68,
        "",
        "SIMULATED learner population (no real learner attempts exist yet).",
        "Recall side = the SHIPPED declarative seed deck (cards_*).",
        "Transfer side = an INDEPENDENTLY authored exam-style application set;",
        "item difficulty is taken from that authored set's own easy/medium/hard",
        "mix. The gap is what the engine's §7d gap-meter surfaces, quantified",
        "HONESTLY on a seeded simulation — NOT a real learner result.",
        "-" * 68,
        f"  seed cards (recall, N)      : {res['n_cards']}",
        f"  authored transfer items (N) : {res['n_transfer_items']} "
        f"(2 per card)",
        f"  simulated learners          : {res['n_learners']}",
        f"  recall difficulty b         : {res['recall_difficulty_b']}",
        f"  transfer offsets            : {res['transfer_difficulty_offsets']}",
        f"  ability ~ Normal(mu={res['ability_mean']}, sigma={res['ability_std']})",
        "",
        f"  mean RECALL accuracy        : {res['mean_recall']:.4f}",
        f"  mean TRANSFER accuracy      : {res['mean_transfer']:.4f}",
        f"  mean GAP  Δ = recall-transfer: {res['mean_gap']:.4f}",
        f"  gap spread (std)            : {res['gap_std']:.4f}",
        f"  gap p10 / p50 / p90         : {res['gap_p10']:.4f} / "
        f"{res['gap_p50']:.4f} / {res['gap_p90']:.4f}",
        "",
        "  per-topic gap (recall -> transfer = Δ):",
    ]
    for topic in sorted(res["per_topic"]):
        row = res["per_topic"][topic]
        lines.append(
            f"    {topic:<40s} {row['recall']:.3f} -> {row['transfer']:.3f} "
            f"= Δ {row['gap']:.3f}  (cards={row['n_cards']}, "
            f"items={row['n_items']})"
        )
    lines += [
        "",
        "SymPy verification of authored transfer answers (REAL, not simulated):",
        "-" * 68,
        f"  machine-checkable items     : {ver['n_checkable']}/{ver['n_items']}",
        f"  verified equal to reference : {ver['n_verified']}/{ver['n_checkable']}",
        f"  all verified                : {ver['all_verified']}",
    ]
    if ver["failures"]:
        lines.append(f"  FAILURES (id#idx)           : {ver['failures']}")
    return "\n".join(lines)


def _emit_artifacts(*, seed: int = 12345) -> tuple[Path, Path]:
    """Write eval/transfer-gap.json + eval/transfer-gap.svg (gated by
    SPEEDRUN_EVAL_EMIT=1 in __main__). Aggregate metrics only."""
    res = transfer_eval(seed=seed)
    ver = verify_sympy_items()
    json_path = _THIS_DIR / "transfer-gap.json"
    svg_path = _THIS_DIR / "transfer-gap.svg"
    payload = {
        "gap_simulated": res,
        "sympy_verification_real": ver,
        "notes": (
            "The gap Δ = recall − transfer is measured on a SIMULATED learner "
            "population (no real learner attempts exist yet). The recall side is "
            "the shipped declarative seed deck; the transfer side is an "
            "independently authored exam-style application set whose easy/medium/"
            "hard difficulty grounds the simulation. The sympy_verification_real "
            "block IS real: it confirms the authored transfer answers are correct "
            "via verify.sympy_verifier. Aggregate numbers only."
        ),
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    svg_path.write_text(transfer_gap_svg(res), encoding="utf-8")
    return json_path, svg_path


if __name__ == "__main__":  # pragma: no cover
    print(format_report())
    if os.environ.get("SPEEDRUN_EVAL_EMIT") == "1":
        jp, sp = _emit_artifacts()
        print(f"\n[emitted] {jp}")
        print(f"[emitted] {sp}")
