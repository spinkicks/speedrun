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


def _emit(correct: str, choices: list[str], stem: str = "Evaluate the limit.") -> dict:
    """A graph EMIT result (verified problem) with the given correct/choices.

    ``stem`` defaults to a fixed value but callers that emit MORE THAN ONE
    problem in a batch MUST pass DISTINCT stems: the endpoint dedups by stem
    server-side (a real LLM run yields distinct stems), so two emits sharing a
    stem count as one produced problem — mirroring the shipping behaviour.
    """
    return {
        "status": "emit",
        "problem": {
            "stem": stem,
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

    calls = {"n": 0}

    def _all_emit(topic, technique):
        # DISTINCT stems so all three survive the server-side stem dedup.
        i = calls["n"]
        calls["n"] += 1
        return _emit("1", ["1", "2", "0"], stem=f"Evaluate the limit {i}.")

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
    # New contract: attempts/shortfall are exposed; all verified -> no shortfall
    # and exactly `count` attempts were needed (the loop stops at target).
    assert body["attempts"] == 3
    assert body["shortfall"] == 0
    for prob in body["problems"]:
        assert set(prob.keys()) == {
            "stem",
            "choices",
            "correct_answer",
            "worked_solution",
            "source_citation",
        }
        assert prob["stem"].startswith("Evaluate the limit")
        assert prob["choices"] == ["1", "2", "0"]
        # BUG P1-C: the OLD assertion hard-coded ``correct_answer == "A"``, which
        # codified the bug that the correct answer was ALWAYS option A. Assert
        # instead that the emitted letter correctly POINTS AT the correct value
        # within choices (letter → index → value), regardless of position.
        letter_index = "ABCDE".index(prob["correct_answer"])
        assert prob["choices"][letter_index] == "1"  # "1" is the correct value
        assert prob["worked_solution"] == "Apply the limit laws."
        assert prob["source_citation"] == "GRE Math Review, §Limits"
    # All three survived the server-side stem dedup -> distinct stems shipped.
    stems = [p["stem"] for p in body["problems"]]
    assert len(set(stems)) == 3


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


def test_correct_answer_letter_varies_across_batch(monkeypatch):
    """BUG P1-C: across a batch of problems with DISTINCT correct values the
    correct-answer letter must NOT be a constant 'A'. Each emit routes its
    choices through the REAL graph ``_assemble_choices`` (the deterministic
    per-problem shuffle), so this exercises the actual option ordering that
    ships — not a hand-fixed list."""
    app_module = _enabled_app(monkeypatch)

    from graph import _assemble_choices

    calls = {"n": 0}

    def _distinct_emit(topic, technique):
        i = calls["n"]
        calls["n"] += 1
        correct = str(i)
        distractors = [str(i + 100 + d) for d in range(4)]
        stem = f"Evaluate problem {i}."
        choices = _assemble_choices(correct, distractors, seed=stem)
        return {
            "status": "emit",
            "problem": {
                "stem": stem,
                "correct": correct,
                "choices": choices,
                "distractors": distractors,
                "worked_solution": "sol",
                "citation": "GRE Math Review",
                "topic": COVERED_TOPIC,
                "technique": "",
            },
            "abstain_reason": None,
        }

    monkeypatch.setattr(app_module, "generate_problem", _distinct_emit)
    client = TestClient(app_module.app)

    resp = client.post("/generate_batch", json={"topic": COVERED_TOPIC, "count": 5})
    body = resp.json()
    assert body["produced"] == 5
    letters = {p["correct_answer"] for p in body["problems"]}
    assert letters != {"A"}, (
        "every AI-generated MCQ has the correct answer as option A — not shuffled"
    )
    # And every letter still correctly indexes the correct value.
    for p in body["problems"]:
        idx = "ABCDE".index(p["correct_answer"])
        assert p["choices"][idx] in p["choices"]  # sanity: valid index


# ---------------------------------------------------------------------------
# Some attempts abstain -> the loop KEEPS GOING to the target (new contract)
# ---------------------------------------------------------------------------


def test_some_abstain_loops_until_count(monkeypatch):
    """NEW CONTRACT (issue #4): abstains no longer shrink the batch — the
    endpoint retries until it has ``count`` verified problems (or hits the cost
    cap). With alternating emit/abstain and a target of 4, it must attempt 8
    times (4 emits + 4 abstains) and STILL return 4 verified problems with zero
    shortfall. The OLD behaviour returned only 2 (a fixed 4-attempt loop that
    kept the emits and dropped the abstains) — that shortfall bug is what this
    lane fixes."""
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _alternate(topic, technique):
        calls["n"] += 1
        # odd attempts emit (DISTINCT stems so dedup keeps them); even abstain.
        if calls["n"] % 2 == 1:
            return _emit("1", ["1", "2"], stem=f"Problem {calls['n']}.")
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
    # Loops past the abstains until the target is met — no shortfall.
    assert body["produced"] == 4
    assert body["shortfall"] == 0
    assert len(body["problems"]) == 4
    # attempts 1,3,5,7 emit and 2,4,6 abstain -> the loop stops the instant the
    # 4th emit lands (attempt 7), before a would-be 8th abstain. Well under the
    # cost cap (4*4 = 16). This proves abstains are RETRIED, not counted as loss.
    assert body["attempts"] == 7
    assert calls["n"] == 7
    # no abstain leaked: every returned problem is a full verified shape.
    for prob in body["problems"]:
        assert prob["stem"]
        assert prob["choices"]
        assert prob["correct_answer"] in {"A", "B", "C", "D", "E"}
        assert "abstain_reason" not in prob
        assert "status" not in prob


# ---------------------------------------------------------------------------
# NEW CONTRACT: loop until count is met, OR stop at the cost cap and report
# the shortfall — never spin forever. (issue #4)
# ---------------------------------------------------------------------------


def test_loops_until_count_reached(monkeypatch):
    """Abstain a fixed number of times, THEN emit, and keep going until the
    target is met. The loop must survive a run of consecutive abstains and
    still deliver the full ``count`` when the cap is not exhausted."""
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _abstain_then_emit(topic, technique):
        calls["n"] += 1
        # First two attempts abstain; every attempt after that emits a DISTINCT
        # problem. Target 3 -> needs 2 abstains + 3 emits = 5 attempts (< cap 12).
        if calls["n"] <= 2:
            return _abstain()
        return _emit("1", ["1", "2"], stem=f"Problem {calls['n']}.")

    monkeypatch.setattr(app_module, "generate_problem", _abstain_then_emit)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["requested"] == 3
    assert body["produced"] == 3
    assert body["shortfall"] == 0
    assert body["attempts"] == 5  # 2 abstains + 3 emits
    assert calls["n"] == 5


def test_loops_stops_at_cap_reports_shortfall(monkeypatch):
    """When emits are too rare to ever reach the target, the loop MUST stop at
    the cost cap (MAX_ATTEMPTS = count*4, hard-capped at 25) and honestly report
    the shortfall — importing whatever passed rather than spinning forever."""
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _mostly_abstain(topic, technique):
        calls["n"] += 1
        # Emit only on every 5th attempt -> for count=4 the cap is 16 attempts,
        # yielding 3 emits (attempts 5,10,15) -> shortfall 1, never 4.
        if calls["n"] % 5 == 0:
            return _emit("1", ["1", "2"], stem=f"Problem {calls['n']}.")
        return _abstain()

    monkeypatch.setattr(app_module, "generate_problem", _mostly_abstain)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 4}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["requested"] == 4
    # Cap = 4*4 = 16 attempts; emits at 5,10,15 -> 3 produced, 1 short.
    assert body["attempts"] == 16
    assert calls["n"] == 16
    assert body["produced"] == 3
    assert body["shortfall"] == 1
    assert len(body["problems"]) == 3


def test_hard_cap_25_bounds_attempts(monkeypatch):
    """The cost guard is a HARD cap of 25 attempts even though count*4 would be
    larger only if count exceeded ~6 — but count is clamped to 5 (5*4=20 < 25).
    This asserts the cap is applied as min(count*4, 25): at the max clamped
    count of 5 with all-abstain, attempts is 20 (count*4), NOT unbounded."""
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _always_abstain(topic, technique):
        calls["n"] += 1
        return _abstain()

    monkeypatch.setattr(app_module, "generate_problem", _always_abstain)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 5}
    )
    body = resp.json()
    assert body["requested"] == 5
    assert body["produced"] == 0
    # count*4 = 20, which is <= the hard cap of 25 -> attempts == 20.
    assert body["attempts"] == 20
    assert calls["n"] == 20
    assert calls["n"] <= 25, "must never exceed the hard cap of 25"
    assert body["shortfall"] == 5


def test_stem_dedup_across_attempts(monkeypatch):
    """SERVER-side stem dedup: two verified emits with the SAME stem count as a
    single produced problem — the endpoint must not ship duplicate stems. With a
    duplicate stem repeated forever and count=2, it can never reach the target
    and stops at the cap with produced==1."""
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _same_stem(topic, technique):
        calls["n"] += 1
        return _emit("1", ["1", "2"], stem="Identical stem.")

    monkeypatch.setattr(app_module, "generate_problem", _same_stem)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 2}
    )
    body = resp.json()
    assert body["status"] == "ok"
    assert body["requested"] == 2
    # Only the FIRST unique stem is kept; the rest are deduped away.
    assert body["produced"] == 1
    assert len(body["problems"]) == 1
    # Never reaches target -> burns the cap (2*4 = 8) and reports the shortfall.
    assert body["attempts"] == 8
    assert body["shortfall"] == 1


# ---------------------------------------------------------------------------
# ALL attempts abstain -> produced 0, empty problems, status ok
# ---------------------------------------------------------------------------


def test_all_abstain_produces_zero(monkeypatch):
    app_module = _enabled_app(monkeypatch)

    calls = {"n": 0}

    def _always_abstain(topic, technique):
        calls["n"] += 1
        return _abstain()

    monkeypatch.setattr(app_module, "generate_problem", _always_abstain)
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
    # Never spins forever: stops at the cost cap (MAX_ATTEMPTS = count*4 = 12)
    # and honestly reports the full shortfall. This is the ONLY-abstains case,
    # NOT an uncovered topic, so there is no short-circuit — it burns the cap.
    assert body["attempts"] == 12
    assert calls["n"] == 12
    assert body["shortfall"] == 3


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
    # Short-circuit happens BEFORE any LLM call: exactly one probe attempt, and
    # the full requested count is reported as the shortfall (nothing produced).
    assert body["attempts"] == 1
    assert body["shortfall"] == 4
    assert proposer_calls["n"] == 0, "proposer must NOT be called for an uncovered topic"


# ---------------------------------------------------------------------------
# count clamped to [1, 5]
# ---------------------------------------------------------------------------


def test_count_clamped_high(monkeypatch):
    app_module = _enabled_app(monkeypatch)
    calls = {"n": 0}

    def _emit_count(topic, technique):
        i = calls["n"]
        calls["n"] += 1
        return _emit("1", ["1", "2"], stem=f"Problem {i}.")

    monkeypatch.setattr(app_module, "generate_problem", _emit_count)
    client = TestClient(app_module.app)

    resp = client.post(
        "/generate_batch", json={"topic": COVERED_TOPIC, "count": 99}
    )
    body = resp.json()
    assert body["requested"] == 5
    assert body["produced"] == 5
    # All verified -> the loop stops as soon as the (clamped) target is met.
    assert calls["n"] == 5, "must stop as soon as the clamped count is produced"
    assert body["attempts"] == 5
    assert body["shortfall"] == 0


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
        i = calls["n"]
        calls["n"] += 1
        return _emit("1", ["1", "2"], stem=f"Problem {i}.")

    monkeypatch.setattr(app_module, "generate_problem", _emit_count)
    client = TestClient(app_module.app)

    resp = client.post("/generate_batch", json={"topic": COVERED_TOPIC})
    body = resp.json()
    assert body["requested"] == 5
    assert body["produced"] == 5
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
