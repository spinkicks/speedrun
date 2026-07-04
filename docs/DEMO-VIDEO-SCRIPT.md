# Speedrun — Demo Video Script

Target 3–5 min. **Read the plain text out loud; do the *italic actions*.** Golden rule: never show a number the app can't back up — where a score has no data, show the honest **"—"**.

---

## Setup before recording (do this once)

All terminals are **PowerShell**, started from the repo root `c:\Users\davir\Ultra\Alpha\Speedrun`.

### Terminal A — Desktop app
```powershell
cd repos\anki
just run
```
Then **off-camera**: `File → Import` → `repos\anki\speedrun\out\gre_math_seed.apkg` (once), and study ~20 cards + run 2 mini-mocks + place a few confidence bets so the scores and visuals have real data. Begin recording on **Speedrun Home**.

### Terminal B — AI service (for scenes 10–12)
Make sure `services\speedrun-ai\.env` has `OPENAI_API_KEY=...` and `SPEEDRUN_AI_ENABLED=1`, then:
```powershell
cd services\speedrun-ai
uv sync                              # first run only: installs deps (incl. uvicorn) into the venv
uv run uvicorn app:app --port 8000   # leave this running; serves on http://127.0.0.1:8000
```
Verify it's up (in Terminal C or a browser): open `http://127.0.0.1:8000/health` → should show `{"status":"ok","ai_enabled":true}`. If it says `ai_enabled:false`, the `.env` key/flag isn't set.

### Terminal C — Eval numbers (run when you reach scene 11)
```powershell
cd services\speedrun-ai
$env:PYTHONIOENCODING = "utf-8"
uv run python -m eval.gate
```

### Terminal D — Android emulator (for scene 9)
```powershell
# paths on this machine
$sdk = "C:\Users\davir\AppData\Local\Android\Sdk"
$adb = "$sdk\platform-tools\adb.exe"
$emu = "$sdk\emulator\emulator.exe"

# 1. Boot the Pixel_10 AVD (detached, so this terminal stays usable)
Start-Process $emu -ArgumentList "-avd","Pixel_10"

# 2. Wait until it's fully booted
& $adb wait-for-device
do { Start-Sleep 2 } until ((& $adb shell getprop sys.boot_completed 2>$null).Trim() -eq "1")
"Emulator booted."

# 3. Install the app + push the deck
& $adb install -r "C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki-android\AnkiDroid\build\outputs\apk\play\debug\AnkiDroid-play-x86_64-debug.apk"
& $adb push "C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki\speedrun\out\gre_math_seed.apkg" /sdcard/Download/
```
In the phone app: open **AnkiDroid → Speedrun: Home**, import the deck from `Download/gre_math_seed.apkg`, then sign into the **same** self-hosted sync server as desktop (`docs\SYNC-SELFHOST.md`).

---

## Script

**1 — Open.** "This is Speedrun *scrolls Speedrun Home* — an honest trainer for the GRE Math Subject Test, built on top of Anki's spaced-repetition engine. Same engine on desktop and phone, our own front door, and one rule: it never shows you a number it can't back up."

**2 — Three scores + Readiness gauge.** "Three scores, each earned from real data *points at Memory, Performance, Readiness*. Memory is recalled mastery, shown as a range. Performance is your chance on a novel problem. And Readiness maps onto the real 200-to-990 exam scale *points at the gauge and its band* — with a band for the uncertainty, not just a point. Below its data threshold it just abstains *points at a '—'* — no fake number."

**3 — THE MAP.** "This is THE MAP *clicks THE MAP ▸* — the prerequisite graph of the whole subject. Every node is colored by your real mastery; grey ones honestly say '—'. Tap a weak topic like Calculus *taps a node* and its blast radius lights up *gestures at the highlighted downstream nodes* — everything it's holding back. Fix the root, and you lift everything above it."

**4 — START RUN.** "START RUN *clicks ► START RUN* drops you into the exam deck. This is Anki's FSRS scheduler, unchanged — what we add is ordering: new cards by points-at-stake, and due reviews interleaved by weakness across topics."

**5 — Problem + auto-grade + worked example.** "These are real multiple-choice problems *clicks a choice* — graded in the engine against the answer key: green if you're right, red with the key if you're not *shows the marking*. So Performance is objectively key-checked, not self-rated. Reveal the solution *reveals the worked solution* and you get a worked example with faded steps — not just the answer."

**6 — Mini-mock.** "A mini-mock *clicks MINI-MOCK* is a short timed set from the problem bank — it's what feeds Readiness, which won't show a number until you've done at least two."

**7 — Calibration.** "Before you check, you bet on yourself — Sure, Think, or Guess *places a bet, then grades the card*. We log that against how you actually did and plot it on the reliability diagram *opens the reliability diagram* — stated confidence versus real accuracy, scored with Brier and ECE. It shows exactly where you're overconfident — and abstains until it has enough bets."

**8 — Memory→Performance gap.** "And the gap we care about most *shows the slope chart* — what you remember versus how you perform under time. When the line drops, you remember it but can't use it yet. That's the difference between flashcards and being exam-ready."

**9 — Two apps, one engine + sync.** "Same app on Android *switches to the emulator* — same engine, the same three scores with ranges, the same MAP. I answer a card on the phone *answers a card, syncs* and it shows up on the desktop *shows it on desktop* — and the reverse — with no lost or double-counted reviews. And it works offline *airplane-mode a review, then reconnect and sync*: review on the plane, and it syncs when you're back."

**10 — AI generate + cited source.** "There's also a separate AI generator — off by default, never inside the study app. Turn it on *(Terminal B running)* and tap Generate on a covered topic *clicks ⚡ Generate 5 practice problems* — every problem it adds was SymPy-verified, grounded in a cited source, and gold-gated, and each card shows its source *points at the citation*. If it can't verify one, it abstains and adds nothing."

**11 — The eval (the "checked" part).** "Before any of that reaches a student, it runs an eval *shows Terminal C output* on a held-out set: zero percent wrong answers against a two-percent cutoff, ninety percent retrieval, zero leakage. Here's the honest side-by-side against keyword and vector search *points at the BM25 / dense / hybrid table* — on this small curated corpus all three tie at ninety percent, so we match them and never regress; we don't fake a win. Where our AI actually beats a naive baseline is safety: zero wrong answers, because every problem is symbolically verified."

**12 — Kill switch.** "And with the AI switched fully off *stops Terminal B — the Generate button disables* the app still does everything — all three scores, the MAP, sync, calibration. The scores come from the engine; the AI is a bonus, never a crutch."

**13 — Close.** "That's Speedrun: one engine on two apps, honest scores that draw their own uncertainty, a map that shows what to fix first, objectively-graded problems, and calibration that measures how well you know yourself. All built on Anki — we'd rather ship something true than something that just looks impressive."

---

## Keep it honest (on camera)
- Show **"—"** wherever a score or topic has no data — never fake a number.
- Don't say we changed **FSRS** — we build on it, unchanged.
- Don't claim the RAG **beats** keyword/vector — it's an honest **tie**; the real win is **0% wrong via verification**.
- Readiness needs **≥2 mini-mocks** and is **exam-level only** (no per-topic Readiness number).

## Friday deliverables covered
AI note + every-output-cited (scene 10) · eval accuracy / wrong-rate / cutoff + baseline (11) · scores with AI off (12) · two-way + offline sync, no lost/double-count (9) · phone shows 3 scores with ranges (9).
**Proof to save:** the scene-11 eval output + `services/speedrun-ai/eval/README.md`, the phone→desktop sync clip, and an Android 3-scores screenshot → log in `docs/PROOF-INDEX.md`.
