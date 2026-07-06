# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
FastAPI app for the AI problem-generation service.

OFF-BY-DEFAULT: ``/generate`` returns HTTP 503 unless the service is enabled
(``SPEEDRUN_AI_ENABLED`` truthy AND ``OPENAI_API_KEY`` present). ``/health`` is
always 200 and never leaks the key. The module imports cleanly with no key.
The real OpenAI-backed proposer is constructed lazily, only when enabled.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import load_settings
from eval.gate import make_gold_gate
from eval.leakage import load_study_texts
from graph import TOPIC_NOT_COVERED_REASON, make_hybrid_retriever, run_generation
from rag.embeddings import make_openai_embedder_if_key
from rag.retriever import covered_topic_ids


def _autoload_dotenv() -> None:
    """Load ``services/speedrun-ai/.env`` into the environment when running the
    service (uvicorn), so an operator's local ``.env`` "just works" without a
    manual ``$env:`` export.

    Deliberately dependency-free (no python-dotenv). Existing environment
    variables ALWAYS win (``setdefault``), so an explicit export overrides the
    file. Skipped under pytest so the hermetic test environment is never
    perturbed, and a no-op when the file is absent (the normal case in CI / the
    public forks, where ``.env`` is gitignored). The kill-switch is unaffected:
    it still enables only when ``SPEEDRUN_AI_ENABLED`` is truthy AND a key is
    present.
    """
    if "pytest" in sys.modules:  # never touch the test environment
        return
    env_path = pathlib.Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_autoload_dotenv()

app = FastAPI(title="Speedrun AI generation service", version="0.1.0")

DISABLED_DETAIL = (
    "AI generation disabled (SPEEDRUN_AI_ENABLED/OPENAI_API_KEY not set). "
    "This is the intended OFF-by-default kill-switch; the study app does not "
    "depend on this service."
)


class GenerateRequest(BaseModel):
    topic: str
    technique: str


class GenerateBatchRequest(BaseModel):
    topic: str
    count: int = 5


# Batch clamp bounds for the desktop "Generate practice" button.
_BATCH_MIN = 1
_BATCH_MAX = 5

# Cost guard for the retry loop (AI bug #4). Abstains no longer shrink the
# batch: we RE-ATTEMPT until we have ``count`` verified problems. Because the
# graph can abstain (unverifiable / ungrounded / gold-gated) on any attempt,
# the loop needs a HARD upper bound so it can never spin forever — each attempt
# is worst-case ~20-60 LLM calls, so an unbounded loop is a real cost hazard.
# Budget = ``count * _ATTEMPT_MULTIPLIER`` attempts, itself never exceeding
# ``_MAX_ATTEMPTS_CAP``. When the cap is hit we return the partials we DID
# verify and report the shortfall honestly (never raise).
_ATTEMPT_MULTIPLIER = 4
_MAX_ATTEMPTS_CAP = 25

# Letters used to index answer choices in the batch response (A..E). The graph
# emits at most 5 choices (1 correct + up to ~3 distractors), so five letters
# always suffice; any position beyond this is treated as unverifiable and the
# problem is dropped (fail closed).
_CHOICE_LETTERS = "ABCDE"


def _batch_problem_from_emit(problem: dict[str, Any]) -> dict[str, Any] | None:
    """Map a graph EMIT ``problem`` payload to the FROZEN desktop shape, or
    ``None`` when it cannot be safely presented (→ the caller DROPS it).

    Contract shape: ``{stem, choices, correct_answer, worked_solution,
    source_citation}`` where ``correct_answer`` is the LETTER (A..E) whose
    position in ``choices`` holds the emitted ``correct`` value.

    Fail closed: if choices are missing, the emitted ``correct`` value is not
    found among the assembled choices, or the source citation is missing, no
    valid letter/citation can be derived → return ``None`` so the attempt is
    treated as unverified and dropped (never ship an answer we cannot point to).
    """
    if not isinstance(problem, dict):
        return None
    choices = problem.get("choices") or []
    correct = str(problem.get("correct", "")).strip()
    citation = problem.get("citation")
    stem = problem.get("stem", "")
    if not choices or not correct or not stem or not citation:
        return None
    try:
        index = choices.index(correct)
    except ValueError:
        return None  # correct value not among choices → cannot letter it → drop
    if index >= len(_CHOICE_LETTERS):
        return None  # more choices than we can letter → drop (fail closed)
    return {
        "stem": stem,
        "choices": list(choices),
        "correct_answer": _CHOICE_LETTERS[index],
        "worked_solution": problem.get("worked_solution", ""),
        "source_citation": citation,
    }


# ---------------------------------------------------------------------------
# Real OpenAI-backed proposer — constructed ONLY when enabled.
# ---------------------------------------------------------------------------


def _make_openai_propose(settings):
    """Build an ``llm_propose(topic, technique) -> dict`` backed by OpenAI.

    Constructed lazily so the app imports with no key. The client is only
    instantiated here, inside the enabled path.
    """
    from openai import OpenAI

    client = OpenAI(api_key=settings.api_key)
    model = settings.model

    def llm_propose(topic: str, technique: str) -> dict:
        prompt = (
            "You generate a single GRE Mathematics Subject Test problem plus a "
            "machine-checkable symbolic spec. Topic: "
            f"{topic}. Technique: {technique}. "
            "Respond with STRICT JSON: "
            '{"candidate": {"stem": str, "correct": str, '
            '"worked_solution": str}, '
            '"spec": {"answer_type": str, "expression": str, '
            '"variable": str, "claimed_answer": str, '
            '"limit_point": str, "lower_bound": str, "upper_bound": str}}. '
            "answer_type is one of expression_equivalence, "
            "equation_solution_set, derivative, integral, limit, numeric_value. "
            "Include limit_point when answer_type is limit; include lower_bound "
            "and upper_bound for a definite integral; omit fields that do not "
            "apply. "
            # The spec strings are parsed by SymPy (parse_expr with implicit
            # multiplication), NOT rendered LaTeX. Instruct the model to emit
            # SymPy-parseable syntax so the verifier can actually check them.
            "Every expression/claimed_answer/bound in `spec` MUST be a "
            "SymPy-parseable string: use ** for powers (write x**4, NEVER x^4), "
            "* for multiplication where needed, sqrt() / exp() / log() / sin() / "
            "cos() for functions, pi for pi, and oo for infinity. Do not use ^, "
            "LaTeX, unicode math, or fractions like \\frac. The `candidate` "
            "fields (stem, correct, worked_solution) are human-facing prose and "
            "may be written normally, but `candidate.correct` MUST be "
            "mathematically equal to `spec.claimed_answer`."
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)

    return llm_propose


def generate_problem(topic: str, technique: str) -> dict[str, Any]:
    """Run the generation graph with the real OpenAI proposer, the real hybrid
    RAG retriever (Task 4.3) for source grounding, AND the real §7f gold gate
    (Task 4.4) for leakage checking.

    Only called from the enabled path. Tests monkeypatch this symbol so they
    never construct an OpenAI client, build a RAG index, or hit the network.
    The retriever is the drop-if-unverifiable gate: a candidate whose top hit
    scores below the grounding threshold takes the graph's abstain path. The
    gold gate is the leakage guard: a candidate that duplicates the curated
    study content fails the gate → the graph abstains ("failed gold-set gate").
    """
    settings = load_settings()
    llm_propose = _make_openai_propose(settings)
    # SEMANTIC grounding gate (FIX 4): build the real OpenAI embedder when a key
    # is present (it is, in the enabled path). Constructing it does not hit the
    # network; corpus embeddings are computed once inside make_hybrid_retriever.
    embedder = make_openai_embedder_if_key(settings)
    retriever = make_hybrid_retriever(embedder=embedder)
    # Real §7f gold gate = leakage-free check against the curated study content.
    gate = make_gold_gate(load_study_texts())
    # FAIL-CLOSED syllabus scoping (AI bug #3): pass the corpus's covered leaf
    # topics so a request for a topic the corpus does not cover ABSTAINS before
    # proposing (no near-neighbour mis-citation), rather than grounding to an
    # unsupporting passage. See graph.topic_is_covered / rag.covered_topic_ids.
    return run_generation(
        topic,
        technique,
        llm_propose=llm_propose,
        retriever=retriever,
        gate=gate,
        covered_topics=covered_topic_ids(),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    """Always 200. Reports the enabled flag only — never the key."""
    return {"status": "ok", "ai_enabled": load_settings().is_enabled()}


@app.post("/generate")
def generate(req: GenerateRequest) -> dict[str, Any]:
    """Generate one verified problem, or refuse (503) when disabled."""
    if not load_settings().is_enabled():
        raise HTTPException(status_code=503, detail=DISABLED_DETAIL)
    return generate_problem(req.topic, req.technique)


@app.post("/generate_batch")
def generate_batch(req: GenerateBatchRequest) -> dict[str, Any]:
    """Batch endpoint for the desktop "Generate practice" button.

    A THIN wrapper over :func:`generate_problem` (the single-problem graph): it
    RE-ATTEMPTS generation for a covered ``topic`` until it has ``count``
    verified, grounded, gold-gated problems — or a cost cap is reached. Every
    abstain / unverified / duplicate attempt is DROPPED, never returned. It
    never reimplements the graph or weakens any gate.

    AI bug #4 fix: the old implementation looped a FIXED ``count`` times and
    kept only the emits, so any abstain silently shrank the batch (4 requested →
    2 delivered). Now the loop condition is ``while produced < target and
    attempts < MAX_ATTEMPTS`` so abstains are retried instead of shrinking the
    result. ``MAX_ATTEMPTS = min(count * _ATTEMPT_MULTIPLIER, _MAX_ATTEMPTS_CAP)``
    is the mandatory cost guard (each attempt is worst-case tens of LLM calls);
    on shortfall we return the partials and report it honestly (never raise).

    Server-side stem dedup: two verified emits with the SAME stem count as ONE
    produced problem — we never ship duplicate stems within a batch.

    Safety contract:
      * Disabled kill-switch → 503 (never generate).
      * Uncovered topic → fail CLOSED: the existing ``covered_topics`` guard in
        ``run_generation`` abstains before proposing; we stop immediately —
        BEFORE any further LLM call — and return ``produced:0, problems:[],
        reason:"topic not in grounding corpus"``.
      * ``count`` is clamped to ``[1, 5]`` (default 5).
      * ``correct_answer`` is the LETTER (A..E) indexing the emitted correct
        value within ``choices``; an emit we cannot letter/cite is dropped.

    Response fields: ``requested`` (clamped target), ``produced`` (verified,
    deduped problems returned), ``attempts`` (graph invocations made),
    ``shortfall`` (``requested - produced``; 0 on success). Lane 4 surfaces
    ``shortfall`` in a client toast; here we only EXPOSE it.
    """
    if not load_settings().is_enabled():
        raise HTTPException(status_code=503, detail=DISABLED_DETAIL)

    target = max(_BATCH_MIN, min(_BATCH_MAX, req.count))
    max_attempts = min(target * _ATTEMPT_MULTIPLIER, _MAX_ATTEMPTS_CAP)

    problems: list[dict[str, Any]] = []
    seen_stems: set[str] = set()
    attempts = 0

    # Retry until we hit the target or exhaust the attempt budget. The budget is
    # a HARD cap — the loop can never spin forever even if every attempt abstains.
    while len(problems) < target and attempts < max_attempts:
        attempts += 1
        result = generate_problem(req.topic, "")
        # Fail closed on an uncovered topic: the syllabus guard fired BEFORE any
        # proposal (no LLM call happened). Every attempt would return the same
        # abstain, so short-circuit — retrying cannot help an uncovered topic.
        if result.get("abstain_reason") == TOPIC_NOT_COVERED_REASON:
            return {
                "status": "ok",
                "topic": req.topic,
                "requested": target,
                "produced": 0,
                "problems": [],
                "attempts": attempts,
                "shortfall": target,
                "reason": TOPIC_NOT_COVERED_REASON,
            }
        # Keep ONLY verified emits; drop every abstain / unverified attempt.
        if result.get("status") != "emit":
            continue
        mapped = _batch_problem_from_emit(result.get("problem") or {})
        if mapped is None:
            continue
        # Server-side stem dedup: never emit two problems with the same stem.
        stem = mapped["stem"]
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        problems.append(mapped)

    return {
        "status": "ok",
        "topic": req.topic,
        "requested": target,
        "produced": len(problems),
        "problems": problems,
        "attempts": attempts,
        "shortfall": target - len(problems),
    }
