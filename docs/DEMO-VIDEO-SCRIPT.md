# Speedrun — Demo Video Script

> **Deliverable:** the "Speedrun Demo Video" (target 3–5 min). Scene-by-scene: **[SHOW]** = on-screen action, **[SAY]** = narration. Content reflects the **currently shipped app** and the honesty rules in `docs/WHAT-WE-BUILT.md` **apply on camera — never present a number the app can't back up.** Draft **2026-07-03** — everything below is **merged to `main`** on every fork (desktop engine, Android, backend, the shared Svelte pages), so this is **safe to record now**. The only setup requirement: record on a **profile that has some accumulated study data** so the scores, the Readiness gauge, and THE MAP are populated with real colors — otherwise honestly show the **abstain states**.

## What Speedrun is (one-liner for the intro)
An **honest** GRE Math Subject Test trainer built **on** Anki — same **Rust engine** on **desktop and Android**, its own **"Speedrun" identity** (Manrope wordmark, near-white **#F4F7FA** accent, mobile-first dark shell), with an **external AI service that is OFF by default**. It never shows you a number it can't defend.

## Before recording (setup)
- **Desktop:** `just run` inside `repos/anki`. **The installer now ships WITH the deck** — it's **auto-imported on first launch**, so the app opens **straight into Speedrun Home with data available**. **Do not do a manual import on camera.**
- **Use a profile that has genuinely accumulated study** so scores/visuals are populated: Memory unlocks per topic after enough graded reviews; Performance needs logged (key-checked) problem attempts; **Readiness needs ≥2 timed mini-mocks**; Calibration needs enough confidence bets. Wherever a score/topic is still abstaining, **show the abstention** ("—" / "review N more to unlock") — that honesty is the differentiator. **Never fake a number for the camera.**
- **Android:** emulator (`Pixel_10`, x86_64) with the app installed, signed into the **same self-hosted sync** account as desktop so you can show a live sync.
- **AI is OFF by default and lives OUTSIDE the app.** Do **not** imply the app calls AI. Only if you deliberately want the optional aside, run `services/speedrun-ai` with `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY` and present it as a separate, gated generator.
- Have both windows ready to alt-tab / screen-record.

## Runtime budget (~5 min)
1. Install & open — 20s · 2. Speedrun Home + Readiness gauge — 40s · 3. **THE MAP** — 45s · 4. START RUN + ordering — 25s · 5. Problem + MCQ auto-grade — 35s · 6. Mini-mock — 20s · 7. Calibration self-bet + reliability diagram — 35s · 8. Memory→Performance gap — 25s · 9. Two apps, one engine + live sync — 40s · 10. Honest close — 20s. *(Optional AI aside — 20s — only if enabled.)*

---

### Scene 1 — Install & open (~20s)
- **[SHOW]** Launch the installed app. It comes up **straight into Speedrun Home** ("The Run") — Manrope ExtraBold wordmark on the **#F4F7FA** accent, mobile-first dark shell — **already populated**, no import step.
- **[SAY]** "This is Speedrun — an honest trainer for the GRE Math Subject Test, built **on top of** Anki's proven spaced-repetition engine. The installer ships **with the deck baked in**: it auto-imports on first launch, so you open the app and you're already home, with data. It's its own app — our own front door, our own scores, the same engine on desktop and phone — and its whole theme is honesty: it never shows a number it can't back up."

### Scene 2 — Speedrun Home + the Readiness gauge (~40s) — the differentiator
- **[SHOW]** Home's three headline scores: **Memory**, **Performance**, exam-level **Readiness**. Focus on the **NEW Readiness gauge** — a **200–990 number line** with the **conformal range drawn as a band** and the point estimate on it. Also show coverage and the calibration stat. Where a score abstains, show the honest "—" / "review N more".
- **[SAY]** "Three scores, each earned from your real data. **Memory** is recalled mastery, shown as a range — never a single fake number. **Performance** is your chance on a *novel* problem. And **Readiness** maps onto the real **200-to-990** exam scale — here on the gauge, with a **conformal range** drawn as a band around the estimate, so you see the uncertainty, not just a point. Below its data threshold it **abstains** and refuses to draw a number at all. That's the pattern everywhere: earn the data, or it stays silent."

### Scene 3 — THE MAP (~45s) — the signature visual
- **[SHOW]** Click **"THE MAP ▸"**. An interactive **prerequisite graph (DAG)** of the exam's topics appears, **nodes colored by your real mastery**, abstaining topics an honest **grey "—"**. **Tap a node — e.g. Calculus** — and its downstream **"blast radius"** lights up: every topic whose ceiling that weakness caps.
- **[SAY]** "This is THE MAP — and it's why Speedrun is built **on** Anki, not just Anki with a skin. It's the prerequisite graph of the whole subject. Every node is colored by your actual mastery, and grey ones honestly say '—' because they haven't earned a score yet. Tap a weak prerequisite like Calculus and watch its **blast radius** light up — every downstream topic it's holding back. Fix the root and you lift everything above it. That's the thesis of the product, made visible."

### Scene 4 — START RUN + our ordering (~25s)
- **[SHOW]** Back on Home, click **► START RUN** → a real review session on the GRE deck (dark reviewer on **desktop**). Answer a card or two; if nothing's due, show the honest "caught up / Custom Study" banner.
- **[SAY]** "START RUN drops you into the exam deck. Under the hood this is Anki's FSRS scheduler — we did **not** change FSRS and we did **not** reinvent memory science. What we add is **ordering**: **new cards by points-at-stake** — the highest-weighted exam topics first — and your **due reviews interleaved by weakness across topics**, which the research shows beats blocked practice."

### Scene 5 — Problem + MCQ auto-grade (~35s)
- **[SHOW]** Study a **Speedrun::Problem** multiple-choice card. **Click a choice** — it's graded **backend-side against the answer key**: **correct → green + locked**, **wrong → red + the key revealed**.
- **[SAY]** "These are real multiple-choice problems, and grading happens **in the engine, against the answer key** — click a choice and it's checked immediately: green and locked if you're right, red with the correct key shown if you're not. That matters, because it means **Performance is now objectively key-checked** — not self-rated. The app knows whether you actually got it right, so the number it reports is real."

### Scene 6 — Timed mini-mock (~20s)
- **[SHOW]** On Home, click **MINI-MOCK** → a **timed** set drawn from the problem bank. Answer a couple, finish.
- **[SAY]** "A mini-mock is a short **timed** set over the problem bank. It's what feeds Readiness — and Readiness won't show a number until you've done **at least two**. Timing is captured automatically; nothing is faked to make the run look good."

### Scene 7 — Calibration self-bet + reliability diagram (~35s)
- **[SHOW]** In the **Memory** area, study a problem and **place a pre-answer bet — Sure / Think / Guess** — then grade it. Then open the **reliability diagram**: **stated confidence vs actual (key-checked) accuracy**, with **Brier / ECE**. Abstains until enough bets; show real once logged.
- **[SAY]** "Before you check, you bet on yourself — Sure, Think, or Guess. We log that bet against how you **actually** did — and because grading is now key-checked, the outcome is objective. The **reliability diagram** plots your stated confidence against your real accuracy, scored with **Brier and ECE**. This is weaponized honesty: it tells you exactly where you're overconfident. And like everything else, it **abstains** until it has enough bets — no fabricated curve."

### Scene 8 — Memory→Performance gap (~25s)
- **[SHOW]** Still in **Memory**, show the **slope chart**: per topic, **recall (Memory)** on one side vs **timed-problem accuracy (Performance)** on the other, lines connecting them.
- **[SAY]** "And here's the gap we care about most — the **slope chart**. For each topic it puts what you **remember** next to how you actually **perform** under time. When the line drops, that's the honest message: *you remember it, but you can't use it yet.* That's the difference between flashcards and being ready for the exam."

### Scene 9 — Two apps, one engine + live sync (~40s)
- **[SHOW]** Switch to the **Android emulator**; open the app → the **same Speedrun Home**, the **same three scores**, the **same THE MAP**. Then trigger a **live self-hosted sync** — study/answer on one device and sync it to the other.
- **[SAY]** "Here's the same app on Android — not a reimplementation. It's the **same Rust engine** cross-compiled for the phone, rendering the **same shared pages** and the same scores. One codebase, two platforms. And it **syncs through a self-hosted server** — your data, your machine — so a problem I answer here shows up over there. One engine, two apps, honestly in sync."

### Scene 10 — Honest close (~20s)
- **[SAY]** "That's Speedrun: one engine on two apps, a Readiness gauge that draws its own uncertainty, a prerequisite map that shows you what to fix first, objectively-graded problems, calibration that measures how well you know yourself — and scores that each know when to stay silent. All built on Anki. We'd rather ship something true than something that just looks impressive."

### Optional — AI aside (~20s, ONLY if you enabled it)
- **[SHOW]** A terminal running `services/speedrun-ai` (`SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`); hit `/generate` → a problem that passed **SymPy verify → RAG source citation → gold-gate**, or an honest **abstain** that emits nothing.
- **[SAY]** "Optionally, there's a **separate** AI generator — **off by default**, and never inside the study app. When you turn it on, every problem is checked by a real symbolic verifier, **grounded in a cited source**, and cleared by a gold-set gate — or it **abstains and emits nothing**. The app never depends on it being up."

---

## Honesty guardrails (enforced on camera)
- ❌ Never show a **fabricated number on an abstaining/empty state** — if a score, the Readiness gauge, or a MAP node has no data, show the honest **"—" / "insufficient data" / "review N more to unlock"**. Real numbers come from real accumulated study, not a config tweak.
- ❌ Never say "we improved / changed **FSRS**" — we build **on** it, unchanged.
- ❌ Don't present **Readiness before ≥2 mini-mocks**; don't draw a per-topic Readiness number — exam-level is the real Readiness.
- ❌ Don't imply the **AI runs inside the app** — it's a separate, OFF-by-default service; only show it in the optional aside after explicitly enabling it (`SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`).
- ✅ **Problem grading is now objective** — MCQ answers are key-checked backend-side, so **Performance is key-checked, not self-rated**. In the calibration beat, be clear: the **confidence bet is self-reported**, but the **outcome is objectively graded**.
- ✅ Safe to show: the auto-imported deck on first launch, the three honest scores, the **Readiness gauge with its conformal band**, **THE MAP** with real mastery colors + grey abstains + the blast-radius highlight, points-at-stake **new-card** ordering + weakness×topic **due-card** interleave, backend MCQ auto-grade, the timed mini-mock, the **calibration self-bet + reliability diagram (Brier/ECE)**, the **memory→performance slope chart**, one-engine-two-apps with a **live self-hosted sync**.

## Pairs with
- `docs/DEMO-SCRIPT.md` (click-by-click operator steps) · `docs/WHAT-WE-BUILT.md` (honest content reference) · `docs/RUN-MVP.md` (how to launch both apps).
