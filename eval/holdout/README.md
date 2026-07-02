# eval/holdout — HELD-OUT gold set (DO NOT let implementer agents read this)

> **ACCESS RULE (hard invariant, AGENTS.md):** this directory is the held-out evaluation set. **Claude's implementer/build subagents must NEVER read, echo, generate into, or train against anything here.** It is authored + owned by mission control (Cursor) / David. Its whole purpose is to be an *independent* gate on the AI problem generator — if the system-under-test sees it, the gate is worthless.

## What this is
`gre_math_gold.jsonl` — 50 human-grade, verified GRE **Mathematics Subject Test** multiple-choice problems used to gate the Friday AI problem-generation service (`services/speedrun-ai/`). The Task 4.4 harness runs the generator/RAG pipeline and measures quality against this set; it also serves as the RAG Recall@10 reference.

## Provenance
- **Authored:** 2026-07-02 by Cursor (mission control) under David's directive (Friday permits AI-authored content). Distributed by ETS topic weight across the 9 scored leaf topics in `repos/anki/speedrun/exam_profiles/gre_math.json`.
- **NOT** copied from any ETS released form (leakage rule). Original problems only.

## Verification protocol (every pair)
1. **Answer correctness:** each `correct_answer` independently confirmed by SymPy (symbolic + numeric) — authored with a per-item `verification` field, then re-verified in a second independent pass at assembly (author's snippet NOT trusted; problem re-solved from scratch).
2. **Structure:** exactly 5 `choices`, exactly one `correct_answer` ∈ `choices`, unique `id`, `topic_id` ∈ the 9 scored leaves. Enforced by `eval/tools/validate_goldset.py`.
3. **Source-grounding:** each item cites a real canonical open source (OpenStax Calculus Vol 1–3; Hefferon *Linear Algebra*; MIT OCW 18.06).
4. **Leakage scan:** checked to not overlap the seed study deck content.
5. **David spot-check:** a random sample hand-verified by the owner.

## Schema (JSONL, one object per line)
```json
{
  "id": "gold_calc_limits_01",
  "question": "…LaTeX with \\( … \\)…",
  "topic_id": "calc::limits",
  "choices": ["…", "…", "…", "…", "…"],
  "correct_answer": "…(exactly one of choices)…",
  "worked_solution": "…",
  "source_citation": "OpenStax Calculus Volume 1, §2.3 (The Limit Laws)",
  "difficulty_hint": "medium",
  "verification": "sympy: limit(...) = ... ; matches correct_answer"
}
```

## Target distribution (50, by ETS weight)
| topic_id | n |
|---|---|
| calc::limits | 5 |
| calc::single_var::differentiation | 7 |
| calc::single_var::integration | 8 |
| calc::sequences_series | 5 |
| calc::multivar | 8 |
| linear_algebra::vector_spaces | 4 |
| linear_algebra::matrices | 4 |
| linear_algebra::eigen | 5 |
| linear_algebra::linear_maps | 4 |
