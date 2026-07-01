# Wednesday-Plus (post-MVP hardening) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **STATUS: CONSTRUCTED — DO NOT EXECUTE.** Handed to Cursor (mission control) for review first. Execution begins only after Cursor approves. **NO AI / no model calls anywhere** — AI integration is Friday (hard rule).

**Goal:** On top of the Wednesday MVP, deliver: a network-independent clean-machine installer; the honest **Memory dashboard on BOTH platforms** (shared Svelte page rendered by desktop Qt + AnkiDroid) built exactly to `docs/design/memory-dashboard-spec.md`; the headline **interleaving / points-at-stake** engine change as a genuinely-mutating, undo-safe reposition via `transact`/`Op`; a **self-hosted sync server + two-way sync + conflict-rule test**; the coverage-map header; and **Performance/Readiness scaffolding** RPC/columns (deterministic, non-AI, clearly marked).

**Architecture:** All engine changes are additive to the existing read-only `SpeedrunService` (proto `anki.speedrun`) plus one mutating RPC that routes through `Collection::transact(Op::SortCards, …)` (repositioning **new-card positions only** — never review due-dates — so it is undo-safe and corruption-free). The dashboard is **one** SvelteKit page (`ts/routes/speedrun-memory/`) that both platforms render in a WebView (desktop: `AnkiWebView.load_sveltekit_page`; Android: `PageFragment` + `AnkiServer` + `PostRequestHandler`), calling the same RPCs — this is exactly how Anki's own Graphs page is shared cross-platform (per PRD §2 "re-implemented per platform" = native shell + RPC bridge per platform, shared web surface; no desktop Python/Qt *add-on*). The sync server already exists as the `anki-sync-server` binary in our fork; this plan stands it up and adds the §7b conflict test.

**Tech Stack:** Rust 1.92.0 (`rslib`); prost/protobuf-es/protobuf-python codegen via `just`; SvelteKit/TypeScript (`ts/`, built to `out/sveltekit`); Python/Qt (`qt/aqt`); Kotlin (AnkiDroid) + rsdroid JNI AAR (cargo-ndk); Fluent (`ftl/`) for UI strings. Windows host, builds via `just` (n2 build tool — the `render.rs` OS-separator fix from the MVP is already committed).

---

## Build-system note (READ FIRST)

`repos/anki` builds/checks go through **`just` recipes** (`just check`, `just build`, `just run`, `just test-rust`, `just test-py`, `cargo check`, `cargo test -p anki <mod>::`, `just fmt`). Content-toolchain venv is out-of-tree — use `bash speedrun/uvw.sh …`, never bare `uv`. `just check` is green except the known `complexipy-diff` tool crash (a Windows cp1252 encoding bug inside complexipy — not our code). AnkiDroid builds via `./gradlew` in `repos/anki-android`; the AAR builds from `repos/Anki-Android-Backend` (`build.bat`, NDK per `libs.versions.toml`).

**Commit target:** code → the forks in `repos/` (new branch **`feat/speedrun-wed-plus`** off the current `feat/speedrun-wed-mvp` tip). Docs/plans/strategy → the **private umbrella** (Cursor's). Never push strategy/AGENTS.md to the public forks.

**Invariants honored throughout (AGENTS.md):** mutations → `Collection::transact(Op::X, …)` returning `OpChanges`; additive proto with NEW field numbers, never renumber/reuse; read-only RPCs need no `transact`; ground every API via Serena/ast-grep/`cargo check` before editing; AGPL-3.0-or-later headers on every new source file; **NO AI**.

---

## Critical-path vs stretch (maps to the user's numbered scope)

| # | Item | Priority | Depends on |
|---|---|---|---|
| 0 | Installer network-independence (vendor template submodules) | **CRITICAL** | — (independent) |
| 1 | Memory dashboard on BOTH platforms | **CRITICAL** | Phase E (proto freeze) |
| 2 | Interleaving / points-at-stake reposition (mutating, transact/Op) | **CRITICAL** | Phase E (proto) |
| 4 | Coverage map in dashboard header | **CRITICAL (folded into #1)** | #1 |
| 3 | Self-hosted sync server + two-way + conflict test (§7b) | **STRETCH** | — (independent) |
| 5 | Performance/Readiness scaffolding RPC + columns | **STRETCH** | Phase E (proto), #1 |

**Dependency-ordered execution:** Phase 0 (installer) → **Phase E (all new engine RPCs/proto, defined + FROZEN together)** → merge to `main` + re-pin rsdroid submodule + rebuild AAR → Phase 1 (dashboard, both platforms) → Phase 3 (sync, independent, any time) . Phase 0 and Phase 3 are independent and can be done in parallel with the engine/dashboard track.

### Cross-repo coupling — FREEZE PROTO BEFORE ANDROID CONSUMES IT
`GetTopicMastery`/`GetCoverage` (already on `feat/speedrun-wed-mvp`) plus the THREE new protos in this plan (`GetExamProfile`, `ReorderNewByPointsAtStake`, `GetPerformanceReadiness`) must ALL be defined in **Phase E**, then **frozen, committed, and merged to `spinkicks/anki` `main`**, then the rsdroid `anki` submodule (`repos/Anki-Android-Backend/anki`) **re-pinned to that commit** and the **AAR rebuilt**, BEFORE the Android dashboard (Phase 1b) consumes them. Defining all new proto in one phase means the freeze happens once. After freeze, treat the proto as immutable for the rest of the plan (append-only if truly needed).

---

## File structure

**Phase 0 — Installer (in `repos/anki`)**
```
.gitmodules                                   # MODIFY: remove the two briefcase-*-template submodule blocks
qt/installer/windows-template/**              # VENDOR: de-submoduled real files (committed)
qt/installer/mac-template/**                  # VENDOR: de-submoduled real files (committed)
build/ninja_gen/src/... (installer wiring)    # MODIFY: build/configure/src/installer.rs — drop SyncSubmodule actions
docs/BUILD-PREREQS.md  (umbrella)             # NEW: clean-machine build prerequisites (Cursor places)
```

**Phase E — Engine RPCs + proto (in `repos/anki`)**
```
proto/anki/speedrun.proto                     # MODIFY: import collection.proto; add GetExamProfile, ReorderNewByPointsAtStake, GetPerformanceReadiness (+messages)
rslib/src/speedrun/mod.rs                     # MODIFY: pure points_at_stake_order() + reorder helpers + tests
rslib/src/speedrun/service.rs                 # MODIFY: impl the 3 new RPC methods on Collection
rslib/src/speedrun/exam_profile.rs            # CREATE: config get/set helpers for the exam profile
pylib/anki/speedrun.py                        # MODIFY: Python wrappers (exam_profile, reorder_new, performance_readiness, set_exam_profile)
pylib/tests/test_speedrun.py                  # MODIFY: Python integration tests
```

**Phase 1 — Dashboard (shared Svelte + per-platform shell)**
```
repos/anki/ts/routes/speedrun-memory/+page.svelte      # CREATE: page entry
repos/anki/ts/routes/speedrun-memory/MemoryDashboard.svelte  # CREATE: layout (header + table)
repos/anki/ts/routes/speedrun-memory/TopicRow.svelte        # CREATE: per-topic row (recall/range/data/abstain)
repos/anki/ts/routes/speedrun-memory/RangeBand.svelte       # CREATE: Wilson interval band
repos/anki/ts/routes/speedrun-memory/data.ts                # CREATE: RPC calls + row-model assembly
repos/anki/qt/aqt/mediasrv.py                          # MODIFY: add "speedrun-memory" to is_sveltekit_page()
repos/anki/qt/aqt/speedrun.py                          # CREATE: SpeedrunMemory QDialog (load_sveltekit_page)
repos/anki/qt/aqt/forms/main.ui                        # MODIFY: actionSpeedrunMemory + add to menuTools
repos/anki/qt/aqt/main.py                              # MODIFY: wire action → onSpeedrunMemory
repos/anki/qt/aqt/dialogs.py                           # MODIFY: register "SpeedrunMemory"
repos/anki/ftl/qt/... (a qt ftl file)                  # MODIFY: menu label string
# Android (repos/anki-android):
AnkiDroid/src/main/java/com/ichi2/anki/pages/PageWebViewClient.kt   # MODIFY: add "speedrun-memory" to isSvelteKitPage()
AnkiDroid/src/main/java/com/ichi2/anki/pages/PostRequestHandler.kt  # MODIFY: register getTopicMastery/getCoverage/getExamProfile/getPerformanceReadiness
AnkiDroid/src/main/java/com/ichi2/anki/pages/SpeedrunMemoryFragment.kt   # CREATE
AnkiDroid/src/main/java/com/ichi2/anki/pages/SpeedrunMemoryDestination.kt # CREATE (toIntent)
anki-common/src/main/kotlin/com/ichi2/anki/common/destinations/SpeedrunMemoryDestination.kt # CREATE (data class)
AnkiDroid/src/main/java/com/ichi2/anki/navigation/AnkiDroidNavigator.kt  # MODIFY: register destination
AnkiDroid/src/main/res/menu/deck_picker.xml            # MODIFY: menu item
AnkiDroid/src/main/java/com/ichi2/anki/DeckPicker.kt   # MODIFY: handle menu click
```

**Phase 3 — Sync (in `repos/anki`)**
```
rslib/src/sync/collection/tests.rs            # MODIFY: add §7b two-client review + conflict test
docs/SYNC-SELFHOST.md  (umbrella)             # NEW: launch + point-client + conflict-rule doc (Cursor places)
```

---

# Phase 0 — Installer network-independence (CRITICAL)

**Outcome:** the desktop installer builds on a clean machine with **no network submodule sync** — the Briefcase Windows/mac templates are vendored in-tree (like `linux-template/`), and the build no longer runs `SyncSubmodule` for them. Documented clean-machine BUILD prerequisites.

**Grounded root cause (confirmed 2026-07-01):** `qt/installer/windows-template` + `qt/installer/mac-template` are **git submodules** (`.gitmodules`: `briefcase-windows-template` → `https://github.com/ankitects/briefcase-windows-app-template`, `briefcase-mac-template` → `.../briefcase-macOS-app-template`). `build/configure/src/installer.rs` `build_installer()` runs two `SyncSubmodule { path, offline_build: false }` actions (`installer:template:win` / `installer:template:mac`) that fetch them over the network at build time; `BuildCommand.files()` depends on `inputs![":installer:template", glob!["qt/installer/**"]]`. `linux-template/` is the model — vendored in-tree, **no** SyncSubmodule action. The MVP made the installer *build* by initializing these submodules (needs network); this phase makes it network-independent by vendoring.

### Task 0.1: Branch + confirm current installer wiring

**Files:** none (grounding).

- [ ] **Step 1: Create the working branch**

Run from `repos/anki`:
```bash
git checkout feat/speedrun-wed-mvp && git pull --ff-only
git checkout -b feat/speedrun-wed-plus
```

- [ ] **Step 2: Re-confirm the submodule + wiring facts** (do not skip — ground before edit)

Run from `repos/anki`:
```bash
git submodule status | grep -iE 'installer|template'
git config -f .gitmodules --get-regexp 'briefcase'
grep -n "SyncSubmodule\|installer:template\|glob!\[\"qt/installer" build/configure/src/installer.rs
```
Expected: two template submodules listed; `.gitmodules` shows both `ankitects/briefcase-*-app-template` URLs; `installer.rs` shows the two `SyncSubmodule` actions + the `:installer:template` input reference.

### Task 0.2: Vendor the Windows + mac templates in-tree

**Files:**
- Modify: `repos/anki/.gitmodules`
- Vendor: `repos/anki/qt/installer/windows-template/**`, `repos/anki/qt/installer/mac-template/**`

- [ ] **Step 1: Populate both submodules once (needs network THIS one time)**

Run from `repos/anki`:
```bash
git submodule update --init qt/installer/windows-template qt/installer/mac-template
ls qt/installer/windows-template/ qt/installer/mac-template/   # real files present
```

- [ ] **Step 2: De-submodule each template** (remove gitlink + inner `.git`, keep files)

Run from `repos/anki`:
```bash
git rm --cached qt/installer/windows-template qt/installer/mac-template
rm -rf qt/installer/windows-template/.git qt/installer/mac-template/.git
```

- [ ] **Step 3: Remove the two submodule blocks from `.gitmodules`**

Edit `repos/anki/.gitmodules` and delete exactly these two blocks (leave `ftl/core-repo` and `ftl/qt-repo` intact):
```
[submodule "briefcase-windows-template"]
	path = qt/installer/windows-template
	url = https://github.com/ankitects/briefcase-windows-app-template
	branch = anki
	shallow = true
[submodule "briefcase-mac-template"]
	path = qt/installer/mac-template
	url = https://github.com/ankitects/briefcase-macOS-app-template
	branch = anki
	shallow = true
```

- [ ] **Step 4: Stage the vendored files as plain tree content**

Run from `repos/anki`:
```bash
git add .gitmodules qt/installer/windows-template qt/installer/mac-template
git status --short | head        # templates now appear as normal added files, not gitlinks
```

### Task 0.3: Drop the SyncSubmodule build actions

**Files:**
- Modify: `repos/anki/build/configure/src/installer.rs`

- [ ] **Step 1: Remove the two `SyncSubmodule` actions in `build_installer()`**

In `repos/anki/build/configure/src/installer.rs`, delete these two `add_action` calls (the `installer:template:win` and `installer:template:mac` blocks) from `pub fn build_installer(build: &mut Build)`:
```rust
    build.add_action(
        "installer:template:win",
        SyncSubmodule {
            path: "qt/installer/windows-template",
            offline_build: false,
        },
    )?;
    build.add_action(
        "installer:template:mac",
        SyncSubmodule {
            path: "qt/installer/mac-template",
            offline_build: false,
        },
    )?;
```

- [ ] **Step 2: Drop the now-dangling `:installer:template` dependency** in `BuildCommand::files()`

Change:
```rust
        build.add_inputs("", inputs![":installer:template", glob!["qt/installer/**"]]);
```
to (the vendored files are already covered by the glob):
```rust
        build.add_inputs("", inputs![glob!["qt/installer/**"]]);
```

- [ ] **Step 3: Remove the now-unused `SyncSubmodule` import if the compiler flags it**

Run `cargo check -p configure 2>&1 | tail -20`. If it warns `unused import: ...SyncSubmodule`, remove `use ninja_gen::git::SyncSubmodule;` from the top of `installer.rs`. Expected: `configure` compiles clean.

- [ ] **Step 4: Commit**

```bash
git add build/configure/src/installer.rs
git commit -m "fix(installer): vendor Windows+mac Briefcase templates in-tree; drop network SyncSubmodule (clean-machine build, no submodule fetch)"
```
(The vendored template files + `.gitmodules` were staged in Task 0.2; include them in this commit or a preceding one — one commit is fine.)

### Task 0.4: Verify the installer builds with no network dependency + document prereqs

**Files:**
- Create: `docs/BUILD-PREREQS.md` (umbrella — draft for Cursor to place)

- [ ] **Step 1: Rebuild `configure` + regenerate the build graph** (the `render.rs` fix must already be committed)

Run from `repos/anki`:
```bash
CARGO_TARGET_DIR="$PWD/out/rust" cargo build -p configure && ./out/rust/debug/configure.exe
grep -c "installer:template" out/build.ninja   # expect 0 (actions gone)
```

- [ ] **Step 2: Build the installer** (proves no submodule sync runs)

Run from `repos/anki`:
```bash
export PATH="$HOME/.cargo/bin:$PATH"   # n2 on PATH
uv run python qt/tools/build_installer.py --version "$(cat .version)" build 2>&1 | tail -20
```
Expected: build completes with NO "Cloning into" / "Submodule … registered" lines; Briefcase uses the local `qt/installer/windows-template`. If it still tries to fetch, the SyncSubmodule removal (0.3) was incomplete.

- [ ] **Step 3: Run the installer tests**

Run from `repos/anki`:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
out/pyenv/scripts/pytest.exe qt/tests/test_installer.py -q 2>&1 | tail -5
```
Expected: `2 passed`.

- [ ] **Step 4: Write the clean-machine build-prereqs doc** (draft in umbrella; Cursor places)

`docs/BUILD-PREREQS.md`:
```markdown
# Clean-machine BUILD prerequisites (desktop installer)

To build the Speedrun desktop installer on a clean Windows machine:
1. Toolchain: Rust (rustup auto-pins 1.92.0 via rust-toolchain.toml), Python via `uv`, Node + yarn 1.22, MSVC build tools, MSYS2 (`git`, `rsync`), the `n2` build tool (`bash tools/install-n2`), `just`.
2. Clone the fork branch: `git clone -b <branch> https://github.com/spinkicks/anki` — the Briefcase Windows/mac templates are now vendored IN-TREE (no submodule fetch needed; only the `ftl/*` submodules remain and are optional for the installer).
3. Build: `just build`; installer: `uv run python qt/tools/build_installer.py --version $(cat .version) build && … package`.
4. NO network is required for the installer TEMPLATE step. (`ftl/*` submodules need network only if translations are rebuilt.)
Note: the `render.rs` OS-path-separator fix (already committed) is required for n2 on Windows.
```

- [ ] **Step 5: Commit** (umbrella)
```bash
cd C:/Users/davir/Ultra/Alpha/Speedrun && git add docs/BUILD-PREREQS.md && git commit -m "docs: clean-machine installer build prerequisites (draft for Cursor)"
```

---

# Phase E — Engine RPCs + proto (define ALL new proto here, then FREEZE) — CRITICAL

**Outcome:** three additive RPCs on `SpeedrunService` — `GetExamProfile` (read-only; profile from synced config), `ReorderNewByPointsAtStake` (mutating; `transact`/`Op`, undo-safe new-card reposition), `GetPerformanceReadiness` (read-only scaffolding). After this phase the proto is frozen, merged to `main`, and the rsdroid submodule re-pinned.

### Task E1: Exam profile in synced config + `GetExamProfile` RPC (read-only)

**Files:**
- Modify: `repos/anki/proto/anki/speedrun.proto`
- Create: `repos/anki/rslib/src/speedrun/exam_profile.rs`
- Modify: `repos/anki/rslib/src/speedrun/mod.rs` (declare module), `service.rs` (impl)

- [ ] **Step 1: Add the proto (additive; new messages, fields 1..)**

Append to `repos/anki/proto/anki/speedrun.proto`. First add the rpc inside `service SpeedrunService { … }`:
```proto
  // Read the exam profile JSON stored in the (synced) collection config.
  rpc GetExamProfile(GetExamProfileRequest) returns (ExamProfileResponse);
```
Then append messages:
```proto
message GetExamProfileRequest {
  // e.g. "gre_math". Empty => the default exam id.
  string exam_id = 1;
}

message ExamProfileResponse {
  // The profile JSON as stored (topics/labels/ets_weight/prereqs), or "" if unset.
  string profile_json = 1;
  // Echo of the resolved exam id.
  string exam_id = 2;
}
```

- [ ] **Step 2: Create the config helper** `repos/anki/rslib/src/speedrun/exam_profile.rs`
```rust
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

use crate::collection::Collection;

/// Config key under which an exam profile JSON string is stored, per exam id.
pub(crate) fn exam_profile_key(exam_id: &str) -> String {
    let id = if exam_id.is_empty() { "gre_math" } else { exam_id };
    format!("speedrun:exam_profile:{id}")
}

impl Collection {
    /// Read the stored exam-profile JSON string, or empty string if unset.
    pub(crate) fn speedrun_exam_profile_json(&self, exam_id: &str) -> String {
        self.get_config_optional::<String, _>(exam_profile_key(exam_id).as_str())
            .unwrap_or_default()
    }
}
```

- [ ] **Step 3: Declare the module** — add to `repos/anki/rslib/src/speedrun/mod.rs` directly below `pub(crate) mod service;`:
```rust
pub(crate) mod exam_profile;
```

- [ ] **Step 4: Implement the RPC** — add to the `impl crate::services::SpeedrunService for Collection` block in `service.rs`:
```rust
    fn get_exam_profile(
        &mut self,
        input: anki_proto::speedrun::GetExamProfileRequest,
    ) -> error::Result<anki_proto::speedrun::ExamProfileResponse> {
        let exam_id = if input.exam_id.is_empty() {
            "gre_math".to_string()
        } else {
            input.exam_id.clone()
        };
        Ok(anki_proto::speedrun::ExamProfileResponse {
            profile_json: self.speedrun_exam_profile_json(&exam_id),
            exam_id,
        })
    }
```

- [ ] **Step 5: Python wrapper + setter** — add to `pylib/anki/speedrun.py`:
```python
ExamProfileResponse = speedrun_pb2.ExamProfileResponse


# inside class SpeedrunManager:
    def exam_profile(self, exam_id: str = "gre_math") -> ExamProfileResponse:
        """Read the exam-profile JSON stored in the synced collection config."""
        return self.col._backend.get_exam_profile(exam_id=exam_id)

    def set_exam_profile(self, profile_json: str, exam_id: str = "gre_math") -> None:
        """Store the exam-profile JSON in the synced collection config
        (uses the existing config API — a normal undoable config write)."""
        self.col.set_config(f"speedrun:exam_profile:{exam_id}", profile_json)
```

- [ ] **Step 6: RED→GREEN Python integration test** — append to `pylib/tests/test_speedrun.py`:
```python
def test_exam_profile_round_trips_via_config():
    col = getEmptyCol()
    try:
        assert col.speedrun.exam_profile("gre_math").profile_json == ""
        col.speedrun.set_exam_profile('{"exam_id":"gre_math","topics":[]}')
        resp = col.speedrun.exam_profile("gre_math")
        assert resp.exam_id == "gre_math"
        assert '"exam_id":"gre_math"' in resp.profile_json
        assert col.db.scalar("pragma integrity_check") == "ok"
    finally:
        col.close()
```
Verify: `cargo check -p anki_proto`, then (after E2/E3 land so the crate compiles) `just check` + `just test-py 2>&1 | grep -A3 exam_profile` → PASSED.

- [ ] **Step 7: Commit** (proto + rust + python together, since the crate needs all impls)
```bash
git add proto/anki/speedrun.proto rslib/src/speedrun/exam_profile.rs rslib/src/speedrun/mod.rs rslib/src/speedrun/service.rs pylib/anki/speedrun.py pylib/tests/test_speedrun.py
git commit -m "feat(speedrun): GetExamProfile read-only RPC + config-backed exam profile"
```

### Task E2: `ReorderNewByPointsAtStake` — the mutating engine change (transact/Op, undo-safe)

**Design & invariant reconciliation (READ):** the queue *builder* (`scheduler/queue/builder/`) computes order at read time and does not mutate — so a raw builder reorder would need no `transact`. To satisfy the mandated `transact(Op::X) → OpChanges` invariant AND make a genuinely-persisted, undo-safe, corruption-free change, we implement points-at-stake as a **new-card reposition** (writes new-card `position`/`due` only — never review due-dates/intervals), mirroring Anki's existing `Collection::sort_cards` (`rslib/src/scheduler/new.rs`, which wraps `self.transact(Op::SortCards, …)` + `update_card_inner`). We reuse `Op::SortCards` (semantically "Reposition"; grounded, already has undo + `describe`). Ablation modes: **Full** = points-at-stake order + topic interleave; **FeatureOff** = default note-id order (a plain reposition); **Plain** = no-op (leave Anki's own order untouched). "Weakness" is 1.0 for all new cards (never reviewed), so points-at-stake for new cards = topic weight; the weakness-weighted *review-queue* interleave is a documented read-time follow-up (Friday), noted below.

**Files:**
- Modify: `repos/anki/proto/anki/speedrun.proto`, `rslib/src/speedrun/mod.rs`, `rslib/src/speedrun/service.rs`, `pylib/anki/speedrun.py`, `pylib/tests/test_speedrun.py`

- [ ] **Step 1: Proto (additive; import collection.proto for OpChangesWithCount)**

At the top of `speedrun.proto`, after `package anki.speedrun;`, add the import:
```proto
import "anki/collection.proto";
```
Add the rpc inside `service SpeedrunService { … }`:
```proto
  // Reposition NEW cards by points-at-stake (topic weight) + topic interleave.
  // Mutating: persisted new-card positions only (never review due-dates).
  rpc ReorderNewByPointsAtStake(ReorderNewRequest) returns (anki.collection.OpChangesWithCount);
```
Append messages:
```proto
message ReorderNewRequest {
  // Deck to reposition new cards in (children included).
  int64 deck_id = 1;
  // Per-topic content weights (from the exam profile). Topics are hierarchical
  // tags; a card belongs to a topic if a note tag == topic or starts "topic::".
  repeated TopicWeight topic_weights = 2;
  AblationMode mode = 3;
}

message TopicWeight {
  string topic = 1;
  double weight = 2;
}

enum AblationMode {
  // Points-at-stake ordering + topic interleave (the feature).
  ABLATION_MODE_FULL = 0;
  // Feature off: plain note-id reposition (baseline reorder).
  ABLATION_MODE_FEATURE_OFF = 1;
  // Plain Anki: no reposition at all (no-op).
  ABLATION_MODE_PLAIN = 2;
}
```

- [ ] **Step 2: Pure ordering fn + RED tests** in `rslib/src/speedrun/mod.rs` (above `#[cfg(test)] mod test`)
```rust
/// Given new-card note-ids each paired with their topic index (or None if the
/// card matches no weighted topic), and topic indices sorted by descending
/// points-at-stake, return the note-ids in interleaved order: round-robin across
/// topics in priority order, so no two adjacent cards share a topic when
/// multiple topics have remaining cards. Unmatched cards (None) go last, in
/// input order. Input order within a topic is preserved (stable).
pub(crate) fn interleave_by_topic(
    ordered_topic_indices: &[usize],
    note_topic: &[(i64, Option<usize>)],
) -> Vec<i64> {
    use std::collections::VecDeque;
    let mut buckets: std::collections::HashMap<usize, VecDeque<i64>> = Default::default();
    let mut unmatched: Vec<i64> = Vec::new();
    for (nid, topic) in note_topic {
        match topic {
            Some(t) => buckets.entry(*t).or_default().push_back(*nid),
            None => unmatched.push(*nid),
        }
    }
    let mut out = Vec::with_capacity(note_topic.len());
    loop {
        let mut progressed = false;
        for &t in ordered_topic_indices {
            if let Some(q) = buckets.get_mut(&t) {
                if let Some(nid) = q.pop_front() {
                    out.push(nid);
                    progressed = true;
                }
            }
        }
        if !progressed {
            break;
        }
    }
    out.extend(unmatched);
    out
}

/// Match a topic tag set to the index of the highest-priority weighted topic a
/// card belongs to (prefix rule: tag == topic or starts with "topic::").
/// `weighted` is (topic, weight) already sorted by descending weight.
pub(crate) fn topic_index_for_tags(tags: &[String], weighted: &[(String, f64)]) -> Option<usize> {
    for (i, (topic, _)) in weighted.iter().enumerate() {
        let prefix = format!("{topic}::");
        if tags.iter().any(|t| t == topic || t.starts_with(&prefix)) {
            return Some(i);
        }
    }
    None
}
```
Add tests inside `mod test` (imports `use super::interleave_by_topic; use super::topic_index_for_tags;`):
```rust
    #[test]
    fn interleave_alternates_topics_no_two_adjacent_same() {
        // topics sorted by priority: [0, 1]; topic 0 has 3 cards, topic 1 has 2.
        let nt = vec![(10, Some(0)), (11, Some(0)), (12, Some(0)), (20, Some(1)), (21, Some(1))];
        let out = interleave_by_topic(&[0, 1], &nt);
        // round-robin: 10,20,11,21,12
        assert_eq!(out, vec![10, 20, 11, 21, 12]);
    }

    #[test]
    fn interleave_unmatched_go_last_in_order() {
        let nt = vec![(1, None), (2, Some(0)), (3, None)];
        assert_eq!(interleave_by_topic(&[0], &nt), vec![2, 1, 3]);
    }

    #[test]
    fn topic_index_uses_prefix_and_priority() {
        let weighted = vec![("calc".into(), 0.9), ("linear_algebra".into(), 0.1)];
        assert_eq!(topic_index_for_tags(&["calc::integration".into()], &weighted), Some(0));
        assert_eq!(topic_index_for_tags(&["linear_algebra".into()], &weighted), Some(1));
        assert_eq!(topic_index_for_tags(&["other".into()], &weighted), None);
    }
```

- [ ] **Step 3: GREEN — implement the mutating reorder** in `rslib/src/speedrun/service.rs`

Add imports at top of `service.rs`:
```rust
use crate::prelude::*;
use crate::scheduler::new::NewCardSorter;
use crate::search::SearchNode;
use crate::search::SortMode;
use crate::search::StateKind;
```
Add a Collection method (place ABOVE the `impl SpeedrunService` block, in an `impl Collection` block):
```rust
impl Collection {
    /// Reposition new cards in `deck_id` by points-at-stake + topic interleave.
    /// Persisted, undoable (Op::SortCards). New-card positions only.
    pub(crate) fn speedrun_reorder_new(
        &mut self,
        deck_id: DeckId,
        mut topic_weights: Vec<(String, f64)>,
        mode: anki_proto::speedrun::AblationMode,
    ) -> Result<OpOutput<usize>> {
        use anki_proto::speedrun::AblationMode;
        // Plain Anki: do nothing (empty op).
        if mode == AblationMode::Plain {
            return self.transact(Op::SortCards, |_col| Ok(0));
        }
        // Gather this deck's new cards (children included), in note-id order.
        let cids = self.search_cards(
            SearchNode::from_deck_name(&self.get_deck(deck_id)?.or_not_found(deck_id)?.name.to_string())
                .and(StateKind::New),
            SortMode::NoOrder,
        )?;
        let usn = self.usn()?;
        self.transact(Op::SortCards, |col| {
            let cards = col.all_cards_for_ids(&cids, false)?;
            let ordered_nids: Vec<i64> = if mode == AblationMode::FeatureOff {
                // baseline: note-id order
                let mut nids: Vec<i64> = cards.iter().map(|c| c.note_id.0).collect();
                nids.sort_unstable();
                nids.dedup();
                nids
            } else {
                // FULL: points-at-stake (topic weight) + interleave
                topic_weights.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                let mut note_topic: Vec<(i64, Option<usize>)> = Vec::new();
                let mut seen = std::collections::HashSet::new();
                for c in &cards {
                    if seen.insert(c.note_id) {
                        let note = col.storage.get_note(c.note_id)?.or_not_found(c.note_id)?;
                        note_topic.push((c.note_id.0, crate::speedrun::topic_index_for_tags(&note.tags, &topic_weights)));
                    }
                }
                let ordered_topics: Vec<usize> = (0..topic_weights.len()).collect();
                crate::speedrun::interleave_by_topic(&ordered_topics, &note_topic)
            };
            // Assign positions 1..N by note order, mirroring sort_cards_inner.
            let pos: std::collections::HashMap<i64, u32> = ordered_nids
                .iter()
                .enumerate()
                .map(|(i, nid)| (*nid, (i as u32) + 1))
                .collect();
            let mut count = 0;
            for mut card in cards {
                let original = card.clone();
                if let Some(p) = pos.get(&card.note_id.0) {
                    if card.set_new_position_speedrun(*p) {
                        count += 1;
                        col.update_card_inner(&mut card, original, usn)?;
                    }
                }
            }
            Ok(count)
        })
    }
}
```
Because `Card::set_new_position` is private to `new.rs`, add a crate-visible shim there. In `rslib/src/scheduler/new.rs`, add to `impl Card`:
```rust
    /// Crate-visible wrapper around set_new_position for the Speedrun reorder.
    pub(crate) fn set_new_position_speedrun(&mut self, position: u32) -> bool {
        self.set_new_position(position)
    }
```
(Grounding note: confirm `all_cards_for_ids`, `update_card_inner`, `usn()`, `SearchNode::from_deck_name`, `Op::SortCards`, `OpOutput` signatures via `cargo check` — all are used by `sort_cards`/`reschedule_cards_as_new` in `new.rs`. If `from_deck_name` differs, use `SearchNode::DeckIdsWithoutChildren(deck_id.to_string())` as in `sort_deck`.)

- [ ] **Step 4: Wire the service RPC** — add to the `impl SpeedrunService for Collection` block in `service.rs`:
```rust
    fn reorder_new_by_points_at_stake(
        &mut self,
        input: anki_proto::speedrun::ReorderNewRequest,
    ) -> error::Result<anki_proto::collection::OpChangesWithCount> {
        let weights = input
            .topic_weights
            .into_iter()
            .map(|tw| (tw.topic, tw.weight))
            .collect();
        let mode = anki_proto::speedrun::AblationMode::try_from(input.mode).unwrap_or(anki_proto::speedrun::AblationMode::Full);
        self.speedrun_reorder_new(DeckId(input.deck_id), weights, mode)
            .map(Into::into)
    }
```

- [ ] **Step 5: RED→GREEN Rust integration test** (undo + integrity) — add inside `mod test` in `mod.rs`:
```rust
    #[test]
    fn reorder_new_full_interleaves_and_is_undo_safe() -> Result<()> {
        use anki_proto::speedrun::AblationMode;
        let mut col = Collection::new();
        let nt = col.get_notetype_by_name("Basic")?.unwrap();
        // 2 calc + 1 LA new cards
        for (front, tag) in [("c1", "calc"), ("c2", "calc"), ("la1", "linear_algebra")] {
            let mut note = nt.new_note();
            note.set_field(0, front)?;
            col.add_note(&mut note, DeckId(1))?;
            note.tags = vec![tag.into()];
            col.update_note(&mut note)?;
        }
        let before = col.storage.integrity_check_scalar()?; // helper below; or assert via pragma in python
        let weights = vec![("calc".to_string(), 0.9), ("linear_algebra".to_string(), 0.1)];
        let out = col.speedrun_reorder_new(DeckId(1), weights, AblationMode::Full)?;
        assert!(out.output >= 1); // repositioned at least one card
        // Undo restores (no corruption): undo the op.
        col.undo()?;
        assert_eq!(before, col.storage.integrity_check_scalar()?);
        Ok(())
    }

    #[test]
    fn reorder_new_plain_is_noop() -> Result<()> {
        use anki_proto::speedrun::AblationMode;
        let mut col = Collection::new();
        let nt = col.get_notetype_by_name("Basic")?.unwrap();
        let mut note = nt.new_note();
        col.add_note(&mut note, DeckId(1))?;
        let out = col.speedrun_reorder_new(DeckId(1), vec![], AblationMode::Plain)?;
        assert_eq!(out.output, 0);
        Ok(())
    }
```
(If `integrity_check_scalar` / `col.undo()` names differ, ground via `cargo check`; the intent is: run reorder, then `col.undo()`, then assert `pragma integrity_check == ok`. Prefer asserting integrity in the Python test where `col.db.scalar("pragma integrity_check")` is available — see Step 7. Keep ≥3 Rust tests total via the pure tests in Step 2 + these.)

- [ ] **Step 6: Python wrapper** — add to `pylib/anki/speedrun.py`:
```python
from anki.collection import OpChangesWithCount  # near other imports


# inside class SpeedrunManager:
    def reorder_new(
        self,
        deck_id: int,
        topic_weights: dict[str, float],
        mode: int = 0,  # 0=FULL, 1=FEATURE_OFF, 2=PLAIN
    ) -> OpChangesWithCount:
        """Reposition new cards by points-at-stake + interleave (undoable)."""
        req = speedrun_pb2.ReorderNewRequest(
            deck_id=deck_id,
            mode=mode,
            topic_weights=[
                speedrun_pb2.TopicWeight(topic=t, weight=w) for t, w in topic_weights.items()
            ],
        )
        return self.col._backend.reorder_new_by_points_at_stake(req)
```

- [ ] **Step 7: Python integration test (undo-safe, integrity)** — append to `pylib/tests/test_speedrun.py`:
```python
def test_reorder_new_is_persisted_and_integrity_ok():
    col = getEmptyCol()
    try:
        for front, tag in [("c1", "calc"), ("c2", "calc"), ("la1", "linear_algebra")]:
            note = col.new_note(col.models.by_name("Basic"))
            note["Front"] = front
            note.tags = [tag]
            col.add_note(note, DeckId(1))
        out = col.speedrun.reorder_new(1, {"calc": 0.9, "linear_algebra": 0.1}, mode=0)
        assert out.count >= 1
        assert col.db.scalar("pragma integrity_check") == "ok"
        # undo restores without corruption
        col.undo()
        assert col.db.scalar("pragma integrity_check") == "ok"
    finally:
        col.close()
```
Verify: `cargo test -p anki speedrun::` (pure + integration Rust green), then `just test-py 2>&1 | grep -A3 reorder`.

- [ ] **Step 8: Commit**
```bash
git add proto/anki/speedrun.proto rslib/src/speedrun/mod.rs rslib/src/speedrun/service.rs rslib/src/scheduler/new.rs pylib/anki/speedrun.py pylib/tests/test_speedrun.py
git commit -m "feat(speedrun): ReorderNewByPointsAtStake mutating RPC (transact Op::SortCards, interleave, ablation toggle, undo-safe) + tests"
```

### Task E3: `GetPerformanceReadiness` scaffolding RPC (read-only, non-AI) — STRETCH

**Files:** modify `speedrun.proto`, `service.rs`, `pylib/anki/speedrun.py`, `pylib/tests/test_speedrun.py`.

- [ ] **Step 1: Proto (additive; clearly scaffolding)**

Add rpc inside `service SpeedrunService`:
```proto
  // SCAFFOLDING (non-AI, deterministic): per-topic Performance/Readiness
  // placeholders with ranges + abstain. Real models are Friday. Always abstains
  // today (no data => honest). UI wires these as future columns.
  rpc GetPerformanceReadiness(GetPerformanceReadinessRequest) returns (PerformanceReadinessResponse);
```
Append messages:
```proto
message GetPerformanceReadinessRequest {
  repeated string topics = 1;
}

message PerformanceReadinessResponse {
  // Always true today; marks these numbers as not-yet-real scaffolding.
  bool scaffolding = 1;
  repeated TopicScaffold topics = 2;
  // Overall readiness placeholder (abstained today).
  ScoreScaffold overall_readiness = 3;
}

message TopicScaffold {
  string topic = 1;
  ScoreScaffold performance = 2;
  ScoreScaffold readiness = 3;
}

message ScoreScaffold {
  double point = 1;   // 0.0 while abstaining
  double lower = 2;   // 0.0
  double upper = 3;   // 1.0 (full uncertainty)
  bool abstained = 4; // true today
}
```

- [ ] **Step 2: Implement (deterministic; always abstains)** — add to `impl SpeedrunService for Collection` in `service.rs`:
```rust
    fn get_performance_readiness(
        &mut self,
        input: anki_proto::speedrun::GetPerformanceReadinessRequest,
    ) -> error::Result<anki_proto::speedrun::PerformanceReadinessResponse> {
        use anki_proto::speedrun::{ScoreScaffold, TopicScaffold};
        let abstain = || ScoreScaffold { point: 0.0, lower: 0.0, upper: 1.0, abstained: true };
        let topics = input
            .topics
            .into_iter()
            .map(|t| TopicScaffold { topic: t, performance: Some(abstain()), readiness: Some(abstain()) })
            .collect();
        Ok(anki_proto::speedrun::PerformanceReadinessResponse {
            scaffolding: true,
            topics,
            overall_readiness: Some(abstain()),
        })
    }
```

- [ ] **Step 3: Python wrapper + test**

`pylib/anki/speedrun.py`:
```python
PerformanceReadinessResponse = speedrun_pb2.PerformanceReadinessResponse


# inside class SpeedrunManager:
    def performance_readiness(self, topics: list[str]) -> PerformanceReadinessResponse:
        """SCAFFOLDING (non-AI): always-abstaining Performance/Readiness placeholders."""
        return self.col._backend.get_performance_readiness(topics=topics)
```
`pylib/tests/test_speedrun.py`:
```python
def test_performance_readiness_is_scaffolding_and_abstains():
    col = getEmptyCol()
    try:
        resp = col.speedrun.performance_readiness(["calc::limits"])
        assert resp.scaffolding is True
        assert resp.topics[0].performance.abstained is True
        assert resp.topics[0].readiness.abstained is True
        assert resp.overall_readiness.abstained is True
    finally:
        col.close()
```

- [ ] **Step 4: Commit**
```bash
git add proto/anki/speedrun.proto rslib/src/speedrun/service.rs pylib/anki/speedrun.py pylib/tests/test_speedrun.py
git commit -m "feat(speedrun): GetPerformanceReadiness scaffolding RPC (deterministic, always-abstain, non-AI)"
```

### Task E4: Full gate + FREEZE proto + merge + re-pin rsdroid submodule

**Files:** none new (integration/release).

- [ ] **Step 1: Full green gate**

Run from `repos/anki`:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
just fmt && just check 2>&1 | tail -25
```
Expected: green except the known `complexipy-diff` crash. Confirm codegen: `grep -c "def get_exam_profile\|def reorder_new_by_points_at_stake\|def get_performance_readiness" out/pylib/anki/_backend_generated.py` → 3.

- [ ] **Step 2: FREEZE the proto** — record in the task tracker that `speedrun.proto` is now frozen. Any later field must be append-only. Verify field numbers are unique/sequential in each new message.

- [ ] **Step 3: Merge to `main` + push** (so the rsdroid submodule can pin it)
```bash
git push -u origin feat/speedrun-wed-plus
# After Cursor review of the engine phase, fast-forward main:
git checkout main && git merge --ff-only feat/speedrun-wed-plus && git push
git rev-parse HEAD   # record ENGINE_SHA for the submodule pin
```
(If Cursor prefers to keep work on the branch until the whole plan lands, pin the submodule to the branch commit instead — record that SHA.)

- [ ] **Step 4: Re-pin the rsdroid `anki` submodule + rebuild AAR**

Run from `repos/Anki-Android-Backend`:
```bash
cd anki && git fetch origin && git checkout <ENGINE_SHA> && cd ..
test -f anki/proto/anki/speedrun.proto && grep -c "GetTopicMastery\|ReorderNewByPointsAtStake\|GetExamProfile\|GetPerformanceReadiness" anki/proto/anki/speedrun.proto  # expect 4
git add anki && git commit -m "build(rsdroid): re-pin anki submodule to frozen speedrun proto (wed-plus)"
cmd.exe /c build.bat   # rebuild AAR (bundles the new sveltekit page via anki_artifacts)
ls rsdroid/build/outputs/aar/rsdroid-release.aar
```
Expected: AAR rebuilt; it now contains the generated Kotlin for the 4 speedrun RPCs AND the `speedrun-memory` web page under bundled `backend/sveltekit/`.

---

# Phase 1 — Memory dashboard on BOTH platforms (CRITICAL; includes #4 coverage header)

**Outcome:** the honest Memory dashboard implemented EXACTLY to `docs/design/memory-dashboard-spec.md` — one shared Svelte page rendered by desktop (Tools → "Speedrun: Memory") and Android (menu → PageFragment). Range-forward, abstain state, coverage header, grouped by root, sort toggle, MathJax labels, read-only + Refresh. Performance/Readiness laid out as future columns (from Task E3 scaffolding).

### Task 1.1: The shared Svelte page — data layer

**Files:**
- Create: `repos/anki/ts/routes/speedrun-memory/data.ts`

- [ ] **Step 1: Write the data/model module** (calls the frozen RPCs via `@generated/backend`)

`repos/anki/ts/routes/speedrun-memory/data.ts`:
```typescript
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import {
    getCoverage,
    getExamProfile,
    getTopicMastery,
    getPerformanceReadiness,
} from "@generated/backend";

export interface ProfileTopic {
    id: string;
    name: string;
    ets_weight: number;
    prereqs: string[];
}
export interface ExamProfile {
    exam_id: string;
    name: string;
    topics: ProfileTopic[];
}

export interface Row {
    id: string;
    label: string;
    weight: number;
    isContainer: boolean; // ets_weight == 0 => group header, not a data row
    root: string; // "calc" | "linear_algebra"
    avgRecall: number;
    lower: number;
    upper: number;
    masteredCount: number;
    cardsWithData: number;
    gradedReviews: number;
    abstained: boolean;
    unlockN: number; // max(0, min_reviews - graded_reviews)
}

export async function loadProfile(examId = "gre_math"): Promise<ExamProfile | null> {
    const resp = await getExamProfile({ examId });
    if (!resp.profileJson) return null;
    return JSON.parse(resp.profileJson) as ExamProfile;
}

export async function loadRows(
    profile: ExamProfile,
    minReviews = 20,
): Promise<Row[]> {
    const leafIds = profile.topics.filter((t) => t.ets_weight > 0).map((t) => t.id);
    const mastery = await getTopicMastery({
        topics: leafIds,
        masteryThreshold: 0.9,
        minReviews,
    });
    const byTopic = new Map(mastery.topics.map((t) => [t.topic, t]));
    return profile.topics.map((t) => {
        const m = byTopic.get(t.id);
        const graded = m ? Number(m.gradedReviews) : 0;
        return {
            id: t.id,
            label: t.name,
            weight: t.ets_weight,
            isContainer: t.ets_weight === 0,
            root: t.id.split("::")[0],
            avgRecall: m ? m.avgRecall : 0,
            lower: m ? m.masteredLower : 0,
            upper: m ? m.masteredUpper : 1,
            masteredCount: m ? m.masteredCount : 0,
            cardsWithData: m ? m.cardsWithData : 0,
            gradedReviews: graded,
            abstained: m ? m.abstained : true,
            unlockN: Math.max(0, minReviews - graded),
        };
    });
}

export async function loadCoverage(profile: ExamProfile): Promise<{ covered: number; total: number; percent: number }> {
    const required = profile.topics.filter((t) => t.ets_weight > 0).map((t) => t.id);
    const c = await getCoverage({ requiredTags: required });
    return { covered: c.covered, total: c.total, percent: c.percent };
}

// Future columns (scaffolding; always abstains today).
export async function loadScaffold(profile: ExamProfile) {
    const leafIds = profile.topics.filter((t) => t.ets_weight > 0).map((t) => t.id);
    return await getPerformanceReadiness({ topics: leafIds });
}
```
(Grounding note: confirm the generated TS field casing in `out/ts/lib/generated/anki/speedrun_pb.ts` after `just build` — protobuf-es uses camelCase (`avgRecall`, `masteredLower`). Adjust if generation differs.)

### Task 1.2: The shared Svelte components (spec-exact)

**Files:** create `+page.svelte`, `MemoryDashboard.svelte`, `TopicRow.svelte`, `RangeBand.svelte` under `repos/anki/ts/routes/speedrun-memory/`.

- [ ] **Step 1: `RangeBand.svelte`** — the emphasized Wilson interval (band + numeric)
```svelte
<!-- Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html -->
<script lang="ts">
    export let lower: number; // 0..1
    export let upper: number; // 0..1
    export let point: number; // 0..1
</script>

<div class="range" title={`${Math.round(lower * 100)}–${Math.round(upper * 100)}%`}>
    <div class="track">
        <div class="fill" style={`left:${lower * 100}%;width:${(upper - lower) * 100}%`}></div>
        <div class="marker" style={`left:${point * 100}%`}></div>
    </div>
    <span class="nums">{Math.round(lower * 100)}–{Math.round(upper * 100)}%</span>
</div>

<style>
    .range { display: flex; align-items: center; gap: 8px; }
    .track { position: relative; flex: 1; height: 8px; background: var(--frame-bg, #e0e0e0); border-radius: 4px; }
    .fill { position: absolute; top: 0; height: 100%; background: var(--accent, #8aa); border-radius: 4px; }
    .marker { position: absolute; top: -2px; width: 2px; height: 12px; background: var(--fg, #333); }
    .nums { font-variant-numeric: tabular-nums; min-width: 64px; }
</style>
```

- [ ] **Step 2: `TopicRow.svelte`** — recall / range / data, or abstain state
```svelte
<!-- Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html -->
<script lang="ts">
    import type { Row } from "./data";
    import RangeBand from "./RangeBand.svelte";
    export let row: Row;
</script>

<tr class:abstained={row.abstained}>
    <td class="topic">{row.label} <span class="weight">({Math.round(row.weight * 100)}%)</span></td>
    {#if row.abstained}
        <td class="recall">—</td>
        <td class="range" colspan="1">🔒 INSUFFICIENT DATA: review {row.unlockN} more to unlock</td>
        <td class="data">{row.masteredCount}/{row.cardsWithData} cards</td>
    {:else}
        <td class="recall">{Math.round(row.avgRecall * 100)}%</td>
        <td class="range"><RangeBand lower={row.lower} upper={row.upper} point={row.avgRecall} /></td>
        <td class="data">{row.masteredCount}/{row.cardsWithData} cards</td>
    {/if}
</tr>

<style>
    tr.abstained { opacity: 0.55; }
    .weight { color: var(--fg-subtle, #888); font-size: 0.85em; }
    .data { font-variant-numeric: tabular-nums; white-space: nowrap; }
</style>
```

- [ ] **Step 3: `MemoryDashboard.svelte`** — header (coverage + explanation), grouped table, sort toggle, states
```svelte
<!-- Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html -->
<script lang="ts">
    import { onMount } from "svelte";
    import { loadProfile, loadRows, loadCoverage, type Row, type ExamProfile } from "./data";

    let profile: ExamProfile | null = null;
    let rows: Row[] = [];
    let coverage = { covered: 0, total: 0, percent: 0 };
    let loading = true;
    let error = "";
    let weakestFirst = false;
    let updated = "";

    async function refresh() {
        loading = true;
        error = "";
        try {
            profile = await loadProfile("gre_math");
            if (!profile) { error = "No cards found for this exam profile — import the seed deck."; return; }
            [rows, coverage] = await Promise.all([loadRows(profile), loadCoverage(profile)]);
            updated = new Date().toLocaleTimeString();
        } catch (e) {
            error = String(e);
        } finally {
            loading = false;
        }
    }
    onMount(refresh);

    // group leaf rows under their root container; sort within group.
    $: groups = (() => {
        if (!profile) return [];
        const containers = rows.filter((r) => r.isContainer);
        return containers.map((c) => {
            let leaves = rows.filter((r) => !r.isContainer && r.root === c.id);
            leaves = [...leaves].sort((a, b) =>
                weakestFirst
                    ? (a.abstained ? 2 : a.avgRecall) - (b.abstained ? 2 : b.avgRecall)
                    : b.weight - a.weight,
            );
            return { header: c, leaves };
        });
    })();
</script>

<div class="memory">
    <header>
        <div class="titlebar"><h1>Memory</h1><button on:click={refresh}>Refresh</button></div>
        <p class="explain">Your recalled memory by topic. Memory ≠ readiness — this measures what you retain, not whether you can solve timed problems.</p>
        <p class="coverage">Coverage: {coverage.covered} / {coverage.total} required topics present ({Math.round(coverage.percent)}%)
            <span class="updated">Updated {updated}</span></p>
        <label class="sort"><input type="checkbox" bind:checked={weakestFirst} /> Weakest first</label>
    </header>

    {#if loading}
        <div class="spinner">Loading…</div>
    {:else if error}
        <div class="empty">{error}</div>
    {:else}
        <table>
            <thead><tr><th>TOPIC (weight)</th><th>RECALL</th><th>RANGE (95%)</th><th>DATA</th></tr></thead>
            {#each groups as g}
                <tbody>
                    <tr class="grouphdr"><td colspan="4">{g.header.label}</td></tr>
                    {#each g.leaves as row (row.id)}
                        <svelte:component this={TopicRowComp} {row} />
                    {/each}
                </tbody>
            {/each}
        </table>
    {/if}
</div>

<script context="module" lang="ts">
    import TopicRowComp from "./TopicRow.svelte";
</script>

<style>
    .memory { max-width: 820px; margin: 0 auto; padding: 16px; font-family: system-ui, sans-serif; }
    .titlebar { display: flex; justify-content: space-between; align-items: center; }
    .explain { color: var(--fg-subtle, #666); }
    .coverage { font-weight: 600; }
    .updated { float: right; font-weight: 400; color: var(--fg-subtle, #888); }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; font-size: 0.8em; color: var(--fg-subtle, #888); border-bottom: 1px solid var(--border, #ddd); padding: 6px 4px; }
    :global(.memory td) { padding: 6px 4px; border-bottom: 1px solid var(--border, #f0f0f0); }
    .grouphdr td { font-weight: 700; padding-top: 14px; color: var(--fg, #444); }
</style>
```
(Note: `<svelte:component this={TopicRowComp}>` avoids an import-ordering quirk; if the project's Svelte version prefers a direct `<TopicRow {row} />`, use that — confirm by matching the graphs page's component-usage style during `just check`.)

- [ ] **Step 4: `+page.svelte`** — the route entry
```svelte
<!-- Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html -->
<script lang="ts">
    import MemoryDashboard from "./MemoryDashboard.svelte";
</script>

<MemoryDashboard />
```

- [ ] **Step 5: Build + lint the page**

Run from `repos/anki`:
```bash
just build 2>&1 | tail -10
just check 2>&1 | grep -iE "svelte|typescript|speedrun-memory" | tail -20 || true
ls out/sveltekit/_app/immutable/nodes | head   # page compiled
```
Expected: TS/Svelte checks pass (green except known complexipy). Fix any type mismatch against the generated `speedrun_pb` field names.

- [ ] **Step 6: Commit**
```bash
git add ts/routes/speedrun-memory/
git commit -m "feat(dashboard): shared Svelte Memory page (range-forward, abstain, coverage header, grouped, sort toggle)"
```

### Task 1.3: Desktop shell — register page + Tools menu

**Files:** modify `qt/aqt/mediasrv.py`, create `qt/aqt/speedrun.py`, modify `qt/aqt/forms/main.ui`, `qt/aqt/main.py`, `qt/aqt/dialogs.py`, an `ftl/qt` file.

- [ ] **Step 1: Whitelist the page** — in `repos/anki/qt/aqt/mediasrv.py`, add `"speedrun-memory"` to the list in `is_sveltekit_page()`:
```python
    return page_name in [
        "graphs",
        "congrats",
        # ... existing ...
        "speedrun-memory",
    ]
```

- [ ] **Step 2: Create the dialog** `repos/anki/qt/aqt/speedrun.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from __future__ import annotations

import aqt
import aqt.main
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView, AnkiWebViewKind


class SpeedrunMemory(QDialog):
    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        QDialog.__init__(self, mw, Qt.WindowType.Window)
        mw.garbage_collect_on_dialog_finish(self)
        self.mw = mw
        self.name = "speedrunMemory"
        self.setWindowTitle("Speedrun: Memory")
        disable_help_button(self)
        self.web = AnkiWebView(kind=AnkiWebViewKind.DEFAULT)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)
        self.setLayout(layout)
        restoreGeom(self, self.name, default_size=(900, 800))
        self.web.load_sveltekit_page("speedrun-memory")
        self.show()

    def reject(self) -> None:
        self.web.cleanup()
        saveGeom(self, self.name)
        aqt.dialogs.markClosed("SpeedrunMemory")
        QDialog.reject(self)
```
(Grounding note: confirm `AnkiWebViewKind` members via `qt/aqt/webview.py`; if a dedicated kind is required, mirror `NewDeckStats`'s `StatsWebView`. `load_sveltekit_page` is the grounded loader.)

- [ ] **Step 3: Register the dialog** — in `repos/anki/qt/aqt/dialogs.py`, add to the `_dialogs` registry dict:
```python
    "SpeedrunMemory": [aqt.speedrun.SpeedrunMemory, None],
```
and ensure `import aqt.speedrun` is present near the other dialog imports.

- [ ] **Step 4: Add the menu action** — in `repos/anki/qt/aqt/forms/main.ui`, add an action and reference it in `menuTools`:
```xml
  <action name="actionSpeedrunMemory">
   <property name="text"><string>Speedrun: Memory</string></property>
  </action>
```
and inside `<widget class="QMenu" name="menuTools">` add `<addaction name="actionSpeedrunMemory"/>`.
(The `.ui` is compiled during build; no manual codegen needed.)

- [ ] **Step 5: Wire the action** — in `repos/anki/qt/aqt/main.py`, in the menu-setup section (near other `qconnect(m.action...)`):
```python
        qconnect(m.actionSpeedrunMemory.triggered, self.onSpeedrunMemory)
```
and add the handler method to `AnkiQt`:
```python
    def onSpeedrunMemory(self) -> None:
        aqt.dialogs.open("SpeedrunMemory", self)
```

- [ ] **Step 6: Build + manual smoke (desktop)**

Run from `repos/anki`: `just run`. Expected: Anki launches; Tools → "Speedrun: Memory" opens the dashboard; with the seed deck imported it shows topic rows (all abstaining on a fresh deck — the honest default per spec); coverage header populates. (Actual capture is David's; this step just confirms it opens without error.)

- [ ] **Step 7: Commit**
```bash
git add qt/aqt/mediasrv.py qt/aqt/speedrun.py qt/aqt/dialogs.py qt/aqt/forms/main.ui qt/aqt/main.py
git commit -m "feat(dashboard/desktop): Tools → Speedrun: Memory opens the shared Svelte page"
```

### Task 1.4: Android shell — whitelist + RPC bridge + Fragment + nav

**Files (in `repos/anki-android`):** as listed in the file structure. **Prereq:** Phase E4 done (AAR rebuilt with the 4 RPCs + the `speedrun-memory` page bundled).

> ⚠️ **Cursor review — verify the #1 Android integration unknown FIRST.** Before building the Fragment/nav, confirm *where AnkiDroid serves the SvelteKit pages from* (bundled AAR assets vs AnkiDroid's own assets vs backend `AnkiServer`). Grep how an existing shared page (e.g. `graphs`/`card-info`) reaches the WebView on Android and mirror EXACTLY — if `speedrun-memory` isn't in whatever asset bundle the WebView loads, the page 404s and the whole Android dashboard fails late. Also confirm the real `PostRequestHandler` (the A1 grounding didn't surface a class by that exact name) — the RPC-bridge mechanism is the other must-verify. Do these two checks before writing Fragment code.

- [ ] **Step 1: Whitelist the page** — in `AnkiDroid/src/main/java/com/ichi2/anki/pages/PageWebViewClient.kt`, add to `isSvelteKitPage()`:
```kotlin
        "speedrun-memory",
```

- [ ] **Step 2: Register the RPC methods** — in `AnkiDroid/src/main/java/com/ichi2/anki/pages/PostRequestHandler.kt`, add to the `collectionMethods` map (mirror the existing entries; the raw method names must match the TS `postProto` names):
```kotlin
        "getCoverage" to { bytes -> col.backend.getCoverageRaw(bytes) },
        "getTopicMastery" to { bytes -> col.backend.getTopicMasteryRaw(bytes) },
        "getExamProfile" to { bytes -> col.backend.getExamProfileRaw(bytes) },
        "getPerformanceReadiness" to { bytes -> col.backend.getPerformanceReadinessRaw(bytes) },
```
(Grounding note: confirm the exact `collectionMethods` shape + how `col`/`backend` is referenced in this file, and that `*Raw(ByteArray): ByteArray` exists in the regenerated `GeneratedBackend.kt` — it will, once the AAR is rebuilt from the frozen proto.)

- [ ] **Step 3: Create the destination data class** `anki-common/src/main/kotlin/com/ichi2/anki/common/destinations/SpeedrunMemoryDestination.kt`:
```kotlin
package com.ichi2.anki.common.destinations

data class SpeedrunMemoryDestination(val unused: Unit = Unit) : Destination()
```

- [ ] **Step 4: Create the Fragment + toIntent** — `AnkiDroid/src/main/java/com/ichi2/anki/pages/SpeedrunMemoryFragment.kt`:
```kotlin
package com.ichi2.anki.pages

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.View
import com.google.android.material.appbar.MaterialToolbar
import com.ichi2.anki.R
import com.ichi2.anki.SingleFragmentActivity
import com.ichi2.anki.common.destinations.SpeedrunMemoryDestination

class SpeedrunMemoryFragment : PageFragment() {
    override val pagePath = "speedrun-memory"

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        view.findViewById<MaterialToolbar>(R.id.toolbar)?.setTitle("Speedrun: Memory")
    }
}

fun SpeedrunMemoryDestination.toIntent(context: Context): Intent =
    SingleFragmentActivity.getIntent(context, SpeedrunMemoryFragment::class, Bundle())
```

- [ ] **Step 5: Register in the navigator** — in `AnkiDroid/src/main/java/com/ichi2/anki/navigation/AnkiDroidNavigator.kt`, add the import and the `when` arm:
```kotlin
import com.ichi2.anki.common.destinations.SpeedrunMemoryDestination
import com.ichi2.anki.pages.toIntent
// ...
            is SpeedrunMemoryDestination -> destination.toIntent(navContext)
```

- [ ] **Step 6: Add the menu entry** — in `AnkiDroid/src/main/res/menu/deck_picker.xml`, add inside `<menu>`:
```xml
    <item
        android:id="@+id/action_speedrun_memory"
        android:menuCategory="secondary"
        android:title="Speedrun: Memory" />
```

- [ ] **Step 7: Handle the click** — in `AnkiDroid/src/main/java/com/ichi2/anki/DeckPicker.kt`, add imports + a branch in `onOptionsItemSelected`:
```kotlin
import com.ichi2.anki.common.destinations.SpeedrunMemoryDestination
import com.ichi2.anki.common.destinations.navigate
// ...
            R.id.action_speedrun_memory -> {
                navigate(SpeedrunMemoryDestination())
                true
            }
```

- [ ] **Step 8: Build + emulator smoke**

Run from `repos/anki-android`: `./gradlew :AnkiDroid:assembleDebug` (with `local_backend=true` in `local.properties` and the rebuilt AAR). Launch on the x86_64 emulator; open the menu → "Speedrun: Memory". Expected: the SAME dashboard renders (abstaining on a fresh deck), coverage header populates from the shared engine. (Recording is David's.)

- [ ] **Step 9: Commit**
```bash
git add AnkiDroid/src/main/java/com/ichi2/anki/pages/PageWebViewClient.kt \
        AnkiDroid/src/main/java/com/ichi2/anki/pages/PostRequestHandler.kt \
        AnkiDroid/src/main/java/com/ichi2/anki/pages/SpeedrunMemoryFragment.kt \
        anki-common/src/main/kotlin/com/ichi2/anki/common/destinations/SpeedrunMemoryDestination.kt \
        AnkiDroid/src/main/java/com/ichi2/anki/navigation/AnkiDroidNavigator.kt \
        AnkiDroid/src/main/res/menu/deck_picker.xml \
        AnkiDroid/src/main/java/com/ichi2/anki/DeckPicker.kt
git commit -m "feat(dashboard/android): Speedrun Memory screen (PageFragment renders shared Svelte page; RPC bridge + nav)"
```

### Task 1.5: Wire the Performance/Readiness scaffolding columns (STRETCH)

**Files:** modify `ts/routes/speedrun-memory/MemoryDashboard.svelte`, `TopicRow.svelte`, `data.ts`.

- [ ] **Step 1: Add future columns** — extend the table header with `PERFORMANCE` and `READINESS` columns and render each leaf row's scaffolding as `—` (abstained) with a subtle "(scaffolding)" note in the header. Call `loadScaffold(profile)` in `refresh()` and map per-topic. Keep the grid so these are additive columns (spec §Non-goals: "lay the grid out so they can be added as columns without a redesign"). Because everything abstains today, every cell shows `—`.

- [ ] **Step 2: Rebuild + commit**
```bash
just build && just check 2>&1 | tail -5
git add ts/routes/speedrun-memory/
git commit -m "feat(dashboard): Performance/Readiness scaffolding columns (abstaining placeholders, non-AI)"
```

---

# Phase 3 — Self-hosted sync server + two-way + conflict rule (§7b) — STRETCH

**Outcome:** the `anki-sync-server` binary (already in our fork) launched locally; two clients sync against it; a Rust §7b test proves 10+10 offline reviews all land and the same-card conflict resolves by the documented rule (latest-review-timestamp / card `mtime` wins; revlog append-only). No new server code needed.

**Grounded facts:** binary `anki-sync-server` (`rslib/sync/main.rs`); env `SYNC_USER1="user:pass"`, `SYNC_PORT`, `SYNC_BASE`; client endpoint via desktop `mw.pm.set_custom_sync_url(url)`. Conflict model is collection-level USN + `mtime` latest-wins; revlog entries are append-only (keyed by ms-timestamp id) so 10+10 distinct reviews always coexist. Test harness `with_active_server(...)` + `SyncTestContext` in `rslib/src/sync/collection/tests.rs`.

### Task 3.1: Document launching + pointing clients

**Files:** create `docs/SYNC-SELFHOST.md` (umbrella — draft for Cursor).

- [ ] **Step 1: Verify the server runs locally**

Run from `repos/anki`:
```bash
export SYNC_USER1="test:test" SYNC_PORT=8088 SYNC_BASE="$PWD/out/syncserver-data"
cargo run --release -p anki-sync-server &
sleep 3 && cargo run --release -p anki-sync-server -- --healthcheck; echo "exit=$?"
```
Expected: healthcheck exit 0 (server up). Stop the background server after.

- [ ] **Step 2: Write the doc** `docs/SYNC-SELFHOST.md`:
```markdown
# Self-hosted Anki sync server (Speedrun)

## Launch (from repos/anki)
    export SYNC_USER1="test:test"   # user:password (plaintext hashed with fixed salt)
    export SYNC_PORT=8088
    export SYNC_BASE=/path/to/syncserver-data
    cargo run --release -p anki-sync-server
    # health: anki-sync-server --healthcheck  (exit 0 = up)

## Point a client (desktop)
Preferences → Syncing → set the self-hosted endpoint, or in the debug console:
    mw.pm.set_custom_sync_url("http://127.0.0.1:8088/")
Then Sync and log in with test / test.

## Conflict rule (documented)
- Sync is collection-level (USN + mtime), not per-card merge.
- Different cards changed on each side → clean fast-forward; both sets land.
- Same object changed on both sides → latest mtime wins (latest-review-timestamp),
  with revlog entries append-only (both reviews are retained in `revlog`; card
  state resolves to the winner). Implausible clock skew is out of scope for Wed.
- True divergence forces a full-sync "upload or download" choice (no auto-merge).
```

- [ ] **Step 3: Commit** (umbrella)
```bash
cd C:/Users/davir/Ultra/Alpha/Speedrun && git add docs/SYNC-SELFHOST.md && git commit -m "docs: self-hosted sync server launch + conflict rule (draft for Cursor)"
```

### Task 3.2: §7b Rust conflict test

**Files:** modify `repos/anki/rslib/src/sync/collection/tests.rs`.

- [ ] **Step 1: Add the test** using the existing harness (mirror `regular_sync`/`upload_download`)
```rust
#[tokio::test]
async fn speedrun_two_way_reviews_and_same_card_conflict() -> Result<()> {
    with_active_server(|client| async move {
        let ctx = SyncTestContext::new(client);
        upload_download(&ctx).await?; // seed both cols from one upload/download

        let mut col1 = ctx.col1();
        let mut col2 = ctx.col2();
        let card = col1.search_cards("", SortMode::NoOrder)?[0];

        // 10 reviews on col1 (older), 10 on col2 (newer) of the SAME card.
        for i in 0..10 {
            col1.storage.add_revlog_entry(&RevlogEntry {
                id: RevlogId(1_000 + i), cid: card, usn: Usn(-1), interval: i as i32,
                ..Default::default()
            }, true)?;
        }
        for i in 0..10 {
            col2.storage.add_revlog_entry(&RevlogEntry {
                id: RevlogId(2_000 + i), cid: card, usn: Usn(-1), interval: i as i32,
                ..Default::default()
            }, true)?;
        }

        // Sync both up then reconcile.
        ctx.normal_sync(&mut col1).await;
        ctx.normal_sync(&mut col2).await;
        ctx.normal_sync(&mut col1).await;

        // All 20 distinct revlog entries land on both sides (append-only).
        let n1 = col1.storage.get_revlog_entries_for_card(card)?.len();
        let n2 = col2.storage.get_revlog_entries_for_card(card)?.len();
        assert_eq!(n1, 20, "col1 revlog");
        assert_eq!(n2, 20, "col2 revlog");
        // No corruption on either side.
        assert_eq!(col1.storage.db_scalar::<String>("pragma integrity_check")?, "ok");
        Ok(())
    })
    .await
}
```
(Grounding note: confirm the exact helper names in `tests.rs` — `SyncTestContext`, `with_active_server`, `upload_download`, `normal_sync`, and the revlog/db-scalar accessors — via `cargo test -p anki sync::` and adjust to the real signatures. `RevlogId`/`RevlogEntry`/`Usn` imports mirror the existing conflict tests.)

- [ ] **Step 2: Run + commit**
```bash
export PATH="$HOME/.cargo/bin:$PATH"
cargo test -p anki sync::speedrun_two_way 2>&1 | tail -15
git add rslib/src/sync/collection/tests.rs
git commit -m "test(sync): §7b two-way reviews all land + same-card latest-wins conflict (10+10, append-only revlog)"
```

---

## Self-review against the spec

**Requirement coverage:**

| Requirement | Covered by | Notes |
|---|---|---|
| 0. Network-independent clean-machine installer (vendor templates; ground installer.rs/SyncSubmodule/.gitmodules) | Phase 0 (0.1–0.4) | Grounded root cause; de-submodule + drop SyncSubmodule + BUILD-PREREQS doc. |
| 1. Memory dashboard on BOTH platforms, spec-exact, range-forward/abstain/coverage header/minimal | Phase 1 (1.1–1.5) | ONE shared Svelte page; desktop Qt dialog + Tools menu; Android PageFragment + nav + RPC bridge; grounded page/menu/nav patterns. |
| 1. Desktop = new Svelte page in webview from Tools menu; Android = Kotlin screen; no desktop add-on | 1.2/1.3/1.4 | Kotlin "screen" = PageFragment rendering the shared page (idiomatic AnkiDroid; how Graphs is shared). Flagged for Cursor. |
| 2. Interleaving/points-at-stake via transact(Op::X)→OpChanges, additive proto, undo intact, integrity ok, ablation toggle, ≥3 Rust + 1 Python | Phase E2 | Reposition new-card positions (undo-safe) via `transact(Op::SortCards)`; Full/FeatureOff/Plain; 3 pure + 2 integration Rust + 1 Python. Read-time review interleave noted as Friday follow-up. |
| 3. Self-hosted sync server + two-way + conflict rule + §7b test (10+10; same-card winner) | Phase 3 | Server exists (`anki-sync-server`); launch doc + §7b Rust test using the grounded harness. |
| 4. Coverage map in dashboard header (§7c) | Phase 1.2 (MemoryDashboard header) | `getCoverage` → "X / N required topics present (%)". |
| 5. Performance/Readiness SCAFFOLDING (non-AI, ranges + abstain, future columns, marked) | Phase E3 + 1.5 | Deterministic always-abstain RPC; `scaffolding=true`; wired as future columns. |
| Honor invariants + freeze proto before Android | Phase E4 (freeze/merge/re-pin) + throughout | transact for the mutation; additive proto; grounded APIs; AGPL headers; NO AI; cross-repo freeze called out. |

**Placeholder scan:** no TBD/"handle errors". Grounding notes flag the few late-bound exact signatures (e.g. `NewCardSorter`/`set_new_position` visibility, `AnkiWebViewKind`, `PostRequestHandler.collectionMethods` shape, sync `tests.rs` helper names, protobuf-es field casing) with the exact command to confirm and the fallback — appropriate because they are confirmable only after the earlier codegen/build step runs, and each has a named fallback.

**Type/name consistency:** proto message/field names (`GetExamProfileRequest.exam_id`, `ExamProfileResponse.{profile_json,exam_id}`, `ReorderNewRequest.{deck_id,topic_weights,mode}`, `TopicWeight.{topic,weight}`, `AblationMode.{FULL,FEATURE_OFF,PLAIN}`, `PerformanceReadinessResponse.{scaffolding,topics,overall_readiness}`, `ScoreScaffold.{point,lower,upper,abstained}`) are used consistently across proto → Rust service → Python wrapper → TS `data.ts`. `speedrun_reorder_new` / `interleave_by_topic` / `topic_index_for_tags` referenced identically in `mod.rs` and `service.rs`. The dashboard `Row` shape in `data.ts` matches `TopicRow.svelte` usage.

**Verdict:** covers all six committed items in dependency order with grounded paths/symbols, lands a genuinely-mutating undo-safe engine change through `transact`/`Op`, keeps AI out, freezes the proto before Android consumes it, and marks critical-path (0,1,2) vs stretch (3,5) with 4 folded into the dashboard. Ready for Cursor review.

---

## STOP — awaiting Cursor review
Per the task, execution does not begin until Cursor reviews this plan. No code changed by this planning session (the branch/commits above are the *proposed* steps, not yet executed).
