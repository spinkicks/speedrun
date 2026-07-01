# Running the Speedrun MVP

Authoritative run guide, **updated 2026-07-01 post wed-plus**: forked Anki (desktop) and AnkiDroid (Android emulator) both drive **one** Rust engine (`rslib`) with 5 `SpeedrunService` RPCs, a shared Svelte **Memory dashboard** on both platforms, a seed exam deck, and a self-hosted sync server. (**Speedrun Home** — branded auto-open landing — is in flight on `feat/speedrun-home`; once merged, desktop launch opens into it.)

All wed-plus work is merged into **`main`** on all three forks (anki `1fed9e109` · Anki-Android-Backend `d4086e0` · anki-android `a56dda6cfb`; feature branches kept as backup), so the steps below just use `main`.

> ⚠️ **Before recording (audit note 2026-07-01):** two critical fixes are landing on `feat/speedrun-home` — the desktop webview→backend data path (without it the dashboard shows a load error on desktop) and the exam-profile bootstrap (without it both platforms show "no cards found for this exam profile" even after importing the seed deck). **Wait for those to merge, then record.** The Android bridge already works.

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
git checkout main          # walking-skeleton work is on main
just run                   # builds + launches the desktop app (first build is slow)
```
The Anki window opens running our forked `rslib`. Web pages serve at `http://localhost:40000/_anki/pages/`. `ANKIDEV` is auto-set (auto-backups off — safe throwaway profile).

**1. Import the seed exam deck:** *File → Import…* → `repos\anki\speedrun\out\gre_math_seed.apkg` (35 calc+LA notes, hierarchical `calc::…` / `linear_algebra::…` tags, Source on every card). Review a few cards for the demo.

**2. Open the Memory dashboard:** *Tools → Speedrun: Memory*. Expect: coverage header (topics present / required), grouped topic rows. On a fresh deck every topic honestly ABSTAINS ("insufficient data — review N more to unlock") — that IS the honest-score demo; ranges appear as reviews accumulate. (Once Speedrun Home merges: launch opens into the branded Home; *START RUN* enters study; Memory reachable from Home or Tools.)

**3. RPC from the Debug Console** (optional, proves the seam directly — *Tools → Debug Console*):
```python
col.speedrun.coverage(["calc", "linear_algebra"])   # CoverageResponse(..., backend_version="26.05")
col.speedrun.topic_mastery(["calc::limits"])        # Wilson range + abstained flag
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
git checkout main
git submodule update --init --recursive   # anki submodule pinned to our fork @ a0ead51c9 (frozen proto + dashboard page)
cargo run -p build_rust                    # (== build.bat) -> rsdroid AAR (x86_64; bundles the sveltekit pages)
```
Output: `rsdroid\build\outputs\aar\rsdroid-release.aar`.

**2. Point AnkiDroid at the local AAR** — PowerShell:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\anki-android
git checkout main
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

**5. Open the Memory dashboard on the phone:** in AnkiDroid, import the same seed `.apkg` (share it to the emulator or use *Import*), then DeckPicker **⋮ overflow menu → "Speedrun: Memory"** (last item). The SAME shared Svelte page renders from the AAR-bundled assets — abstaining honestly on fresh data, identical to desktop.

**6. Re-run the "one engine, two apps" proof (the gate test)** — PowerShell, in `repos\anki-android`:
```powershell
.\gradlew :AnkiDroid:connectedPlayDebugAndroidTest --tests "*SpeedrunCoverageTest*"
```
`SpeedrunCoverageTest` calls `getCoverage(...)` through the Android `.so` and asserts `backendVersion == "26.05"` — identical to desktop. Green = same engine on both apps.

---

## Notes
- AAR is **x86_64-only** (emulator). Add `arm64-v8a` to the cargo-ndk build only if running on a physical device (not needed for the emulator demo).
- First builds are slow (deps download + full Rust/Python/web compile, and the Android cross-compile). Subsequent builds are cached.
- Public forks contain only the AGPL code/work; strategy docs (AGENTS.md, BrainLift, PRD, STATE.md, this file) live only in the **private** umbrella repo.
