<!--
Copyright: Speedrun contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

# Proof index — verify every claim (grader-facing)

**Purpose:** for each rubric deliverable, this maps the CLAIM → the ARTIFACT (file/number) → the EXACT command to re-run it yourself. Every number is measured + reproducible or explicitly labeled simulated/abstained/deferred. Companion docs: `docs/RESULTS.md` (the results report + model descriptions) and `docs/VERIFY.md` (a 10-minute walkthrough). Media (recordings) are NOT committed to git — they're uploaded to the submission; paths recorded below.

**Current pins (2026-07-05):** anki `main` **`e774ff339`** · anki-android `main` **`5680917f79`** · Anki-Android-Backend `main` **`5e02a2b`** (AAR re-pin to `e774ff339` in flight) · umbrella `spinkicks/speedrun` `main` **`5bda552`**.

---

## Models & evidence (§9, §4)

| Claim | Status | Artifact | Re-run |
|---|---|---|---|
| **Memory model calibrated** (Brier/log-loss + reliability chart, held-out) | ✅ | `RESULTS.md §9.1`: Brier **0.0569**, log-loss **0.2177**, ECE **0.0042** (N=4000, labeled SIMULATED FSRS stream); chart `repos/anki/speedrun/eval/memory-calibration.svg` + `.json` | `cargo test -p anki speedrun::calibration_eval -- --nocapture` (+ `SPEEDRUN_EVAL_EMIT=1` to regen chart) |
| **Performance accuracy** on held-out exam questions | ✅ | `RESULTS.md §9.2`: sim predictive **Brier 0.2486 / AUC 0.6645 / Wilson-cov 90.7%**; hermetic auto-grader fidelity **50/50** real gold; chart `services/speedrun-ai/eval/perf-accuracy.svg` | `cd services/speedrun-ai && uv run pytest tests/test_perf_eval.py` ; `SPEEDRUN_EVAL_EMIT=1 uv run python -m eval.perf_eval` |
| **Score mapping** written down + range | ✅ | `RESULTS.md §1.3` + `DECISIONS.md`: θ = ETS-weighted flat-IRT sum → equate to **200–990** → conformal range (base 40 + 8·sparsity) → give-up rule (≥2 mini-mocks, ≥0.60 coverage, ≤200 width) | n/a (documented method); config `repos/anki/speedrun/exam_profiles/gre_math.json` |
| **Model descriptions** (one page each: Memory/Performance/Readiness + give-up rule) | ✅ | `RESULTS.md Part 1` | n/a |

## Concrete challenges (§7)

| Claim | Status | Artifact | Re-run |
|---|---|---|---|
| **§7a Rust change** + ≥3 Rust tests + 1 Python-calling test; undo + no corruption; why-Rust; files-touched | ✅ | `rslib/src/speedrun/` (`SpeedrunService`); `docs/artifacts/why-rust-not-python.md` + `docs/artifacts/upstream-files-touched.md`; 84 speedrun Rust tests | `cargo test -p anki speedrun::` ; Python integ: `uv run pytest pylib/tests/... ` |
| **§7b sync conflict** (offline both sides same card → correct merge, documented) | ✅ code/test · ⬜ recording | `docs/SYNC-SELFHOST.md` (rule) + `rslib/src/sync/collection/tests.rs` `speedrun_two_way_reviews_and_same_card_conflict` (20 distinct revlog both sides, integrity ok) | `cargo test -p anki speedrun_two_way` ; live: `docs/VERIFY.md` sync section |
| **§7c coverage map** + abstain-below-line | ✅ | Memory dashboard coverage row; `gre_math.json` topic list; engine abstains < thresholds | in-app Memory page; `cargo test -p anki speedrun::` |
| **§7d paraphrase/transfer gap** (Performance ≠ Memory) | ✅ | `RESULTS.md §7d`: recall **0.907** vs transfer **0.703**, gap **Δ=0.204**; 70/70 authored answers SymPy-verified (REAL) | `cd services/speedrun-ai && uv run pytest tests/test_transfer_eval.py` ; `SPEEDRUN_EVAL_EMIT=1 uv run python -m eval.transfer_eval` |
| **§7e leakage check** (scan training data for leaked test items → clean) | 🔄 citable run in progress | scanner `services/speedrun-ai/eval/leakage.py` (validated `tests/test_leakage.py`); standalone clean-run artifact being produced (`eval/leakage-check.json`) → `RESULTS.md §7e` | `cd services/speedrun-ai && uv run python -m eval.leakage_check` (pending) ; `uv run pytest tests/test_leakage.py` |
| **§7f AI card check** (50 cards, 3-count, cutoff pre-set) | ✅ | `RESULTS.md §7f`: **47/47 useful, 0 wrong, 0 bad-teaching** (live gpt-4o judge; wrong=0 by construction); `services/speedrun-ai/eval/ai-quality.json` | `cd services/speedrun-ai && uv run pytest tests/test_ai_quality_eval.py` (hermetic) ; live: `SPEEDRUN_AI_ENABLED=1 uv run python -m eval.ai_quality_eval --n 50 --topic calc::single_var::differentiation` |
| **§7g crash ×20 + offline** (zero corruption; AI-off still scores) | ✅ | `RESULTS.md §7g`: **20/20 integrity-ok** mid-write kills; AI-offline scores compute; `repos/anki/speedrun/eval/crash-offline-results.json` | `out/pyenv/Scripts/python.exe speedrun/eval/crash_offline_test.py` |
| **§7h one-command benchmark** (p50/p95/worst vs §10) | ✅ | `RESULTS.md §7h`: button-ack p95 **0.102ms** PASS, next-card p95 **0.038ms** PASS, dashboard **MISS@50k** (honest, scan-dominated); | `just bench` (release, deterministic) |

## Study feature (§8) & AI safety baseline

| Claim | Status | Artifact | Re-run |
|---|---|---|---|
| **§8 ablation** — 3 builds (Full/FeatureOff/Plain), pre-registered metric, honest miss reported | ✅ | `docs/ablation-s8-results.md` + `RESULTS.md §8`: M1 Full **0.0000** vs **0.7949** baselines; M2 pre-registered MISS (reported); M3 exploratory | `cargo test -p anki --release speedrun::ablation -- --nocapture` |
| **AI beats a simpler method** (baseline side-by-side) | ✅ (honest tie) | `services/speedrun-ai/eval/README.md` + `RESULTS.md §7f/Part 3`: BM25 **0.900** / dense **0.900** / hybrid **0.900** (non-regression; corpus saturates — honest tie, NOT a win). Real "beats naive" = **0% wrong via SymPy verify**. | `cd services/speedrun-ai && uv run python -m eval.gate` |
| **Every AI output cites a named source** | ✅ | `services/speedrun-ai/graph.py` emit drops anything without a citation; in-app Generate imports only cited | `uv run pytest tests/test_graph.py` |
| **App scores with AI OFF** (kill-switch) | ✅ | `/generate` → **503** disabled; 3 scores engine-computed, service never imported into rslib/rsdroid | stop the service → scores still render; `uv run pytest tests/test_gate.py::test_generate_returns_503_when_disabled` |

## Two apps, one engine + builds

| Claim | Status | Artifact | Re-run |
|---|---|---|---|
| **One engine, two apps** (same Rust engine desktop + Android) | ✅ | instrumentation test (identical backend version); AAR bundles shared Svelte UI | `cd ../Anki-Android-Backend && cargo run -p build_rust` |
| **Packaged desktop installer** | ✅ | GitHub Release `v0.1.0-early` → `anki-26.05-win-x64.msi` (~194 MB); bundles + auto-imports seed deck; `test_installer.py` 27/27 | download from Releases, or rebuild per `README.md` |
| **Signed release APK** (real device) | ✅ | `AnkiDroid-play-arm64-v8a-release.apk` (50.2 MB), v2-signed, `apksigner verify` passes | `docs/RESULTS.md Part 4` repro |
| **Sidebar / clean UX** (both platforms) | ✅ code · 🔄 native-verify | `ts/lib/speedrun/SpeedrunShell.svelte` (svelte-check 0/0, vitest 89); native-verify on `e774ff339` in flight | `corepack yarn svelte-check:once` + `vitest:once` |

## Recordings (§12, human — the main remaining work)

| Recording | Status | Note |
|---|---|---|
| Clean-machine desktop install | ✅ | `C:\Users\Public\Videos\CleanTestInstall.mp4` (MSI on fresh account) — **re-record with the CURRENT MSI** (post-sidebar) for the final submission |
| **Demo video (3–5 min)** | ⬜ | per `docs/DEMO-VIDEO-SCRIPT.md` — review session, Rust change, phone→desktop sync, 3 scores w/ ranges, AI features, test results; **highlight what changed since the MVP** |
| **Phone build install + run on clean device** | ⬜ | install the signed APK on a fresh emulator/device; review session |
| **Live two-way + offline sync** | ⬜ | desktop↔Android via self-hosted server (`docs/SYNC-SELFHOST.md`); card reviewed on phone appears on desktop + reverse + offline-reconnect |
| **Android three-scores + sidebar (native-verify)** | ✅ | Cursor ran it on the Pixel_10 emulator (x86_64 debug APK on AAB `ccccad3`): Home shows the sidebar nav + all 3 scores abstaining honestly; The Map graph renders (Part-B `speedrun-map` route works); Memory renders w/ abstains. Screenshots `repos/anki/speedrun/out/emu-04-home.png`, `emu-05-map.png`, `emu-06-memory.png` — re-usable in the demo/submission |

---

**Honesty reminder (every recording):** the three scores are live but **abstain below their data thresholds** — show the abstain ("—"/"review N more"), never a fabricated number; never claim we changed FSRS. Performance is **objectively key-checked** (MCQ auto-grade, desktop). The RAG baseline is an **honest tie** (non-regression), not a win — the real safety win is **0% wrong via SymPy verification**. Calibration confidence is **self-reported**; the outcome is objectively graded. The AI service is **OFF by default** — only show it after enabling (`SPEEDRUN_AI_ENABLED=1` + the service running).
