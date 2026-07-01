# Speedrun — Progress Tracker (done / left), mapped to the spec

Living checklist. Legend: ✅ done · ⚠️ partial · ❌ not started. Keep honest (project thesis). Last updated 2026-06-30 (Tue eve), after the walking skeleton merged to `main` on all forks.

## ✅ Done so far (the walking skeleton — technical foundation)
- ✅ Anki **forked & building from source** (desktop); `just run` launches; `just check` green modulo known env items (installer template-clone, complexipy — both deferred/cosmetic).
- ✅ **Real read-only Rust engine change**: `SpeedrunService.GetCoverage` (proto → Rust `Collection` impl → Python wrapper), read-only, additive proto, no `transact` needed, `pragma integrity_check == ok`.
- ✅ **Tests**: 4 Rust unit/integration tests + 1 Python integration test (exceeds the 3+1 floor). Two independent reviews → APPROVED.
- ✅ **One engine, two apps**: AAR cross-compiled from our `rslib` (cargo-ndk, NDK 29.0.14206865); AnkiDroid on x86_64 emulator (`Pixel_10`) ran an instrumentation test asserting `getCoverage().backendVersion == "26.05"` == desktop.
- ✅ All work merged to `main` + pushed on the 3 public forks; reproducible-build fix (`build_rust` gradlew) landed.
- ✅ Docs/orchestration: PRD, ARCHITECTURE, BUILD-WORKFLOW, BrainLift, plan, STATE, RUN-MVP (this repo, private).

**Reality check:** this is the *foundation*, not the study product. No GRE content, no memory score, no dashboard, no learning-science engine feature yet. Details below.

---

## Wednesday MVP — "both apps work & review the same deck, NO AI"  (updated 2026-06-30 late eve)
Executed via the `docs/plans/2026-07-01-wednesday-mvp.md` plan on branch `feat/speedrun-wed-mvp`.
### Desktop
- ✅ Anki forked and building from source (Windows build fixed: n2 forward-slash `render.rs` patch + out-of-tree uv venv).
- ✅ Rust change end-to-end + tests — now TWO read-only RPCs: `GetCoverage` + `GetTopicMastery` (FSRS retrievability → mastered proportion + Wilson 95% range + abstain). 9+ Rust tests + 2 Python integration tests; read-only, `integrity_check ok`.
- ✅ Seed exam deck built (`speedrun/out/gre_math_seed.apkg`, ≥30 tagged calc+LA declarative notes w/ Source) → **review loop on the exam deck works** (import into either app).
- ⚠️ **Memory model with honest score (range + give-up):** the RPC + Wilson range + abstain rule are DONE and pushed; **the visible score UI is Cursor's job** (Svelte/TS panel on the `GetTopicMastery` seam) — IN PROGRESS.
- ✅ **Clean-machine installer:** fixed with **zero upstream change** — the Briefcase Windows/mac templates are git *submodules*; the fix was populating them via the existing `SyncSubmodule` (once the `render.rs` fix let n2 spawn the runner).
### Mobile
- ✅ Phone app builds and runs on the emulator on the shared engine.
- ⚠️ **Loads exam deck + real review session:** deck is ready to import; the actual review-session run is David's recording (Wed).
### §7a artifacts — ✅ placed in `docs/artifacts/` (`why-rust-not-python.md`, `upstream-files-touched.md`; upstream surface = 4 files: lib.rs +1, proto/src/lib.rs +1, collection.py +2, render.rs +8/−2).
### Proof to capture — **David does these Wednesday** (apps just need to be runnable): clean-build, clean-machine install, phone review session, honest-score demo (Step 4b). Run steps in `docs/RUN-MVP.md`.

**Wednesday status: code/build ✅ DONE & green (except the known complexipy tool crash).** Remaining: **(Cursor)** the memory-score UI + these docs (done); **(David, Wed)** the recordings. Known non-blocking env item: complexipy tool crash.

---

## Friday — AI added & checked; phone syncs; three scores
- ❌ **Topic-aware interleaving / points-at-stake** scheduler change (the *mutating* engine change, via `transact`/`Op`) — the headline learning-science feature (§8 ablation, 15%).
- ❌ Self-hosted **sync server** (`rslib/sync`) + **two-way sync** + offline-reconnect + **conflict rule** (§7b).
- ❌ **Performance** model (P(correct on novel problem)) + **memory→performance gap** meter (§7d paraphrase test).
- ❌ **Readiness** score (flat IRT → scaled 200–990) + range (conformal) + abstention; **three scores on phone**.
- ❌ **External AI/RAG service** (FastAPI, off by default): generate → CAS verify → source-ground → gold-set gate (§7f); LangGraph fits here. Beats keyword/vector baseline.
- ❌ App still scores with **AI off**.

## Sunday — prove it & ship
- ❌ Memory **calibration** (chart + Brier/log loss on held-out) (§9 step 1).
- ❌ Performance accuracy on held-out exam questions (§9 step 2); score mapping written up + range (step 3).
- ❌ **3-build ablation** (full / feature-off / plain Anki), equal study time, pre-registered metric (§8).
- ❌ **Leakage check** script (§7e); **crash ×20** + offline tests (§7g); **`make bench`** p50/p95/worst on 50k deck (§7h, §10).
- ❌ Packaged **installers** (desktop) + **signed APK**; sync conflict handling; both apps score with AI off.
- ❌ Results report + model description one-pagers + demo video (3–5 min) + BrainLift.

---

## Rubric weight coverage (where we stand)
| Area | Weight | Status |
|---|---|---|
| Rust change & fit with Anki | 20% | ⚠️ real change exists (read-only) + tests; write-ups missing; may strengthen |
| Score accuracy & honest uncertainty | 20% | ❌ no memory/perf/readiness scores yet |
| Study feature on learning science | 15% | ❌ interleaving/points-at-stake not built |
| AI checking & safety | 15% | ❌ Friday |
| Fair re-runnable tests | 12% | ❌ ablation/held-out/leakage not built |
| Two apps one engine + sync | 10% | ⚠️ one engine ✅ proven; sync ❌ |
| Useful product & clean UX | 8% | ❌ no study UX/content yet |

**Hard limits watch:** real Rust change ✅ (have one; keep/strengthen). Phone shares engine ✅; sync ❌ (needed to lift the 70% cap by Fri). Clean-device run ❌ until installer works (50% cap risk). No fake readiness numbers — we abstain by design ✅ philosophy.
