# Running the Speedrun MVP (walking skeleton)

Authoritative run guide for the Phases 0–2 walking skeleton: forked Anki (desktop) and AnkiDroid (Android emulator) both driving **one** Rust engine (`rslib`) that answers a real read-only RPC, `SpeedrunService.GetCoverage`, returning the engine version `26.05`.

All paths are relative to the workspace root `C:\Users\davir\Ultra\Alpha\Speedrun`. Build commands use `just` (NOT `./ninja`/`./run`) per `repos/anki/CLAUDE.md`.

## Prerequisites (already installed on the build machine)
- Rust (auto-pinned to **1.92.0** by `repos/anki/rust-toolchain.toml`) + Android targets; `cargo-ndk`.
- `uv`, Node, `yarn`, MSYS2 (`git`, `rsync`), **n2**, **just**, JDK 21.
- Windows Defender **exclusion** on `repos/anki` (fixes the transient protoc-rename lock).
- Android SDK + **NDK `29.0.14206865`**, `ANDROID_HOME` + `ANDROID_NDK_HOME` set, an **x86_64** AVD (e.g. `Pixel_10`, `android-36.1`/`google_apis`).

---

## A. Desktop (forked Anki with our engine)

```powershell
cd repos\anki
git checkout feat/speedrun-coverage-rpc
just run
```
The Anki desktop window launches running our forked `rslib`. Web pages are served at `http://localhost:40000/_anki/pages/`. `ANKIDEV` is auto-set (auto-backups disabled — safe throwaway profile).

**Exercise the RPC** (there is no dedicated UI yet — it is a backend RPC). From a Python shell against an open collection:
```python
col.speedrun.coverage(["calc", "linear_algebra"])
# -> CoverageResponse(covered=..., total=2, percent=..., backend_version="26.05")
```

**Run the engine tests / full gate:**
```powershell
cd repos\anki
cargo test -p anki speedrun::   # 4 Speedrun tests
just test-py                    # includes pylib test_speedrun (Python integration)
just check                      # full build + lint + tests (green modulo known env items)
```

---

## B. Android (AnkiDroid on the x86_64 emulator, same engine)

**1. Build the AAR from our `rslib`** (cross-compiles via cargo-ndk + generates Kotlin protobuf):
```powershell
cd repos\Anki-Android-Backend
git checkout feat/speedrun-walking-skeleton
git submodule update --init --recursive   # anki submodule pinned to spinkicks/anki @ b8b5369
cargo run -p build_rust                    # (equivalently: build.bat) -> rsdroid AAR (x86_64)
```
Output: `rsdroid/build/outputs/aar/rsdroid-release.aar`.

**2. Point AnkiDroid at the local AAR:**
```powershell
cd repos\anki-android
git checkout feat/speedrun-walking-skeleton
# ensure local.properties contains: local_backend=true
```

**3. Launch the emulator** (with a window; drop nothing to watch it):
```powershell
& "$env:ANDROID_HOME\emulator\emulator.exe" -avd Pixel_10
# headless/unattended variant: add  -no-window -no-snapshot -no-boot-anim
```

**4. Build + install + run the app on the emulator:**
```powershell
cd repos\anki-android
.\gradlew :AnkiDroid:installDebug
# then open the AnkiDroid app on the emulator
```
(Or open `repos/anki-android` in Android Studio and press Run with the emulator selected.)

**5. Re-run the "one engine, two apps" proof (the gate test):**
```powershell
cd repos\anki-android
.\gradlew :AnkiDroid:connectedDebugAndroidTest --tests "*SpeedrunCoverageTest*"
```
`SpeedrunCoverageTest` calls `getCoverage(...)` through the Android `.so` and asserts `backendVersion == "26.05"` — identical to desktop. Green = same engine on both apps.

---

## Notes
- AAR is **x86_64-only** (emulator). Add `arm64-v8a` to the cargo-ndk build only if running on a physical device.
- First builds are slow (deps download + full Rust/Python/web compile, and the Android cross-compile).
