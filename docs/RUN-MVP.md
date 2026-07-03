# Running the Speedrun MVP

Authoritative run guide, **updated 2026-07-03**: forked Anki (desktop) and AnkiDroid (Android emulator) both drive **one** Rust engine (`rslib`) exposing the `SpeedrunService` RPCs (coverage, topic-mastery, exam-profile, **performance/readiness**, **calibration**, and the mutating points-at-stake reorder), a shared Svelte **Speedrun Home** + **Memory dashboard** on both platforms, a seed exam deck **plus a 64-problem `Speedrun::Problem` MCQ bank + timed mini-mock**, desktop calibration self-bet capture, and a self-hosted sync server. **Speedrun Home is merged and auto-opens on launch** on desktop (Manrope ExtraBold / #F4F7FA branding).

All work is merged into **`main`** on all three forks (anki `c54afe2b1` · Anki-Android-Backend `14c2992` · anki-android `f2cf66ac35`; feature branches kept as backup), so the steps below just use `main`. The **Phase 6 AAR is already rebuilt** against anki `main`, and the Android APK is compiled.

> **Human gates still pending (not blockers to running):** the on-emulator visual pass, a live desktop↔phone sync-demo recording, the demo video, Sunday evals, and a signed APK. Everything below runs today off `main` — the earlier pre-merge audit blockers (desktop webview→backend path, exam-profile bootstrap) are fixed and merged.

All paths are relative to the workspace root `C:\Users\davir\Ultra\Alpha\Speedrun`. Build commands use `just` (NOT `./ninja`/`./run`) per `repos/anki/CLAUDE.md`.

## Which terminal
- **Use Windows PowerShell (or `pwsh`) for everything below.** That's the shell where Rust, `just`, `uv`, `node`/`yarn`, and (for Android) `ANDROID_HOME`/`ANDROID_NDK_HOME` are on PATH.
- **MSYS2 must be on PATH** for the desktop build (it shells out to `rsync`): ensure `C:\msys64\usr\bin` is on PATH. (MSYS2 **bash** was only needed once, for `tools/install-n2`; you do NOT need bash to run/build.)
- One-time per machine (already done here): MSYS2 `rsync`, `n2`, `just`, the Defender exclusion on `repos\anki`, Android SDK + NDK `29.0.14206865`, and the `Pixel_10` x86_64 AVD.

---

## A. Desktop (forked Anki with our engine)

In **PowerShell**:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki
git checkout main          # all Speedrun work is on main (c54afe2b1)
just run                   # builds + launches the desktop app (first build is slow)
```
The Anki window opens running our forked `rslib` and **auto-opens Speedrun Home** ("The Run"). Web pages serve at `http://localhost:40000/_anki/pages/`. `ANKIDEV` is auto-set (auto-backups off — safe throwaway profile). (Auto-open is config-gated by `speedrunHomeAutoOpenEnabled`, default on; *Tools → Speedrun: Home* / *Tools → Speedrun: Memory* reopen the pages.)

**0. (once) Build the seed deck with the problem bank** — the seed apkg now bundles the declarative cards **and** the 64 `Speedrun::Problem` MCQs. If `speedrun\out\gre_math_seed.apkg` is stale or missing, rebuild it (out-of-tree venv via the `uvw` wrapper — do NOT run bare `uv` here, per `speedrun/README.md`):
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki\speedrun
pwsh uvw.ps1 sync
pwsh uvw.ps1 run python seed\build_seed_deck.py   # -> out\gre_math_seed.apkg (35 cards + 64 problems)
```

**1. Import the seed exam deck:** *File → Import…* → `repos\anki\speedrun\out\gre_math_seed.apkg`. This imports two decks: `Speedrun::GRE Math` (35 hand-authored calc+LA notes, hierarchical `calc::…` / `linear_algebra::…` tags, Source on every card) and `Speedrun::GRE Math::Problems` (the 64 scored `Speedrun::Problem` MCQs the mini-mock draws from). Review a few cards for the demo.

**2. Run the honest-score flow from Speedrun Home:**
- **► START RUN** → launches a real reviewer session on `Speedrun::GRE Math` (new cards ordered by points-at-stake; due reviews weakness×topic interleaved). On a fresh/empty deck it shows an honest banner ("import" / "caught up" / Custom Study) instead of a dead-end.
- **MINI-MOCK** → builds a **timed** filtered deck over the Problems subdeck; per-answer wall-clock is captured automatically and feeds **Performance** + the **Readiness** give-up counter (Readiness needs **≥2** mini-mocks before it shows a number).
- On a **`Speedrun::Problem`** card, the pre-answer **Sure / Think / Guess** confidence buttons log a self-bet (desktop capture hook) that powers the **Calibration** score (Brier/ECE; abstains under 20 attempts; self-rated framing).
- The three headline scores on Home — **Memory** (Wilson 95% range), **Performance** (P(correct) on problems + memory→performance gap Δ), **Readiness** (flat-IRT 200–990 + conformal range) — each **abstain honestly** until they have enough real data. That abstention IS the honest-score demo; ranges/points fill in only as real reviews and mini-mocks accumulate. **Never expect a filled score on a fresh deck.**

**3. Open the Memory dashboard:** *Tools → Speedrun: Memory* (or the Home link). Expect: coverage header (topics present / required), grouped topic rows with recall ranges, and per-topic ABSTAIN ("insufficient data — review N more to unlock") on fresh data. Per-topic Readiness is intentionally "—" (exam-level Readiness on Home is the real score).

**4. RPC from the Debug Console** (optional, proves the seam directly — *Tools → Debug Console*):
```python
col.speedrun.coverage(["calc", "linear_algebra"])          # CoverageResponse(..., backend_version="26.05")
col.speedrun.topic_mastery(["calc::limits"])               # Wilson range + abstained flag
col.speedrun.performance_readiness(["calc::limits"])       # per-topic P(correct) + overall Readiness (abstains until enough data)
col.speedrun.calibration([])                               # Brier/ECE over logged self-bets (abstains < 20 attempts)
col.speedrun.reorder_new(1, {"calc": 0.9, "linear_algebra": 0.1})  # mutating; undoable via Edit→Undo
```

**Run the engine tests / full gate** (PowerShell, in `repos\anki`):
```powershell
cargo test -p anki speedrun::   # Speedrun Rust tests (pure + integration)
cargo test -p anki sync::speedrun_two_way   # §7b sync conflict test
just test-py                    # pylib test_speedrun (Python integration)
just check                      # full build + lint + tests (green modulo known complexipy crash)
```

**Self-hosted sync demo:** launch + point clients per `docs/SYNC-SELFHOST.md` (server: `anki-sync-server` env `SYNC_USER1/SYNC_PORT/SYNC_BASE`; desktop custom sync URL; Android custom sync server → `http://10.0.2.2:8088/` from the emulator).

---

## B. Android (AnkiDroid on the x86_64 emulator, same engine)

**1. Build the AAR from our `rslib`** — PowerShell:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\Anki-Android-Backend
git checkout main                         # 14c2992 (Phase 6 AAR rebuilt against anki main)
git submodule update --init --recursive   # anki submodule pinned to our fork @ c54afe2b1 (main)
cargo run -p build_rust                    # (== build.bat) -> rsdroid AAR (x86_64; bundles the sveltekit pages)
```
Output: `rsdroid\build\outputs\aar\rsdroid-release.aar`. (The submodule pin already tracks anki `main` `c54afe2b1`, so the shipped AAR includes the three scores, calibration, and mini-mock frontend. Rebuild only if you change `rslib` / the shared pages.)

**2. Point AnkiDroid at the local AAR** — PowerShell:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki-android
git checkout main                          # f2cf66ac35
# ensure local.properties contains:  local_backend=true
```

**3. Launch the emulator** — PowerShell (separate window is fine):
```powershell
& "$env:ANDROID_HOME\emulator\emulator.exe" -avd Pixel_10
# headless/unattended variant: add  -no-window -no-snapshot -no-boot-anim
```

**4. Build + install + run the app on the emulator** — PowerShell, in `repos\anki-android`:
```powershell
.\gradlew :AnkiDroid:installPlayDebug
# NOTE: AnkiDroid has product flavors (amazon/full/play) — there is NO plain
# `installDebug`. Use installPlayDebug (standard dev) or installFullDebug (FOSS).
# then open the AnkiDroid app on the emulator
```
(Or open `repos\anki-android` in Android Studio and press Run with `Pixel_10` selected.)

**5. Open Speedrun Home + Memory on the phone:** in AnkiDroid, import the same seed `.apkg` (share it to the emulator or use *Import*), then from the DeckPicker **⋮ overflow menu → "Speedrun: Home"** (and **"Speedrun: Memory"**). The SAME shared Svelte pages render from the AAR-bundled assets — the same three scores, abstaining honestly on fresh data, identical to desktop. (The desktop-only calibration self-bet capture and the bespoke timed mini-mock UI are desktop-side this cycle; Android studies the same Problems subdeck through its native reviewer.)

**6. Re-run the "one engine, two apps" proof (the gate test)** — PowerShell, in `repos\anki-android`:
```powershell
.\gradlew :AnkiDroid:connectedPlayDebugAndroidTest --tests "*SpeedrunCoverageTest*"
```
`SpeedrunCoverageTest` calls `getCoverage(...)` through the Android `.so` and asserts `backendVersion == "26.05"` — identical to desktop. Green = same engine on both apps.

---

## C. (Optional) AI problem-generation service — OFF by default

The external AI/RAG generator lives OUTSIDE all native libs (`services/speedrun-ai/`) and is **disabled unless BOTH** `SPEEDRUN_AI_ENABLED=1` **and** `OPENAI_API_KEY` are set. The study app never depends on it; leave it off for the normal demo. To run it standalone — PowerShell, in `services\speedrun-ai`:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\services\speedrun-ai
uv sync --extra dev
uv run pytest -q                                  # hermetic (stubbed LLM/retriever/gate; no network)
uv run uvicorn app:app --reload                   # DISABLED -> POST /generate returns 503
# enable (needs a real key):
$env:SPEEDRUN_AI_ENABLED = "1"; $env:OPENAI_API_KEY = "sk-..."; uv run uvicorn app:app
```
Enabled, every emitted problem is proven by the SymPy verifier, grounded in a source citation, and cleared by the gold-set gate — otherwise it **abstains and emits nothing**.

---

## Notes
- AAR is **x86_64-only** (emulator). Add `arm64-v8a` to the cargo-ndk build only if running on a physical device (not needed for the emulator demo).
- First builds are slow (deps download + full Rust/Python/web compile, and the Android cross-compile). Subsequent builds are cached.
- Public forks contain only the AGPL code/work; strategy docs (AGENTS.md, BrainLift, PRD, STATE.md, this file) live only in the **private** umbrella repo. The AI service (`services/speedrun-ai/`) is AGPL and lives in the umbrella repo, never imported into `rslib`/`rsdroid`.
