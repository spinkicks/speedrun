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

### 2026-07-01 — Speedrun Home gate review (branch `feat/speedrun-home`, fixes @ `6341b6f61`)
Cursor reviewed the fix commit diff. **Fixes 1–3 verified correct** (webview `SPEEDRUN` kind in `have_api_access` + used by both dialogs; 4 methods in `exposed_backend_list`; `include_str!` profile bootstrap; `closeWithCallback` on both dialogs). Adversarial + e2e evidence accepted.

**ONE MISS — gate-blocker #4 (auto-open placement) was NOT done.** In `qt/aqt/main.py`, the auto-open is still:
```python
gui_hooks.profile_did_open()
if self.pm.profile.get("speedrunHomeAutoOpenEnabled", True):
    aqt.dialogs.open("SpeedrunHome", self)
self.maybe_auto_sync_on_open_close(_onsuccess)
```
Two problems the spec's fix #4 called out:
1. It fires BEFORE `maybe_auto_sync_on_open_close` → the sync-progress dialog can stack under Home on launch (janky for the headline auto-open demo). Move the auto-open INTO the `_onsuccess(synced)` post-sync callback.
2. No `safeMode` guard → Home auto-opens even in safe mode (recovery mode). Add `and not self.safeMode` (or guard inside `_onsuccess`).

Please fix, keep it config-gated + Tools-fallback as-is, re-run `just check`, and this item is done. No re-review of 1–3 needed. Then David runs `just run` for the visual/GUI-auth confirmation (the only path e2e couldn't exercise) and Cursor merges all three forks to `main`.

## Resolved
- 2026-07-01 — Speedrun Home audit gate-blockers (desktop data path, exam-profile bootstrap, closeWithCallback, auto-open placement + safeMode) were delivered via the paste-block relay + `speedrun-home-spec.md`; channel file created after the fact. Future feedback flows through here.
