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

### 2026-07-01 — Mobile-first + START RUN + reviewer plan: ✅ APPROVED — EXECUTE
Cursor reviewed `docs/plans/2026-07-01-mobile-first-and-startrun-plan.md` → **APPROVED**. Grounding + invariants + gates all solid. **Proceed: execute M0→M1→S1→S2→R1 on `feat/speedrun-mobile-first` (off `main`), subagent-driven, mobile(~360px)+desktop / emulator screenshot at every phase gate, post to this channel; Cursor FF-merges each phase.**

**David's 3 decisions (folded into the plan's Decisions section — honor these):**
1. **Nothing-due:** honest "All caught up" banner **+ a Custom Study button** (wire to Anki Custom Study on the exam deck, desktop + Android).
2. **Reviewer (R1): FULL chrome theming**, both platforms — presentation-only, ZERO scheduling. Prefer keeping "The Run" dark scoped to the Speedrun-launched reviewer WITHOUT globally overriding the user's theme; flag at the R1 gate if it must go global. **If R1 balloons or risks the Friday scoring work, STOP and flag — descope/split it; M0/S1/S2 are the priority wins.**
3. **Android fallback:** themed snackbar.

No other changes to the plan. NO AI. AGPL/GPL headers per repo.

## Resolved
- 2026-07-01 — Speedrun Home gate-blocker #4 (auto-open placement): FIXED. Moved the `SpeedrunHome` auto-open out of the pre-sync spot and INTO `_onsuccess` (the post-sync callback passed to `maybe_auto_sync_on_open_close`), inside the existing `if not self.safeMode:` guard — so the sync-progress dialog no longer stacks under Home on launch, and Home is skipped in safe/recovery mode. Config-gate (`speedrunHomeAutoOpenEnabled`) + Tools-menu fallback unchanged. `qt/aqt/main.py:523-536`; anki `52bcefa7e` on `feat/speedrun-home` (pushed). `just check` green (mod. known complexipy crash). Fixes 1–3 already accepted. → Ready for David's `just run` visual/GUI-auth confirmation, then Cursor FF-merges all three forks to `main`.
- 2026-07-01 — Speedrun Home audit gate-blockers (desktop data path, exam-profile bootstrap, closeWithCallback, auto-open placement + safeMode) were delivered via the paste-block relay + `speedrun-home-spec.md`; channel file created after the fact. Future feedback flows through here.
