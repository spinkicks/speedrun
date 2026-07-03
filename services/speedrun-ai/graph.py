# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
LangGraph verify / retry / abstain pipeline for AI problem generation.

This is the correctness-critical core of the AI service. Every node is a pure
function of the state (side-effect-free except for calling injected
collaborators). The SymPy ``verify`` node uses the REAL verifier from
``verify/sympy_verifier.py`` — the hard safety gate that makes the "AI off"
failsafe honest.

Pipeline
--------
    propose -> verify
    verify  -> rag_ground        (if verification passed)
            -> propose           (if failed AND retries < max_retries; +1 retry)
            -> abstain           (if failed AND retries exhausted)
    rag_ground -> distractors    (if a citation was found)
               -> abstain        (if ungrounded)
    distractors -> gold_gate
    gold_gate -> emit            (if gate passes)
              -> abstain         (if gate fails)
    emit / abstain -> END

Dependency injection is REQUIRED: ``llm_propose`` must be supplied by the
caller. ``retriever``, ``make_distractors`` and ``gate`` default to safe stubs
so tests never touch OpenAI or a real retriever. The real OpenAI-backed
``llm_propose`` and (later) the real RAG retriever / §7f gold gate are wired in
by the caller (``app.py`` and Tasks 4.3 / 4.4).
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TypedDict

from langgraph.graph import END, StateGraph

from verify.sympy_verifier import ProblemSpec, answers_equivalent, verify

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# A collaborator that proposes a problem for a (topic, technique) pair.
LLMPropose = Callable[[str, str], dict]
# A collaborator that returns a source citation for a candidate (or None/"").
Retriever = Callable[[dict], Optional[str]]
# A collaborator that returns plausible-but-wrong distractor answers.
MakeDistractors = Callable[[dict], list]
# A collaborator that returns True iff a candidate clears the gold-set gate.
Gate = Callable[[dict], bool]


class GraphState(TypedDict, total=False):
    """State carried through the pipeline."""

    topic: str
    technique: str
    spec: dict  # the ProblemSpec dict the LLM proposed
    candidate: dict  # stem / choices / correct / worked_solution
    verification: dict  # VerificationResult-ish {passed, reason, ...}
    citation: Optional[str]
    distractors: list
    gate_result: Optional[bool]
    retries: int
    max_retries: int
    status: Optional[str]  # "emit" | "abstain" | None
    abstain_reason: Optional[str]
    problem: Optional[dict]  # packaged emission payload (None unless emit)


# ---------------------------------------------------------------------------
# Default stub collaborators (safe, offline)
# ---------------------------------------------------------------------------


def default_retriever(candidate: dict) -> Optional[str]:
    """STUB retriever (kept for tests and the offline default).

    Returns a placeholder citation so the offline pipeline is grounded. A real
    retriever returning ``None``/``""`` signals "ungrounded" and forces abstain.
    The REAL hybrid retriever (Task 4.3) is available via
    :func:`make_hybrid_retriever`; it is injected by the caller (``app.py``)
    while this stub remains the default so the graph/app unit tests never build
    an index.
    """
    return "PLACEHOLDER-CITATION (stub retriever; real grounding in Task 4.3)"


# The default grounding threshold on the fused RRF score. This is the SECOND
# line of defence for the drop-if-unverifiable gate; the FIRST is that each
# retrieval arm now only ranks docs with real (nonzero) raw similarity (see
# HybridRetriever._ranked_ids_from_scores — BUG 3 fix), so a zero-signal query
# yields NO candidates and grounds nothing regardless of this threshold.
#
# For queries that DO match, RRF scores are ~1/(k+rank) summed over the two arms
# (k=60). A doc ranked #1 in only ONE arm scores ~1/60 (~0.0167); a genuine top
# hit near the top of BOTH arms scores ~1/60 + 1/60 ≈ 0.0333 (and ~0.031 even at
# rank ~1+10). The floor is 0.03: above the single-arm-only score (~0.0167,
# rejected) yet below a real both-arms top hit (~0.031-0.033, admitted). This
# prunes weak, single-arm-only matches. Tunable by the caller.
DEFAULT_MIN_GROUND_SCORE = 0.03


def make_hybrid_retriever(
    *,
    corpus: Optional[list[dict]] = None,
    min_score: float = DEFAULT_MIN_GROUND_SCORE,
) -> Retriever:
    """Build the REAL hybrid-retriever grounding function for injection.

    Returns a ``Retriever`` closure ``candidate -> citation | None`` backed by
    :class:`rag.retriever.HybridRetriever`. Imported lazily so importing this
    module (and running the stubbed graph/app tests) never constructs an index
    or pulls in the RAG dependencies. If ``corpus`` is omitted, the vendored
    ``rag/corpus/gre_math_sources.jsonl`` is loaded.

    A top hit below ``min_score`` yields ``None`` → the graph's "no source
    grounding" abstain path (the drop-if-unverifiable gate).
    """
    from rag.retriever import HybridRetriever, load_corpus

    rows = corpus if corpus is not None else load_corpus()
    return HybridRetriever(rows).as_graph_retriever(min_score=min_score)


def default_make_distractors(candidate: dict) -> list:
    """STUB distractor generator (real mal-rule generator arrives later).

    Produces a few plausible wrong options and NEVER duplicates the correct
    answer.
    """
    correct = str(candidate.get("correct", "")).strip()
    # A handful of generic mal-rule style wrong answers.
    raw = [
        f"{correct} + 1",
        f"2*({correct})" if correct else "2",
        f"-({correct})" if correct else "-1",
    ]
    seen: set[str] = set()
    distractors: list[str] = []
    for option in raw:
        option = option.strip()
        if not option or option == correct or option in seen:
            continue
        seen.add(option)
        distractors.append(option)
    return distractors[:3]


def default_gate(candidate: dict) -> bool:
    """STUB gold-set gate (real §7f gate arrives in Task 4.4). Accepts all."""
    return True


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def _spec_from_dict(spec: dict) -> ProblemSpec:
    """Build a ProblemSpec from a proposal dict, tolerating extra/missing keys."""
    allowed = {
        "answer_type",
        "expression",
        "variable",
        "claimed_answer",
        "definite",
        "lower_bound",
        "upper_bound",
        "limit_point",
        "extra_symbols",
        "numeric_eps",
        "numeric_samples",
        "numeric_seed",
    }
    kwargs = {k: v for k, v in spec.items() if k in allowed}
    return ProblemSpec(**kwargs)


def _make_propose_node(llm_propose: LLMPropose):
    def propose(state: GraphState) -> dict:
        proposal = llm_propose(state["topic"], state["technique"])
        return {
            "candidate": proposal.get("candidate", {}),
            "spec": proposal.get("spec", {}),
        }

    return propose


def verify_node(state: GraphState) -> dict:
    """Run the REAL SymPy verifier on the proposed spec.

    Safety cross-check (BUG 1 — verify/emit divergence): the verifier validates
    ``spec.claimed_answer``, but the emit path ships ``candidate.correct``. If
    those two DIVERGE, the shipped answer was never the one that passed
    verification — a wrong answer could ship on a "verify passed". So after a
    successful verify we REQUIRE that the shipped ``candidate.correct`` is
    equivalent to the verified ``claimed_answer`` (using the verifier's own
    conservative equivalence). Any divergence downgrades the result to a FAIL
    (→ retry/abstain), so the pipeline fails closed and never ships an unverified
    answer.
    """
    spec_dict = state.get("spec") or {}
    candidate = state.get("candidate") or {}
    try:
        spec = _spec_from_dict(spec_dict)
        result = verify(spec)
        passed = bool(result.passed)
        reason = result.reason
        if passed:
            shipped = str(candidate.get("correct", ""))
            claimed = str(spec_dict.get("claimed_answer", ""))
            extra = spec_dict.get("extra_symbols") or None
            if not answers_equivalent(shipped, claimed, extra_symbols=extra):
                # The verifier proved ``claimed`` correct, but the problem would
                # ship ``shipped`` — refuse (fail closed) rather than emit an
                # answer that was never verified.
                passed = False
                reason = (
                    "shipped answer diverges from the verified answer "
                    f"(candidate.correct={shipped!r} != verified "
                    f"claimed_answer={claimed!r})"
                )
        verification = {
            "passed": passed,
            "reason": reason,
            "symbolic_ran": result.symbolic_ran,
            "numeric_ran": result.numeric_ran,
        }
    except Exception as exc:  # malformed spec → treat as a verification failure
        verification = {
            "passed": False,
            "reason": f"could not build/verify spec: {exc}",
            "symbolic_ran": False,
            "numeric_ran": False,
        }
    return {"verification": verification}


def _make_rag_node(retriever: Retriever):
    def rag_ground(state: GraphState) -> dict:
        citation = retriever(state.get("candidate", {}))
        return {"citation": citation}

    return rag_ground


def _make_distractors_node(make_distractors: MakeDistractors):
    def distractors(state: GraphState) -> dict:
        candidate = state.get("candidate", {})
        options = make_distractors(candidate) or []
        correct = str(candidate.get("correct", "")).strip()
        # Defence in depth: never let a distractor equal the correct answer.
        cleaned: list[str] = []
        seen: set[str] = set()
        for option in options:
            option = str(option).strip()
            if not option or option == correct or option in seen:
                continue
            seen.add(option)
            cleaned.append(option)
        return {"distractors": cleaned}

    return distractors


def _assemble_choices(correct: str, distractors: list) -> list[str]:
    """Assemble the answer choices: correct answer + distractors, deduped, with
    the correct answer appearing exactly once. Shared by the gold_gate node (so
    the gate scans exactly what will ship) and :func:`emit_node`.
    """
    choices: list[str] = []
    for option in [correct, *distractors]:
        option = str(option).strip()
        if option and option not in choices:
            choices.append(option)
    return choices


def _candidate_for_gate(state: GraphState) -> dict:
    """Build the candidate dict the gold gate should scan.

    BUG 4: the raw proposed candidate carries only stem/correct/worked_solution.
    The distractors live in a SEPARATE state key (from the distractors node) and
    the answer choices are assembled only at emit time — both human-visible and
    both AFTER the gate ran. If the gate only sees the raw candidate, a leak
    buried solely in a distractor is never scanned and ships. So we enrich the
    candidate with the distractors AND the assembled choices before gating, so
    the gate scans every field that will actually be emitted.
    """
    candidate = dict(state.get("candidate", {}))
    correct = str(candidate.get("correct", "")).strip()
    distractors = list(state.get("distractors", []))
    candidate["distractors"] = distractors
    candidate["choices"] = _assemble_choices(correct, distractors)
    return candidate


def _make_gate_node(gate: Gate):
    def gold_gate(state: GraphState) -> dict:
        # Scan the ENRICHED candidate (stem/solution/correct + distractors +
        # assembled choices) so a leak hidden only in a distractor/choice is
        # caught before emit (BUG 4).
        return {"gate_result": bool(gate(_candidate_for_gate(state)))}

    return gold_gate


def emit_node(state: GraphState) -> dict:
    """Terminal success: package the verified, grounded, gated problem."""
    candidate = state.get("candidate", {})
    correct = str(candidate.get("correct", "")).strip()
    distractors = list(state.get("distractors", []))
    # Assemble the answer choices: correct answer + distractors, deduped, with
    # the correct answer appearing exactly once.
    choices = _assemble_choices(correct, distractors)

    problem = {
        "stem": candidate.get("stem", ""),
        "correct": correct,
        "choices": choices,
        "distractors": distractors,
        "worked_solution": candidate.get("worked_solution", ""),
        "citation": state.get("citation"),
        "topic": state.get("topic"),
        "technique": state.get("technique"),
        "spec": state.get("spec", {}),
        "verification": state.get("verification", {}),
    }
    return {"status": "emit", "problem": problem, "abstain_reason": None}


def _make_abstain_node() -> Callable[[GraphState], dict]:
    def abstain(state: GraphState) -> dict:
        # abstain_reason is set by the routing edge before we get here; keep it.
        reason = state.get("abstain_reason") or "abstained"
        return {"status": "abstain", "problem": None, "abstain_reason": reason}

    return abstain


# ---------------------------------------------------------------------------
# Conditional-edge routers
# ---------------------------------------------------------------------------


def _make_verify_router(max_retries: int):
    """After verify: proceed / retry / abstain.

    Because a router cannot mutate state, retry accounting is done via the
    ``propose`` re-entry: we route back to a wrapper that bumps ``retries``.
    Here we only decide the direction and stamp the abstain reason when giving
    up.
    """

    def route(state: GraphState) -> str:
        verification = state.get("verification", {})
        if verification.get("passed"):
            return "rag_ground"
        retries = state.get("retries", 0)
        if retries < max_retries:
            return "retry"
        return "abstain"

    return route


def route_after_rag(state: GraphState) -> str:
    citation = state.get("citation")
    if citation:  # non-empty, non-None
        return "distractors"
    return "abstain"


def route_after_gate(state: GraphState) -> str:
    return "emit" if state.get("gate_result") else "abstain"


# Retry bookkeeping: a tiny node between verify's "retry" decision and propose.
def _bump_retries(state: GraphState) -> dict:
    return {"retries": state.get("retries", 0) + 1}


# Reason-stamping nodes: set abstain_reason then fall through to the abstain
# terminal. Keeping the reason on the routing side keeps each cause explicit.
def _abstain_verify(state: GraphState) -> dict:
    verification = state.get("verification", {})
    max_retries = state.get("max_retries", 0)
    detail = verification.get("reason", "")
    return {
        "abstain_reason": (
            f"answer failed SymPy verification after {max_retries} retries"
            + (f" (last reason: {detail})" if detail else "")
        )
    }


def _abstain_grounding(state: GraphState) -> dict:
    return {"abstain_reason": "no source grounding"}


def _abstain_gate(state: GraphState) -> dict:
    return {"abstain_reason": "failed gold-set gate"}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(
    *,
    llm_propose: LLMPropose,
    retriever: Retriever = default_retriever,
    make_distractors: MakeDistractors = default_make_distractors,
    gate: Gate = default_gate,
    max_retries: int = 2,
):
    """Build and compile the verify/retry/abstain pipeline.

    Parameters
    ----------
    llm_propose : callable(topic, technique) -> dict
        REQUIRED. Returns ``{"candidate": {...}, "spec": {...}}``.
    retriever, make_distractors, gate : callables
        Injected collaborators; default to offline stubs.
    max_retries : int
        Max number of re-proposals after a verification failure.
    """
    builder: StateGraph = StateGraph(GraphState)

    builder.add_node("propose", _make_propose_node(llm_propose))
    builder.add_node("verify", verify_node)
    builder.add_node("bump_retries", _bump_retries)
    builder.add_node("rag_ground", _make_rag_node(retriever))
    builder.add_node("distractors", _make_distractors_node(make_distractors))
    builder.add_node("gold_gate", _make_gate_node(gate))
    builder.add_node("emit", emit_node)
    builder.add_node("abstain", _make_abstain_node())
    # Reason-stamping shims feeding the abstain terminal.
    builder.add_node("abstain_verify", _abstain_verify)
    builder.add_node("abstain_grounding", _abstain_grounding)
    builder.add_node("abstain_gate", _abstain_gate)

    builder.set_entry_point("propose")
    builder.add_edge("propose", "verify")

    builder.add_conditional_edges(
        "verify",
        _make_verify_router(max_retries),
        {
            "rag_ground": "rag_ground",
            "retry": "bump_retries",
            "abstain": "abstain_verify",
        },
    )
    # retry path: bump the counter then re-propose.
    builder.add_edge("bump_retries", "propose")

    builder.add_conditional_edges(
        "rag_ground",
        route_after_rag,
        {"distractors": "distractors", "abstain": "abstain_grounding"},
    )
    builder.add_edge("distractors", "gold_gate")
    builder.add_conditional_edges(
        "gold_gate",
        route_after_gate,
        {"emit": "emit", "abstain": "abstain_gate"},
    )

    # Reason shims → abstain terminal.
    builder.add_edge("abstain_verify", "abstain")
    builder.add_edge("abstain_grounding", "abstain")
    builder.add_edge("abstain_gate", "abstain")

    builder.add_edge("emit", END)
    builder.add_edge("abstain", END)

    return builder.compile()


def run_generation(
    topic: str,
    technique: str,
    *,
    llm_propose: LLMPropose,
    retriever: Retriever = default_retriever,
    make_distractors: MakeDistractors = default_make_distractors,
    gate: Gate = default_gate,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Convenience: build the graph and run it once, returning the final state."""
    graph = build_graph(
        llm_propose=llm_propose,
        retriever=retriever,
        make_distractors=make_distractors,
        gate=gate,
        max_retries=max_retries,
    )
    initial: GraphState = {
        "topic": topic,
        "technique": technique,
        "retries": 0,
        "max_retries": max_retries,
        "status": None,
        "abstain_reason": None,
        "problem": None,
    }
    return dict(graph.invoke(initial))
