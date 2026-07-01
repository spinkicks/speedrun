# Speedrun Home — design spec ("The Run")

**Status:** APPROVED (David, 2026-07-01) after visual mockup review. First slice of the frontend/UX revamp (see `FUTURE-PLANS.md`). Mockup: `docs/design/mockups/speedrun-home.html`.

**Goal.** When you open Speedrun, the first screen is unmistakably OURS — a branded home that shows your honest state (Memory now; Performance/Readiness scaffolded) and a single clear way to start studying. Reuses the frozen `SpeedrunService` RPCs; **no engine changes** — pure frontend (shared Svelte page + per-platform shell wiring).

## Design language ("focused momentum" × quant/terminal, no AI-slop)
Hard rules: **no rounded corners, no gradients, no glow.** Flat, sharp, high-contrast, hairline dividers, monospace numerals, grid-driven. Distinctiveness comes from the SUBJECT (speedrunning + math + honesty), not the styling.

**Tokens**
- Color: `--ink #0B0E12` (bg) · `--panel #12161C` · `--line #232A33` (hairlines) · `--fg #E6EAEF` · `--muted #7C8794` · single accent `--pace #E8B23A` (amber "pace/record" LED). No other accents (add red for "at risk" ONLY if it later earns its place).
- Type: **Space Grotesk** (wordmark + segment headings) · **IBM Plex Mono** (ALL numerals, splits, eyebrow labels, status). Must be bundled/offline-safe for the Anki webview (self-host or fall back to a strong stack; confirm during build).
- Motion: minimal. At most a quiet page-load reveal of the splits and a hover state on rows. Respect `prefers-reduced-motion`.

**Signature element.** The **split row**: `topic  recall%  |—[low‑high]—|  range%  ✓` — knowledge read like a speedrun split with an inline 95% confidence **error-bracket** (bracket = interval, amber tick = point estimate). Abstention reads `NOT TIMED — review N more to unlock a split`. This is the one memorable thing; everything else stays quiet.

## Layout
Fixed max-width column (~960px) with left/right hairline borders.
1. **Run header** — `SPEED``RUN` wordmark (amber "RUN"), mono subtitle `GRE MATHEMATICS · SUBJECT TEST`, right-aligned run status (`RUN ACTIVE · SESSION n · PB PACE` — momentum cue; keep honest/derived, not fake).
2. **Stat row** (3 cells, hairline-separated): **Coverage** `covered/total` + completion meter; **Memory · verified** `timed/total` + meter; **Readiness · pace** `—` abstains today (amber empty meter, clearly scaffolding).
3. **Splits** — heading + sort toggle (default by ETS weight; toggle weakest-timed-first). Segments = top-level topics, numbered `01/02…` by weight (legitimate ordering from the exam DAG), each with `ETS WEIGHT n%`. Leaf rows = the split rows (signature). Abstained rows dimmed with the unlock message.
4. **Action bar** — single primary `► START RUN` (amber) + `NEXT SEGMENT · <weakest timed topic>`.
5. **Footer** — one honest line: "Speedrun measures what you can recall — not a guessed score. Ranges are 95% intervals; untimed segments abstain by design."

## Data contract (existing frozen RPCs — no new proto)
- `getExamProfile({examId:"gre_math"})` → segments (top-level topics), leaf topics, ETS weights, order. Container topics (`ets_weight==0`) = segment headers.
- `getTopicMastery({topics, masteryThreshold:0.9, minReviews:20})` → per-leaf `avgRecall`, `masteredLower/Upper` (the bracket), `gradedReviews`, `cardsWithData`, `abstained`. `unlockN = max(0, minReviews - gradedReviews)`.
- `getCoverage({requiredTags})` → `covered/total/percent` (Coverage cell).
- `getPerformanceReadiness({topics})` → always-abstain scaffolding (Readiness cell + future columns).
- Reuse the row-assembly logic already in `ts/routes/speedrun-memory/data.ts` (extract shared helpers rather than duplicate).

## Entry point (biggest "our app" lever)
- **Desktop:** auto-open Speedrun Home on launch (deck picker still reachable behind it). Ground the startup flow in `qt/aqt/main.py`; add a `SpeedrunHome` dialog (mirror `qt/aqt/speedrun.py`) + register in `dialogs.py` + a Tools entry as fallback. Add "open Speedrun on startup" as a config-gated behavior so it is reversible.
- **Android:** launch into the home PageFragment (mirror the Memory screen wiring); needs the AAR rebuild (bundles the new route) — Claude's engine/Android lane; David runs the emulator smoke.
- **START RUN** opens the exam deck's study session (reuse Anki's reviewer for now; restyling the reviewer is a later revamp slice).

## Non-goals (this slice)
- No restyle of Anki's card reviewer yet (later slice).
- No new engine/proto work.
- Readiness stays abstaining (real model = Friday).
- Full nav shell (Home/Study/Memory/Scores tabs) is a later slice; Home links to the existing Memory dashboard for now.

## Success criteria
- `just run` opens directly into Speedrun Home; branded, flat/sharp, honest (fresh deck abstains; seed deck shows split rows + ranges).
- Same shared Svelte page renders on Android after AAR rebuild (no 404).
- `just check` green (mod. known complexipy crash). AGPL headers on new files. No AI.

## REQUIRED fixes folded into this slice (2026-07-01 audit — gate blockers)
1. **Desktop webview→backend data path:** add `get_coverage`, `get_topic_mastery`, `get_exam_profile`, `get_performance_readiness` to `exposed_backend_list` (`qt/aqt/mediasrv.py` ~L728) AND give the speedrun dialogs an API-enabled `AnkiWebViewKind` (add e.g. `SPEEDRUN` to `_profileForPage`, `qt/aqt/webview.py` ~L136). `DEFAULT` kind has NO API access — without both fixes every RPC POST 403s and the page shows only an error. Android needs nothing (bridge already wired).
2. **Exam-profile bootstrap:** fresh collections return `""` from `GetExamProfile` → Home/Memory error forever. Bootstrap `speedrun/exam_profiles/gre_math.json` into collection config (engine `include_str!` default or set-on-open; both platforms must resolve it).
3. **Dialog lifecycle:** `closeWithCallback` on `SpeedrunHome` + `SpeedrunMemory` (mirror `stats.py` L86-88) — `DialogManager.closeAll` crashes on quit/profile-switch without it; mainline once Home auto-opens.
- **Gate evidence:** the page RENDERED with live data — screenshot of desktop Home (fresh-collection abstain state and/or seed-deck split rows), not just a green build. (Process rule from the audit: UI gates require visual proof.)

## Coordination note
`ts/` + `qt/aqt` shell = **Cursor's lane**; engine/Android/AAR = **Claude's lane**. Only one branch can be checked out in the shared `repos/anki` tree — sequence so Cursor and Claude are not editing/building `repos/anki` simultaneously.
