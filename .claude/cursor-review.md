<!-- CURSOR → CLAUDE review channel.
     Cursor (mission control) writes gate feedback / fix requests / decisions here.
     Claude reads this at each gate (or when told "read cursor-review.md").
     Protocol:
       - Cursor appends a new dated block at the TOP under "## Pending".
       - When Claude has addressed a block, it (or Cursor) moves it to "## Resolved".
       - Keep it terse: what to do + where (file:line) + why. Not a chat log.
     This file lives in the umbrella repo only; it is NOT pushed to the public forks. -->

# Cursor → Claude review channel

## Pending

### 2026-07-01 — NEW PLAN: Mobile-first UX + START RUN fixes + reviewer restyle
David tested on-device and found bugs. **Read `docs/plans/2026-07-01-mobile-first-and-startrun.md`** (Cursor-authored brief), ground it into a task-by-task plan, and post it for Cursor review before executing. Summary:
- **Bug — desktop START RUN** dead-ends into stock Anki "Congratulations" (`_start_run` → `moveToState("overview")` with no due cards). Fix: launch real study on the exam deck + honest fallback states surfaced in OUR UI.
- **Bug — Android START RUN** is a no-op (documented: no pycmd bridge in PageFragment). Fix: wire native study-launch (verify-first how other AnkiDroid pages trigger native nav).
- **Mobile-first redesign** (manager directive — mobile is the harder target, build it first): responsive rework of shared Home + Memory (fix one-word-per-line wrapping; stacked mobile layout → columns on desktop); fold in Android toolbar/system-bar dark theming.
- **Reviewer restyle** (David chose this scope) — LAST phase, presentation-only, two surfaces (desktop web reviewer + Android native reviewer), ZERO scheduling changes.
- Order M0→M1→S1→S2→R1 on new branch `feat/speedrun-mobile-first`; screenshot at mobile (~360px) AND desktop for every gate; Cursor gates + FF-merges.
- AFTER: demo script (`docs/DEMO-SCRIPT.md`), doc refresh, grader-launch README accuracy — Cursor tracks as todos.

## Resolved
- 2026-07-01 — Speedrun Home gate-blocker #4 (auto-open placement): FIXED. Moved the `SpeedrunHome` auto-open out of the pre-sync spot and INTO `_onsuccess` (the post-sync callback passed to `maybe_auto_sync_on_open_close`), inside the existing `if not self.safeMode:` guard — so the sync-progress dialog no longer stacks under Home on launch, and Home is skipped in safe/recovery mode. Config-gate (`speedrunHomeAutoOpenEnabled`) + Tools-menu fallback unchanged. `qt/aqt/main.py:523-536`; anki `52bcefa7e` on `feat/speedrun-home` (pushed). `just check` green (mod. known complexipy crash). Fixes 1–3 already accepted. → Ready for David's `just run` visual/GUI-auth confirmation, then Cursor FF-merges all three forks to `main`.
- 2026-07-01 — Speedrun Home audit gate-blockers (desktop data path, exam-profile bootstrap, closeWithCallback, auto-open placement + safeMode) were delivered via the paste-block relay + `speedrun-home-spec.md`; channel file created after the fact. Future feedback flows through here.
