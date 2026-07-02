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

## Pre-registration — §7f gold-set gate cutoffs

The gold-set gate (`gate`) is a **stub returning `True`** in this task. The real
§7f gate arrives in **Task 4.4**, together with its pre-registered acceptance
cutoffs. Pre-register the thresholds **before** running against the held-out
set, and record them here:

| Metric                         | Cutoff | Notes                     |
| ------------------------------ | ------ | ------------------------- |
| *(to be filled in Task 4.4)*   | TBD    | pre-registered before eval |

Do not tune these against the held-out set after the fact — pre-registration is
what keeps the honest-score claim honest.
