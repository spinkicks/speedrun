# Speedrun — MVP Demo Video Script (draft)

> **Deliverable:** the "Speedrun MVP Demo Video" (target 3–5 min). Scene-by-scene: **[SHOW]** = on-screen action, **[SAY]** = narration. Content is grounded in `docs/WHAT-WE-BUILT.md`; **honesty rules from there apply — never claim scaffolding/planned items as done.** Draft 2026-07-01 — **record after** the mobile-first + START RUN work lands (scenes flagged ⏳ depend on it).

## Before recording (setup)
- Desktop: `just run` (Anki in **dark mode**; Speedrun Home auto-opens). Import the seed deck `speedrun/out/gre_math_seed.apkg` in a throwaway profile; do ~a few reviews on 1–2 topics beforehand so at least one topic shows a **real recall % + range** (not all-abstaining) — this makes the honesty story land.
- Android: emulator (`Pixel_10`) with the app installed (`installPlayDebug`), same seed deck.
- Have both windows ready to alt-tab / screen-record.

## Runtime budget (~4 min)
1. Positioning — 20s · 2. Honest measurement — 60s · 3. Study loop — 45s · 4. Two apps, one engine — 45s · 5. Under the hood — 45s · 6. Sync + installer — 20s · 7. Honest close — 25s.

---

### Scene 1 — Positioning (~20s)
- **[SHOW]** Desktop launches straight into **Speedrun Home** ("The Run").
- **[SAY]** "This is Speedrun — an honest study trainer for the GRE Math Subject Test. It's built **on top of Anki's** proven spaced-repetition engine, but it's its own app: our own front door, our own scores, running the same engine on desktop and phone. The theme of the whole thing is honesty — it never shows you a number it can't back up."

### Scene 2 — The honest measurement (~60s) — the differentiator
- **[SHOW]** Point at the splits: a topic with a real recall % and its **95% range bracket**; then an abstaining row ("🔒 20 more to unlock").
- **[SAY]** "Each topic is a split. For topics you've studied enough, we show your recalled memory with a **95% confidence range** — not a single fake number. For topics without enough data, we **abstain**: 'review 20 more to unlock.' Most study apps invent a confident score; we refuse to until the data earns it."
- **[SHOW]** Open the **Memory dashboard** (Tools → Speedrun: Memory, or the Home link); coverage header + per-topic ranges.
- **[SAY]** "The Memory dashboard is the same idea in depth — coverage against the real exam blueprint, and per-topic mastery with ranges and abstention."

### Scene 3 — The study loop ⏳ (~45s) *(needs START RUN fix S1)*
- **[SHOW]** Click **► START RUN** → a real review session on the GRE deck; answer a card or two. (If nothing's due, show the honest "all caught up / Custom Study" state.)
- **[SAY]** "START RUN drops you straight into studying the exam deck. Under the hood this is Anki's FSRS scheduler — we didn't reinvent memory science, we built on the best. What we add on top is **how the new cards are ordered**: by points-at-stake — the highest-weighted exam topics — and **interleaved** across topics, which the research shows beats blocked practice."

### Scene 4 — Two apps, one engine (~45s)
- **[SHOW]** Switch to the Android emulator; open the app → the **same Speedrun Home**, then Memory; same splits, same abstention.
- **[SAY]** "Here's the same app on Android — and it's not a reimplementation. It's the **same Rust engine** cross-compiled for the phone, rendering the **same shared UI**. One codebase, one engine, two platforms — build it once, it works on both."

### Scene 5 — Under the hood (~45s) — the real engine change
- **[SHOW]** Briefly: the `speedrun.proto` service / the test suite passing (`cargo test -p anki speedrun::`) — or just narrate over the app.
- **[SAY]** "The engine change is real Rust in Anki's core: read-only RPCs for coverage and topic mastery, and one **mutating** change — the points-at-stake reorder — done the safe way through Anki's transaction system, fully undoable, with tests proving the database stays intact. Small, surgical, and it runs identically on both apps."

### Scene 6 — Sync + clean install (~20s)
- **[SAY]** (over the app, or a quick sync screen) "It syncs through a **self-hosted server** — your data, your machine — with a tested conflict rule. And it builds into a real installer on a clean machine with no external dependencies."

### Scene 7 — Honest close (~25s)
- **[SAY]** "That's the honest MVP: one engine on two apps, real memory measurement that knows when to stay silent, and a genuine learning-science ordering feature — all built on Anki. Coming next: performance and readiness scores with the same honesty bar, and AI-generated practice that's checked before you ever see it. We'd rather ship something true than something that looks impressive. That's Speedrun."

---

## Honesty guardrails (do NOT say on camera — not built yet)
- ❌ "readiness score / performance prediction / it's calibrated" — those **abstain by design** today; don't present a number.
- ❌ "the AI checks the problems" — no AI yet (Friday).
- ❌ "we improved / changed FSRS" — we build **on** it, unchanged.
- ❌ "weakness-driven scheduling" — the reorder is **new-card order** only so far.
- ✅ Safe: mastery + ranges + abstention, points-at-stake **new-card** interleaving, one-engine-two-apps, self-hosted sync + tested conflict rule, clean-machine installer.

## Pairs with
- `docs/DEMO-SCRIPT.md` (click-by-click operator steps — written after the UI lands) · `docs/WHAT-WE-BUILT.md` (honest content reference) · `docs/RUN-MVP.md` (how to launch both apps).
