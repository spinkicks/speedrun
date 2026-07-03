<!--
Copyright: Speedrun contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

# speedrun-ai — AI problem-generation service

An **OFF-by-default** service that generates GRE Mathematics Subject Test
problems through a verify / retry / abstain LangGraph pipeline. Every emitted
problem is proven correct by the real SymPy verifier, grounded in a source
citation, and cleared by the gold-set gate — otherwise the pipeline **abstains
and emits nothing**.

> The study app's correctness must never depend on this service being up. It is
> a bonus generator, gated behind a kill switch, not a dependency.

## OFF-by-default contract (kill switch)

The service is **ENABLED only when BOTH** of the following hold:

| Requirement            | Env var               | Default        |
| ---------------------- | --------------------- | -------------- |
| Feature flag is truthy | `SPEEDRUN_AI_ENABLED` | `0` (off)      |
| API key is present     | `OPENAI_API_KEY`      | *(unset)*      |

Optional: `OPENAI_MODEL` (default `gpt-4o`).

Behavior when **disabled** (default):

- `GET /health` → `200 {"status":"ok","ai_enabled":false}` (never leaks the key).
- `POST /generate` → **`503`** with a clear
  `AI generation disabled (SPEEDRUN_AI_ENABLED/OPENAI_API_KEY not set)` message.
- The app **imports and serves without any API key**. The OpenAI client is
  constructed lazily, only inside the enabled path.

Truthy flag but **no key** ⇒ still disabled (both are required).

## Pipeline

```
        propose ───► verify
                       │
        passed ────────┼──────► rag_ground ──► distractors ──► gold_gate
                       │             │                              │
   failed &            │        no citation                    gate pass ──► emit ──► END
   retries<max ──► (bump) ──┐        │                              │
        │                   │        ▼                          gate fail
        └──► re-propose ◄───┘     abstain ◄──────────────────────────┘
                       │             ▲
   failed &            │             │
   retries==max ──────►┴──────► abstain ──► END
```

Nodes (each a pure function of state; side effects only via injected
collaborators):

1. **propose** — injected `llm_propose(topic, technique) -> {candidate, spec}`.
2. **verify** — builds a `ProblemSpec` and calls the **real** `verify()` from
   `verify/sympy_verifier.py` (symbolic + numeric). Sets `state.verification`.
3. **rag_ground** — injected `retriever(candidate) -> citation | None`
   (default stub returns a placeholder; real hybrid retriever = Task 4.3).
4. **distractors** — injected `make_distractors(candidate) -> list[str]`
   (default stub, mal-rule style; never duplicates the correct answer).
5. **gold_gate** — injected `gate(candidate) -> bool` (default stub returns
   `True`; real §7f gate = Task 4.4).
6. **emit** — terminal success; packages the problem dict (`status="emit"`).
7. **abstain** — terminal failure; emits nothing (`status="abstain"` + honest
   `abstain_reason`).

Conditional edges (the honest-abstain core):

- `propose → verify`
- `verify → rag_ground` if `verification.passed`; else retry (`propose`, +1
  `retries`) while `retries < max_retries`; else `abstain`
  (reason: *answer failed SymPy verification after N retries*).
- `rag_ground → distractors` if a citation is present; else `abstain`
  (reason: *no source grounding*).
- `distractors → gold_gate`.
- `gold_gate → emit` if the gate passes; else `abstain`
  (reason: *failed gold-set gate*).
- `emit` / `abstain` → `END`.

Dependency injection is **required**: `llm_propose` must be supplied by the
caller; `retriever` / `make_distractors` / `gate` default to offline stubs so
tests never touch OpenAI or the network.

## Grounding safety

Two independent grounding guards protect every emission:

1. **Semantic grounding gate** (in `rag/ground()`): a candidate must clear a
   calibrated query-to-top-passage cosine threshold or the pipeline abstains
   ("no source grounding"). See
   [`rag/README.md` → grounding gate](rag/README.md).
2. **Fail-closed syllabus scoping** (AI bug #3): the corpus covers exactly nine
   leaf topics (`rag.covered_topic_ids()`). A request for a topic the corpus
   does **not** cover (ODEs, arc length, partial-fraction integration, PCA, …)
   **abstains before proposing** (`abstain_reason = "topic not in grounding
   corpus"`) instead of grounding to a near-neighbour-but-unsupporting passage —
   a *misleading citation* the cosine gate cannot separate. `app.generate_problem`
   passes the covered set so the running service is fail-closed by default; the
   matcher is `graph.topic_is_covered` (exact `topic_id` match, or normalized
   content-token / alias overlap).

The **known coverage-gap mis-citation limitation** (why fail-closed scoping is
needed, and the future entailment/support-check fix) is documented in
[`rag/README.md` → *Known limitation: coverage-gap mis-citation*](rag/README.md)
and tracked in `docs/FUTURE-PLANS.md`.

## Run

```bash
# from services/speedrun-ai/
uv sync --extra dev            # install runtime + dev deps

# tests (stubbed LLM/retriever/gate; no network)
uv run pytest -q
uv run ruff check .

# serve (DISABLED by default → /generate returns 503)
uv run uvicorn app:app --reload

# enable (requires a real key; not needed for tests)
SPEEDRUN_AI_ENABLED=1 OPENAI_API_KEY=sk-... uv run uvicorn app:app
```

Programmatic use (stubbed, offline):

```python
from graph import run_generation

def llm(topic, technique):
    return {
        "candidate": {"stem": "d/dx of x**2?", "correct": "2*x",
                      "worked_solution": "power rule"},
        "spec": {"answer_type": "derivative", "expression": "x**2",
                 "variable": "x", "claimed_answer": "2*x"},
    }

state = run_generation("calculus", "power_rule", llm_propose=llm)
assert state["status"] == "emit"
```

## §7f gold-set gate (Task 4.4)

The real §7f gate now lives in [`eval/`](eval/README.md): a Recall@10 retrieval
eval + corpus coverage, a wrong-answer-by-construction proof, the leakage
scanner (`eval/leakage.py`), and the LLM-judge scaffold. The graph's default
`gate` remains the offline stub (so graph/app unit tests stay hermetic); the
**real** leakage-free gate is built by `eval.gate.make_gold_gate(study_texts)`
and injected in `app.py`'s enabled path.

Pre-registered cutoffs (fixed **before** results — see
[`eval/README.md`](eval/README.md) for the full pre-registration + honest
numbers):

| Metric               | Cutoff                          | Measured                    |
| -------------------- | ------------------------------- | --------------------------- |
| Wrong-answer rate    | ≤ 2 % (target 0)                | hermetic (0 by construction)|
| Useful               | ≥ 80 %                          | LLM-judge / human (at demo) |
| Bad-teaching         | ≤ 15 %                          | LLM-judge / human (at demo) |
| Leakage              | 0                               | hermetic (scanner)          |
| Hybrid RAG margin    | ≥ 5 pts Recall@10 over baseline | hermetic (reported)         |

Do not tune these against the held-out set after the fact — pre-registration is
what keeps the honest-score claim honest.

Reproduce the aggregate numbers (never echoes raw gold pairs):

```bash
PYTHONIOENCODING=utf-8 uv run python -m eval.gate
```
