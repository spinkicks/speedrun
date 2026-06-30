# Running the Speedrun MVP (walking skeleton)

Authoritative run guide for the Phases 0–2 walking skeleton: forked Anki (desktop) and AnkiDroid (Android emulator) both driving **one** Rust engine (`rslib`) that answers a real read-only RPC, `SpeedrunService.GetCoverage`, returning the engine version `26.05`.

The walking-skeleton work is now merged into **`main`** on all three forks (feature branches kept as backup), so the steps below just use `main`.

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

**Exercise the new RPC** (no dedicated UI yet — it's a backend RPC). In Anki's Debug Console (menu: *Tools → Debug Console*, or a pyanki shell) against an open collection:
```python
col.speedrun.coverage(["calc", "linear_algebra"])
# -> CoverageResponse(covered=..., total=2, percent=..., backend_version="26.05")
```

**Run the engine tests / full gate** (PowerShell, in `repos\anki`):
```powershell
cargo test -p anki speedrun::   # 4 Speedrun Rust tests
just test-py                    # pylib test_speedrun (Python integration)
just check                      # full build + lint + tests (green modulo known env items)
```

---

## B. Android (AnkiDroid on the x86_64 emulator, same engine)

**1. Build the AAR from our `rslib`** — PowerShell:
```powershell
cd C:\Users\davir\Ultra\Alpha\Speedrun\repos\Anki-Android-Backend
git checkout main
git submodule update --init --recursive   # anki submodule pinned to our fork @ b8b5369
cargo run -p build_rust                    # (== build.bat) -> rsdroid AAR (x86_64)
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
.\gradlew :AnkiDroid:installDebug
# then open the AnkiDroid app on the emulator
```
(Or open `repos\anki-android` in Android Studio and press Run with `Pixel_10` selected.)

**5. Re-run the "one engine, two apps" proof (the gate test)** — PowerShell, in `repos\anki-android`:
```powershell
.\gradlew :AnkiDroid:connectedDebugAndroidTest --tests "*SpeedrunCoverageTest*"
```
`SpeedrunCoverageTest` calls `getCoverage(...)` through the Android `.so` and asserts `backendVersion == "26.05"` — identical to desktop. Green = same engine on both apps.

---

## Notes
- AAR is **x86_64-only** (emulator). Add `arm64-v8a` to the cargo-ndk build only if running on a physical device (not needed for the emulator demo).
- First builds are slow (deps download + full Rust/Python/web compile, and the Android cross-compile). Subsequent builds are cached.
- Public forks contain only the AGPL code/work; strategy docs (AGENTS.md, BrainLift, PRD, STATE.md, this file) live only in the **private** umbrella repo.
