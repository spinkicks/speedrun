# Speedrun Identity — design spec (branding / de-Anki-fication)

**Status:** LOCKED (David, 2026-07-02) after mockup review. Slice B of the frontend/UX revamp (see `FUTURE-PLANS.md` → "DISTINCT-IDENTITY MANDATE"). Mockup: `docs/design/mockups/speedrun-identity.html`. Supersedes the type/accent choices in `speedrun-home-spec.md` §"Design language" (that spec's layout/signature-element still stand; only the typeface + accent color change).

**David's locked picks (2026-07-02):** wordmark/display font = **Manrope ExtraBold**; accent = **near-white `#F4F7FA`**; wordmark = **subtle SPEED+RUN split** (`SPEED` in `--fg`, `RUN` in the white accent); **type-only this cycle — NO bespoke logo/icon asset** (launcher/window icon uses a simple type-based mark; polished icon deferred).

**Goal.** A first-time user or grader must read the running app as **Speedrun — a substantial, purpose-built GRE-Math trainer**, not "Anki with a couple of extra pages." Before reading a line of code they should see: our name on the launcher/window, our first screen, our navigation, our review surface — and *not* Anki's default deck-picker/menus/branding. Pure presentation + shell wiring; **zero engine changes**, all invariants untouched.

## What changes from "The Run" v1 (David's direction, 2026-07-02)
v1 read too "AI/code": a techy display face (Space Grotesk), **every numeral in a monospace** (IBM Plex Mono), and a "random yellow" accent (amber `#e8b23a`). Revised language:

**1. Typography — bolder & professional, kill the "code" look.**
- **Display / wordmark / headings:** **Manrope ExtraBold (800)** — LOCKED. Geometric-humanist, professional, heavier than Inter for the wordmark; reads "serious product," not "terminal."
- **Numerals:** stop using a monospace face. Use the same professional sans with `font-variant-numeric: tabular-nums` so splits/percentages still align in columns **without** the code aesthetic. This single change removes most of the "AI slop / terminal" read.
- Retire `--mono` (IBM Plex Mono) from numerals/labels; keep it (if at all) only for genuinely code-like content (there is none on these surfaces), so effectively drop it.
- Must be **offline-safe** in the Anki webview — self-host/bundle the woff2 (Manrope is OFL-licensed; ships fine — bundle the 500 + 800 weights) with a strong system fallback stack (`"Manrope", "Segoe UI", system-ui, sans-serif`).

**2. Color — professional white/light accent, retire the amber.**
- Keep the dark base (David only objected to the accent + font): `--ink #0B0E12` · `--panel #12161C` · `--line #232A33` · `--fg #E6EAEF` · `--muted #7C8794` (unchanged).
- **Replace `--pace: #e8b23a` (amber) → `--pace: #F4F7FA` (near-white).** The accent now = bright white: primary button is white-on-dark (a clean, professional CTA), the point-estimate tick in the error-bracket is white, the wordmark accent is white. Hierarchy comes from **weight + size + brightness**, not a colored accent.
- Reserve exactly one semantic color for later, opt-in only: a restrained red **only** for "at risk" if it ever earns its place (not used now). No other accents. No gradients/glow/rounded corners (that rule from v1 stands — it keeps it professional, not flashy).

**3. Wordmark.** `SPEEDRUN` set in **Manrope ExtraBold**, tight tracking, as a **subtle two-tone light split**: `SPEED` in `--fg #E6EAEF`, `RUN` in the white accent `--pace #F4F7FA` (both light; `RUN` reads a touch brighter — the "record/pace" cue without color). Subtitle `GRE MATHEMATICS · SUBJECT TEST` in `--muted`, Manrope (not mono).

## Branding / de-Anki deliverables (the visible "we built a lot" signal)
Design-first → build → **screenshot-gate on both platforms**. Pure shell/presentation.
1. **Wordmark + accent re-skin** applied to Home (and Memory, folding in the shared dark tokens) — new font + white accent. Re-accent everywhere `--pace` is used (Home `StatRow`/`Splits`/`ActionBar`, Memory range-bands).
2. **App name = "Speedrun"** everywhere a user sees it:
   - **Desktop:** window title + app/window icon (Qt `setWindowTitle`/`setWindowIcon`; ground in `qt/aqt/main.py` / `aqt/__init__.py`). Confirm the About/title reads Speedrun without breaking Anki attribution in the source/AGPL notices.
   - **Android:** launcher label + adaptive launcher icon (`anki-android` `AndroidManifest`/`res/mipmap-*` + `strings.xml` app_name for the flavor we ship). Keep AnkiDroid attribution in-app/licenses per GPL.
3. **App icon / launcher icon — TYPE-ONLY this cycle (David):** no bespoke designed logo. Use a simple **type-based mark** derived from the font — a Manrope ExtraBold `S` monogram (white on `--ink`, plus a white-tile variant for the Android adaptive icon) — as a placeholder that already reads as "Speedrun." A polished/custom icon is deferred to a later branding pass; do NOT sink time into logo design now.
4. **Anki-chrome trimming (default-off for normal users):** demote the deck picker + upstream menus so the default path is Home → Study → Memory/Scores. Keep them reachable (maintenance/back-office), don't delete. Desktop: menu slimming + Home-as-startup (already shipped, config-gated). Android: launch into Home fragment.

## Non-goals (this slice)
- Full nav shell (Home/Study/Memory/Scores tabs) — that's the **NEXT** revamp slice and folds into Friday Phase 5 (it touches the same Svelte surface as the scores UI). This identity slice just does font/accent/branding/chrome so we don't restyle the nav twice.
- Reviewer restyle beyond the already-shipped dark chrome (later slice).
- No engine/proto/scheduling changes. No AI.

## Success criteria
- `just run` opens into a Home that reads as **Speedrun** in a bold professional face with a white/light accent — no amber, no monospace numerals; window title/icon = Speedrun.
- Android launcher shows "Speedrun" + our icon; app launches into Home; toolbar/system bars dark (already done).
- Same shared Svelte page renders on both platforms after AAR rebuild; `just check` green (mod. known complexipy). AGPL/GPL headers on any new files. No AI.
- Screenshot proof on BOTH platforms at the gate (visual-verification protocol).

## Grounding notes for the implementer (Claude)
- Current tokens live in `ts/routes/speedrun-home/SpeedrunHome.svelte` (`--disp`/`--mono`/`--pace` defined ~L133-143) and are consumed across `speedrun-home/*` + `speedrun-memory/*`. Change the token DEFINITIONS in one place; consumers inherit. Grep `--pace` and `var(--mono)` to catch every use.
- Font bundling: follow how the webview already serves assets; self-host Inter woff2 next to the sveltekit bundle so it works offline in the Qt/Android webview (no CDN — offline is a hard requirement, same as the installer).
- Desktop title/icon: ground the Qt entry (`qt/aqt/main.py`, `aqt/__init__.py`, `aqt/mediasrv.py` for the webview title) before editing; show file:line first.
- Android: ground the shipped flavor's `app_name` + launcher icon set before editing; keep AnkiDroid GPL attribution intact.

## Coordination
`ts/` + `qt/aqt` shell + `anki-android` shell = the surface for this slice. Only one branch checks out in each shared repo tree — sequence so this slice and the Friday **engine** work (rslib) don't build `repos/anki` simultaneously (engine work is rslib-heavy; this is ts/qt-heavy — mostly disjoint, but coordinate the checkout).
