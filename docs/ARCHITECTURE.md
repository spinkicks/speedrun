# Speedrun — Architecture & Build-Feasibility

> **Status: this was the pre-build feasibility/design doc (2026-06). As-built state is in `docs/STATE.md` + `docs/WHAT-WE-BUILT.md`.** The feasibility calls below held up; "future/not-yet" language has been lightly corrected where it's now shipped, but this remains a largely historical design doc.

Based on a deep read of the cloned repos (`repos/anki` @ version 26.05, `repos/anki-android`) plus official Anki/AnkiDroid developer docs. Every claim cites a real file path or doc URL.

## 0. Feasibility verdict

| Target | Verdict | Confidence | Core reason |
|---|---|---|---|
| **Desktop (one engine)** | ✅ Feasible, low risk | High | `./run` builds the whole stack; adding a proto method + Rust impl + Python call is a documented, well-trodden path. |
| **Android (same engine)** | ✅ Feasible, medium risk | Medium | AnkiDroid does NOT vendor `rslib` source — it pulls a prebuilt JNI AAR (`io.github.david-allison:anki-android-backend:0.1.64-anki25.09.2`). To ship OUR modified `rslib` we forked & built a **third repo**, `ankidroid/Anki-Android-Backend` (rsdroid) — ✅ **cloned to `repos/Anki-Android-Backend`, AAR built, `local_backend=true` swap proven on the emulator.** |
| **iOS (same engine)** | ⚠️ Not realistic in a 1-week build | High | AnkiMobile is closed-source; we'd write a Swift shell over `rslib`'s protobuf FFI from scratch. **Android-first is the correct call.** |

**The single most important fact:** the engine is `rslib` (Rust); both desktop and Android consume it, but through **different bridges** — desktop via a PyO3 bridge (`pylib/rsbridge`), Android via a JNI bridge built in the separate **rsdroid** repo. Our Rust change lives in one place; the work multiplier is in the *bridges*, not the engine.

> **DONE:** the third repo was cloned beside the others at `repos/Anki-Android-Backend` (i.e. `../Anki-Android-Backend` relative to the anki-android root), forked, and its AAR rebuilt from our modified `rslib`.

## 1. Build system (desktop)
- **Toolchain:** Rust `1.92.0` (pinned in `repos/anki/rust-toolchain.toml`); custom Rust-based **Ninja/N2** generator (`./ninja`, `build/configure`, `build/runner`) — NOT Bazel/cargo at top level; Python 3.9+ via `uv`; Node/TS via `yarn`; Qt via PyQt; protobuf via prost (Rust) / protobuf-es (TS).
- **Docs (real paths):** `repos/anki/docs/development.md` (authoritative), `docs/build.md`, `docs/windows.md`, online mirror https://dev-docs.ankiweb.net.
- **Minimal path:** install Rustup → install N2/Ninja (`tools/install-n2`) → **`./run`** (builds + launches) → tests `./ninja check`, format `./ninja format`, fix `./ninja fix`; wheels via `tools/build`.
- **Windows pitfalls (`docs/windows.md`):** needs MSVC Build Tools + Windows SDK, MSYS2 (`pacman -S git rsync`); **WSL bash conflicts with MSYS2 bash** (use `C:\msys64\usr\bin\bash.exe tools/install-n2`); **path must have no spaces & be short** — our clone path has no spaces but is deep; if long-path/linker errors appear, relocate to `C:\anki`. `ANKIDEV` auto-set by `./run` (disables auto-backups — don't point at a real profile).

## 2. The Rust engine (`rslib`)
**Layers** (`docs/architecture.md`, `docs/language_bridge.md`): TS/Svelte → Python (`pylib/anki` lib, `qt/aqt` GUI) → Rust core (`rslib`). Calls flow downward only.

**Key dirs in `rslib/src/`:** `collection/` (incl. `transact.rs`), **`scheduler/queue/builder/`** (our queue logic), `scheduler/answering/`, `scheduler/states/`, `scheduler/fsrs/` (FSRS is already here — crate `fsrs 5.2.0`), `storage/` (SQLite/rusqlite), `backend/mod.rs`, `services.rs`, `ops.rs`, `undo/mod.rs`, `latex.rs`, `cloze.rs`.

**Codegen pipeline** (`rslib/proto/build.rs`): `proto/anki/*.proto` → prost (Rust types + Service traits, included in `rslib/src/services.rs`) + `out/pylib/anki/_backend_generated.py` + TS. Dispatch is by numeric (service_index, method_index).

**Add ONE new message + backend method + Python call (required by spec):**
1. Define proto in `proto/anki/scheduler.proto` (or new `proto/anki/speedrun.proto`, auto-discovered) — message(s) + `service SpeedrunService { rpc GetReadiness(...) returns (...); }`.
2. Implement the trait in Rust: `impl crate::services::SpeedrunService for Collection { fn get_readiness(...) }` (mirror `rslib/src/decks/service.rs`); wire module into parent `mod.rs`.
3. Register the service so it gets an index.
4. Rebuild → `_backend_generated.py` gains the method.
5. Add a clean Python wrapper in `pylib/anki/` (never call `col._backend.*` from app code).
6. (Optional) TS import from `@generated/backend`.

**Undo / integrity (avoid corruption):** route every mutation through `Collection::transact` (`collection/transact.rs`) + add an `Op` variant (`ops.rs`) so undo + sync USN tracking work (`UNDO_LIMIT=30`). Keep DB-stored proto fields **additive** (`docs/protobuf.md` — never renumber stored fields). Read-only methods (e.g. `GetReadiness`) need none of this and are trivially safe.

## 3. Two apps, one engine (mobile)
- AnkiDroid has a Kotlin 1:1 port of pylib at `repos/anki-android/libanki/`, wrapping the Rust backend; engine loaded as a JNI native lib via `net.ankiweb.rsdroid.Backend` (`libanki/.../Storage.kt`). Android drives SQLite through `AnkidroidService` DB-proxy RPCs (`proto/anki/ankidroid.proto`).
- Backend pinned in `repos/anki-android/gradle/libs.versions.toml`: `ankiBackend = '0.1.64-anki25.09.2'`, `io.github.david-allison:anki-android-backend`.
- **Swap mechanism exists** (`AnkiDroid/build.gradle` ~507–517 + `buildSrc/.../BackendDependencies.kt`): set `local_backend=true` in `local.properties` to use a locally-built `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`.
- **Steps to ship our modified rslib to Android:** clone `Anki-Android-Backend` → point its rslib at our forked anki → build AAR (uses cargo-ndk to cross-compile `.so` for arm64-v8a/x86_64 + generate Kotlin protobuf) → `local_backend=true` → build AnkiDroid → add Kotlin wrapper in `libanki/`. **Risk: medium** (NDK + cargo-ndk + version alignment). Budget a full day to get a green `local_backend` build first.
- **iOS:** technically `rslib` cross-compiles to `aarch64-apple-ios` and exposes the same byte/protobuf FFI, but you'd rebuild AnkiMobile's whole Swift shell (cards in WKWebView, media, sync, DB proxy, protobuf-swift). **Not realistic in 1 week → defer.**

## 4. Sync
- Lives in `rslib/src/sync/` (axum-based `http_server/`, `http_client/`, collection + media sync, `login.rs`). **Standalone server binary:** `rslib/sync/main.rs` → `SimpleServer::run()`. **We can self-host from the repo.**
- Run options (https://docs.ankiweb.net/sync-server, `docs/syncserver/`): bundled, `python -m anki.syncserver`, Cargo standalone, or Docker. Env: `SYNC_USER1=user:pass`, `SYNC_BASE`, `SYNC_HOST`, `SYNC_PORT`. Clients point Sync prefs at `http://<ip>:8080/`.
- **Conflict model:** reviews stored locally (cards/revlog), synced as **incremental USN-keyed deltas**; server merges by USN. **No field-level 3-way merge** — divergent histories force a **full sync "upload or download" choice**. Media syncs separately. Design the spec's offline + conflict test around this (clean fast-forward when one side changed; forced one-way resolution when both did), not CRDT auto-merge.

## 5. Where our layers plug in
| Layer | Home | Why |
|---|---|---|
| Memory (FSRS) | Already in Rust core (`scheduler/fsrs/`) | Consume/extend; don't reimplement. |
| Prerequisite taxonomy/DAG | Add-on data + read-only RPC | Portable to Android with no extra native work; only put in core if queue building consumes it. |
| Practice-problem queue selection | Rust core (`scheduler/queue/builder/`) **if** it changes what's shown next | The one shared decision point both apps use → identical behavior for free. This is where the real engine change is justified. |
| IRT/readiness model | Split: light inference as read-only RPC; heavy calibration/training as external service | Keeps the mobile `.so` small; readiness display is just a returned number. **As-built: Performance & Readiness are computed *in-engine, deterministically, recompute-on-read* — no synced score blob** (see Decision 15 / D1). |
| RAG problem generation | External service; generated cards imported as notes (`rslib/src/adding.rs`) + synced down | Network/LLM deps must NOT enter the mobile native lib. **As-built: shipped as `services/speedrun-ai/` (FastAPI; SymPy verify + hybrid RAG + gold-set gate), OFF by default (`SPEEDRUN_AI_ENABLED=1` + `OPENAI_API_KEY`); both apps score fully with AI off.** |

**Math rendering:** Anki uses **MathJax in a WebView on both platforms** (desktop `ts/` + `qt/aqt/data/web/`; AnkiDroid `AnkiDroid/src/main/assets/mathjax/` + `libanki/.../template/MathJax.kt`; `rslib/src/latex.rs`, `cloze.rs`). Author cards with `\(...\)`/`\[...\]` → both render identically. No need for KaTeX.

**Rule of thumb:** only logic that changes *what the scheduler shows / how cards are scheduled* belongs in the Rust core; everything else is an add-on or external service (keeps the JNI `.so` small, avoids rebuilding rsdroid each iteration).

## 6. Risk register + day-1 walking skeleton
**Top risks:** (1) rsdroid build chain (High) — clone `Anki-Android-Backend`, get a stock `local_backend` AAR building first; (2) engine fork drift (High) — ONE forked anki repo feeds both bridges, keep proto additive; (3) Windows build friction (Med) — follow `docs/windows.md`, relocate to `C:\anki` if needed; (4) undo/corruption (Med-High) — `transact` + `Op` + additive fields, prefer read-only RPCs; (5) sync conflict expectations (Med) — design test around USN + forced one-way; (6) iOS scope creep (Med) — defer; (7) perf on mobile (Low-Med) — keep IRT/RAG off-device; (8) math rendering (Low) — use bundled MathJax.

**Walking skeleton (the real feasibility gate) — ✅ COMPLETE (all six steps landed; see `docs/STATE.md`):**
1. ✅ Desktop builds & runs (now via `just run`; `just check` green).
2. ✅ Read RPC end-to-end on `SpeedrunService` — proves proto→Rust→Python seam (grew into the full scoring RPC set).
3. ✅ Stood up our own sync server from `rslib/sync`; desktop syncs against it (see `docs/SYNC-SELFHOST.md`).
4. ✅ Cloned `Anki-Android-Backend`, built a `local_backend=true` AAR, ran AnkiDroid against it.
5. ✅ Rebuilt the AAR from our forked rslib (with the RPCs), called from `libanki` — **the "one engine, two apps" milestone, proven on the emulator.**
6. ✅ Real logic layered: queue-builder interleave (core), taxonomy DAG (add-on), the 3 honest scores (in-engine + read RPC), RAG generation (external `services/speedrun-ai/`, off by default).

## Key references
Repo: `repos/anki/docs/{development,build,architecture,protobuf,language_bridge,windows}.md`; `rust-toolchain.toml`; `rslib/proto/{build.rs,rust.rs,python.rs}`; `rslib/src/{services.rs,backend/mod.rs,ops.rs,collection/mod.rs,collection/transact.rs,undo/mod.rs,scheduler/queue/builder/mod.rs,latex.rs,cloze.rs}`; `rslib/src/sync/http_server/mod.rs`; `rslib/sync/main.rs`; `proto/anki/{decks,backend,ankidroid}.proto`; `Cargo.toml` (fsrs 5.2.0). anki-android: `libanki/README.md`, `AnkiDroid/build.gradle` (507–517), `buildSrc/.../BackendDependencies.kt`, `gradle/libs.versions.toml`, `libanki/.../Storage.kt`, `AnkiDroid/src/main/assets/mathjax/`, `libanki/.../template/MathJax.kt`.
Docs: https://dev-docs.ankiweb.net · https://docs.ankiweb.net/sync-server · https://github.com/ankidroid/Anki-Android-Backend · https://github.com/open-spaced-repetition/fsrs-rs
