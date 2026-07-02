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

### 2026-07-02 (THU) — ✅ FRIDAY PLAN APPROVED + 🎨 BRANDING SLICE GREENLIT — two tracks this cycle
David's calls (2026-07-02): run **both tracks** this cycle; Friday design decisions **D1–D4 APPROVED**; branding gets a **new visual direction** (see below).

**TRACK A — Friday plan `docs/plans/2026-07-03-friday-ai-scores-sync.md`: APPROVED — START NOW.**
- **D1–D4 confirmed** (in-engine deterministic Performance; recompute-on-read scores, NO separate synced blob; extend `GetPerformanceReadiness` append-only; filtered-deck mini-mock). D2's deviation from the brief (recompute-on-read vs persist) is accepted — it's the more honest + deterministic choice; do NOT add the score blob.
- **Start immediately with Phase 0 → Phase 1** (they have ZERO open-question blockers: N+1 batch, determinism pin, then the due-card interleave that completes the headline Rust change). Cursor gate-reviews at Gate 0 and Gate 1 as specified.
- **Phases 2–6 gating on David's open answers (do NOT block Phase 0/1 on these):**
  - **#3 mini-mock length → DECIDED: 10 problems @ 2.5 min/q** (Decision 13 default). Wire this as the config default in Task 3.2; still config-driven.
  - **#1 problem-bank floor → interim default ≥8 scorable problems per leaf** to enable a 10-item mini-mock; abstain below it (honest). David curates the real content Thu-night/Fri; treat the seed set as a starter, keep everything abstaining until the floor is met. (David to confirm/raise the floor.)
  - **#2 LLM/API → DECIDED: OpenAI (GPT).** Task 4.2: use the OpenAI SDK; read the key from `services/speedrun-ai/.env` as **`OPENAI_API_KEY`** (already gitignored via root `.env`/`.env.*`). Ship a committed `services/speedrun-ai/.env.example` with a placeholder. Service stays OFF unless `SPEEDRUN_AI_ENABLED=1` + key present. David drops the real key into that `.env` locally when you reach Phase 4 — do NOT ask for it in chat or write it to any tracked file.
  - **STILL BLOCKING their phases (David owes, not blocking today):** #4 gold-set 50 pairs authored by David/Cursor in `eval/holdout/` (blocks Task 4.4 gate; agents must NOT read/write it), #5 permanent `PROBLEM_MODEL_ID` (blocks Task 3.1 — David picks a fixed id, never reuse `1607392319`).
- Sequence so Phase 4 (AI service, umbrella `services/`) runs parallel-safe; don't build `repos/anki` while Track B builds `ts/qt`.

**TRACK B — Branding / de-Anki-fication identity slice: GREENLIT, spec ready.** `docs/design/speedrun-identity-spec.md` (+ mockup `docs/design/mockups/speedrun-identity.html`). **New visual direction (David):** the v1 "The Run" look read too AI/code — so:
  - **Typography (LOCKED):** drop Space Grotesk display + the all-monospace numerals; use **Manrope ExtraBold (800)** for wordmark/headings and **Manrope** with `tabular-nums` for numerals (kills the "code" look while keeping column alignment). Retire `--mono` from these surfaces. **Bundle Manrope 500+800 woff2 OFFLINE** (OFL; no CDN — offline is a hard req like the installer). Fallback `"Manrope","Segoe UI",system-ui,sans-serif`.
  - **Accent (LOCKED):** replace amber `--pace #e8b23a` → **near-white `--pace #F4F7FA`**. White primary CTA on dark; white point-estimate tick; hierarchy via weight/size, not color. Dark base unchanged.
  - **Wordmark (LOCKED):** subtle SPEED+RUN split — `SPEED` in `--fg #E6EAEF`, `RUN` in `--pace #F4F7FA`. **Icon = TYPE-ONLY this cycle** (Manrope `S` monogram placeholder + white-tile adaptive variant; NO bespoke logo — don't sink time into icon design). Full spec: `docs/design/speedrun-identity-spec.md` (LOCKED).
  - **Deliverables:** re-skin Home+Memory tokens (change token DEFINITIONS in `SpeedrunHome.svelte` ~L133-143; grep every `--pace`/`var(--mono)`); **app name "Speedrun"** on desktop window title+icon and Android launcher label+icon; **Anki-chrome trimming** (default path Home→Study→Memory/Scores; deck picker/menus demoted, not deleted). Pure presentation/shell; ZERO engine/proto. Screenshot-gate BOTH platforms.
  - **Nav shell is NOT this slice** — it folds into Friday Phase 5 (same Svelte surface as scores). This slice = font/accent/branding/chrome only, so we don't restyle nav twice.

**Folds in the Memory "back to Home" gap** (below) → handled by the nav-shell slice in Friday Phase 5, not separately.

### 2026-07-01 — 🐞 UX gap (desktop): Memory dashboard has no "back to Home"
David caught this while recording. Desktop Memory opens as its own `SpeedrunMemory` QDialog (`aqt.dialogs.open("SpeedrunMemory")`), so there's no in-page way back to Home — Home links INTO Memory ("MEMORY ▸" in `SpeedrunHome.svelte`) but Memory has no return path. One-way trip.
**Fix (small, low priority — schedule with Friday UI or as a quick standalone):** add a "‹ HOME" / back affordance on the Memory page that returns to Home. Options: (a) a bridge cmd `open:home` mirroring Home's `open:memory` (desktop `_on_bridge_cmd` in `qt/aqt/speedrun.py` opens `SpeedrunHome`; Android nav back); or (b) simplest — since Memory is a separate desktop dialog, a "‹ HOME" link that closes Memory (returns focus to the still-open Home) + on Android navigates up. Keep it in the shared Svelte page so both platforms get it. Screenshot-gate. NOT blocking the Wednesday submission — desktop demo just uses Home's link into Memory, not back.

### 2026-07-01 — 📋 FRIDAY PLAN READY FOR YOUR REVIEW (grounded, not executed)
Per your note, I grounded `docs/plans/2026-07-03-friday-brief.md` into a full task-by-task TDD plan: **`docs/plans/2026-07-03-friday-ai-scores-sync.md`**. Grounding was a 6-agent read-only sweep of the actual source (queue builder, proto/scoring scaffolding, problem/seed layer, AI-service/eval surface, UI/sync, PRD-requirements map) — every file:line verified. **NOT executed — awaiting your review.**

**Structure:** Phase 0 (verify the 2 unverified prereqs) → Phase 1 (due-card interleave) → Phase 2 (proto + scores) → Phase 3 (problem layer) → Phase 4 (AI service, parallel-safe) → Phase 5 (UI) → Phase 6 (AAR re-pin + sync demo). Maps 1:1 to brief Items 1–6.

**Key grounded findings that shaped it:**
- **Prereqs:** 4/5 carry-in fixes already merged; **#4 (get_topic_mastery N+1) and #5 (Full-mode determinism test) are NOT done** — Phase 0 does them first (bench/ablation are meaningless until then).
- **Item 1 interleave is read-time / NO transact:** new `QueueBuilder::sort_review()` off `build()` (`builder/mod.rs:187`, mirrors `sort_new`), gated by `AblationMode` (which is NOT currently threaded into the builder — must plumb from synced config). The persisted new-card reposition already satisfies the mutating-op requirement.
- **Proto stays frozen-compatible:** append-only fields (verified next-free numbers: `ScoreScaffold`=5, `TopicScaffold`=4, `PerformanceReadinessResponse`=4) + a new `ScoreScale` enum so Readiness 200–990 isn't misread as the 0–1 band.
- **TS boundary bug spotted:** `ScaffoldCell` (`data.ts:87-89`) currently DROPS `point/lower/upper` (proto already delivers them) — that's why Perf/Readiness render "—". Phase 5 widens it.

**4 design decisions I made (brief delegates them) — please confirm:**
- **D1** Performance = **in-engine deterministic** (FSRS recall + observed problem accuracy + coverage; abstains), IRT difficulty fit **offline** and baked into Problem notes. Rationale: kill-switch-safe + deterministic for the ablation/rubric + honest. (Not a live service-side fit.)
- **D2** Scores are **recomputed on read, not persisted** in a separate synced blob — deterministic-from-synced-inputs ⇒ byte-identical on both platforms without fighting Anki's whole-blob config sync. (Deviation from the brief's "persist in config blob" — flag if you want literal persistence for audit.)
- **D3** **Extend** `GetPerformanceReadiness` (append-only), don't split into `GetPerformance`/`GetReadiness`.
- **D4** Mini-mock = **Anki filtered deck** over `tag:Speedrun::Problem` (per-answer wall-clock already in `revlog.taken_millis` — zero engine change).

**Open questions for David (block specific tasks; in the plan's final section):** (1) problem-bank floor per topic; (2) which LLM/API + key; (3) mini-mock length (recommend 10 @ 2.5 min/q); (4) gold-set authorship (you/Cursor write the 50 pairs in `eval/holdout/` — agents must not); (5) permanent `PROBLEM_MODEL_ID`. **Review the plan + these decisions; I'll revise or start Phase 0 on your go.**

### 2026-07-01 — Package the desktop installer (for the clean-machine recording)
Mobile-first + START RUN all merged + David-verified on BOTH platforms (Android review session confirmed). Last Wednesday gap = the installer artifact. **Please build the packaged desktop installer** so David can run it in Windows Sandbox and record the clean-machine install:
- From `repos/anki` on `main`: `uv run python qt/tools/build_installer.py --version "$(cat .version)" build` then the `… package` step → produce the real `.exe`/`.msi` and report its exact output path + size.
- Confirm it builds with NO network submodule fetch (the Phase-0 vendoring should hold) and that `qt/tests/test_installer.py` still passes.
- Windows installer only (`.dmg` is out of scope — decided; macOS-CI is the documented fallback). Report the artifact path when done; Cursor updates `WEDNESDAY-DELIVERABLES.md`.
- Then you're clear to switch to grounding the **Friday brief** (`docs/plans/2026-07-03-friday-brief.md`) into a full plan for Cursor review (Thursday work — do whenever).

**→ Claude 2026-07-01 — ✅ INSTALLER BUILT (offline) + test green. Artifact ready; one quality decision pending David.**
- **Canonical build path used** (not the raw `build_installer.py` one-liner — that omits our fork wheels and would pull upstream Anki from PyPI): `tools\ninja installer:package`, which builds `:wheels:anki` + `:wheels:aqt` from our fork, runs briefcase `build`, then `package` (WiX → MSI). Built from `main` @ `af1138428`.
- **Artifact:** `repos/anki/out/installer/dist/anki-26.05-win-x64.msi` — **636,633,982 bytes (~607 MiB)**. Valid MSI (OLE magic `d0cf11e0`). Built in 288s, 19 ninja tasks.
- **Offline confirmed:** no submodule fetch, no template clone, no network. The Phase-C **vendoring held** — `qt/installer/windows-template` is now in-tree (empty `.gitmodules`, 19 files), not an uninitialized submodule; briefcase used the local cookiecutter template + the warm briefcase cache (support pkg / WiX / stub all present).
- **`qt/tests/test_installer.py` → 27 passed** (incl. `test_build_and_package` + `test_compile_fails_loudly`, the two that previously failed on the `v0.4.2` template-clone). The known-CI installer failures are RESOLVED.
- **✅ RELEASE=1 rebuild done (David's call).** Rebuilt with the Release profile (`out/env`=`;1;` → cargo `--release`, opt-level 3 → **optimized engine**), then packaged directly (as CI does — `build_installer.py package`, since the ninja `installer:package` target doesn't re-run package after a reconfigure) with `compression_level="high"`.
  - **FINAL artifact:** `repos/anki/out/installer/dist/anki-26.05-win-x64.msi` — **627,602,302 bytes (~599 MiB)**, valid MSI (`d0cf11e0`), engine = release (opt-level 3), MSI compression = high. Offline; `test_installer.py` 27/27.
  - **Size note (honest):** it only dropped ~9 MB vs the debug MSI, most of that from smaller release binaries — WiX LZX compresses the Qt6+Chromium payload poorly, so it stays ~599 MB (upstream Anki ships smaller via a different pipeline + stripped symbols). Fully functional for a Windows-Sandbox recording. Meaningfully shrinking it = a separate packaging task (strip symbols / prune Qt / stronger compression) — out of scope here; can do on request.
- **This block can move to Resolved.** Next: Friday-brief grounding per your note.

### 2026-07-01 — ✅ RESOLVED (was GATE FAIL): S1 desktop START RUN false "all caught up"
**Fixed (`f0a06ce68`) + David-verified 2026-07-01 20:35** — START RUN now launches a real review session (20 new cards due, dark reviewer confirmed on-screen). Fix used `col.sched.deck_due_tree(did)` + a characterization regression test. Merge to `main` pending only Claude's QA-sweep triage (bug-class hunt). Original report retained below.

### (original) 🐞 GATE FAIL (S1 desktop START RUN): false "all caught up"
David's smoke test caught a real bug. After importing the seed deck (coverage correctly shows 9/9), clicking **START RUN** shows **"ALL CAUGHT UP FOR TODAY"** even though the deck HAS due cards (he studied one via the normal Decks path — screenshot confirms a reviewable card).

**Root cause (grounded):** `SpeedrunHome._start_run` computes due from `self.mw.col.decks.deck_tree()`, which is the **structural** tree with **no scheduling counts** — its `new_count`/`review_count`/`learn_count` are 0. `pylib/anki/scheduler/legacy.py:114` literally says: *"use decks.deck_tree() for a tree without counts, or sched.deck_due_tree()."* So `due` is always 0 → false caught-up; real study never launches.

**Fix:** get the due counts from the scheduler, not the structural tree. `col.sched.deck_due_tree(did)` (overload `deck_due_tree(top_deck_id: DeckId) -> DeckTreeNode | None`, `pylib/anki/scheduler/base.py:74`) returns the deck's node WITH counts (or None). Suggested:
```python
did = self.mw.col.decks.id_for_name(self.EXAM_DECK)
if did is None: … importNeeded; return
node = self.mw.col.sched.deck_due_tree(did)      # scheduler tree = real counts
due = 0 if node is None else (node.new_count + node.review_count + node.learn_count)
if due == 0: … caughtUp(new_left); return
self.mw.col.decks.select(did); self.close(); self.mw.moveToState("review")
```
(Drop the `decks.find_deck_in_tree(decks.deck_tree(), …)` usage.) **Verify on Android S2 too** — the Kotlin path used `sched.deckDueTree().find(did)?.hasCardsReadyToStudy()`; that one likely IS the scheduler tree (correct), but confirm it isn't the countless structural tree. Re-run David's Step 3 after the fix: import → START RUN → real review launches.

**Verified GOOD in the same smoke (no action):** no-deck "import" banner ✅; caught-up banner UI + Custom Study button ✅; **R1a desktop dark reviewer ✅** (dark chrome + MathJax render confirmed); coverage 9/9 after import ✅. Only the due-count logic is wrong.

**→ Claude 2026-07-01 — ✅ FIXED exactly as you prescribed. anki `f0a06ce68` on `feat/speedrun-mobile-first` (pushed).**
- **Fix:** `_start_run` now reads counts from `col.sched.deck_due_tree(did)` (real counts), dropped the `decks.find_deck_in_tree(decks.deck_tree(), …)` structural-tree usage. Confirmed at the engine level too: `rslib/src/decks/service.rs:65` maps `now==0 → None` and `rslib/src/decks/tree.rs:263` then **skips the entire counts block** → your "structural tree has 0 counts" diagnosis is exactly right.
- **Refactor for testability:** extracted the decision into a **Qt-free** `qt/aqt/speedrun_logic.py::decide_start_run` (importNeeded / caughtUp / ready) so it's unit-testable without a QApplication. `_start_run` is now thin glue. Presentation-only w.r.t. scheduling: read-only counts; no `transact`/FSRS/`answerCard`.
- **Android (your ask to verify S2):** confirmed CORRECT — `SpeedrunHomeFragment.onStartRun` uses `sched.deckDueTree().find(did)?.hasCardsReadyToStudy()` = the **scheduler** tree, not the countless structural one. No change needed.
- **Regression tests:** new `qt/tests/test_speedrun.py`, 4/4 green (`check:pytest:aqt` + direct pytest), ruff+format+mypy green. Covers importNeeded / caughtUp / ready **+ a characterization test** that pins the mechanism on a live collection with a due card (`decks.deck_tree()`→`new_count==0`; `sched.deck_due_tree()`→`new_count==1`) so this can't silently regress. **Root cause of the miss:** e2e bypasses the Qt bridge (`pycmd` no-op) so `_start_run` had zero automated coverage — now closed.
- **QA sweep (David's ask — DONE):** independent 12-agent read-only audit of 5 Speedrun cross-layer contract areas, every finding adversarially verified. **45 contracts confirmed correct**; of 7 reported issues, **6 refuted** as dead-code/latent/test-coverage (not user-facing), **1 confirmed real** and now fixed:
  - **✅ FIXED `af1138428` — desktop START RUN double-fire.** `ActionBar.svelte` fired BOTH `pycmd` + `bridgeCommand`, but the Qt webview aliases them to the **same function** (`qt/aqt/webview.py:93`) → `startrun` dispatched twice → `_start_run()` ran twice (redundant `decks.select` + double `moveToState("review")` = reviewer re-entry). Android injects only `bridgeCommand`, so it was unaffected. Fix: fire exactly one, `(g.pycmd ?? g.bridgeCommand)?.("startrun")` — correct on desktop/Android/dev. Low severity (terminal state was correct; worst case a flicker), but same bug-class as the caught-up fix so worth closing. `check:svelte` green.
  - **Explicitly verified GOOD (no action):** deck name `"Speedrun::GRE Math"` byte-identical across desktop/Android/seed/test; due-count semantics provably equivalent desktop↔Android (`sum>0 ⇔ any>0`, both on the `now=int_time` scheduler tree); all 4 RPCs allow-listed + `SPEEDRUN` webview API-enabled; TS↔proto field shapes match; Memory/Home CSS tokens all defined (no phantom); `_custom_study` selects deck before Custom Study; command routing order correct; Android snackbar action wired.
- **Both fixes on `feat/speedrun-mobile-first`** (anki tip `af1138428`, pushed). Caught-up fix already David-verified on `just run`. **Ready for your FF-merge to `main`** (double-fire fix is desktop-web only — David can eyeball on next `just run`, but it's low-risk and typecheck-green).

### 2026-07-01 — Mobile-first + START RUN + reviewer plan: ✅ APPROVED — EXECUTE
Cursor reviewed `docs/plans/2026-07-01-mobile-first-and-startrun-plan.md` → **APPROVED**. Grounding + invariants + gates all solid. **Proceed: execute M0→M1→S1→S2→R1 on `feat/speedrun-mobile-first` (off `main`), subagent-driven, mobile(~360px)+desktop / emulator screenshot at every phase gate, post to this channel; Cursor FF-merges each phase.**

**David's 3 decisions (folded into the plan's Decisions section — honor these):**
1. **Nothing-due:** honest "All caught up" banner **+ a Custom Study button** (wire to Anki Custom Study on the exam deck, desktop + Android).
2. **Reviewer (R1): FULL chrome theming**, both platforms — presentation-only, ZERO scheduling. Prefer keeping "The Run" dark scoped to the Speedrun-launched reviewer WITHOUT globally overriding the user's theme; flag at the R1 gate if it must go global. **If R1 balloons or risks the Friday scoring work, STOP and flag — descope/split it; M0/S1/S2 are the priority wins.**
3. **Android fallback:** themed snackbar.

No other changes to the plan. NO AI. AGPL/GPL headers per repo.

**UPDATE 2026-07-01 — M0 APPROVED + MERGED to anki `main` (`0c5112957`).** Cursor reviewed the CSS diff (correct mobile-first base + `@media(min-width:768px)` desktop restore; compact abstain copy) + accepted the e2e no-overflow evidence. **Proceed to M1.**
**Added task (fold in — small): theme the Memory page dark to match "The Run".** You correctly flagged Memory renders LIGHT while Home is dark (Memory predates the dark tokens + used non-existent `--accent`/`--frame-bg`, per the earlier audit). Since David chose full dark theming everywhere, re-theme `ts/routes/speedrun-memory/*` to the same `--ink/--panel/--line/--fg/--muted/--pace` tokens as Home (real tokens, not the missing ones) so the whole app is consistently "The Run". Do this alongside M1/S-phases (your call where it slots); screenshot-gate it with the rest. This resolves the audit's RangeBand-token finding too.

**→ Claude 2026-07-01 — MOBILE-FIRST CYCLE CODE-COMPLETE (S1/S2/R1 gate; awaiting your FF-merges + David's visual gates).** Branch `feat/speedrun-mobile-first` on all 3 forks (pushed): anki `00a1e45c3`, anki-android `fdfd086031`, Anki-Android-Backend `9aa21ec` (rsdroid pin → anki `eb4f5a3ff`; AAR rebuilt + app assembleDebug green).
- **S1 (desktop START RUN, `d0719ab1d`):** rewrote `_start_run` — resolve `"Speedrun::GRE Math"` → launch reviewer if due; else honest IN-PAGE banner (import / all-caught-up **+ Custom Study button**). Real dialogs: `mw.onImport()`, `CustomStudy.fetch_data_and_show`. No more Anki-congrats dead-end. Banner e2e passes; 3-state `just run` gate = David.
- **S2 (Android START RUN):** `eb4f5a3ff` shared ActionBar fires both `pycmd`+`bridgeCommand` (guarded, cross-platform); `fdfd086031` `SpeedrunHomeFragment.bridgeCommands["startrun"]` → `Reviewer.getIntent` on the exam deck + themed snackbar fallbacks (import / all-caught-up + Custom Study via `CustomStudyDialog`). AAR re-pinned+rebuilt (bundle has speedrun-home + `bridgeCommand`), app assembleDebug green. Emulator gate = David.
- **R1 (minimal, per David):** R1a desktop reviewer `00a1e45c3` — "The Run" dark chrome via `:root.night-mode` CSS var overrides (bg + buttons + bars); CSS-only, ZERO scheduling/`#qa`/`data-ease`; confirmed compiled into `out/.../reviewer.css`. Rides Anki night-mode (scoped-to-Speedrun refinement deferred). `just run` Dark-theme gate = David. **R1b Android reviewer = DEFERRED (correctly flagged, no change):** `CardViewerActivity` is shared with Previewer/TemplatePreviewer, so no clean per-screen scope without touching the START RUN launch path or globally recoloring all dark-mode users — both out of "minimal/no-over-reach". Clean post-Friday path documented: add a thin `SpeedrunReviewerActivity` + scoped `Theme.Speedrun.Reviewer`. Full-chrome reviewer polish also deferred per your R1 decision.
- **David's visual gates queued** (I can't drive GUI/emulator): M1 dark shell · S1 3-state START RUN · S2 tap→reviewer/snackbar · R1a desktop reviewer (Dark theme + review a card).

**→ Claude 2026-07-01 — M1 + Memory-dark + UI bug-hunt gate (awaiting your review/FF-merge + David's emulator).**
- **M1 (Android shell dark theming):** `anki-android feat/speedrun-mobile-first @ 776117580c` (pushed). Scoped `applySpeedrunDarkShell` helper on both Speedrun fragments (dark toolbar + status/nav bars, light icons), mirroring `NoteEditorFragment`; verified NOT global (each `SingleFragmentActivity` resets on its own `onCreate`). `assembleDebug` BUILD SUCCESSFUL. No AAR change. **Emulator visual gate = David.**
- **Memory-dark re-theme (your folded-in task + fixes the bug-hunt blocker):** `anki feat/speedrun-mobile-first @ 281db9420` (pushed). Memory now uses the REAL dark tokens (`--ink/--panel/--line/--fg/--muted/--pace`); replaced ALL phantom tokens (`--accent`→`--pace`/faint `--fg`, `--frame-bg`→`#0a0d11`+`--line`, `--fg-subtle`→`--muted`, `--border`→`--line`) — grep confirms none remain. This also resolves the audit's RangeBand-token finding. Verified DARK at runtime (`.memory` bg = `#0B0E12`). Screenshots sent to David.
- **UI bug-hunt (David's ask — 3 independent testers):** live Playwright smoke `@ ef0407f3e` (11/11 pass: zero console errors, zero failed `/_anki/*` POSTs, no 360px overflow, interactions safe — sort toggle, START RUN no-op, Weakest-first). Read-only UX + logic critics. Findings: the light-Memory blocker (now FIXED) + minor touch targets (FIXED: 44px on sort + weakest-first). **Reviewed-no-change:** segment ETS-weight % is intentionally the raw honest per-segment weight (not normalized — normalizing would reduce honesty if leaves sum <1.0). **Backlogged (surfaced, not fixed):** i18n/FTL + MathJax topic labels (pre-existing FUTURE-PLANS). Data/logic layer clean (guards, sort, keys, error/empty states all sound). Next: S1 (desktop START RUN + Custom Study).

**→ Claude 2026-07-01 — M0 GATE (mobile-first responsive) DONE, awaiting your FF-merge.** Branch `feat/speedrun-mobile-first` off `main` @ `0c5112957` (pushed to `spinkicks/anki`): `5ee33b3a0` = mobile-first CSS across all 9 Home+Memory components (base ~360px stacked; `@media(min-width:768px)` restores the EXACT current desktop layout — desktop visually unchanged; compact abstain copy <480px), `0c5112957` = e2e responsive gate test. Evidence: `just test-e2e` 4/4 pass; **no horizontal overflow at 360px** (asserted ≤2px both pages); both pages render live data at 360px AND 1280px. Screenshots sent to David: `scratchpad/m0-{home,memory}-{360,desktop}.png`. `just check` green (mod. complexipy). **Observation (not an M0 defect):** the Memory page renders LIGHT while Home is dark "The Run" — pre-existing (Memory predates the dark tokens); re-theming Memory to dark is out of M0 scope — flagging as a possible follow-up (fold into R-series or a Memory-dark slice?). Next: M1 (Android shell theming) after your M0 merge.

## Resolved
- 2026-07-01 — Speedrun Home gate-blocker #4 (auto-open placement): FIXED. Moved the `SpeedrunHome` auto-open out of the pre-sync spot and INTO `_onsuccess` (the post-sync callback passed to `maybe_auto_sync_on_open_close`), inside the existing `if not self.safeMode:` guard — so the sync-progress dialog no longer stacks under Home on launch, and Home is skipped in safe/recovery mode. Config-gate (`speedrunHomeAutoOpenEnabled`) + Tools-menu fallback unchanged. `qt/aqt/main.py:523-536`; anki `52bcefa7e` on `feat/speedrun-home` (pushed). `just check` green (mod. known complexipy crash). Fixes 1–3 already accepted. → Ready for David's `just run` visual/GUI-auth confirmation, then Cursor FF-merges all three forks to `main`.
- 2026-07-01 — Speedrun Home audit gate-blockers (desktop data path, exam-profile bootstrap, closeWithCallback, auto-open placement + safeMode) were delivered via the paste-block relay + `speedrun-home-spec.md`; channel file created after the fact. Future feedback flows through here.
