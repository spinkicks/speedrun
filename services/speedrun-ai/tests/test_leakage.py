# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the §7f leakage scanner (``eval/leakage.py``).

Hermetic and deterministic. The scanner flags a candidate that overlaps the
study content by a long verbatim n-gram OR by high TF-IDF cosine similarity.
"""

from __future__ import annotations

from eval.leakage import leaks, load_study_texts

# A small, self-contained study corpus for the unit tests (no file I/O).
STUDY = [
    "The derivative of x squared is two x by the power rule for polynomials.",
    "By the Fundamental Theorem of Calculus the definite integral equals "
    "F of b minus F of a where F prime equals f.",
    "A square matrix is invertible if and only if its determinant is nonzero.",
]


# ---------------------------------------------------------------------------
# n-gram (verbatim) leakage
# ---------------------------------------------------------------------------


def test_near_duplicate_of_study_card_leaks():
    # A candidate that copies a long run of words from a study card must leak.
    candidate = (
        "Recall: the derivative of x squared is two x by the power rule for "
        "polynomials, which students should memorize."
    )
    assert leaks(candidate, STUDY) is True


def test_exact_study_card_leaks():
    assert leaks(STUDY[0], STUDY) is True


def test_unrelated_string_does_not_leak():
    candidate = (
        "The capital of France is Paris and the Eiffel Tower is a famous "
        "landmark visited by many tourists every single year."
    )
    assert leaks(candidate, STUDY) is False


def test_short_shared_phrase_does_not_leak_on_ngram():
    # Only a few words shared (< 13-gram) and topically different wording:
    # must not trip the verbatim n-gram rule (similarity may still be low).
    candidate = "The power rule is one differentiation technique."
    assert leaks(candidate, STUDY, ngram=13, sim_threshold=0.95) is False


# ---------------------------------------------------------------------------
# TF-IDF cosine similarity leakage
# ---------------------------------------------------------------------------


def test_paraphrase_high_similarity_leaks():
    # Heavy lexical overlap but not a 13-gram run → caught by the cosine arm.
    candidate = (
        "Determinant nonzero means the square matrix is invertible; a square "
        "matrix invertible determinant nonzero if and only if."
    )
    assert leaks(candidate, STUDY, ngram=13, sim_threshold=0.5) is True


def test_similarity_threshold_is_respected():
    # With an impossibly high threshold and no verbatim run, nothing leaks.
    candidate = "matrix determinant invertible"
    assert leaks(candidate, STUDY, ngram=13, sim_threshold=0.999) is False


# ---------------------------------------------------------------------------
# determinism + edge cases
# ---------------------------------------------------------------------------


def test_deterministic():
    candidate = "the derivative of x squared is two x by the power rule for polynomials"
    first = leaks(candidate, STUDY)
    second = leaks(candidate, STUDY)
    assert first == second is True


def test_empty_candidate_does_not_leak():
    assert leaks("", STUDY) is False


def test_empty_corpus_does_not_leak():
    assert leaks("anything at all here", []) is False


# ---------------------------------------------------------------------------
# study-text loader (reads the real seed YAML; path configurable)
# ---------------------------------------------------------------------------


def test_load_study_texts_returns_nonempty_or_empty_gracefully():
    # If the seed path is reachable, we get study strings; if not, an empty
    # list (documented, configurable) — never an exception.
    texts = load_study_texts()
    assert isinstance(texts, list)
    for t in texts:
        assert isinstance(t, str)
