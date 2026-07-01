# Memory Dashboard — design spec (desktop Svelte + Android Kotlin, identical)

The visible surface for the honest **Memory** score (built on the `GetTopicMastery` RPC). Implement the SAME layout/behavior on both platforms. Today = Memory only; leave room for Performance + Readiness columns later (the full three-number dashboard is Friday). Design ethos = **SPOV 5: minimal, honest, trustworthy — no gamification, no single fake confident number.**

## Data source
`col.speedrun.topic_mastery(topics, mastery_threshold=0.9, min_reviews=20)` → per topic: `avg_recall`, `mastered_count`, `cards_with_data`, `mastered_lower`, `mastered_upper` (Wilson 95%), `graded_reviews`, `abstained`. Topic list + human labels + `ets_weight` come from the exam profile (`gre_math.json`). Coverage header uses `col.speedrun.coverage(required_tags)`.

## Layout
```
Memory                                                   [Refresh]
Your recalled memory by topic. Memory ≠ readiness — this measures
what you retain, not whether you can solve timed problems.
Coverage: 7 / 10 required topics present (70%)      Updated 10:42
─────────────────────────────────────────────────────────────────
TOPIC (weight)            RECALL      RANGE (95%)         DATA
Integration (16%)          78%     ▕▁▁▁███▁▁▏ 61–89%      12/15 cards
Differentiation (14%)      —       INSUFFICIENT DATA:      3/15 cards
                                   review 17 more to unlock
Multivariable (15%)        64%     ▕▁▁███▁▁▁▏ 44–80%       8/11 cards
...
```

## Per-topic row
- **Topic** — human label from the profile (e.g. "Integration"); show the `ets_weight` as a small "(16%)". Render MathJax if a label contains math (use Anki's bundled MathJax on both platforms).
- **Recall** — `avg_recall` as a whole-percent point estimate. If `abstained`, show `—` (never a fake number).
- **Range (95%)** — the Wilson interval `mastered_lower–mastered_upper` as BOTH a compact horizontal band (0–100%) AND the numeric "lo–hi%". **The range is the emphasized element** (honesty = the interval, not the point).
- **Data** — `mastered_count`/`cards_with_data` cards.
- **Abstain state** — when `abstained`, replace Recall+Range with: `INSUFFICIENT DATA: review N more to unlock` where `N = max(0, min_reviews − graded_reviews)`. Style the whole row muted/"locked" (a subtle lock glyph is fine; no alarming red).

## Sorting & sections
- Default sort: by `ets_weight` descending (highest-yield topics first). Provide a toggle to sort by "weakest first" (lowest `avg_recall` among non-abstained).
- Group under the two roots (Calculus / Linear algebra) with a subtle subheader; container topics (weight 0) are headers, not rows.

## States
- **Fresh deck (everything abstains):** that's the honest default — the header line already explains it; don't show scary zeros. Each row shows the unlock hint.
- **Empty / no matching cards:** "No cards found for this exam profile — import the seed deck."
- **Loading:** simple spinner; the RPC is fast.

## Visual language (both platforms)
- Minimal, calm palette; plenty of whitespace; system font. No streaks, no badges, no confetti.
- Range band: neutral track + a filled segment for the interval; point estimate as a thin marker inside it.
- Abstain: reduced opacity + muted text (not red — abstaining is honest, not a failure).
- Everything read-only; the only control is Refresh (+ the sort toggle).

## Placement
- **Desktop:** a new Svelte page in Anki's webview (mirror the built-in Stats/Graphs page pattern), opened from a menu/toolbar entry (e.g. Tools → "Speedrun: Memory").
- **Android:** a Kotlin screen reachable from the AnkiDroid nav/menu, rendering the identical structure from the same RPC.

## Non-goals (today)
- No Performance/Readiness columns yet (Friday) — but lay the grid out so they can be added as columns without a redesign.
- No editing, no AI, no network.
