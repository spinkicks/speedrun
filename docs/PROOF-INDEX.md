# Proof artifacts index

Tracks the required proofs + where each file lives. Media files are NOT committed to git (see `.gitignore`) — they're uploaded to the submission. Keep recordings in `C:\Users\Public\Videos\` (or a `proof/` folder) and record the path here.

| Proof (rubric) | Status | Location / note |
|---|---|---|
| **Commit hashes** | ✅ | anki `348db0c6c` · Anki-Android-Backend `70b8eaf` · anki-android `6845e4e70a` · umbrella `spinkicks/speedrun` `e36d765` (`main`) — see `docs/STATE.md` |
| **Clean-machine install recording** | ✅ | `C:\Users\Public\Videos\CleanTestInstall.mp4` (19 MB) — MSI installed + launched on the fresh `CleanTest` local account |
| **§8 ablation results doc** | ✅ | `docs/ablation-s8-results.md` — Full/FeatureOff/Plain; M1 same-topic-adjacency **Full 0.00 vs 0.79** baselines (decisive); M2 pre-registered secondary mis-specified (reported honestly); M3 exploratory |
| **AI gold-set gate evidence (§7f)** | ✅ | `services/speedrun-ai/eval/` (`gate.py` + README) — wrong-answer **0%** (verify-gate), leakage **0** (scanner now scans distractors too); RAG beats baselines but **did not** clear the ≥5-pt Recall@10 margin (reported honestly); gold set `eval/holdout/gre_math_gold.jsonl` (50, triple-verified, leakage-cleared) |
| **Interactive visuals (4) — screenshots** | ✅ | live-verified + Claude-reviewed on branch `feat/speedrun-visuals` (merging to anki `main`): **The Map** (`/speedrun-map`, prerequisite-DAG) incl. **tap-node blast-radius** interaction, **calibration reliability diagram**, **memory→performance gap-slope**, **readiness gauge** — all pure-SVG, both platforms, **abstain honestly** ("—"/grey); unit tests **11/11** green + `svelte-check` clean |
| **Interactive MCQ auto-grade** | ✅ | merged (anki `a47dac310`): `Speedrun::Problem` choices clickable, graded **backend-authoritatively** vs `CorrectAnswer` → **Performance objectively key-checked** (desktop); Android answer-capture deferred |
| **7 adversarial-sweep bugs** | ✅ | all fixed + merged — bug #3 RAG grounding (semantic-embedding gate + syllabus fail-closed), leakage-scans-distractors, single-card 0%–100% band abstains, Android `getCalibration` exposed, calibration-capture hygiene |
| **Test results** | ⬜ | run `cargo test -p anki speedrun::` (66+ green) + `just check`; save output (text log or screen capture) |
| **Clean-build recording** | ⬜ | record `just run` (builds + launches) or `just check` green from `main` |
| **Three-scores-on-phone screenshot** | ⬜ | Memory + Performance + Readiness rendered on the Android emulator (abstain text where thresholds unmet — no fabricated numbers) |
| **Phone review-session recording** | ⬜ (screenshot exists) | short screen recording of a review on the emulator (rubric asks for a recording, not just a still) |
| **Timed mini-mock recording** | ⬜ | desktop mini-mock over the `Speedrun::GRE Math::Problems` filtered deck (10 @ 2.5 min, `reschedule=true`) |
| **Live two-way sync demo** | ⬜ | desktop↔Android via self-hosted `anki-sync-server` per `docs/SYNC-SELFHOST.md`; show identical recomputed scores both sides |
| **MVP demo video** | ⬜ | per `docs/DEMO-VIDEO-SCRIPT.md` (3–5 min) |
| **Sunday eval RUNS** | ⬜ | calibration reliability chart + Brier/log-loss on held-out; performance accuracy on held-out; score-mapping writeup; robustness (crash×20, offline, `make bench` p50/p95 on 50k deck) |
| **Signed APK** | ⬜ | release-signed AnkiDroid APK (current Phase-6 build is `assembleDebug`) |
| **Installer bundles seed deck (auto-import on first launch)** | ⬜ | in-flight (Claude): installer ships the seed deck + **auto-imports on first launch** so graders install and test with the deck **pre-loaded** — not yet merged |

**Honesty reminder (for every recording):** the **three scores are live** (Memory / Performance / Readiness) but **abstain below their data thresholds** — show the abstain text, never a fabricated number, and never claim we changed FSRS. **Performance is now objectively key-checked** (interactive MCQ auto-grade vs `CorrectAnswer`, desktop). The **4 visuals** (**The Map** + calibration-reliability, gap-slope, readiness-gauge charts) also **abstain honestly** ("—"/grey) — never show a fabricated node/point/band. Calibration is **self-rated** (not a model prediction). The **AI service ships OFF by default** — don't enable it on camera unless you're deliberately demoing the AI path (SymPy-verify + gold-gate).
