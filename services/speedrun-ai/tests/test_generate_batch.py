# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for POST /generate_batch — the desktop "Generate practice" endpoint.

SAFETY-CRITICAL CONTRACT
------------------------
The batch endpoint is a THIN wrapper over the single-problem generation graph.
It must ONLY ever return VERIFIED, grounded, gold-gated problems: every abstain
/ unverified attempt is DROPPED, and an uncovered topic fails CLOSED (no
proposal). It must never weaken any gate.

Hermetic: no OpenAI client, no RAG index, no network. Heavy collaborators are
stubbed exactly like ``test_app.py`` / ``test_graph.py`` — the covered-topic
path stubs ``generate_problem`` (the app's wrapper over the graph); the
uncovered path drives the REAL ``generate_problem``/``run_generation`` fail-closed
guard with a spy proposer to prove the proposer is never called.
"""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

COVERED_TOPIC = "calc::limits"
UNCOVERED_TOPIC = "differential equations by separation of variables"


def _enabled_app(monkeypatch):
    """Reload the app with the kill-switch ENABLED (flag + fake key)."""
    monkeypatch.setenv("SPEEDRUN_AI_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)
    return app_module


def _emit(correct: str, choices: list[str]) -> dict:
    """A graph EMIT result (verified problem) with the given correct/choices."""
    return {
        "status": "emit",
        "problem": {
            "stem": "Evaluate the limit.",
            "correct": correct,
            "choices": choices,
            "distractors": [c for c in choices if c != correct],
            "worked_solution": "Apply the limit laws.",
            "citation": "GRE Math Review, §Limits",
            "topic": COVERED_TOPIC,
            "technique": "",
        },
        "abstain_reason": None,
    }


def _abstain(reason: str = "no source grounding") -> dict:
    return {"status": "abstain", "problem": None, "abstain_reason": reason}


# ---------------------------------------------------------------------------
# Covered topic, ALL attempts verified -> produced == count, valid letters
# ---------------------------------------------------------------------------


def test_covered_all_verified_produces_count(monkeypatch):
    app_module = _enabled_app(monkeypatch)

    def _all_emit(topic, technique):
        return _emit("1", ["1", "2", "0"])

    monkeypatch.setattr(app_module, "generate_problem", _all_emit)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["topic"] == COVERED_TOPIC
    assert body["requested"] == 3
    assert body["produced"] == 3
    assert len(body["problems"]) == 3
    for prob in body["problems"]:
        assert set(prob.keys()) == {
            "stem",
            "choices",
            "correct_answer",
            "worked_solution",
            "source_citation",
        }
        assert prob["stem"] == "Evaluate the limit."
        assert prob["choices"] == ["1", "2", "0"]
        # correct value "1" is at index 0 -> letter "A"
        assert prob["correct_answer"] == "A"
        assert prob["worked_solution"] == "Apply the limit laws."
        assert prob["source_citation"] == "GRE Math Review, §Limits"


def test_correct_letter_indexes_choices(monkeypatch):
    """The letter must be the position of the correct value within choices."""
    app_module = _enabled_app(monkeypatch)

    # correct "9" sits at index 2 of the choices -> letter "C".
    def _emit_c(topic, technique):
        return _emit("9", ["7", "8", "9", "10"])

    monkeypatch.setattr(app_module, "generate_problem", _emit_c)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 1}
    )
    body = resp.json()
    assert body["produced"] == 1
    prob = body["problems"][0]
    assert prob["choices"] == ["7", "8", "9", "10"]
    assert prob["correct_answer"] == "C"


# ---------------------------------------------------------------------------
# Some attempts abstain -> produced < count, only verified returned
# ---------------------------------------------------------------------------


def test_some_abstain_only_verified_returned(monkeypatch):
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _alternate(topic, technique):
        calls["n"] += 1
        # attempts 1,3 emit; attempts 2,4 abstain.
        if calls["n"] % 2 == 1:
            return _emit("1", ["1", "2"])
        return _abstain()

    monkeypatch.setattr(app_module, "generate_problem", _alternate)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 4}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["requested"] == 4
    assert body["produced"] == 2
    assert len(body["problems"]) == 2
    # no abstain leaked: every returned problem is a full verified shape.
    for prob in body["problems"]:
        assert prob["stem"]
        assert prob["choices"]
        assert prob["correct_answer"] in {"A", "B", "C", "D", "E"}
        assert "abstain_reason" not in prob
        assert "status" not in prob


# ---------------------------------------------------------------------------
# ALL attempts abstain -> produced 0, empty problems, status ok
# ---------------------------------------------------------------------------


def test_all_abstain_produces_zero(monkeypatch):
    app_module = _enabled_app(monkeypatch)

    monkeypatch.setattr(
        app_module, "generate_problem", lambda topic, technique: _abstain()
    )
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["requested"] == 3
    assert body["produced"] == 0
    assert body["problems"] == []


# ---------------------------------------------------------------------------
# Uncovered topic -> fail closed; proposer NOT called (guard fires first)
# ---------------------------------------------------------------------------


def test_uncovered_topic_fails_closed_proposer_not_called(monkeypatch):
    """Drive the REAL generate_problem/run_generation fail-closed guard.

    Only the proposer + embedder + retriever + gate are neutralized (offline);
    ``run_generation`` and ``covered_topic_ids`` are the real ones. The proposer
    is a SPY: for an uncovered topic the syllabus guard must abstain before the
    graph runs, so the spy must never be called.
    """
    app_module = _enabled_app(monkeypatch)

    proposer_calls = {"n": 0}

    def _spy_propose(settings):
        def _propose(topic, technique):
            proposer_calls["n"] += 1
            return {"candidate": {}, "spec": {}}

        return _propose

    monkeypatch.setattr(app_module, "_make_openai_propose", _spy_propose)
    monkeypatch.setattr(
        app_module, "make_openai_embedder_if_key", lambda settings: None
    )
    monkeypatch.setattr(
        app_module, "make_hybrid_retriever", lambda **kw: (lambda c: None)
    )
    monkeypatch.setattr(app_module, "make_gold_gate", lambda texts: (lambda c: True))
    monkeypatch.setattr(app_module, "load_study_texts", lambda: [])

    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": UNCOVERED_TOPIC, "count": 4}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["topic"] == UNCOVERED_TOPIC
    assert body["produced"] == 0
    assert body["problems"] == []
    assert body["reason"] == "topic not in grounding corpus"
    assert proposer_calls["n"] == 0, "proposer must NOT be called for an uncovered topic"


# ---------------------------------------------------------------------------
# count clamped to [1, 5]
# ---------------------------------------------------------------------------


def test_count_clamped_high(monkeypatch):
    app_module = _enabled_app(monkeypatch)
    calls = {"n": 0}

    def _emit_count(topic, technique):
        calls["n"] += 1
        return _emit("1", ["1", "2"])

    monkeypatch.setattr(app_module, "generate_problem", _emit_count)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 99}
    )
    body = resp.json()
    assert body["requested"] == 5
    assert body["produced"] == 5
    assert calls["n"] == 5, "must attempt exactly the clamped count"


def test_count_clamped_low(monkeypatch):
    app_module = _enabled_app(monkeypatch)
    calls = {"n": 0}

    def _emit_count(topic, technique):
        calls["n"] += 1
        return _emit("1", ["1", "2"])

    monkeypatch.setattr(app_module, "generate_problem", _emit_count)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 0}
    )
    body = resp.json()
    assert body["requested"] == 1
    assert body["produced"] == 1
    assert calls["n"] == 1


def test_count_defaults_to_five(monkeypatch):
    app_module = _enabled_app(monkeypatch)
    calls = {"n": 0}

    def _emit_count(topic, technique):
        calls["n"] += 1
        return _emit("1", ["1", "2"])

    monkeypatch.setattr(app_module, "generate_problem", _emit_count)
    client = TestClient(app_module.app)

    resp = client.post("/generate_batch", json={"topic": COVERED_TOPIC})
    body = resp.json()
    assert body["requested"] == 5
    assert calls["n"] == 5


# ---------------------------------------------------------------------------
# Disabled service -> 503, never generates
# ---------------------------------------------------------------------------


def test_disabled_returns_503(monkeypatch):
    monkeypatch.delenv("SPEEDRUN_AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)

    # If generation were attempted, this would blow up — proving we never do.
    def _boom(topic, technique):
        raise AssertionError("generation must not run when disabled")

    monkeypatch.setattr(app_module, "generate_problem", _boom)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 3}
    )
    assert resp.status_code == 503
    detail = resp.json()["detail"].lower()
    assert "disabled" in detail


# ---------------------------------------------------------------------------
# Edge case: an emit whose correct value is NOT in choices -> unverifiable -> drop
# ---------------------------------------------------------------------------


def test_emit_with_correct_not_in_choices_is_dropped(monkeypatch):
    """If the correct value cannot be located in the assembled choices, no valid
    letter can be derived -> the attempt is not verifiable -> DROP it (fail
    closed), never ship a problem with an unknown correct answer."""
    app_module = _enabled_app(monkeypatch)

    def _bad_emit(topic, technique):
        result = _emit("42", ["1", "2", "3"])  # "42" absent from choices
        return result

    monkeypatch.setattr(app_module, "generate_problem", _bad_emit)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["produced"] == 0
    assert body["problems"] == []
