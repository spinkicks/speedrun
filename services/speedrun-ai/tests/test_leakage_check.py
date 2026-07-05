# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the §7e leakage-check runner (``eval/leakage_check.py``).

§7e (grader rubric): "a script that scans your training data and flags any test
item, or a near-copy of one, that slipped in. Run it and show the result is
clean." This runner loads the TRAINING/study corpus (seed declarative cards +
curated problem bank, and the vendored RAG passages) and scans every item
against the held-out gold set using the validated ``eval.leakage`` scanner,
reporting AGGREGATE counts only.

Hermetic + deterministic. The unit tests below use a small SYNTHETIC training +
gold corpus (no file I/O, no holdout read) to pin the scanner's behaviour; a
final aggregate-only test exercises the real runner and asserts it never
surfaces gold/near-copy text.
"""

from __future__ import annotations

from eval import leakage_check


# A tiny synthetic "held-out gold" set (stand-in test items — NOT the real
# holdout). Long enough that a copy shares a >13-word run.
_GOLD = [
    "Evaluate the limit of sine of three x divided by x as x approaches zero "
    "using the standard trigonometric limit and simplify the resulting value.",
    "A square matrix is invertible if and only if its determinant is nonzero, "
    "which follows directly from the properties of the inverse matrix.",
]


# ---------------------------------------------------------------------------
# scan() — the pure, injectable core (aggregate counts only)
# ---------------------------------------------------------------------------


def test_clean_training_reports_zero_leaks():
    training = [
        {"source": "seed_study", "text": "The capital of France is Paris and "
         "the Eiffel Tower is a famous landmark visited by many tourists."},
        {"source": "rag_corpus", "text": "Photosynthesis converts sunlight, "
         "water and carbon dioxide into glucose and oxygen inside chloroplasts."},
    ]
    result = leakage_check.scan(training, _GOLD)
    assert result["num_leaks"] == 0
    assert result["clean"] is True
    assert result["runnable"] is True
    assert result["num_training_items"] == 2
    assert result["num_gold_items"] == 2


def test_verbatim_copy_of_a_gold_item_is_flagged():
    # A training item that is an exact copy of a gold "test item" must leak.
    training = [{"source": "seed_study", "text": _GOLD[0]}]
    result = leakage_check.scan(training, _GOLD)
    assert result["num_leaks"] == 1
    assert result["clean"] is False
    assert result["by_source"]["seed_study"]["leaks"] == 1


def test_near_copy_of_a_gold_item_is_flagged():
    # Paraphrase / wrapper text around a long verbatim run must still leak.
    near = (
        "Reminder for students: a square matrix is invertible if and only if "
        "its determinant is nonzero, which follows directly from the properties "
        "of the inverse matrix (memorize this)."
    )
    training = [{"source": "rag_corpus", "text": near}]
    result = leakage_check.scan(training, _GOLD)
    assert result["num_leaks"] == 1
    assert result["clean"] is False


def test_leak_records_are_aggregate_safe_no_text():
    # Even when a leak IS found, the record must carry NO gold / near-copy text —
    # only source, index, which arm fired, and the cosine (holdout stays sealed).
    training = [{"source": "seed_study", "text": _GOLD[0]}]
    result = leakage_check.scan(training, _GOLD)
    assert result["leaks"], "expected a leak record"
    rec = result["leaks"][0]
    assert set(rec.keys()) == {
        "source",
        "training_index",
        "ngram_overlap",
        "max_cosine",
    }
    # No record value may be one of the gold/near-copy strings.
    for value in rec.values():
        assert value not in _GOLD


def test_empty_gold_is_not_runnable_and_not_clean():
    # If the gold set is missing/empty the check CANNOT run — it must fail
    # closed (never report a false "clean"), mirroring the gate's fail-closed.
    training = [{"source": "seed_study", "text": "anything at all here friend"}]
    result = leakage_check.scan(training, [])
    assert result["runnable"] is False
    assert result["clean"] is False
    assert result["num_gold_items"] == 0


def test_empty_training_is_not_runnable():
    result = leakage_check.scan([], _GOLD)
    assert result["runnable"] is False
    assert result["clean"] is False
    assert result["num_training_items"] == 0


def test_thresholds_are_recorded_and_respected():
    # An impossibly high cosine threshold with no verbatim run → no leak.
    training = [{"source": "seed_study", "text": "matrix determinant invertible"}]
    result = leakage_check.scan(training, _GOLD, ngram=13, sim_threshold=0.999)
    assert result["ngram"] == 13
    assert result["sim_threshold"] == 0.999
    assert result["num_leaks"] == 0


def test_per_source_counts_partition_the_scan():
    training = [
        {"source": "seed_study", "text": "unrelated harmless sentence one two "
         "three four five six seven eight nine ten eleven twelve."},
        {"source": "rag_corpus", "text": "another unrelated sentence alpha beta "
         "gamma delta epsilon zeta eta theta iota kappa lambda mu."},
        {"source": "seed_study", "text": _GOLD[0]},  # a leak
    ]
    result = leakage_check.scan(training, _GOLD)
    total_items = sum(b["num_items"] for b in result["by_source"].values())
    total_leaks = sum(b["leaks"] for b in result["by_source"].values())
    assert total_items == result["num_training_items"] == 3
    assert total_leaks == result["num_leaks"] == 1
    assert result["by_source"]["seed_study"]["num_items"] == 2


def test_scan_is_deterministic():
    training = [{"source": "seed_study", "text": _GOLD[0]}]
    a = leakage_check.scan(training, _GOLD)
    b = leakage_check.scan(training, _GOLD)
    assert a == b


# ---------------------------------------------------------------------------
# format_report() + emit_artifact() — aggregate-only presentation
# ---------------------------------------------------------------------------


def test_report_summary_line_is_present_when_clean():
    training = [{"source": "seed_study", "text": "wholly unrelated content "
                 "about weather patterns over the northern pacific ocean this year."}]
    result = leakage_check.scan(training, _GOLD)
    text = leakage_check.format_report(result)
    assert "LEAKAGE: 0 found" in text
    assert "clean" in text.lower()
    # The report must not echo any gold text.
    for gold in _GOLD:
        assert gold not in text


def test_emit_artifact_writes_aggregate_json(tmp_path):
    training = [{"source": "seed_study", "text": "unrelated safe filler text "
                 "with plenty of ordinary words to avoid any overlap at all."}]
    result = leakage_check.scan(training, _GOLD)
    out = tmp_path / "leakage-check.json"
    written = leakage_check.emit_artifact(result, out)
    assert written == out and out.is_file()
    import json

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["num_leaks"] == 0
    assert payload["clean"] is True
    assert payload["num_gold_items"] == 2
    # The serialized artifact must carry NO gold text anywhere.
    blob = out.read_text(encoding="utf-8")
    for gold in _GOLD:
        assert gold not in blob


# ---------------------------------------------------------------------------
# Real runner — reads the actual training corpus + gold at runtime, AGGREGATE
# only (mirrors tests/test_gate.py: the harness may consume gold for counts).
# ---------------------------------------------------------------------------


_AGG_SAFE_LEAK_KEYS = {"source", "training_index", "ngram_overlap", "max_cosine"}


def test_real_runner_is_aggregate_only_and_runnable():
    result = leakage_check.run()
    # Structure / aggregate keys only — never raw gold or near-copy text.
    forbidden = {"question", "correct_answer", "worked_solution", "choices"}
    assert forbidden.isdisjoint(set(result.keys()))
    assert isinstance(result["num_training_items"], int)
    assert isinstance(result["num_gold_items"], int)
    assert isinstance(result["num_leaks"], int)
    # With the real holdout + seed present this is a runnable check over the
    # known 50-item gold set and a non-empty training corpus (seed + RAG corpus).
    assert result["num_gold_items"] == 50
    assert result["num_training_items"] > 0
    assert result["runnable"] is True
    assert {"seed_study", "rag_corpus"} <= set(result["by_source"].keys())
    # Any leak record (primary OR strict) stays aggregate-safe (no text fields).
    strict = result["strict_full_content"]
    for rec in list(result["leaks"]) + list(strict["leaks"]):
        assert set(rec.keys()) == _AGG_SAFE_LEAK_KEYS


def test_real_training_data_is_clean_no_leaks():
    """§7e headline: the real training/study data contains NO held-out gold
    TEST ITEM (question) or near-copy. If this ever fails, a test question
    slipped in — investigate and report it; do NOT weaken this assertion."""
    result = leakage_check.run()
    assert result["num_leaks"] == 0
    assert result["clean"] is True


def test_no_paraphrase_near_copies_in_either_surface():
    """The TF-IDF cosine (near-duplicate / paraphrase) arm must find ZERO
    near-copies — on BOTH the test-item-identity surface and the stricter
    full-content surface. This is the robust invariant: nothing in the training
    data is a paraphrase of a held-out item."""
    result = leakage_check.run()
    assert result["cosine_near_copies"] == 0
    assert result["strict_full_content"]["cosine_near_copies"] == 0


def test_strict_full_content_flags_are_verbatim_derivation_only():
    """Transparency pin (documents the known state): the STRICT full-content
    surface (which also compares gold worked-solution derivations) may surface a
    small number of shared VERBATIM derivation steps on canonical examples. Any
    such flag must be n-gram (verbatim) — never a cosine paraphrase — so it is a
    shared standard computation, not a reproduced test question."""
    strict = leakage_check.run()["strict_full_content"]
    assert strict["cosine_near_copies"] == 0
    for rec in strict["leaks"]:
        assert rec["ngram_overlap"] is True
        assert rec["max_cosine"] < leakage_check.DEFAULT_SIM_THRESHOLD
