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

## Wednesday MVP — "both apps work & review the same deck, NO AI"
### Desktop
- ✅ Anki forked and building from source.
- ⚠️ Rust change working end-to-end + 3 Rust unit tests + 1 Python test. *(Have it via `GetCoverage`. Gaps: the required §7a artifacts — one-page "why Rust not Python" note + list of upstream files touched & merge difficulty — are NOT written. Also `GetCoverage` is a lightweight coverage query; consider strengthening — see "Recommended Wednesday plan".)*
- ❌ **A review loop running on your exam deck.** *(No GRE deck exists — blocked on content.)*
- ❌ **A memory model with an honest score: range + give-up rule.** *(Not built. FSRS retrievability exists in-engine but is not aggregated per-topic, scored, ranged, or displayed.)*
- ❌ **An installer that runs on a clean machine.** *(Briefcase installer template-clone currently fails; needs fixing + a clean-machine recording.)*
### Mobile
- ✅ Phone app builds and runs on the emulator on the shared engine.
- ❌ **Loads your exam deck and runs a real review session.** *(No deck; only the RPC gate test has run, not a study session.)*
### Proof to capture
- ✅ Commit hash. ✅ Test results (capturable). ❌ Clean-build recording. ❌ Clean-machine install recording. ❌ Phone review-session screen recording.

**Wednesday status: ~3.5 of 7 items done.** The hardest *technical* risk (build + shared engine + Rust change) is cleared; the remaining Wednesday items are **content (exam deck)**, **memory model + honest score/give-up**, **clean-machine installer**, the **§7a Rust-change write-ups**, and **recordings**.

### Recommended Wednesday plan (highest-leverage order)
1. **Seed exam deck + exam-profile** (topic taxonomy/DAG + ETS weights; a starter calc/LA deck of tagged declarative cards). Unblocks the review loop on both apps + coverage %.
2. **Memory model + honest score** — add `GetTopicMastery` (per-topic FSRS retrievability aggregate + mastered count + avg recall). This simultaneously (a) is a *stronger* §7a Rust change ("mastery query" option), (b) powers the honest memory score with a **range** (Wilson/bootstrap) + **give-up rule** (abstain below N graded reviews). Read-only, so still corruption-safe.
3. **Clean-machine installer** — fix the Briefcase template-clone; produce an installer + recording.
4. **§7a artifacts** — one-page "why this belongs in Rust" + touched-upstream-files/merge-difficulty list.
5. **Record proofs** — clean build, install, and a phone review session on the seed deck.

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
