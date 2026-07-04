# Speedrun

A desktop + Android study app built **on Anki**, focused on one graduate exam: the **GRE Mathematics Subject Test**.

> One exam. Two apps on one Rust engine. A real engine change. Honest scores that show a **range** and **refuse to answer** when they lack data.

> **📦 Graders — download the desktop installer:** **[Releases → Speedrun – Early Submission](https://github.com/spinkicks/speedrun/releases/tag/v0.1.0-early)** → `anki-26.05-win-x64.msi` (~194 MB, Windows x64). Run it, launch **Speedrun**, and the study deck **auto-imports on first launch** — no manual import. Full run guide (Android, sync, AI): [How to run](#how-to-run-for-graders--reviewers).

Licensed **AGPL-3.0-or-later**, with credit to [Anki](https://github.com/ankitects/anki). Some upstream components are BSD-3-Clause; the Android app is GPL-3.0.

---

## Status (2026-07-03 — full feature set merged to `main`, both platforms)

Desktop and Android share one Speedrun-patched Rust engine and the same SvelteKit UI. All three scores render with honest ranges and abstain when data is insufficient. The curated problem bank powers timed mini-mocks and Performance/Readiness **without AI**. An external AI generation service is **shipped but OFF by default** — SymPy-verified, gold-set-gated, never required to study — and, when enabled, is reachable from an in-app **⚡ Generate practice** button on THE MAP (imports only verified, cited problems). Four pure-SVG **interactive visuals** — headlined by **THE MAP** (an interactive prerequisite graph) — ship on both platforms and abstain honestly like the scores. The **Windows installer bundles the seed deck and auto-imports it on first launch** (graders install → launch → data is already there).

**Current `main` pins:** anki `8cd09ec51` · Anki-Android-Backend `5e02a2b` · anki-android `6845e4e70a` · umbrella `149ab33` (advances with docs commits).

See `docs/WHAT-WE-BUILT.md` for the honest per-feature real / scaffolding / pending breakdown, and `docs/STATE.md` for the live handoff state.

### What's real today
- **One engine, two apps.** Forked Anki building from source; the same Rust engine runs on desktop (PyO3) and Android (JNI AAR), proven by an instrumentation test (identical backend version).
- **A real Rust engine change** on `SpeedrunService` (`rslib/src/speedrun/`, append-only `proto/anki/speedrun.proto`): read-only RPCs (coverage, topic mastery, exam profile, performance/readiness, calibration) + one **mutating, undo-safe** RPC (`ReorderNewByPointsAtStake`, via `transact(Op::SortCards)`). 66+ Rust speedrun tests + Python integration.
- **Three honest scores:**
  - **Memory** — per-topic recall from FSRS retrievability → Wilson 95% interval + **abstention** below a data threshold.
  - **Performance** — P(correct) on novel `Speedrun::Problem` MCQs, now **objectively key-checked** by the interactive auto-grading reviewer (not self-rated), with a mean-CI band, a memory→performance gap Δ, and abstention below thresholds.
  - **Readiness** — flat IRT → scaled **200–990** + conformal range + a give-up rule (needs ≥2 timed mini-mocks); exam-level on Home, per-topic abstains by design.
- **Interactive visuals — the "not-Anki" layer** (all pure-SVG, both platforms, honest abstains):
  - **THE MAP** (`ts/routes/speedrun-map/`, route `/speedrun-map`) — an interactive **prerequisite graph**; tap a node to light up its downstream **blast radius**. The signature differentiator that makes Speedrun not look like Anki.
  - **Calibration reliability diagram + memory→performance gap chart** on the Memory dashboard.
  - **Readiness gauge** on Home (200–990 + conformal band).
- **Weakness-aware scheduling** — new-card points-at-stake reorder **and** due-card weakness×topic-weight interleave (read-time, ablation-gated).
- **Problem bank + timed mini-mock** — `Speedrun::Problem` MCQ note type + 64-problem bank (double-SymPy-verified); a filtered-deck timed mini-mock that scores real attempts.
- **Learning-science layer** — LS1 calibration (pre-answer confidence self-bet → Brier/ECE, self-rated framing, abstains below threshold), LS2 worked-examples-first + faded step reveal, LS3 honesty-guardrail copy (gated to render only on real data).
- **Speedrun identity** — Manrope ExtraBold wordmark + near-white `#F4F7FA` accent, mobile-first dark shell; Speedrun Home auto-opens on launch.
- **Self-hosted sync** + a §7b two-way conflict test; **network-independent installer** (clean-machine build).
- **Ablation harness (§8)** — one build, three modes (`AblationMode` Full/FeatureOff/Plain), pre-registered metrics (`docs/ablation-s8-results.md`).

### Optional, OFF by default
- **AI/RAG generation service** (`services/speedrun-ai/`, FastAPI + LangGraph) — propose → SymPy verify → hybrid RAG ground → distractors → gold-set gate → emit or abstain. Requires `SPEEDRUN_AI_ENABLED=1` **and** `OPENAI_API_KEY`. Never imported into `rslib`/`rsdroid`; the app scores fully with AI off. Pre-registered eval numbers (wrong-answer **0 %**, Recall@10 **90 %**, leakage **0**, honest baseline side-by-side) in `services/speedrun-ai/eval/README.md`.
- **In-app ⚡ Generate practice button** (desktop, THE MAP) — enabled only when the service is reachable **and** the node is a covered leaf topic; imports **only verified, cited** problems as `Speedrun::Problem` (tagged `ai-generated`). Disabled with an honest hint when AI is off. Desktop-first; hidden/disabled on Android.

### Still pending (human / Sunday)
Android emulator visual gate + live desktop↔Android sync-demo recording + demo video; Sunday eval runs (calibration reliability + Brier/log-loss, performance accuracy on held-out, score-mapping writeup); robustness (crash×20, offline, `make bench` p50/p95 on a 50k-card deck); signed APK; final BrainLift pass.

---

## How to run (for graders / reviewers)

**Prerequisites:** see `docs/BUILD-PREREQS.md` (Rust via rustup, Python via `uv`, Node+yarn, MSVC build tools, MSYS2 `rsync`, the `n2` build tool, `just`). Full step-by-step: `docs/RUN-MVP.md`.

### Desktop — easiest: the installer (deck pre-loaded)
**⬇️ Download:** **[Releases → Speedrun – Early Submission](https://github.com/spinkicks/speedrun/releases/tag/v0.1.0-early)** → `anki-26.05-win-x64.msi` (~194 MB, Windows x64; built 2026-07-03 from anki `main` `8cd09ec51` — full Friday UI: 4 visuals + MCQ auto-grade + AI Generate button). *(Also prebuilt locally at `repos/anki/out/installer/dist/anki-26.05-win-x64.msi`.)* — install it and launch **Speedrun** (it opens into Speedrun Home). **The installer bundles the seed deck and auto-imports it on first launch** (idempotent, config-gated, skips if the exam deck already exists), so the 35 declarative cards + the 64-problem bank are already loaded — **no manual File → Import needed**. From Home, follow the **THE MAP ▸** link to the prerequisite graph, click **► START RUN** to review, or try a timed **mini-mock**. The installer build is network-independent (`test_installer.py` 27/27). To rebuild, use the `RELEASE=1` ninja `installer:build` → `build_installer.py … package` path in `docs/BUILD-PREREQS.md` (NOT the bare `build_installer.py … build` line — that omits our fork wheels).

### Desktop — from source
```powershell
cd repos/anki
git checkout main
just run              # builds + launches; Speedrun Home auto-opens
```
This from-source path does NOT auto-import, so **File → Import** `repos/anki/speedrun/out/gre_math_seed.apkg` (35-card seed deck + 64-problem bank), then click **► START RUN** to review, follow **THE MAP ▸** from Home to the prerequisite graph, try a timed **mini-mock**, and open Tools → **Speedrun: Memory** for the dashboard. Run tests: `cargo test -p anki speedrun::` and `just check`.

### Android — emulator (x86_64)
```powershell
# 1. Build the engine AAR from our rslib (submodule pinned to anki main):
cd repos/Anki-Android-Backend
git checkout main
git submodule update --init --recursive
cargo run -p build_rust            # -> rsdroid AAR (bundles the shared pages)
# 2. Launch the x86_64 emulator, then:
cd ../anki-android
git checkout main                  # local.properties has local_backend=true
.\gradlew :AnkiDroid:installPlayDebug
```
Open **AnkiDroid** → **Speedrun: Home**. To review: `adb push speedrun/out/gre_math_seed.apkg /sdcard/Download/`, import it, then **START RUN**.

Self-hosted sync demo: `docs/SYNC-SELFHOST.md`. Optional AI service: `services/speedrun-ai/README.md` (OFF by default).

---

## Architecture: two apps, one engine
Our code lives in three public forks (linked below); this umbrella repo holds docs, the plan, the AI service, and proof.
- **Desktop + shared engine:** **[`spinkicks/anki`](https://github.com/spinkicks/anki)** (fork of [`ankitects/anki`](https://github.com/ankitects/anki)) — the Rust engine change lives in **`rslib/src/speedrun/`** + `proto/anki/speedrun.proto`; UI in `ts/routes/speedrun-*` (Svelte, including **THE MAP** interactive prerequisite graph at `ts/routes/speedrun-map/`) + `qt/aqt/speedrun*.py`. **← the headline engine change.**
- **Phone:** **[`spinkicks/Anki-Android`](https://github.com/spinkicks/Anki-Android)** (fork of [`ankidroid/Anki-Android`](https://github.com/ankidroid/Anki-Android)) — renders the same shared Svelte pages via `PageFragment`.
- **Engine → Android bridge:** **[`spinkicks/Anki-Android-Backend`](https://github.com/spinkicks/Anki-Android-Backend)** (fork of rsdroid) — cross-compiles `rslib` into the JNI AAR (with `local_backend=true`).
- The external AI/RAG service (`services/speedrun-ai/`) lives **outside** all native libs, OFF by default.

## Repository layout
```
Speedrun/
├── brainlift/     # BrainLift (thesis, SpikyPOVs, evidence base)
├── docs/          # PRD, architecture, run guide, plans, honest "what we built", ablation results
├── research/      # Research notes and source captures
├── services/      # speedrun-ai — external AI/RAG generation service (OFF by default)
├── eval/          # holdout/ — 50-problem gold set + gate tooling (implementer agents must NOT read holdout)
└── repos/         # Forks: anki, anki-android, Anki-Android-Backend (not tracked here)
```

## Key docs
`docs/STATE.md` (live handoff) · `docs/WHAT-WE-BUILT.md` (honest status) · `docs/RUN-MVP.md` (run steps) · `docs/PRD.md` · `docs/DECISIONS.md` · `docs/ablation-s8-results.md` · `docs/DEMO-VIDEO-SCRIPT.md` · `services/speedrun-ai/README.md` · `brainlift/BrainLift.md`.
