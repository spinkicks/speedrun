# Speedrun — MVP Demo Video Script (draft)

> **Deliverable:** the "Speedrun MVP Demo Video" (target 3–5 min). Scene-by-scene: **[SHOW]** = on-screen action, **[SAY]** = narration. Content is grounded in `docs/WHAT-WE-BUILT.md`; **honesty rules from there apply — never claim scaffolding/planned items as done.** Draft 2026-07-03 — the mobile-first shell, the **three honest scores** (Memory/Performance/Readiness), calibration, the **Problem MCQ bank + timed mini-mock**, and worked-examples-first are all **merged to `main`** on every fork (anki `c54afe2b1` · Anki-Android-Backend `14c2992` · anki-android `f2cf66ac35`), so this is **safe to record now**. Remaining human gates before publish: the emulator visual pass and a live desktop↔phone sync recording.

## Before recording (setup)
- Desktop: `just run` inside `repos/anki`. **Speedrun Home auto-opens on launch** — the branded "The Run" landing (**Manrope ExtraBold** headings, **#F4F7FA** surface). Use a throwaway profile.
- **Rebuild + import the seed deck so you have the problems.** From `repos/anki/speedrun`: `pwsh uvw.ps1 run python seed/build_seed_deck.py` → `out/gre_math_seed.apkg`, then import it. The apkg now bundles **both** the 35 declarative cards (`Speedrun::GRE Math`) **and** the **64-problem MCQ bank** (`Speedrun::GRE Math::Problems`, note type `Speedrun::Problem`).
- **To show real (non-abstaining) scores you need real accumulated study.** A brand-new deck honestly **abstains** on every score: Memory unlocks per topic only after ~20 graded reviews; Performance needs logged problem attempts; **Readiness needs ≥2 timed mini-mocks**; Calibration needs ≥20 confidence bets. Record on a profile where you've genuinely studied enough that some scores are non-abstaining, then show those real numbers. Wherever a score is still abstaining, **show the abstention** ("review N more to unlock" / "—") — that honesty IS the differentiator. **Never fake a number for the camera** (a filled range comes from real days of study, not a config tweak).
- Android: emulator (`Pixel_10`, x86_64) with the app installed (`installPlayDebug`), same seed deck.
- **AI is OFF by default and is a separate service, not part of the app.** Do **not** imply the app calls AI. Only if you deliberately want an AI beat, run `services/speedrun-ai` with `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY` and present it as an optional, gated generator (see the optional scene).
- Have both windows ready to alt-tab / screen-record.

## Runtime budget (~5 min)
1. Positioning — 20s · 2. Three honest scores — 55s · 3. Study loop + ordering — 35s · 4. Problem card + calibration self-bet — 40s · 5. Timed mini-mock — 30s · 6. Worked-example faded reveal — 25s · 7. Two apps, one engine — 35s · 8. Under the hood — 35s · 9. Sync + installer — 20s · 10. Honest close — 25s. *(Optional AI aside — 20s — only if you enabled it.)*

---

### Scene 1 — Positioning (~20s)
- **[SHOW]** Desktop launches straight into **Speedrun Home** ("The Run") — the Manrope ExtraBold title on the #F4F7FA surface.
- **[SAY]** "This is Speedrun — an honest study trainer for the GRE Math Subject Test, built **on top of** Anki's proven spaced-repetition engine. But it's its own app: our own front door, our own scores, the same engine on desktop and phone. The theme of the whole thing is honesty — it never shows you a number it can't back up."

### Scene 2 — Three honest scores (~55s) — the differentiator
- **[SHOW]** Home's three headline scores: **Memory**, **Performance**, and exam-level **Readiness** (200–990). On a profile with real study, show the actual values — Memory as a **95% range**, Performance with its **memory→performance gap Δ**, Readiness as a point **with a conformal range**. Where a score still abstains, show the honest "—" / "review N more to unlock".
- **[SAY]** "Three scores, each earned from your real data. **Memory** is recalled mastery from Anki's FSRS, shown as a **95% confidence range** — never a single fake number. **Performance** is your probability of getting a *novel* problem right, and we show the **gap** between what you remember and what you can actually do. **Readiness** maps to the real 200-to-990 scale with a **conformal range**, and it refuses to appear until you've done at least two timed mini-mocks. Every one of them **abstains** when it doesn't have the data — that's the point."
- **[SHOW]** Open the **Memory dashboard** (Tools → Speedrun: Memory, or the Home link): coverage header (**9/9 topics**), per-topic ranges, per-topic abstention.
- **[SAY]** "The Memory dashboard is the same idea in depth — coverage against the real exam blueprint, per-topic mastery with ranges, and honest abstention on any topic that hasn't earned a number yet."

### Scene 3 — The study loop + our ordering (~35s)
- **[SHOW]** Click **► START RUN** → a real review session on the GRE deck (dark reviewer on **desktop**); answer a card or two. If nothing's due, show the honest "caught up / Custom Study" banner. (The **desktop** reviewer is themed "The Run"; the **Android** reviewer is still Anki's default light theme — so show the *dark reviewer beat on desktop*.)
- **[SAY]** "START RUN drops you straight into the exam deck. Under the hood this is Anki's FSRS scheduler — we did **not** reinvent memory science and we did **not** change FSRS. What we add is **how cards are ordered**: **new cards** by **points-at-stake** — the highest-weighted exam topics — and your **due reviews interleaved by weakness across topics**, which the research shows beats blocked practice."

### Scene 4 — Problem card + calibration self-bet (~40s) — LS1
- **[SHOW]** Study a **Speedrun::Problem** multiple-choice card. Before revealing, click a pre-answer confidence button — **Sure / Think / Guess**. Reveal, then self-grade. Then show Home's **Calibration** stat (Brier / ECE) — abstaining under 20 bets, real once you've logged enough.
- **[SAY]** "These are real multiple-choice problems. Before you check, you place a bet on yourself — Sure, Think, or Guess. We log that against how you actually did and score your **calibration** — how well your confidence matches reality. It's **self-reported** accuracy, and like everything else it **abstains** until it has at least twenty bets. No fabricated calibration curve."

### Scene 5 — Timed mini-mock (~30s)
- **[SHOW]** Back on Home, click **MINI-MOCK** → a **timed** filtered session drawn from the 64-problem bank. Answer a couple, finish.
- **[SAY]** "A mini-mock is a short **timed** run over the problem bank. It's what feeds Performance, and it's the gate for Readiness — you need at least two before Readiness will show a number. Timing is captured automatically; nothing about the scheduler is faked to make the run look good."

### Scene 6 — Worked-example faded reveal (~25s) — LS2
- **[SHOW]** On a flagged problem, show the **worked example up front**; then on the answer side click **"Reveal next step"** to fade the solution in one step at a time.
- **[SAY]** "For weaker topics we lead with a **worked example**, then fade the support — you attempt each step before you see it. That's straight out of the worked-example and desirable-difficulty literature, and it's pure presentation — no change to scheduling or the engine."

### Scene 7 — Two apps, one engine (~35s)
- **[SHOW]** Switch to the Android emulator; open the app → the **same Speedrun Home**, the **same three scores**, then Memory — same ranges, same abstention.
- **[SAY]** "Here's the same app on Android — and it's not a reimplementation. It's the **same Rust engine** cross-compiled for the phone, rendering the **same shared UI** and the same three scores. One codebase, one engine, two platforms — build it once, it works on both."

### Scene 8 — Under the hood (~35s) — the real engine change
- **[SHOW]** Briefly: the `proto/anki/speedrun.proto` service / the test suite passing (`cargo test -p anki speedrun::`) — or just narrate over the app.
- **[SAY]** "The engine change is real Rust in Anki's core: read-only RPCs for coverage, mastery, performance, readiness and calibration — the Wilson intervals, the flat-IRT scaling to 200–990, the conformal range, all computed honestly — plus one **mutating** change, the points-at-stake reorder, done the safe way through Anki's transaction system, fully undoable, with tests proving the database stays intact. Small, surgical, and it runs identically on both apps."

### Scene 9 — Sync + clean install (~20s)
- **[SAY]** (over the app, or a quick sync screen) "It syncs through a **self-hosted server** — your data, your machine — with a tested conflict rule. And it builds into a real installer on a clean machine with no external dependencies."

### Scene 10 — Honest close (~25s)
- **[SAY]** "That's the honest MVP: one engine on two apps, three scores that each know when to stay silent, calibration that measures how well you know yourself, and genuine learning-science ordering — all built on Anki. We'd rather ship something true than something that looks impressive. That's Speedrun."

### Optional — AI aside (~20s, ONLY if you enabled it)
- **[SHOW]** A terminal running `services/speedrun-ai` with `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`; hit `/generate` and show a problem that passed verify → ground → gold-gate (or an honest **abstain** that emits nothing).
- **[SAY]** "Optionally, there's a separate AI generator — **off by default**. When you turn it on, every problem is checked by a real symbolic verifier, grounded in a source citation, and cleared by a gold-set gate — or it **abstains and emits nothing**. The study app never depends on it being up."

---

## Honesty guardrails (still enforced on camera)
- ❌ Never show a **fabricated number on an abstaining/empty deck** — if a score abstains, show the abstention ("—" / "review N more to unlock"). Record real numbers only from real accumulated study.
- ❌ Never say "we improved / changed **FSRS**" — we build **on** it, unchanged.
- ❌ Don't imply the **AI runs inside the app** — it's a separate, OFF-by-default service; only show it in the optional aside after explicitly enabling it (`SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`).
- ❌ Don't present **Readiness** before ≥2 mini-mocks, and don't present **per-topic** Readiness as a number — exam-level is the real Readiness; per-topic abstains by design.
- ✅ Frame calibration as **self-reported** (self-graded Good/Easy), not key-checked accuracy.
- ✅ Safe to show: three honest scores with ranges + abstention, the memory→performance gap, points-at-stake **new-card** ordering + weakness×topic **due-card** interleave, the calibration self-bet, the timed mini-mock, the worked-example faded reveal, one-engine-two-apps, self-hosted sync + tested conflict rule, clean-machine installer.

## Pairs with
- `docs/DEMO-SCRIPT.md` (click-by-click operator steps) · `docs/WHAT-WE-BUILT.md` (honest content reference) · `docs/RUN-MVP.md` (how to launch both apps).
