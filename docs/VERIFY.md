<!--
Copyright: Speedrun contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->

# Verify Speedrun in ~10 minutes (grader guide)

Every claim is re-runnable. This is the fast path; the full artifact map is `docs/PROOF-INDEX.md` and the numbers live in `docs/RESULTS.md`. Pins: anki `main` `e774ff339` · anki-android `main` `5680917f79` · umbrella `main` `5bda552`.

## 0. One-command bring-up (optional, Windows)
```powershell
# from the repo root — starts the AI service + self-hosted sync server + desktop app (AI enabled)
powershell -ExecutionPolicy Bypass -File scripts\speedrun-launch.ps1 -All
# stop everything:  ... -File scripts\speedrun-launch.ps1 -Stop
```

## 1. The engine change + tests (§7a)  ~2 min
```powershell
cd repos\anki
cargo test -p anki speedrun::            # 84 speedrun tests (scores, abstain, ablation, calibration, bench-guard)
```
Why-Rust + upstream-files notes: `docs/artifacts/why-rust-not-python.md`, `docs/artifacts/upstream-files-touched.md`.

## 2. The model evals (§9.1 / §9.2)  ~2 min
```powershell
# Memory calibration — Brier 0.0569 / log-loss 0.2177 / ECE 0.0042 (labeled SIMULATED FSRS stream)
cargo test -p anki speedrun::calibration_eval -- --nocapture
# Performance accuracy — sim predictive + hermetic auto-grader fidelity 50/50 on real gold
cd ..\..\services\speedrun-ai
uv sync
uv run pytest tests/test_perf_eval.py -q
```
Charts: `repos/anki/speedrun/eval/memory-calibration.svg`, `services/speedrun-ai/eval/perf-accuracy.svg`.

## 3. AI safety: verification, baseline, leakage, 3-count (§7e / §7f)  ~2 min
```powershell
cd services\speedrun-ai            # (uv sync once)
uv run python -m eval.gate         # wrong-answer 0%, Recall@10 90%, baseline BM25/dense/hybrid all 0.900 (honest tie), leakage 0
uv run pytest tests/test_ai_quality_eval.py tests/test_leakage.py tests/test_transfer_eval.py -q
```
- §7f 3-count (live gpt-4o judge): **47/47 useful, 0 wrong, 0 bad-teaching** — `eval/ai-quality.json`.
- §7d gap (Performance ≠ Memory): recall **0.907** vs transfer **0.703** — `eval/transfer-gap.svg`.
- AI OFF by default: `uv run pytest tests/test_gate.py::test_generate_returns_503_when_disabled`.

## 4. Robustness + benchmark (§7g / §7h / §8)  ~3 min
```powershell
cd repos\anki
just bench                                        # §7h latency p50/p95/worst vs §10 targets
out\pyenv\Scripts\python.exe speedrun\eval\crash_offline_test.py   # §7g crash x20 = 20/20 integrity-ok (SPEEDRUN_7G_FULL=1 for all 20)
cargo test -p anki --release speedrun::ablation -- --nocapture     # §8 three-build ablation
```

## 5. The apps (run the product)
- **Desktop:** `cd repos\anki; just run` → import `speedrun\out\gre_math_seed.apkg` (or use the MSI, which auto-imports) → Home shows the three scores; sidebar → The Map / Memory; START RUN; MCQ auto-grade; mini-mock.
- **Android:** install the signed APK (`AnkiDroid-play-arm64-v8a-release.apk`) → same shared UI on the same engine.
- **Sync:** `scripts\speedrun-launch.ps1 -Sync` (or `docs\SYNC-SELFHOST.md`) → point desktop + emulator at it → review on one, sync, see it on the other.

## What's honest / deferred (we say what we didn't do)
- Calibration/§7d gaps are on **labeled simulated** learners (no real learner logs exist yet) — the auto-grader fidelity + SymPy verification + 70/70 answer checks are REAL.
- RAG **ties** the baselines (corpus saturates) — non-regression, not a win; the real win is 0% wrong via verification.
- §7h dashboard **misses** §10 at 50k (scan-dominated; documented fix path); fast at demo scale.
- §10 cold-start + memory@50k: not separately profiled this cycle (documented in `RESULTS.md §7h/§10 note`).
- Android in-reviewer MCQ capture + Android crash-test: deferred (desktop-first).
