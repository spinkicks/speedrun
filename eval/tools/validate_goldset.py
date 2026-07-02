#!/usr/bin/env python3
"""Structural validator for the held-out GRE-Math gold set.

Checks (does NOT verify math correctness — that's the independent SymPy re-pass):
  - valid JSONL, required fields present, correct types
  - exactly 5 choices, unique choices, correct_answer is exactly one choice
  - unique ids
  - topic_id in the 9 scored leaves of gre_math.json
  - per-topic counts match the ETS-weighted target distribution
  - total == 50

Usage: python eval/tools/validate_goldset.py [path-to-jsonl]
Default path: eval/holdout/gre_math_gold.jsonl
Exit code 0 = all good; 1 = problems found (printed).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / "repos" / "anki" / "speedrun" / "exam_profiles" / "gre_math.json"
DEFAULT = REPO / "eval" / "holdout" / "gre_math_gold.jsonl"

TARGET = {
    "calc::limits": 5,
    "calc::single_var::differentiation": 7,
    "calc::single_var::integration": 8,
    "calc::sequences_series": 5,
    "calc::multivar": 8,
    "linear_algebra::vector_spaces": 4,
    "linear_algebra::matrices": 4,
    "linear_algebra::eigen": 5,
    "linear_algebra::linear_maps": 4,
}
REQUIRED = {
    "id", "question", "topic_id", "choices", "correct_answer",
    "worked_solution", "source_citation", "difficulty_hint",
}
DIFF = {"easy", "medium", "hard"}


def leaf_topics() -> set[str]:
    prof = json.loads(PROFILE.read_text(encoding="utf-8"))
    return {t["id"] for t in prof["topics"] if t.get("ets_weight", 0) > 0}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1

    leaves = leaf_topics()
    errors: list[str] = []
    ids: set[str] = set()
    per_topic: Counter[str] = Counter()

    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {n}: invalid JSON ({e})")
            continue
        rows.append((n, obj))

    for n, obj in rows:
        oid = obj.get("id", f"<line{n}>")
        missing = REQUIRED - obj.keys()
        if missing:
            errors.append(f"{oid}: missing fields {sorted(missing)}")
            continue
        if oid in ids:
            errors.append(f"{oid}: duplicate id")
        ids.add(oid)
        choices = obj["choices"]
        if not isinstance(choices, list) or len(choices) != 5:
            errors.append(f"{oid}: choices must be a list of exactly 5 (got {len(choices) if isinstance(choices, list) else type(choices).__name__})")
        elif len(set(choices)) != 5:
            errors.append(f"{oid}: choices not unique")
        if obj["correct_answer"] not in (choices if isinstance(choices, list) else []):
            errors.append(f"{oid}: correct_answer is not exactly one of choices")
        if obj["topic_id"] not in leaves:
            errors.append(f"{oid}: topic_id '{obj['topic_id']}' not a scored leaf")
        else:
            per_topic[obj["topic_id"]] += 1
        if obj["difficulty_hint"] not in DIFF:
            errors.append(f"{oid}: difficulty_hint '{obj['difficulty_hint']}' not in {DIFF}")
        for f in ("question", "worked_solution", "source_citation"):
            if not str(obj.get(f, "")).strip():
                errors.append(f"{oid}: empty {f}")

    total = sum(per_topic.values())
    if total != 50:
        errors.append(f"total scored-topic items = {total}, expected 50")
    for topic, want in TARGET.items():
        got = per_topic.get(topic, 0)
        if got != want:
            errors.append(f"distribution: {topic} has {got}, target {want}")

    if errors:
        print(f"FAIL — {len(errors)} issue(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK — {total} items, schema valid, distribution matches target.")
    for topic in TARGET:
        print(f"  {topic}: {per_topic[topic]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
