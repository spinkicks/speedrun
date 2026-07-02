# Change log — 2026-07-01 (Wednesday)

Everything shipped today, grounded in the git history across the 3 forks. Honesty rules from `WHAT-WE-BUILT.md` apply (real / scaffolding / planned). Final `main` pins: **anki `af1138428` · Anki-Android-Backend `9aa21ec` · anki-android `fdfd086031` · umbrella latest**.

## Headline
Went from "wed-plus engine work on a branch" to **both apps working end-to-end on one engine, with Speedrun's own branded, mobile-first, dark UI** — Home + Memory + START RUN → real study, on desktop AND Android. Two smoke/audit-caught bugs found and fixed before merge. NO AI (Friday).

## Wednesday-Plus (engine + dashboard + sync + installer) → merged to `main`
- `1fc5128` **Installer network-independence** — vendored Briefcase Windows+mac templates in-tree; dropped network `SyncSubmodule`; clean-machine build, no submodule fetch.
- `ce0f729` **`GetExamProfile`** read-only RPC + config-backed exam profile.
- `4d2cf76` **`ReorderNewByPointsAtStake`** — the mutating engine change: `transact(Op::SortCards)`, new-card reposition + topic interleave, ablation modes, undo-safe; `f0d717f` adds pre-undo integrity assertion.
- `126654a` **`GetPerformanceReadiness`** scaffolding RPC (deterministic, always-abstain, non-AI); `20dd7a2` rustfmt + mypy (proto FROZEN here).
- `a558dbc`/`8aea05f`/`a0ead51c` **Memory dashboard** — shared Svelte page (range-forward, abstain, coverage header, grouped, sort toggle) + desktop Tools menu + Perf/Readiness scaffold columns.
- `1fed9e1` **§7b sync test** — two-way, 10+10 same-card revlog union, latest-wins, integrity ok.
- Android (dashboard): `a56dda6c` Memory screen (PageFragment + RPC bridge + nav). Backend: `299bb44`/`d4086e0` rsdroid re-pin + `--locked` Cargo.lock.
- **Consolidated all 3 forks to `main`** (FF, no merge commits).

## 7-agent audit (Cursor/Fable) — caught a real defect class
- Found: the Memory dashboard shipped "code-complete" but **never rendered on desktop** (RPCs 403/404: methods missing from `exposed_backend_list` + `AnkiWebViewKind.DEFAULT` has no API access) AND the **exam profile was never bootstrapped** (fresh collections errored). Both would have broken the demo.
- Verified genuinely solid: invariants, tag↔topic alignment, Android bridge, §7b honesty caveat.
- Docs corrected: rubric table (was falsely "no scores/no interleaving/sync ❌"), STATE SHA contradictions, plan STATUS banners, refreshed `upstream-files-touched.md`; new `friday-brief.md`.

## Speedrun Home ("The Run") — new branded product shell → merged
- `dbf19ef` shared Svelte Home page (flat/sharp, split rows w/ 95% error-brackets, honest run status); `92149aa` desktop dialog + config-gated auto-open on launch + START RUN bridge.
- `6341b6f` **audit gate-blocker fixes:** desktop data path (`SPEEDRUN` webview kind + 4 methods allow-listed — fixes Home AND Memory), `include_str!` exam-profile bootstrap (both platforms), `closeWithCallback`; `52bcefa` auto-open moved post-sync + safeMode guard; `7df9f5a` e2e render-proof.
- Android: `2146d885` Speedrun Home screen (PageFragment). Backend `e964fb3` re-pin. **Verified on both platforms** (David screenshots).

## Mobile-first + START RUN + reviewer → merged
- `5ee33b3` **mobile-first responsive** Home+Memory (stacked ≤768px → desktop columns; compact copy); `0c5112957` e2e no-overflow gate.
- `281db94` **Memory re-themed dark** to "The Run" (real tokens; fixes phantom `--accent`/`--frame-bg`; 44px touch targets); `ef0407f` live UI smoke (11/11).
- `d0719ab` **desktop START RUN** launches real study + honest import/caught-up banner + Custom Study; `eb4f5a3` cross-platform ActionBar.
- `00a1e45` **R1a desktop dark reviewer** chrome (CSS-only, night-mode vars; no scheduling change).
- Android: `776117580` **dark shell** (toolbar + system bars, scoped); `fdfd0860` **START RUN → native reviewer** + snackbar fallbacks. Backend `9aa21ec` re-pin.
- **Two bugs caught + fixed:** `f0a06ce` false "all caught up" (read count-less `deck_tree()` → use `sched.deck_due_tree()`; +Qt-free `decide_start_run` + characterization test) — **David-smoke-caught**; `af1138428` desktop double-fire (`pycmd`≡`bridgeCommand` alias → fire once) — **QA-sweep-caught**. Coverage gap (Playwright bypasses Qt bridge) closed with backend unit tests.
- **Deferred post-Friday:** R1b Android reviewer theming (shared `CardViewerActivity` scope risk), full reviewer chrome polish, i18n/FTL + MathJax labels.

## Verified on-device (David)
- Desktop: Home auto-opens, START RUN → real review, dark reviewer, honest banners. ✅
- Android emulator: same Home renders; START RUN → native reviewer running a real card (epsilon-delta, 20 due, MathJax). ✅ (reviewer still default light theme = R1b deferred.)

## Docs created/updated (umbrella)
STATE, PROGRESS, FUTURE-PLANS, DECISIONS (Decision 14), RUN-MVP, AGENTS, `artifacts/upstream-files-touched.md`; new: `friday-brief.md`, `speedrun-home-spec.md` + mockup, `WHAT-WE-BUILT.md`, `DEMO-VIDEO-SCRIPT.md`, `WEDNESDAY-DELIVERABLES.md`, this changelog. Infra: `.claude/cursor-review.md` channel + notify hook (dormant).

## Still open (for the recording)
- Installer **package** artifact (Claude) → clean-machine install recording via **Windows Sandbox** (David).
- Recordings: clean-build, test results, clean-machine install, phone review (phone review already captured). Script: `DEMO-VIDEO-SCRIPT.md`.
