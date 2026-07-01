# Mobile-First UX + START RUN + Reviewer Restyle — plan brief

> **STATUS: BRIEF (Cursor-authored, for Claude to ground → task-by-task plan → execute with Cursor gates).** Created 2026-07-01 after David's on-device testing found two START RUN bugs + mobile layout issues. Manager directive: **build the mobile UI first** (it's the harder target; desktop scales up from it). NO AI (that's Friday). Every UI change is **presentation/navigation only** — never touch scheduling, `transact`, proto, or FSRS.

**Decisions locked (David, 2026-07-01):**
1. **START RUN** = launch a real study session on the GRE exam deck, with **honest fallback states** (never a bare Anki "Congratulations" dead-end).
2. **Mobile-first responsive redesign** of the shared pages (Home + Memory) — phone-first, scales up to desktop; fold in the Android shell theming.
3. **Restyle the reviewer too** this cycle (accepted added scope/risk) — as its own final phase.

**Cross-cutting rule (from the 2026-07-01 audit):** every UI change is verified by an actual render — screenshot at **mobile width (~360–390px)** AND desktop — before its gate. A green build is not sufficient evidence.

---

## Confirmed root causes (grounded 2026-07-01)
- **Desktop START RUN dead-end:** `ts/routes/speedrun-home/ActionBar.svelte` fires `pycmd("startrun")`; `qt/aqt/speedrun.py::SpeedrunHome._start_run` does `self.close(); self.mw.moveToState("overview")`. On a collection with no due cards (fresh profile, seed deck not imported) Anki's overview redirects to the deck browser's "Congratulations! finished this deck." → exits our shell + dead-ends.
- **Android START RUN no-op:** `SpeedrunHomeFragment.kt` documents it explicitly — *"AnkiDroid has no pycmd bridge in PageFragment, so the call is a safe JS no-op."* The stuck-white is the button's un-styled `:active` state.
- **Mobile layout:** `SpeedrunHome.svelte` is desktop-shaped (`max-width: 960px`; `SplitRow`/`Splits` use a multi-column row). On a phone the columns collapse and abstain text wraps one word per line. Renders, but not mobile-optimized.
- **Android shell:** `SpeedrunHomeFragment`/`SpeedrunMemoryFragment` `MaterialToolbar` + system status/nav bars render white against the dark page.

---

## Phase M0 — Mobile-first responsive foundation (shared Svelte pages) — CRITICAL, do FIRST
**Outcome:** Home + Memory are designed phone-first and reflow cleanly from ~360px up to desktop; no more one-word-per-line wrapping; touch-friendly.
- **Files:** `ts/routes/speedrun-home/{SpeedrunHome,Splits,SplitRow,StatRow,RunHeader,ActionBar}.svelte`; `ts/routes/speedrun-memory/{MemoryDashboard,TopicRow,RangeBand}.svelte`; extract shared responsive tokens if useful.
- **Approach:** mobile-first CSS (base styles target narrow; `min-width` media queries add desktop columns). Replace the fixed multi-column split row with a **stacked card on mobile** (topic name on its own line; recall / range-bracket / status as a compact second line or wrapped block) → **grid/table columns only at wider breakpoints**. Fluid type (`clamp()`), min 44px touch targets, remove the desktop `max-width:960px`/side borders on mobile (full-bleed), keep the centered column on desktop.
- **Wording (concise on small screens):** the abstain string "NOT TIMED — review 20 more to unlock a split" must not wrap word-per-word — use a compact mobile form (e.g., "🔒 20 more to unlock" / "NOT TIMED · 20 to unlock") and the full phrase only where width allows. Audit all copy for mobile brevity.
- **Keep** the flat/sharp "The Run" aesthetic + honesty semantics exactly (tokens in `SpeedrunHome.svelte`).
- **Verify:** `just build`; render Home + Memory at 360px and desktop (Playwright screenshots at both widths — same harness Claude used for the audit e2e). Gate evidence = both screenshots.

## Phase M1 — Android shell theming (fold in) — small
**Outcome:** the Android toolbar + system status/nav bars match the dark page.
- **Files (verify-first):** `SpeedrunHomeFragment.kt` / `SpeedrunMemoryFragment.kt` (toolbar color), and the fragment/activity theme for `statusBarColor`/`navigationBarColor` (likely `SingleFragmentActivity` theme). Ground how AnkiDroid themes other PageFragments before editing.
- **Verify:** emulator screenshot — dark bars, no white flash.

## Phase S1 — START RUN: real study + honest fallbacks (desktop) — CRITICAL
**Outcome:** START RUN launches study on the GRE exam deck; when it can't, it says why in OUR UI.
- **Behavior:** on click → resolve the exam deck (the seed deck's deck id / name). Branch:
  - deck present + cards due → open the reviewer for that deck (ground the API: select deck then `moveToState("review")`, or the deck-overview→study path; confirm via `qt/aqt/main.py` / `overview.py`).
  - deck present, nothing due → honest inline state on Home ("All caught up — N new cards unlock next; or Custom Study"), NOT the bare Anki congrats.
  - **no exam deck imported** → inline "Import the GRE exam deck to start a run" (point at `speedrun/out/gre_math_seed.apkg`), ideally a button that opens Anki's import.
- **Where the state shows:** prefer surfacing fallback states **in the Home page** (pass a status from the shell back to the Svelte page, or check before navigating) rather than dumping into Anki chrome.
- **Files:** `qt/aqt/speedrun.py` (`_start_run` + a new bridge cmd for status), `ActionBar.svelte`/`SpeedrunHome.svelte` (render the fallback states), maybe a tiny read helper (deck/due lookup — reuse existing Collection APIs; no new proto).
- **Verify:** `just run` — START RUN with (a) no deck, (b) deck imported + due, (c) deck imported + nothing due; screenshot each.

## Phase S2 — START RUN wiring (Android) — CRITICAL
**Outcome:** START RUN launches study on Android (currently a documented no-op).
- **Verify-first (the key unknown):** how does an AnkiDroid PageFragment web page trigger a NATIVE action/navigation? Grep how existing pages do it (e.g., the Congrats page's "study more", or `PostRequestHandler` + a JS bridge / `AnkiServer` message). Mirror that mechanism — do NOT invent a new bridge.
- Then wire `startrun` → open AnkiDroid's Reviewer on the exam deck, with the same fallback semantics as desktop (no deck / nothing due).
- **Files:** `SpeedrunHomeFragment.kt` (+ whatever bridge the grounding reveals), possibly `PostRequestHandler.kt`.
- **Verify:** emulator — tap START RUN → reviewer opens (or honest fallback); screenshot.

## Phase R1 — Reviewer restyle (BIGGEST / riskiest — do LAST, presentation-only)
**Outcome:** the study reviewer visually matches "The Run" on both platforms.
- **Honest scoping:** this is **two different surfaces** — desktop's reviewer (Qt webview + card template CSS / `ts/reviewer`) and AnkiDroid's **native** reviewer (Kotlin, not the shared Svelte page). NOT write-once. Ground both mechanisms first.
- **Desktop:** theme the reviewer chrome + answer buttons + background to the dark palette (night-mode / reviewer CSS). Do not alter card *content* templates users author, only app chrome.
- **Android:** theme the native Reviewer activity to dark/"The Run" palette (colors/theme only).
- **HARD invariant:** presentation only — zero changes to scheduling, answer-button intervals, `transact`, or card ordering. If a change would touch scheduling logic, STOP and flag.
- **Verify:** desktop + emulator screenshots of a review in progress.
- **Note:** this phase can be split/deferred if it risks the demo timeline — M0/S1/S2 are the higher-value, lower-risk wins. Flag at the gate if R1 balloons.

---

## Post-implementation deliverables (after the above land + merge)
1. **Demo script** — `docs/DEMO-SCRIPT.md`: exact click-by-click walkthrough for BOTH apps (desktop + mobile) — launch → Home → (import seed deck) → START RUN → review a card → Memory dashboard → (optional sync). Written for someone who's never seen the app.
2. **Docs refresh** — update `PROGRESS.md`, `STATE.md`, `FUTURE-PLANS.md`; move done items out of backlog.
3. **Grader-launch accuracy** — ensure the READMEs / `RUN-MVP.md` let a grader launch BOTH apps locally from a clean clone with correct, current commands (desktop `just run`; Android `installPlayDebug`); call out prerequisites (`BUILD-PREREQS.md`). Verify the commands as written.

## Execution & gating
- Order: **M0 → M1 → S1 → S2 → R1**, then deliverables. M0 first honors the mobile-first directive.
- Branch: new `feat/speedrun-mobile-first` off `main`. Cursor reviews at each phase gate (screenshots required); Cursor does the FF-merge to `main`.
- Feedback flows via `.claude/cursor-review.md`. NO AI. AGPL/GPL headers per repo.

## Open questions for David (nice-to-have; Claude can proceed with the recommended defaults)
1. START RUN with nothing due — is "All caught up + offer Custom Study" the right message, or keep it minimal?
2. Reviewer restyle depth — full chrome theming, or just dark background + buttons to reduce risk?
