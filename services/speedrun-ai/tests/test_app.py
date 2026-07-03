# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Tests for the FastAPI app — the OFF-by-default kill-switch contract.

No API key is used anywhere in this file. The app must import and serve
/health with no key present, and /generate must refuse (503) when disabled.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def disabled_client(monkeypatch):
    """A TestClient with the service fully DISABLED (no flag, no key)."""
    monkeypatch.delenv("SPEEDRUN_AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_health_ok_when_disabled(disabled_client):
    resp = disabled_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ai_enabled"] is False
    # never leaks a key
    assert "OPENAI_API_KEY" not in body
    assert "api_key" not in body


def test_generate_503_when_disabled(disabled_client):
    resp = disabled_client.post(
        "/generate", json={"topic": "calculus", "technique": "power_rule"}
    )
    assert resp.status_code == 503
    detail = resp.json()["detail"].lower()
    assert "disabled" in detail
    assert "speedrun_ai_enabled" in detail or "openai_api_key" in detail


def test_flag_on_but_no_key_still_disabled(monkeypatch):
    """Flag truthy but no key → still disabled (both are required)."""
    monkeypatch.setenv("SPEEDRUN_AI_ENABLED", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)
    client = TestClient(app_module.app)

    health = client.get("/health").json()
    assert health["ai_enabled"] is False

    resp = client.post(
        "/generate", json={"topic": "calculus", "technique": "power_rule"}
    )
    assert resp.status_code == 503


def test_app_imports_without_key(monkeypatch):
    """Construction must not fail when disabled / no key present."""
    monkeypatch.delenv("SPEEDRUN_AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import app as app_module

    importlib.reload(app_module)
    assert app_module.app is not None


def test_generate_enabled_with_stubbed_graph(monkeypatch):
    """With enabled config + a stubbed graph runner, /generate returns the
    final state — no real key or network needed."""
    monkeypatch.setenv("SPEEDRUN_AI_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)

    def _fake_runner(topic, technique):
        return {
            "status": "emit",
            "problem": {
                "stem": f"stub stem for {topic}/{technique}",
                "correct": "2*x",
                "choices": ["2*x", "3*x"],
                "distractors": ["3*x"],
                "citation": "stub-citation",
            },
            "abstain_reason": None,
        }

    monkeypatch.setattr(app_module, "generate_problem", _fake_runner)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate", json={"topic": "calculus", "technique": "power_rule"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "emit"
    assert body["problem"]["correct"] == "2*x"


def test_generate_problem_passes_covered_topics_fail_closed(monkeypatch):
    """AI bug #3 wiring: the running service must be fail-closed by default —
    ``generate_problem`` must pass the corpus's covered topic set to
    ``run_generation`` so an uncovered topic abstains without proposing.

    Every heavy collaborator is stubbed so no OpenAI client / RAG index / network
    is constructed; we assert on the ``covered_topics`` kwarg that reaches
    ``run_generation``.
    """
    monkeypatch.setenv("SPEEDRUN_AI_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    import config
    import app as app_module

    importlib.reload(config)
    importlib.reload(app_module)

    # Neutralize every heavy collaborator so generate_problem stays offline.
    monkeypatch.setattr(app_module, "_make_openai_propose", lambda settings: (lambda t, tech: {}))
    monkeypatch.setattr(app_module, "make_openai_embedder_if_key", lambda settings: None)
    monkeypatch.setattr(app_module, "make_hybrid_retriever", lambda **kw: (lambda c: None))
    monkeypatch.setattr(app_module, "make_gold_gate", lambda texts: (lambda c: True))
    monkeypatch.setattr(app_module, "load_study_texts", lambda: [])

    captured = {}

    def _fake_run_generation(topic, technique, **kwargs):
        captured["covered_topics"] = kwargs.get("covered_topics")
        return {"status": "abstain", "problem": None, "abstain_reason": "stub"}

    monkeypatch.setattr(app_module, "run_generation", _fake_run_generation)

    from rag.retriever import covered_topic_ids

    app_module.generate_problem("some uncovered topic", "power_rule")

    assert captured["covered_topics"] == covered_topic_ids(), (
        "generate_problem must pass the corpus covered-topic set to "
        "run_generation so the running service is fail-closed by default"
    )
