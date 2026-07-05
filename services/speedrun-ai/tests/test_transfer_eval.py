# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the §7d paraphrase/transfer harness (``eval/transfer_eval.py``).

The §7d "gap meter" claim: declarative flashcard RECALL is high while TRANSFER
(solving a reworded, exam-style application of the same concept) is lower, so
Performance != Memory. This proves + quantifies that gap HONESTLY:

* Dataset integrity — the authored transfer set has 2 exam-style items per seed
  card, each with a non-empty stem + correct_answer + topic, and NO transfer
  stem is a substring-copy of its source card front (authored INDEPENDENTLY from
  the concept, never derived from the card front or the held-out gold set).
* Harness metrics — on a seeded SIMULATED learner population the gap
  Δ = recall - transfer_accuracy is > 0 (the expected direction), every metric
  is finite/in-range, and two runs with the same seed are identical.
* SymPy-checkable answers — every transfer item that carries a ``sympy_check``
  really verifies with the project's own ``verify.sympy_verifier``. This part is
  REAL (not simulated): it proves the authored transfer answers are correct.

Hermetic: no network, seeded RNG. The simulated learner population is LABELED
simulated everywhere; item difficulty is grounded in the authored transfer set's
own structure (recall vs application), not in any real learner data.
"""

from __future__ import annotations

import pytest

from eval.transfer_eval import (
    SEED_CARD_FILES,
    load_seed_cards,
    load_transfer_items,
    transfer_eval,
    transfer_gap_svg,
    verify_sympy_items,
)

# ---------------------------------------------------------------------------
# 1. Seed cards load (the declarative recall side; read-only cross-repo)
# ---------------------------------------------------------------------------


def test_seed_cards_load():
    cards = load_seed_cards()
    # The shipped declarative GRE-math seed deck (~30 cards).
    assert len(cards) >= 30
    ids = [c["source_card_id"] for c in cards]
    # Deterministic, unique, stable ids.
    assert len(set(ids)) == len(ids)
    for c in cards:
        assert c["source_card_id"]
        assert c["front"].strip()
        assert c["topic"].strip()


def test_seed_card_files_are_declarative_only():
    # We read ONLY the declarative `cards_*` seed files (the recall side), never
    # the `problems_*` MCQs (those are the shipped exam deck) and never holdout.
    for name in SEED_CARD_FILES:
        assert name.startswith("cards_")
        assert "holdout" not in name


# ---------------------------------------------------------------------------
# 2. Dataset integrity — 2 authored transfer items per card, independent
# ---------------------------------------------------------------------------


def test_two_transfer_items_per_card():
    cards = load_seed_cards()
    items = load_transfer_items()
    card_ids = {c["source_card_id"] for c in cards}
    # Exactly two transfer items per seed card.
    assert len(items) == 2 * len(cards)
    from collections import Counter

    per_card = Counter(it["source_card_id"] for it in items)
    assert set(per_card) == card_ids
    assert all(v == 2 for v in per_card.values())


def test_every_item_has_required_fields():
    for it in load_transfer_items():
        assert it["stem"].strip()
        assert str(it["correct_answer"]).strip()
        assert it["topic"].strip()
        assert it["source_card_id"].strip()


def test_transfer_item_topics_match_source_card():
    cards = {c["source_card_id"]: c for c in load_seed_cards()}
    for it in load_transfer_items():
        # Every item points at a real seed card and shares its topic.
        assert it["source_card_id"] in cards
        assert it["topic"] == cards[it["source_card_id"]]["topic"]


def test_no_stem_is_substring_copy_of_source_front():
    """Independence sanity: a transfer item must be an APPLICATION reworded from
    the concept, never a substring-copy of the source card front (which would be
    plain recall, not transfer)."""
    cards = {c["source_card_id"]: c for c in load_seed_cards()}

    def norm(s: str) -> str:
        return " ".join(str(s or "").lower().split())

    for it in load_transfer_items():
        front = norm(cards[it["source_card_id"]]["front"])
        stem = norm(it["stem"])
        assert stem, "empty stem"
        # Neither direction may be a substring of the other.
        assert stem not in front
        assert front not in stem


# ---------------------------------------------------------------------------
# 3. SymPy-checkable transfer answers actually verify (REAL, not simulated)
# ---------------------------------------------------------------------------


def test_sympy_checkable_items_verify():
    result = verify_sympy_items()
    # There is a meaningful number of machine-checkable items.
    assert result["n_checkable"] >= 10
    # Every checkable item's authored answer verifies against its reference form.
    assert result["n_verified"] == result["n_checkable"]
    assert result["all_verified"] is True


# ---------------------------------------------------------------------------
# 4. Harness metrics — the gap Δ is positive (transfer < recall) & in range
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def result():
    return transfer_eval(seed=12345)


def test_transfer_eval_is_deterministic():
    a = transfer_eval(seed=777)
    b = transfer_eval(seed=777)
    assert a["mean_recall"] == b["mean_recall"]
    assert a["mean_transfer"] == b["mean_transfer"]
    assert a["mean_gap"] == b["mean_gap"]
    assert a["per_topic"] == b["per_topic"]


def test_gap_is_positive_and_labeled_simulated(result):
    # Clearly labeled as a simulated learner population.
    assert result["simulated"] is True
    # The headline §7d claim: recall exceeds transfer, so the gap is positive.
    assert result["mean_recall"] > result["mean_transfer"]
    assert result["mean_gap"] > 0.0
    # mean_gap is exactly recall - transfer.
    assert result["mean_gap"] == pytest.approx(
        result["mean_recall"] - result["mean_transfer"]
    )


def test_all_metrics_finite_and_in_range(result):
    for key in ("mean_recall", "mean_transfer", "mean_gap"):
        v = result[key]
        assert isinstance(v, float)
        assert v == v  # not NaN
        assert -1.0 <= v <= 1.0
    assert 0.0 <= result["mean_recall"] <= 1.0
    assert 0.0 <= result["mean_transfer"] <= 1.0
    # Distribution of the gap is reported.
    assert 0.0 <= result["gap_p10"] <= result["gap_p50"] <= result["gap_p90"] <= 1.0
    assert result["gap_std"] >= 0.0
    # Grounded in the real seed deck + authored transfer set.
    assert result["n_cards"] >= 30
    assert result["n_transfer_items"] == 2 * result["n_cards"]
    assert result["n_learners"] >= 100


def test_per_topic_gaps_present_and_mostly_positive(result):
    per_topic = result["per_topic"]
    assert isinstance(per_topic, dict) and per_topic
    for topic, row in per_topic.items():
        assert 0.0 <= row["recall"] <= 1.0
        assert 0.0 <= row["transfer"] <= 1.0
        assert row["gap"] == pytest.approx(row["recall"] - row["transfer"])
        assert row["n_cards"] >= 1
    # Every topic shows the gap in the expected direction (recall >= transfer).
    assert all(row["gap"] > 0.0 for row in per_topic.values())


# ---------------------------------------------------------------------------
# 5. Report / SVG are self-contained and LABEL the simulation
# ---------------------------------------------------------------------------


def test_svg_is_self_contained_and_labeled(result):
    svg = transfer_gap_svg(result)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    # Self-contained: no external references, no scripts.
    assert "http://" not in svg.replace("http://www.w3.org", "")  # allow xmlns
    assert "<script" not in svg.lower()
    # Must LABEL the simulated population.
    assert "SIMULATED" in svg
