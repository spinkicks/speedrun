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
from graph import make_hybrid_retriever, run_generation
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
            "apply."
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
