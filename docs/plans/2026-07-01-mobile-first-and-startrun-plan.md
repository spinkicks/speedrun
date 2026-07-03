# Mobile-First UX + START RUN + Reviewer Restyle — EXECUTABLE PLAN

> **STATUS: APPROVED 2026-07-01 (see "Cursor gate verdict" below) — EXECUTED and merged to anki `main`.** Grounded by Claude 2026-07-01 from the Cursor brief `docs/plans/2026-07-01-mobile-first-and-startrun.md` (read that for intent/decisions). This file is the task-by-task version. (Historical record: the plan was approved at the Cursor gate and the M0/M1/S1/S2/R1 work is on `main`.)
>
> **REQUIRED SUB-SKILL when executing:** subagent-driven-development (fresh implementer per task + spec/quality review). Steps use `- [ ]` checkboxes.

**Goal.** Fix the two START RUN bugs (desktop dead-ends into stock Anki congrats; Android is a no-op), make the shared Home + Memory pages mobile-first responsive, theme the Android shell dark, and restyle both reviewers to "The Run" — all **presentation/navigation only**.

**Architecture.** Shared SvelteKit pages (`ts/routes/speedrun-home`, `ts/routes/speedrun-memory`) render on both platforms; desktop shell = `qt/aqt/speedrun.py` dialogs + Qt reviewer; Android shell = `PageFragment`s + native `ReviewerFragment`. START RUN crosses the web→native boundary differently per platform (desktop `pycmd`, Android `bridgeCommand`).

**Branch.** `feat/speedrun-mobile-first` off `main` (all 3 forks currently on `main`).

**HARD invariants (all phases).** Presentation/navigation ONLY — never touch scheduling, `Collection::transact`, proto, FSRS, answer-button intervals, `data-ease`, `_answerCard`/`ReviewerViewModel.answerCard`, or card-content templates. No AI. AGPL headers (engine/`ts`) / GPL-3.0 (`anki-android`). If any change would touch scheduling/order → STOP and flag.

**Gate rule (from the 2026-07-01 audit).** Every UI phase is verified by an ACTUAL render — screenshot at **mobile ~360–390px AND desktop** (or emulator for Android) — before its gate. A green build is not sufficient. Reuse the Playwright e2e harness (`ts/tests/e2e/`, `just test-e2e`, `page.setViewportSize` for widths) that produced the audit screenshot.

**Order:** M0 → M1 → S1 → S2 → R1, then post-deliverables. M0 first (mobile-first directive). Cursor gates + FF-merges each phase.

---

## Grounded facts (confirmed 2026-07-01; APIs the plan relies on)
- **Seed/exam deck:** name `"Speedrun::GRE Math"` (deck id 2059400110), built by `repos/anki/speedrun/seed/build_seed_deck.py:62`; ships as `speedrun/out/gre_math_seed.apkg`.
- **Desktop deck resolve/due:** `mw.col.decks.id_for_name(name) -> DeckId | None` (`pylib/anki/decks.py:141-154`); due counts from `mw.col.decks.deck_tree()` → `DeckTreeNode{new_count, review_count, learn_count}`, located via `Decks.find_deck_in_tree(root, did)`.
- **Desktop launch study:** `mw.col.decks.select(did)` then `mw.moveToState("review")` (`qt/aqt/main.py` `_reviewState`). `overview` redirects to `deckBrowser` when nothing selected — the current dead-end path we're replacing.
- **Desktop Qt→page push:** `self.web.eval(js)` / `evalWithCallback` (`qt/aqt/webview.py:735-755`); page→Qt is `pycmd(...)` (already wired via `set_bridge_command` in `speedrun.py`).
- **Android web→native:** `bridgeCommand("name")` → fragment `override val bridgeCommands = mapOf("name" to { … })` (pattern: `CongratsPage.kt` `"customStudy" to { onStudyMore() }`). `bridgeCommand` global is injected by `PageFragment.setupBridgeCommand()` ONLY when the map is non-empty.
- **Android launch study:** `withCol { decks.select(did) }` + `startActivity(Reviewer.getIntent(requireContext()))` (`Reviewer.getIntent` picks `ReviewerFragment` vs legacy `Reviewer` via `Prefs.isNewStudyScreenEnabled`); due via `withCol { sched.deckDueTree().find(did) }?.hasCardsReadyToStudy()` (`DeckNode.hasCardsReadyToStudy() = rev|new|lrn > 0`). Deck-id-by-name: `withCol { decks.idForName("Speedrun::GRE Math") }` (confirm exact Kotlin method during S2).
- **Mobile CSS:** current fixed `max-width:960px` (home) / `820px` (memory) + pixel-width columns in `SplitRow`/`TopicRow` collapse to one-word-per-line on phones. `ts/lib/sass/breakpoints.scss` has a `with-breakpoint` mixin (md=768px). `app.html` viewport meta is correct. Precedent: `GraphsPage.svelte` uses `@media (max-width:600px)` full-bleed.
- **Android theming:** `fragment_page.xml` toolbar has no explicit bg; `SingleFragmentActivity.setTransparentStatusBar()` makes status bar transparent; `theme_dark.xml` `colorSurface`=`#303030` ≠ page `#0B0E12`. `page_statistics.xml` shows the `AppBarLayout`+`statusBarForeground` pattern. **Scope the fix to the speedrun screens** — do NOT globally change `colorSurface` (app-wide regression risk).
- **Desktop reviewer:** chrome (bottom-bar buttons `reviewer-bottom.scss`, top bar, bg) is safe to theme via `:root.night-mode` CSS custom-property overrides (`ts/lib/sass/_root-vars.scss`); card content `#qa` and `data-ease`/`_answerCard` are OFF-LIMITS.
- **Android reviewer:** native `ReviewerFragment` (2024, `com.ichi2.anki.ui.windows.reviewer`); chrome colors are theme attrs (`topBarColor`, `againBackgroundColor`, …) in `theme_dark.xml`; `ReviewerViewModel.answerCard(rating)` + `Rating` enum are scheduling — OFF-LIMITS. Genuinely separate from desktop (not write-once).

---

# Phase M0 — Mobile-first responsive foundation (shared Svelte pages) — CRITICAL, do FIRST

**Outcome:** Home + Memory are phone-first (~360px), reflow to desktop columns at ≥768px, no one-word-per-line wrapping, 44px touch targets. "The Run" aesthetic + honesty semantics unchanged.

**Files:** `ts/routes/speedrun-home/{SpeedrunHome,Splits,SplitRow,StatRow,RunHeader,ActionBar}.svelte`; `ts/routes/speedrun-memory/{MemoryDashboard,TopicRow,RangeBand}.svelte`.

**Approach (all components):** mobile-first — base styles target ~360px; add `@media (min-width: 768px) { … }` blocks to restore the current desktop layout. Keep the token block in `SpeedrunHome.svelte` as-is.

### Task M0.1 — SplitRow.svelte → stacked card on mobile
- [ ] Base (<768px): `tr{display:block}`; each `td{display:block;width:100%;padding:6px 16px}`; topic on its own line (full width); recall + range numeric inline (`display:inline-block;width:~48%`); band track full-width single line; flag on its own centered line. Abstained row: compact locked line (see M0.7 wording).
- [ ] Desktop (≥768px): restore `display:table-row`/`table-cell`, the existing pixel widths (`.c-topic:200px` … `.c-flag:40px`), `padding:7px 28px`.
- [ ] Min row height 44px on mobile.

### Task M0.2 — StatRow.svelte → stack vertically on mobile
- [ ] Base: `.stats{flex-direction:column}`; `.stat{border-bottom:1px solid var(--line);border-right:none;padding:12px 16px}`; `.val{font-size:clamp(20px,6vw,26px)}`.
- [ ] Desktop (≥768px): restore `flex-direction:row`, `flex:1`, `border-right`, `:last-child{border-right:none}`, original font sizes.

### Task M0.3 — RunHeader.svelte → stack wordmark/status on mobile
- [ ] Base: `header{flex-direction:column;gap:12px;padding:16px}`; `.status{text-align:left}`; slightly smaller wordmark.
- [ ] Desktop (≥768px): restore row layout + original padding/sizes.

### Task M0.4 — ActionBar.svelte → full-width START RUN on mobile
- [ ] Base: `.action{flex-direction:column;gap:12px;padding:16px}`; `.run{width:100%;padding:16px}` (≥44px); `.next{text-align:center}`.
- [ ] Desktop (≥768px): restore row + original padding. (NOTE: the cross-platform `onStartRun` bridge change is Task S2.0, not here — keep M0 presentation-only.)

### Task M0.5 — Splits.svelte header reflow
- [ ] Base: `.splits-hd{flex-wrap:wrap;gap:8px;padding:16px}`. Desktop (≥768px): restore `padding:20px 28px 10px`.

### Task M0.6 — SpeedrunHome.svelte container full-bleed on mobile
- [ ] Base `.app{width:100%}` (drop `max-width`/side borders). Desktop (≥768px): restore `max-width:960px;margin:0 auto;border-left/right:1px solid var(--line)`.

### Task M0.7 — MemoryDashboard.svelte + TopicRow.svelte + RangeBand.svelte → card-ify on mobile
- [ ] MemoryDashboard: base `.memory{width:100%;padding:12px}`; hide `thead` <768px; convert `tbody tr` to card blocks; stacked `td` with `::before` data labels. Desktop (≥768px): restore table + thead.
- [ ] RangeBand: base `.range{flex-wrap:wrap}`; track full-width; nums wrap below. Desktop restore inline.
- [ ] TopicRow: same card conversion as SplitRow (M0.1).

### Task M0.8 — Compact mobile copy audit
- [ ] Abstain string must not wrap word-per-word on mobile. Use a compact form under ~480px (e.g. `🔒 20 more to unlock`) and the full `NOT TIMED — review N more to unlock a split` at wider widths (CSS `@media`, or two spans toggled by breakpoint). Audit all page copy for mobile brevity.

### Task M0.9 — Build + dual-width screenshot gate
- [ ] `just build`; `just check` (green mod. complexipy); `just fix-fmt`.
- [ ] Extend/add a Playwright e2e that screenshots Home + Memory at **360px** and **1280px** (`page.setViewportSize`). Save both; confirm no horizontal scroll at 360px, columns restore at ≥768px.
- [ ] Commit: `feat(mobile): mobile-first responsive Home + Memory (stacked ≤768px, desktop columns above)`.
- [ ] **GATE:** post both-width screenshots to Cursor.

---

# Phase M1 — Android shell theming (dark toolbar + system bars) — small

**Outcome:** the Android toolbar + status/nav bars match the dark `#0B0E12` page on the speedrun screens; no white flash. **Scoped to the speedrun screens** (no global theme change).

**Files (verify-first):** `SpeedrunHomeFragment.kt` / `SpeedrunMemoryFragment.kt`; possibly a dedicated theme in `res/values/themes*.xml`; `res/values/colors.xml`.

### Task M1.1 — Dark toolbar on the speedrun fragments
- [ ] Add a `speedrun_shell_bg` color (`#0B0E12`) in `colors.xml`. In both fragments' `onViewCreated`, set the `MaterialToolbar` background + title/icon tint to the dark palette (mirror how an existing PageFragment tints its toolbar). Keep it scoped to these fragments — do NOT edit global `theme_dark.xml colorSurface`.

### Task M1.2 — Dark status/nav bars for the hosting activity
- [ ] Ground how `SingleFragmentActivity`/`setTransparentStatusBar()` interacts with the page. Set the status-bar/nav-bar appearance so the bars read dark for the speedrun screens (via the activity window when hosting a speedrun fragment, or a scoped theme). If a scoped theme is cleaner than per-fragment window calls, add `Theme.Speedrun.Dark` extending the dark base and apply it only to these fragments/host — verify it doesn't leak to other `SingleFragmentActivity` screens.

### Task M1.3 — Emulator screenshot gate
- [ ] Rebuild AAR if needed (only if the page bundle changed — M0 changes DO require the AAR rebuild before Android reflects them; see cross-cutting note). Build `:AnkiDroid:assembleDebug`.
- [ ] **GATE (David/emulator):** screenshot Home + Memory on emulator — dark bars, no white flash, page + chrome consistent.

---

# Phase S1 — START RUN: real study + honest fallbacks (DESKTOP) — CRITICAL

**Outcome:** START RUN launches study on `"Speedrun::GRE Math"`; when it can't, it says why in OUR page (never the bare Anki congrats).

**Files:** `qt/aqt/speedrun.py` (`_start_run` rewrite + a status-push helper), `ts/routes/speedrun-home/{SpeedrunHome,ActionBar}.svelte` (render fallback banner).

### Task S1.1 — Page: inline START-RUN status banner
- [ ] In `SpeedrunHome.svelte`, add a small inline status banner (flat/sharp, uses tokens) driven by a global the shell can call: `window.speedrunStartStatus = (state, payload) => {…}` where `state ∈ {importNeeded, caughtUp}`. `importNeeded` → "Import the GRE exam deck to start a run" (+ optional Import button firing `pycmd("startrun:import")`). `caughtUp` → "All caught up — N new cards unlock next" (honest; wording per Open Q1). Banner is dismissible; hidden by default. AGPL header unchanged.
- [ ] Keep ActionBar's button calling the bridge (unchanged here; S2.0 makes it cross-platform).

### Task S1.2 — Shell: resolve deck, branch, launch or push status
- [ ] Rewrite `SpeedrunHome._start_run` in `speedrun.py`:
```python
def _start_run(self) -> None:
    did = self.mw.col.decks.id_for_name("Speedrun::GRE Math")
    if did is None:
        self.web.eval('window.speedrunStartStatus && window.speedrunStartStatus("importNeeded");')
        return
    node = self.mw.col.decks.find_deck_in_tree(self.mw.col.decks.deck_tree(), did)
    due = 0 if node is None else (node.new_count + node.review_count + node.learn_count)
    if due == 0:
        self.web.eval('window.speedrunStartStatus && window.speedrunStartStatus("caughtUp");')
        return
    self.mw.col.decks.select(did)
    self.close()
    self.mw.moveToState("review")
```
- [ ] Ground `find_deck_in_tree` signature + `deck_tree()` return; adjust if the real API differs (it may be `Decks.find_deck_in_tree(node, did)` or a walk). Confirm `new_count` etc. field names on the node.
- [ ] Handle `startrun:import` bridge cmd → open Anki's import dialog pointed at the seed apkg (or the generic import). (If import wiring is non-trivial, the banner text + pointing at the file path is acceptable for this slice — flag at gate.)

### Task S1.3 — Verify (desktop, three states)
- [ ] `just check` green; `just fix-fmt`.
- [ ] `just run` three ways: (a) fresh profile, no deck → banner "import"; (b) seed imported + due → reviewer opens on the deck; (c) seed imported + nothing due → banner "caught up". Screenshot each. (Claude can also add an e2e that stubs the three states if feasible; the `just run` screenshots are David's.)
- [ ] Commit: `fix(home/desktop): START RUN launches real study + honest import/caught-up states in-page`.
- [ ] **GATE:** three screenshots to Cursor.

---

# Phase S2 — START RUN wiring (ANDROID) — CRITICAL

**Outcome:** START RUN opens the native reviewer on the exam deck (or an honest fallback), via the real `bridgeCommand` channel.

**Files:** `ts/routes/speedrun-home/ActionBar.svelte` (cross-platform call), `SpeedrunHomeFragment.kt` (`bridgeCommands` map + handler). No `PostRequestHandler` change expected.

### Task S2.0 — Shared page: make START RUN cross-platform (prereq)
- [ ] In `ActionBar.svelte`, change the default `onStartRun` to fire BOTH guarded bridges so the platform's existing one runs:
```ts
export let onStartRun: () => void = () => {
    const g = globalThis as { pycmd?: (c: string) => void; bridgeCommand?: (c: string) => void };
    g.pycmd?.("startrun");          // desktop (Qt AnkiWebView)
    g.bridgeCommand?.("startrun");  // Android (PageFragment)
};
```
- [ ] Rebuild the page (`just build`) — this changes the shared bundle, so the **AAR must be rebuilt** for Android to pick it up (cross-cutting note).

### Task S2.1 — Fragment: bridgeCommands → open reviewer with fallbacks
- [ ] In `SpeedrunHomeFragment.kt`, add:
```kotlin
override val bridgeCommands = mapOf("startrun" to { onStartRun() })

private fun onStartRun() = launchCatchingTask {
    val did = withCol { decks.idForName("Speedrun::GRE Math") }   // confirm exact API
    if (did == null) { showThemedSnackbar(R.string.speedrun_import_needed); return@launchCatchingTask }
    val node = withCol { sched.deckDueTree().find(did) }
    if (node?.hasCardsReadyToStudy() != true) { showThemedSnackbar(R.string.speedrun_caught_up); return@launchCatchingTask }
    withCol { decks.select(did) }
    startActivity(Reviewer.getIntent(requireContext()))
}
```
- [ ] Ground the exact Kotlin APIs: deck-id-by-name (`decks.idForName` vs `decks.id`), `sched.deckDueTree().find(did)`, `hasCardsReadyToStudy()`, `Reviewer.getIntent`, `launchCatchingTask`, `withCol`, and the snackbar/toast helper. Mirror `CongratsPage.kt` + `DeckPicker.kt` exactly. Add the two strings (`translatable="false"` or FTL per repo norm).
- [ ] Fallback UI: a themed snackbar/toast is acceptable for Android this slice (matching desktop's page-banner intent as closely as the platform allows); if pushing the same in-page banner via `webview.evaluateJavascript("window.speedrunStartStatus(...)")` is clean, prefer that for parity — flag the choice at the gate.

### Task S2.2 — Re-pin rsdroid + rebuild AAR + build app + verify
- [ ] Re-pin the rsdroid `anki` submodule to the `feat/speedrun-mobile-first` tip (fetch locally as in prior cycles), rebuild AAR (`cargo run -p build_rust`) so the M0 + S2.0 page bundle ships. `:AnkiDroid:assembleDebug`.
- [ ] Commit (anki-android): `feat(home/android): START RUN opens native reviewer on exam deck + honest fallbacks (bridgeCommand)`.
- [ ] **GATE (David/emulator):** tap START RUN with (a) no deck, (b) due, (c) nothing due; screenshot each.

---

# Phase R1 — Reviewer restyle ("The Run" dark) — BIGGEST/riskiest, LAST, presentation-only

**Outcome:** the study reviewer chrome visually matches "The Run" on both platforms. **Two separate surfaces. ZERO scheduling changes.** (Open Q2: full chrome theming vs. just dark bg + buttons — default to the lower-risk "dark bg + answer buttons + bars" unless David wants full.)

### Task R1.1 — Desktop reviewer chrome (CSS only)
- [ ] Create `ts/reviewer/_run-palette.scss` overriding `:root.night-mode` custom props (`--canvas`, `--fg`, `--border`, `--button-bg`, …) to "The Run" palette; `@import` it in `ts/reviewer/reviewer.scss`. Add dark button rules in `qt/aqt/data/web/css/reviewer-bottom.scss` targeting the bottom-bar `button`/`#outer` chrome.
- [ ] **NEVER touch** `#qa` card content, `data-ease`, `onclick=pycmd("easeN")`, `_answerCard`, or any Python scheduling. Only CSS vars + chrome selectors.
- [ ] `just rebuild-web` / `just check`. Verify: `just run` → Dark theme → reviewer chrome themed; answer a card (advances normally); card template unchanged.
- [ ] Commit: `feat(reviewer/desktop): The Run dark chrome (CSS-only, night-mode; no scheduling change)`.
- [ ] **GATE:** desktop screenshot of a review in progress.

### Task R1.2 — Android native reviewer chrome (theme attrs only)
- [ ] Add a dark "The Run" theme variant (e.g. `Theme.Speedrun.Reviewer` extending the dark base) overriding presentation color attrs only: `topBarColor`, `again/hard/good/easyBackgroundColor` + text colors, `alternativeBackgroundColor`, count colors. Apply to the native reviewer surface (verify how the reviewer theme is selected — via `android:theme` on the fragment/activity or the theme preference; keep scoped so it doesn't override the user's global theme unexpectedly — flag if it must be global).
- [ ] **NEVER touch** `ReviewerViewModel.answerCard`/`Rating`/`executeAction` or the custom-scheduling JS key.
- [ ] `:AnkiDroid:assembleDebug`.
- [ ] Commit: `feat(reviewer/android): The Run dark reviewer chrome (theme attrs only; no scheduling change)`.
- [ ] **GATE (David/emulator):** screenshot of a review in progress.

> **R1 note:** if R1 balloons or risks the demo timeline, split/defer — M0/S1/S2 are the higher-value, lower-risk wins. Flag at the R1 gate.

---

## Cross-cutting notes
- **AAR rebuild trigger:** any change to the shared `ts/routes/speedrun-*` bundle (M0, S2.0) requires re-pinning rsdroid + rebuilding the AAR before Android reflects it. Batch: do the Android AAR rebuild once after M0+S2.0 land (at S2.2), not per-M0-task.
- **Adding a new `ts/routes/*` file** needs `out/rust/*/configure.exe` re-run (glob expands at configure time) — not relevant if only editing existing files (M0 edits existing components).
- **Screenshots** are the gate currency for every phase (mobile+desktop / emulator). Reuse the Playwright harness (bypasses AuthInterceptor via `ANKI_API_HOST=0.0.0.0`; fine for render/screenshot; it does not exercise the Qt 403 path — already fixed).

## Decisions (David, 2026-07-01 — CONFIRMED at Cursor gate)
1. **START RUN, nothing due:** show the honest "All caught up — N new unlock next" banner **AND a Custom Study button** (wire it to Anki's Custom Study on the exam deck; desktop + Android).
2. **Reviewer restyle depth:** **FULL chrome theming** (both platforms) — accepted added scope/risk. Still presentation-only, zero scheduling. Cursor will scrutinize this gate hardest; descope/split first if it threatens the Friday scoring work. Also decide at R1: keep reviewer theming scoped to Anki's night-mode (Home is always dark → light-mode users get a mismatch) vs. forcing "The Run" dark on the Speedrun-launched review WITHOUT globally overriding the user's theme elsewhere — prefer the latter for brand consistency if it can be kept scoped; flag if it must go global.
3. **Android fallback surface:** **themed snackbar** (idiomatic; simplest).

## Cursor gate verdict (2026-07-01): APPROVED for execution
Grounded facts resolve all verify-first unknowns; invariants airtight (presentation-only, off-limits lists explicit); mobile-first + dual-width screenshot gates correct. Execute M0→M1→S1→S2→R1 on `feat/speedrun-mobile-first`; Cursor reviews each phase gate (mobile ~360px + desktop / emulator screenshots) and FF-merges. NO AI.

## Post-implementation deliverables (Cursor-tracked; after phases land + merge)
1. `docs/DEMO-SCRIPT.md` — click-by-click for both apps (launch → Home → import seed → START RUN → review a card → Memory → optional sync).
2. Docs refresh — `PROGRESS.md`, `STATE.md`, `FUTURE-PLANS.md` (move done items out of backlog).
3. Grader-launch accuracy — verify `RUN-MVP.md`/READMEs launch both apps from a clean clone (desktop `just run`; Android `installPlayDebug`); prereqs in `BUILD-PREREQS.md`.

## Execution & gating
- On approval: create `feat/speedrun-mobile-first` off `main` (all 3 forks), execute M0→M1→S1→S2→R1 via subagent-driven-development, screenshot gate each phase, Cursor FF-merges. Feedback via `.claude/cursor-review.md`. NO AI.
