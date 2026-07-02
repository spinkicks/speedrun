# Speedrun

A desktop + Android study app built **on Anki**, focused on one graduate exam: the **GRE Mathematics Subject Test**.

> One exam. Two apps on one Rust engine. A real engine change. Honest scores that show a **range** and **refuse to answer** when they lack data.

Licensed **AGPL-3.0-or-later**, with credit to [Anki](https://github.com/ankitects/anki). Some upstream components are BSD-3-Clause; the Android app is GPL-3.0.

---

## Status (2026-07-01 — working MVP, both platforms, NO AI yet)
Both apps build, run, and review the same GRE deck on **one shared Rust engine**. See `docs/WHAT-WE-BUILT.md` for the honest, per-item real / scaffolding / planned breakdown, and `docs/CHANGELOG-2026-07-01.md` for the full change log.

**Real today:**
- Forked Anki building from source; **one engine, two apps** (desktop + Android emulator), proven by an instrumentation test (identical backend version).
- A real **Rust engine change** on `SpeedrunService`: read-only RPCs (`GetCoverage`, `GetTopicMastery`, `GetExamProfile`) + one **mutating, undo-safe** RPC (`ReorderNewByPointsAtStake`, via `transact(Op::SortCards)`) + a non-AI scaffolding RPC. ~15 Rust tests + Python integration.
- **Honest Memory score:** per-topic recall from FSRS retrievability → Wilson 95% interval + **abstention** below a data threshold ("review N more to unlock"). No fake numbers.
- **Speedrun Home + Memory dashboard** — our own branded, mobile-first, dark UI (one shared SvelteKit surface rendered on both platforms). START RUN launches a real review session.
- Self-hosted **sync** + a §7b two-way conflict test; **network-independent installer** (clean-machine build).
- 35-card GRE calc+LA seed deck + exam-profile coverage map.

**Not built yet (Friday/Sunday — do NOT assume these work):** Performance & Readiness scores (currently abstain-only scaffolding), calibration, weakness-driven *review-queue* scheduling, the AI problem-generation service, and the 3-build ablation. Anki's FSRS is the memory engine — we build **on** it, unchanged.

---

## How to run (for graders / reviewers)

**Prerequisites:** see `docs/BUILD-PREREQS.md` (Rust via rustup, Python via `uv`, Node+yarn, MSVC build tools, MSYS2 `rsync`, the `n2` build tool, `just`). Full step-by-step: `docs/RUN-MVP.md`.

### Desktop — easiest: the installer
A packaged Windows installer (`.msi`) is produced by the build (network-independent). Install it on any Windows machine and launch **Speedrun** — it opens into Speedrun Home. (Build it with `uv run python qt/tools/build_installer.py --version "$(cat .version)" build` then `… package` in `repos/anki`; artifact under `repos/anki/out/`.)

### Desktop — from source
```powershell
cd repos/anki
git checkout main
just run              # builds + launches; Speedrun Home auto-opens
```
Then **File → Import** `repos/anki/speedrun/out/gre_math_seed.apkg`, and click **► START RUN** to review. Tools → **Speedrun: Memory** for the dashboard. Run tests: `cargo test -p anki speedrun::` and `just check`.

### Android — emulator (x86_64)
```powershell
# 1. Build the engine AAR from our rslib:
cd repos/Anki-Android-Backend
git checkout main
git submodule update --init --recursive
cargo run -p build_rust            # -> rsdroid AAR (bundles the shared pages)
# 2. Launch the Pixel_10 x86_64 emulator, then:
cd ../anki-android
git checkout main                  # local.properties has local_backend=true
.\gradlew :AnkiDroid:installPlayDebug
```
Open **AnkiDroid** → ⋮ → **Speedrun: Home**. To review: `adb push speedrun/out/gre_math_seed.apkg /sdcard/Download/`, import it in AnkiDroid, then **START RUN**.

Self-hosted sync demo: `docs/SYNC-SELFHOST.md`.

---

## Architecture: two apps, one engine
- **Desktop + shared engine:** `repos/anki` — fork of [`ankitects/anki`](https://github.com/ankitects/anki). The engine change lives in `rslib/src/speedrun/`; desktop UI in `ts/routes/speedrun-*` (Svelte) + `qt/aqt/speedrun.py`.
- **Phone:** `repos/anki-android` — fork of [`ankidroid/Anki-Android`](https://github.com/ankidroid/Anki-Android); renders the same shared Svelte pages via `PageFragment`.
- **Engine → Android bridge:** `repos/Anki-Android-Backend` — fork of `rsdroid`; cross-compiles `rslib` into the JNI AAR (with `local_backend=true`).
- The external AI/RAG service (Friday) lives **outside** all native libs.

## Repository layout
```
Speedrun/
├── brainlift/     # BrainLift (thesis, SpikyPOVs, evidence base)
├── docs/          # PRD, architecture, run guide, changelog, honest "what we built", plans
├── research/      # Research notes and source captures
└── repos/         # Forks: anki, anki-android, Anki-Android-Backend (not tracked here)
```

## Key docs
`docs/RUN-MVP.md` (run steps) · `docs/WHAT-WE-BUILT.md` (honest status) · `docs/CHANGELOG-2026-07-01.md` · `docs/PRD.md` · `docs/DEMO-VIDEO-SCRIPT.md` · `brainlift/BrainLift.md`.
