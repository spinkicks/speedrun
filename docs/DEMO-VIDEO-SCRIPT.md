# Speedrun — Demo Video Script

> **Deliverable:** the "Speedrun Demo Video" (target 3–5 min). Scene-by-scene: **[SHOW]** = on-screen action, **[SAY]** = narration. Content reflects the **currently shipped app** and the honesty rules in `docs/WHAT-WE-BUILT.md` **apply on camera — never present a number the app can't back up.** Draft **2026-07-03** — everything below is **merged to `main`** on every fork (desktop engine, Android, backend, the shared Svelte pages), so this is **safe to record now**. The only setup requirement: record on a **profile that has some accumulated study data** so the scores, the Readiness gauge, and THE MAP are populated with real colors — otherwise honestly show the **abstain states**.

## What Speedrun is (one-liner for the intro)
An **honest** GRE Math Subject Test trainer built **on** Anki — same **Rust engine** on **desktop and Android**, its own **"Speedrun" identity** (Manrope wordmark, near-white **#F4F7FA** accent, mobile-first dark shell), with an **external AI service that is OFF by default**. It never shows you a number it can't defend.

## Friday deliverables → where each one appears (checklist for the recording)
Every "Due Friday" item must be visible on camera or in the captured proof. Map:

| Due-Friday item | Scene / proof |
| --- | --- |
| **AI: a short note on what you built, why, what you skipped** | Scene 11 [SAY] + show `services/speedrun-ai/README.md` |
| **AI: every output traces to a named source** | Scene 11 — each generated card shows its **cited source**; no citation ⇒ abstains, emits nothing |
| **AI: eval before students see anything — accuracy + wrong-answer rate on a held-out set, with a cutoff** | Scene 12 — `uv run python -m eval.gate`: **wrong-answer 0 %** (cutoff ≤2 %), **Recall@10 90 %** (family), **leakage 0** |
| **AI: side-by-side vs a simpler method (keyword / vector)** | Scene 12 — BM25 vs dense vs hybrid table (**honest framing — see guardrails**) |
| **AI: app still scores with AI OFF** | Scene 4/13 — kill-switch (`/generate` → 503 disabled); the 3 scores are engine-computed, AI service never imported |
| **Mobile: two-way sync, no lost/double-counted reviews** | Scene 9 — review on phone → appears on desktop and the reverse; back it with the §7b test (20 distinct revlog both sides, `integrity_check ok`) |
| **Mobile: offline review, then syncs on reconnect** | Scene 9 — airplane-mode a review on one device, reconnect, sync |
| **Mobile: phone shows the three scores with ranges + follows the give-up rule** | Scene 9 — Android Home: Memory/Performance/Readiness with **RangeBand** + honest **"review N more to unlock"** abstains |
| **Proof: eval numbers + baseline comparison + phone→desktop sync recording** | Scene 12 (numbers) + Scene 9 (sync capture) + `docs/PROOF-INDEX.md` |

## Before recording (setup)
- **Desktop:** `just run` inside `repos/anki`. **The installer now ships WITH the deck** — it's **auto-imported on first launch**, so the app opens **straight into Speedrun Home with data available**. **Do not do a manual import on camera.**
- **Use a profile that has genuinely accumulated study** so scores/visuals are populated: Memory unlocks per topic after enough graded reviews; Performance needs logged (key-checked) problem attempts; **Readiness needs ≥2 timed mini-mocks**; Calibration needs enough confidence bets. Wherever a score/topic is still abstaining, **show the abstention** ("—" / "review N more to unlock") — that honesty is the differentiator. **Never fake a number for the camera.**
- **Android:** emulator (`Pixel_10`, x86_64) with the app installed, signed into the **same self-hosted sync** account as desktop so you can show a live sync.
- **AI is a REQUIRED Friday beat now (Scenes 11–13), but still lives OUTSIDE the app.** Have `services/speedrun-ai` ready to start with `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY` (`uv run uvicorn app:app --port 8000`) for the Generate button + eval scenes, then stop it for the kill-switch scene. Never imply the AI runs inside rslib/rsdroid — the in-app **Generate** button calls the service over localhost and imports only verified problems.
- Have both windows ready to alt-tab / screen-record.

## Runtime budget (~6–7 min; AI + eval scenes are REQUIRED for Friday, not optional)
1. Install & open — 20s · 2. Speedrun Home + Readiness gauge — 40s · 3. **THE MAP** — 45s · 4. START RUN + ordering — 25s · 5. Problem + MCQ auto-grade — 35s · 6. Mini-mock — 20s · 7. Calibration self-bet + reliability diagram — 35s · 8. Memory→Performance gap — 25s · 9. **Two apps, one engine + two-way / offline sync + phone 3 scores** — 55s · 10. Honest close — 20s · **11. AI generator + named-source citation — 35s · 12. AI eval + baseline side-by-side (the "checked" deliverable) — 40s · 13. Kill-switch: app still scores with AI OFF — 15s.**

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

### Scene 9 — Two apps, one engine + two-way / offline sync + phone three scores (~55s) — the Friday MOBILE deliverable
- **[SHOW]** Switch to the **Android emulator**; open the app → the **same Speedrun Home**, the **same three scores** (Memory / Performance / Readiness) each with its **range band**, and where a topic hasn't earned data, the honest **"review N more to unlock"** give-up state. Same **THE MAP**.
- **[SHOW — two-way, no lost/double-count]** Both devices signed into the **same self-hosted sync** account. **Answer a card on the phone → sync → it appears on the desktop.** Then the **reverse**: answer on desktop → sync → shows on the phone. Point out the review count is consistent — **nothing lost, nothing double-counted**.
- **[SHOW — offline then reconnect]** Put the phone in **airplane mode**, review a card offline (it works), then **turn the connection back on and sync** — the offline review lands on the desktop.
- **[SAY]** "Here's the same app on Android — not a reimplementation. It's the **same Rust engine** cross-compiled for the phone, rendering the **same shared pages** and the same three scores, each with its honest range and the same give-up rule. It **syncs through a self-hosted server** — your data, your machine. A card I answer on the phone shows up on the desktop, and the reverse — with **no lost or double-counted reviews** (the engine unions the review log and checks integrity). And it works **offline**: review on the plane, and when the connection comes back it syncs cleanly. One engine, two apps, honestly in sync."
- **[PROOF]** This scene is the required **phone→desktop sync recording**; also grab a still of the **Android three-scores** screen for `docs/PROOF-INDEX.md`. Backing test: the §7b conflict test (`repos/anki/rslib/src/sync/collection/tests.rs`) asserts all 20 distinct revlog entries on both sides + `integrity_check = ok`.

### Scene 10 — Honest close (~20s)
- **[SAY]** "That's Speedrun: one engine on two apps, a Readiness gauge that draws its own uncertainty, a prerequisite map that shows you what to fix first, objectively-graded problems, calibration that measures how well you know yourself — and scores that each know when to stay silent. All built on Anki. We'd rather ship something true than something that just looks impressive."

### Scene 11 — AI generator + named-source citation (~35s) — REQUIRED (Due-Friday: AI added; every output cites a source)
- **[SHOW]** Start the external service (`services/speedrun-ai`, `SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`). On the desktop, open **THE MAP**, tap a **covered leaf topic (e.g. Calculus)**, and click **"⚡ Generate 5 practice problems."** The button is **only enabled when the service is reachable AND the topic is covered** (else it's disabled with an honest hint). On success: a toast "**Added N verified problems**," and each new card shows its **cited source**. Briefly show `services/speedrun-ai/README.md` — the **what / why / skipped** note.
- **[SAY]** "The AI is a **separate service, off by default** — the study app never depends on it. Turn it on and you get a **Generate** button right on THE MAP, but only for topics the corpus actually covers. Every problem it adds went through a real **SymPy symbolic verifier**, was **grounded in a cited source**, and cleared a **gold-set leakage gate** — and every card it imports **shows that named source**. If it can't produce a verified, grounded problem, it **abstains and emits nothing** — it never imports a guess. What we skipped is written down too: no LLM reranker, and an entailment/support check is future work."

### Scene 12 — AI eval + baseline side-by-side (~40s) — REQUIRED (Due-Friday: "checked" — accuracy, wrong-answer rate, cutoff, baseline)
- **[SHOW]** A terminal: `PYTHONIOENCODING=utf-8 uv run python -m eval.gate` in `services/speedrun-ai/`. Show the recorded numbers (also in `services/speedrun-ai/eval/README.md`):
  - **Wrong-answer rate = 0 %** (0/6 deliberately-wrong specs survived the verifier), pre-registered cutoff **≤ 2 %**.
  - **Recall@10 = 90 %** (family, 45/50) on the **held-out** gold set; **leakage = 0**.
  - **Baseline side-by-side (Recall@10):** BM25 **0.900** · dense/vector **0.900** · **hybrid 0.900** — hybrid **≥ each single-arm baseline (never regresses)**.
- **[SAY]** "Before any of this reaches a student, it runs an eval on a **held-out set the generator and corpus never saw**. The number that matters most: **zero percent wrong answers** — anything the symbolic verifier can't confirm is dropped, against a pre-registered two-percent cutoff. Retrieval hits **ninety percent** of the right sources, with **zero leakage**. And here's the honest **side-by-side against the simpler methods** — keyword search and vector search: on this small, curated corpus **all three saturate at the same ninety percent**, so our hybrid **matches** them and, importantly, **never regresses below either** — we deliberately **don't manufacture a win the data doesn't support.** Where our AI decisively **beats** a naive generator is safety: **zero wrong answers** because every problem is symbolically verified — a plain keyword-or-vector pipeline with no verifier ships wrong answers."
- **[PROOF]** The eval output + `services/speedrun-ai/eval/README.md` are the **eval-numbers + baseline** proof for submission (`docs/PROOF-INDEX.md`).

### Scene 13 — Kill-switch: the app still scores with AI OFF (~15s) — REQUIRED (Due-Friday: score with AI switched off)
- **[SHOW]** Stop the AI service (or unset the key). The **Generate** button on THE MAP goes **disabled**; the three scores on Home are **unchanged**. Optionally show `POST /generate` → **503** when disabled.
- **[SAY]** "And with the AI switched **completely off** — service down, no key — the app still does everything: all three scores, THE MAP, sync, calibration. The scores are computed by the **Anki engine** from the curated bank; the AI service is **never imported** into it. The intelligence is a bonus, never a crutch."

---

## Honesty guardrails (enforced on camera)
- ❌ Never show a **fabricated number on an abstaining/empty state** — if a score, the Readiness gauge, or a MAP node has no data, show the honest **"—" / "insufficient data" / "review N more to unlock"**. Real numbers come from real accumulated study, not a config tweak.
- ❌ Never say "we improved / changed **FSRS**" — we build **on** it, unchanged.
- ❌ Don't present **Readiness before ≥2 mini-mocks**; don't draw a per-topic Readiness number — exam-level is the real Readiness.
- ❌ Don't imply the **AI runs inside rslib/rsdroid** — the generator is a separate, OFF-by-default HTTP service; the in-app **Generate** button calls it over localhost and imports only verified problems. The three scores never depend on it.
- ❌ **On the baseline side-by-side, do NOT claim "our RAG beats keyword/vector."** The honest measured result is a **tie at the coverage ceiling (all 0.900)** with **non-regression** (hybrid ≥ each arm). The legitimate "beats a simpler method" claim is at the **safety** layer: **0 % wrong-answer via SymPy verification** vs an unverified generator. Say it exactly that way.
- ✅ **Problem grading is now objective** — MCQ answers are key-checked backend-side, so **Performance is key-checked, not self-rated**. In the calibration beat, be clear: the **confidence bet is self-reported**, but the **outcome is objectively graded**.
- ✅ **Useful / bad-teaching quality metrics are LLM-judge-gated** — only their cutoffs (≥80 % useful, ≤15 % bad-teaching) are pre-registered; run them at demo time with the key if you want them on camera, otherwise don't claim they're met.
- ✅ Safe to show: the auto-imported deck on first launch, the three honest scores, the **Readiness gauge with its conformal band**, **THE MAP** with real mastery colors + grey abstains + the blast-radius highlight + the **⚡ Generate** button, points-at-stake **new-card** ordering + weakness×topic **due-card** interleave, backend MCQ auto-grade, the timed mini-mock, the **calibration self-bet + reliability diagram (Brier/ECE)**, the **memory→performance slope chart**, one-engine-two-apps with a **two-way + offline self-hosted sync**, the **0 % wrong-answer eval + baseline table**, and the **AI-off kill-switch**.

## Proof to capture for submission (Friday)
1. **Eval numbers** — terminal run of `python -m eval.gate` (wrong-answer 0 %, Recall@10 90 %, leakage 0) + `services/speedrun-ai/eval/README.md`.
2. **Baseline comparison** — the BM25 / dense / hybrid table (honest parity + non-regression) from the same eval README.
3. **Phone→desktop sync recording** — a card reviewed on the phone appearing on the desktop after sync (and the reverse; plus the offline-then-reconnect clip).
4. **Android three-scores still** — Home showing Memory/Performance/Readiness with ranges + a give-up state.
5. Log all four in `docs/PROOF-INDEX.md`.

## Pairs with
- `docs/DEMO-SCRIPT.md` (click-by-click operator steps) · `docs/WHAT-WE-BUILT.md` (honest content reference) · `docs/RUN-MVP.md` (how to launch both apps).
