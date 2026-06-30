# Walking Skeleton → Wednesday MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get our forked Anki building & running on desktop, land one *real* read-only Rust engine change (`SpeedrunService.GetCoverage`) end-to-end through proto→Rust→Python via TDD, then rebuild the same `rslib` into an Android AAR so AnkiDroid runs the identical engine — proven by both apps returning the same backend version string.

**Architecture:** ONE forked `rslib` (Rust core) feeds two bridges — desktop via PyO3 (`pylib/rsbridge`) and Android via the JNI AAR built in the separate `Anki-Android-Backend` (rsdroid) repo. Our change is a new `proto/anki/speedrun.proto` service + a `Collection`-trait impl that reads real collection tag data (read-only, no DB mutation, no transact needed) and reports it plus the engine version. The proto is the frozen contract both bridges generate from, so identical behavior on both platforms is automatic once both link our `rslib`.

**Tech Stack:** Rust 1.92.0 (pinned by `repos/anki/rust-toolchain.toml`); `just` recipes wrapping the cargo `runner` + n2 build (`tools/ninja`); Python 3.9+ via `uv` (auto-managed venv in `out/pyenv`); prost (Rust protobuf), protobuf-es (TS), protobuf-python; Android: cargo-ndk cross-compile → JNI AAR, Gradle, Kotlin. Windows host (MSVC toolchain + MSYS2).

---

## Build-system note (READ FIRST — supersedes older docs)

`repos/anki/CLAUDE.md` is authoritative for the anki repo and mandates **`just` recipes** — *"Do not invoke `./ninja`, `./run`, or scripts under `./tools` directly."* The `justfile` wraps the platform build (`tools\ninja` on Windows → cargo `runner` → n2). Older Speedrun docs (`docs/STATE.md`, `AGENTS.md`, `docs/BUILD-WORKFLOW.md`) still reference `./run` / `./ninja check`; for `repos/anki` those are **superseded** by:

| Need | Command (run inside `repos/anki`) |
|---|---|
| Build + launch desktop Anki | `just run` |
| Build + all checks (lint+test) | `just check` |
| Rust tests only | `just test-rust` |
| Python tests only | `just test-py` |
| Fast Rust iteration (no full build) | `cargo check` |
| Single Rust test module | `cargo test -p anki speedrun::` |
| Format / fix formatting | `just fmt` / `just fix-fmt` |

Exception: `tools/install-n2` is a one-time bootstrap with no `just` recipe — invoking it directly is correct.

All paths below are relative to the workspace root `C:\Users\davir\Ultra\Alpha\Speedrun` unless stated. Commands shown for **Git Bash / MSYS2 bash**; Windows-native equivalents are given where they differ.

---

# Phase 0 — Desktop build green

**Outcome:** `just run` launches our forked Anki and `just check` is green on an unmodified checkout. This is the feasibility gate; do not start Phase 1 until both pass.

### Task 0.1: Install remaining Phase-0 prerequisites (N2, just, MSYS2 rsync)

**Files:** none (environment only).

Already present per `docs/STATE.md`: Rust (rustup, Android targets), JDK 21, uv, Node, yarn 1.22, cargo-ndk, gh, Android Studio, ast-grep, repomix, Serena. Missing: MSYS2 `rsync`, the n2 build tool, and `just`.

- [ ] **Step 1: Install MSYS2 build deps** (Windows path/linker support per `repos/anki/docs/windows.md`)

Run in an **MSYS2 shell** (`C:\msys64\usr\bin\bash.exe`), NOT WSL bash:
```bash
pacman -S --needed --noconfirm git rsync
```
Expected: `git` and `rsync` resolve as installed (no errors).

- [ ] **Step 2: Install n2** (pinned revision; the cargo `runner` drives n2)

Run from `repos/anki` using MSYS2 bash (WSL bash conflicts with MSYS2):
```bash
C:/msys64/usr/bin/bash.exe tools/install-n2
```
This runs `cargo install --git https://github.com/evmar/n2.git --rev 53ec691df749277104d1d4201a344fe4243d6d0a`.
Expected: `Installed package n2 ...` and `n2` on PATH:
```bash
n2 --version   # prints a version, exit 0
```

- [ ] **Step 3: Install just** (the mandated build entry point)

PowerShell:
```powershell
winget install --id Casey.Just -e --accept-source-agreements --accept-package-agreements
```
(Fallback if winget unavailable: `cargo install just`.)
Expected:
```powershell
just --version   # e.g. "just 1.x.y"
```

- [ ] **Step 4: Commit nothing — this is environment setup.** Record completion in the task tracker only.

### Task 0.2: First desktop build & launch

**Files:** none (build artifacts land in `repos/anki/out/`, which is gitignored).

- [ ] **Step 1: Confirm the pinned toolchain resolves**

Run from `repos/anki`:
```bash
rustc --version   # rustup auto-selects 1.92.0 from rust-toolchain.toml
```
Expected: `rustc 1.92.0 (...)`. If rustup reports it's downloading 1.92.0, let it finish.

- [ ] **Step 2: Build and launch Anki** (first build is slow — downloads deps, builds Rust + Python + web)

Run from `repos/anki`:
```bash
just run
```
Expected: the build completes with no error, then the Anki desktop window opens. Web pages are served at `http://localhost:40000/_anki/pages/`. `ANKIDEV` is auto-set (auto-backups disabled) — safe for a throwaway profile.

> If you hit long-path or linker (`LNK`) errors: per `docs/windows.md`, relocate the clone to a short path like `C:\anki` and retry. Our path has no spaces but is deep.

- [ ] **Step 3: Close Anki.** Confirm the process exits cleanly.

### Task 0.3: Baseline checks green + branch

**Files:** none.

- [ ] **Step 1: Run the full check suite on the untouched tree**

Run from `repos/anki`:
```bash
just check
```
Expected: builds pylib + qt, runs Rust/Python/TS lint + tests, exits 0. Note the run time — Phase 1 reuses this command.

- [ ] **Step 2: Create the feature branch** (keep `main` clean; one branch feeds both bridges per invariant "ONE forked anki")

Run from `repos/anki`:
```bash
git checkout -b feat/speedrun-coverage-rpc
git status   # clean, on new branch
```

- [ ] **Step 3: Commit nothing yet.** Phase 0 is verified by green `just run` + `just check`; no source changed.

---

# Phase 1 — `SpeedrunService.GetCoverage` read-only RPC (TDD)

**Outcome:** A new additive proto service + `Collection` impl that computes topic **coverage** (how many required exam-profile topic tags are present in the collection, by hierarchical-prefix match) and returns the engine version. ≥3 Rust unit tests + 1 Python-calling integration test, all green. `PRAGMA integrity_check = ok`. Read-only ⇒ no `transact`, no `Op`, trivially undo-safe.

**Why this is a *real* change, not a no-op:** it reads live collection tag state through `Collection`/`storage`, implements genuine hierarchical-tag coverage logic (the PRD §3 taxonomy / §5 coverage signal), and is the exact read-RPC seam the walking skeleton requires (`ARCHITECTURE.md` step 2, PRD §10.2).

### File structure for this phase

- Create `repos/anki/proto/anki/speedrun.proto` — the frozen contract (messages + the two paired services).
- Create `repos/anki/rslib/src/speedrun/mod.rs` — module root + pure `coverage()` function + `#[cfg(test)]` unit tests.
- Create `repos/anki/rslib/src/speedrun/service.rs` — `impl crate::services::SpeedrunService for Collection`.
- Modify `repos/anki/rslib/src/lib.rs` — register `pub mod speedrun;`.
- Create `repos/anki/pylib/anki/speedrun.py` — clean Python wrapper (`SpeedrunManager`).
- Modify `repos/anki/pylib/anki/collection.py` — expose `col.speedrun`.
- Create `repos/anki/pylib/tests/test_speedrun.py` — Python integration test (drives the real backend).

> **Invariant reminders (AGENTS.md):** proto fields are append-only with NEW numbers; never edit generated files (`*_pb2.py`, `_backend_generated.py`, `@generated/*`); read-only methods need no `transact`. Tests in this plan are written by the implementer here, but once committed they are READ-ONLY (never weaken to pass).

### Task 1.1: Define the proto contract (additive, paired services)

**Files:**
- Create: `repos/anki/proto/anki/speedrun.proto`

- [ ] **Step 1: Write the proto file**

```proto
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

syntax = "proto3";

option java_multiple_files = true;

package anki.speedrun;

// Speedrun read-only analytics. Read-only: no collection mutation, no undo.
service SpeedrunService {
  // Report how many of the supplied exam-profile topic tags are present in the
  // collection (hierarchical prefix match), plus the engine version string.
  rpc GetCoverage(GetCoverageRequest) returns (CoverageResponse);
}

// Required: get_services() asserts one Backend<Name>Service per <Name>Service.
// Empty body => all SpeedrunService methods auto-delegate to the collection impl.
service BackendSpeedrunService {}

message GetCoverageRequest {
  // Exam-profile topic tags to check for, e.g. "calc", "calc::integration".
  repeated string required_tags = 1;
}

message CoverageResponse {
  // Number of required_tags present in the collection (by prefix match).
  uint32 covered = 1;
  // Total number of required_tags supplied.
  uint32 total = 2;
  // covered / total * 100, or 0.0 when total == 0.
  double percent = 3;
  // rslib version (crate::version::version()); proves which engine answered.
  string backend_version = 4;
}
```

- [ ] **Step 2: Verify the proto is syntactically discovered by the codegen** (proto files are auto-gathered via `read_dir` in `rslib/proto/rust.rs`; no manifest edit needed)

Run from `repos/anki`:
```bash
cargo check -p anki_proto 2>&1 | tail -20
```
Expected: compiles (the generated Rust types `anki_proto::speedrun::*` and the `SpeedrunService` trait now exist). If `get_services` panics with `missing associated service` or an `assert_eq!` length mismatch, the `BackendSpeedrunService {}` line is missing — re-add it.

- [ ] **Step 3: Commit the contract**

```bash
git add proto/anki/speedrun.proto
git commit -m "feat(speedrun): add additive SpeedrunService.GetCoverage proto contract"
```

### Task 1.2: RED — failing Rust unit tests for the pure coverage function

**Files:**
- Create: `repos/anki/rslib/src/speedrun/mod.rs` (tests only in this task)

- [ ] **Step 1: Write the module with ONLY the failing tests** (the `coverage` fn does not exist yet → compile-error RED)

```rust
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

pub(crate) mod service;

#[cfg(test)]
mod test {
    use super::coverage;

    fn strs(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn all_required_present_counts_full() {
        let all = strs(&["calc::integration", "linear_algebra::eigen"]);
        let required = strs(&["calc", "linear_algebra"]);
        assert_eq!(coverage(&all, &required), (2, 2));
    }

    #[test]
    fn partial_coverage_counts_present_only() {
        let all = strs(&["calc::integration"]);
        let required = strs(&["calc", "linear_algebra", "abstract_algebra"]);
        assert_eq!(coverage(&all, &required), (1, 3));
    }

    #[test]
    fn prefix_matches_descendants_but_not_substrings() {
        // "calc" is covered by "calc" or "calc::*", but NOT by "calculus_tricks".
        let all = strs(&["calculus_tricks", "calc::limits"]);
        assert_eq!(coverage(&all, &strs(&["calc"])), (1, 1));
        // Exact, no descendants.
        let all_exact = strs(&["calc"]);
        assert_eq!(coverage(&all_exact, &strs(&["calc"])), (1, 1));
        // Empty required => zero of zero.
        assert_eq!(coverage(&all_exact, &[]), (0, 0));
    }
}
```

- [ ] **Step 2: Register the module so it compiles** — modify `repos/anki/rslib/src/lib.rs`

Insert `pub mod speedrun;` between the existing `pub mod services;` and `mod stats;` lines (alphabetical order):
```rust
pub mod services;
pub mod speedrun;
mod stats;
```

- [ ] **Step 3: Run the tests to verify they FAIL (compile error)**

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -20
```
Expected: FAIL — `cannot find function 'coverage' in this scope` (or unresolved import `super::coverage`). This is the RED state.

### Task 1.3: GREEN — implement the pure coverage function

**Files:**
- Modify: `repos/anki/rslib/src/speedrun/mod.rs`

- [ ] **Step 1: Add the `coverage` function above the test module**

Insert directly after the `pub(crate) mod service;` line:
```rust
/// Count how many `required` topic tags are present among the collection's
/// `all_tags`. A required tag `t` is "present" if any collection tag equals `t`
/// or is a hierarchical descendant `t::...` (Anki uses `::` for tag hierarchy).
/// Returns `(covered, total)`.
pub(crate) fn coverage(all_tags: &[String], required: &[String]) -> (u32, u32) {
    let total = required.len() as u32;
    let covered = required
        .iter()
        .filter(|req| {
            let prefix = format!("{req}::");
            all_tags
                .iter()
                .any(|t| t.as_str() == req.as_str() || t.starts_with(&prefix))
        })
        .count() as u32;
    (covered, total)
}
```

- [ ] **Step 2: Run the unit tests to verify they PASS**

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -20
```
Expected: `test result: ok. 3 passed; 0 failed` for the `speedrun::test` module.

- [ ] **Step 3: Commit**

```bash
git add rslib/src/speedrun/mod.rs rslib/src/lib.rs
git commit -m "feat(speedrun): pure hierarchical-tag coverage fn + unit tests (3)"
```

### Task 1.4: RED — failing Rust integration test against a real Collection

**Files:**
- Modify: `repos/anki/rslib/src/speedrun/mod.rs` (add a 4th test using `Collection`)

- [ ] **Step 1: Add an end-to-end Rust test inside the existing `mod test`**

Add these imports at the top of `mod test` (below `use super::coverage;`):
```rust
    use crate::collection::Collection;
    use crate::decks::DeckId;
    use crate::error::Result;
    use crate::services::SpeedrunService;
```

Add this test inside `mod test`:
```rust
    #[test]
    fn get_coverage_reads_live_collection_tags() -> Result<()> {
        let mut col = Collection::new();

        // No notes yet => nothing covered, version present.
        let resp = col.get_coverage(anki_proto::speedrun::GetCoverageRequest {
            required_tags: strs(&["calc", "linear_algebra"]),
        })?;
        assert_eq!(resp.total, 2);
        assert_eq!(resp.covered, 0);
        assert_eq!(resp.percent, 0.0);
        assert!(!resp.backend_version.is_empty());

        // Add a note tagged calc::integration.
        let nt = col.get_notetype_by_name("Basic")?.unwrap();
        let mut note = nt.new_note();
        col.add_note(&mut note, DeckId(1))?;
        note.tags = vec!["calc::integration".into()];
        col.update_note(&mut note)?;

        let resp = col.get_coverage(anki_proto::speedrun::GetCoverageRequest {
            required_tags: strs(&["calc", "linear_algebra"]),
        })?;
        assert_eq!(resp.covered, 1);
        assert_eq!(resp.total, 2);
        assert!((resp.percent - 50.0).abs() < 1e-9);
        Ok(())
    }
```

- [ ] **Step 2: Run to verify FAIL** (the trait method `get_coverage` is not implemented for `Collection` yet)

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -25
```
Expected: FAIL — `no method named 'get_coverage' found for struct 'Collection'` / unresolved `SpeedrunService` impl. RED state.

### Task 1.5: GREEN — implement the `SpeedrunService` trait on `Collection`

**Files:**
- Create: `repos/anki/rslib/src/speedrun/service.rs`

- [ ] **Step 1: Write the service impl** (mirrors `rslib/src/tags/service.rs` `all_tags`; reads `self.storage.all_tags()`)

```rust
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

use crate::collection::Collection;
use crate::error;

impl crate::services::SpeedrunService for Collection {
    fn get_coverage(
        &mut self,
        input: anki_proto::speedrun::GetCoverageRequest,
    ) -> error::Result<anki_proto::speedrun::CoverageResponse> {
        let all_tags: Vec<String> = self
            .storage
            .all_tags()?
            .into_iter()
            .map(|t| t.name)
            .collect();
        let (covered, total) = crate::speedrun::coverage(&all_tags, &input.required_tags);
        let percent = if total == 0 {
            0.0
        } else {
            (covered as f64) / (total as f64) * 100.0
        };
        Ok(anki_proto::speedrun::CoverageResponse {
            covered,
            total,
            percent,
            backend_version: crate::version::version().to_string(),
        })
    }
}
```

- [ ] **Step 2: Run the full speedrun test module to verify GREEN**

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -25
```
Expected: `test result: ok. 4 passed; 0 failed`.

- [ ] **Step 3: Confirm clippy is clean on the new code**

```bash
cargo clippy -p anki 2>&1 | grep -i "warning\|error" | grep -i speedrun || echo "no speedrun clippy issues"
```
Expected: `no speedrun clippy issues`.

- [ ] **Step 4: Commit**

```bash
git add rslib/src/speedrun/service.rs rslib/src/speedrun/mod.rs
git commit -m "feat(speedrun): implement read-only GetCoverage on Collection + integration test (4 Rust tests)"
```

### Task 1.6: Regenerate cross-language bindings (full build)

**Files:** none edited by hand (generated files land in `out/`, gitignored).

- [ ] **Step 1: Run a full build so prost regenerates the Rust trait dispatch and the Python `_backend_generated.py` gains `get_coverage`**

Run from `repos/anki`:
```bash
just check
```
Expected: exits 0. `.proto` changes require a full build (per `repos/anki/CLAUDE.md`); `just check` builds pylib + qt then runs all checks. The generated Python method is `RustBackend.get_coverage(required_tags=...)`.

- [ ] **Step 2: Confirm the generated Python method exists** (read-only inspection of generated output; do not edit)

```bash
grep -n "def get_coverage" out/pylib/anki/_backend_generated.py
```
Expected: one match — a generated `def get_coverage(self, *, required_tags...)` method.

### Task 1.7: RED — failing Python integration test (drives the real backend)

**Files:**
- Create: `repos/anki/pylib/tests/test_speedrun.py`

- [ ] **Step 1: Write the integration test** (uses the not-yet-existing `col.speedrun` wrapper → RED)

```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.decks import DeckId
from tests.shared import getEmptyCol


def test_coverage_rpc_end_to_end():
    col = getEmptyCol()
    try:
        # Empty collection => nothing covered, but the engine answers with a version.
        resp = col.speedrun.coverage(["calc", "linear_algebra"])
        assert resp.total == 2
        assert resp.covered == 0
        assert resp.percent == 0.0
        assert resp.backend_version  # non-empty proves OUR rslib answered

        # Add a note tagged calc::integration.
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"] = "integral of 1/x"
        note["Back"] = "ln|x| + C"
        note.tags = ["calc::integration"]
        col.add_note(note, DeckId(1))

        resp = col.speedrun.coverage(["calc", "linear_algebra"])
        assert resp.covered == 1
        assert resp.total == 2
        assert abs(resp.percent - 50.0) < 1e-9

        # No-corruption gate (read-only RPC must not have touched the DB).
        assert col.db.scalar("pragma integrity_check") == "ok"
    finally:
        col.close()
```

- [ ] **Step 2: Run to verify FAIL**

Run from `repos/anki`:
```bash
just test-py 2>&1 | grep -A3 test_speedrun
```
Expected: FAIL — `AttributeError: 'Collection' object has no attribute 'speedrun'`. RED state.

### Task 1.8: GREEN — clean Python wrapper + expose on Collection

**Files:**
- Create: `repos/anki/pylib/anki/speedrun.py`
- Modify: `repos/anki/pylib/anki/collection.py`

- [ ] **Step 1: Write the wrapper** (mirrors `pylib/anki/tags.py` `TagManager`; never call `col._backend.*` from app code directly)

```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Speedrun read-only analytics wrapper over the Rust SpeedrunService."""

from __future__ import annotations

import anki
import anki.collection
from anki import speedrun_pb2

# public export
CoverageResponse = speedrun_pb2.CoverageResponse


class SpeedrunManager:
    def __init__(self, col: anki.collection.Collection) -> None:
        self.col = col.weakref()

    def coverage(self, required_tags: list[str]) -> CoverageResponse:
        """How many of required_tags are present in the collection (prefix match),
        plus the engine version string."""
        return self.col._backend.get_coverage(required_tags=required_tags)
```

- [ ] **Step 2: Import and instantiate on `Collection`** — modify `repos/anki/pylib/anki/collection.py`

(a) Add the import next to the other manager imports (near `from anki.tags import TagManager`, ~line 87):
```python
from anki.speedrun import SpeedrunManager
```
(b) Instantiate it next to the others in `Collection.__init__` (right after `self.tags = TagManager(self)`, ~line 160):
```python
        self.tags = TagManager(self)
        self.speedrun = SpeedrunManager(self)
```

- [ ] **Step 3: Run the Python integration test to verify GREEN**

Run from `repos/anki`:
```bash
just test-py 2>&1 | grep -A3 test_speedrun
```
Expected: `test_speedrun.py::test_coverage_rpc_end_to_end PASSED` (exit 0).

- [ ] **Step 4: Commit**

```bash
git add pylib/anki/speedrun.py pylib/anki/collection.py pylib/tests/test_speedrun.py
git commit -m "feat(speedrun): Python SpeedrunManager wrapper + integration test (undo-safe, integrity_check ok)"
```

### Task 1.9: REFACTOR + full verification gate

**Files:** none (verification only; refactor inline if needed).

- [ ] **Step 1: Format**

Run from `repos/anki`:
```bash
just fmt
```
Expected: exit 0 (no formatting diffs). If it reports changes, run `just fix-fmt`, re-review the diff, and amend.

- [ ] **Step 2: Full green gate** (the BUILD-WORKFLOW §5 "done" definition for the Rust change)

Run from `repos/anki`:
```bash
just check
```
Expected: exit 0 — Rust (≥4 speedrun tests), Python (integration test), TS, lint all pass.

- [ ] **Step 3: Re-assert no-corruption / additive-proto invariants held**
  - Read-only RPC: confirm `rslib/src/speedrun/service.rs` contains no `transact`, no DB writes, no `Op` — it only reads `self.storage.all_tags()`. ✅ by construction.
  - Proto: confirm `speedrun.proto` only *added* messages/services and used field numbers 1–4 on new messages (no renumber/reuse). ✅
  - Integrity: the Python test already asserts `pragma integrity_check == "ok"`. ✅

- [ ] **Step 4: Push the branch to the fork** (needed so the Android submodule can reference this exact commit in Phase 2)

```bash
git push -u origin feat/speedrun-coverage-rpc
git rev-parse HEAD   # record this SHA -> used in Task 2.1
```
Expected: branch pushed to `spinkicks/anki`; note the HEAD SHA.

---

# Phase 2 — One engine, two apps (rebuild AAR from our `rslib`)

**Outcome:** AnkiDroid runs an AAR cross-compiled from OUR forked `rslib` (the one with `SpeedrunService`), and a Kotlin call to `get_coverage` returns the **same `backend_version` string** the desktop build reports. This is the "one engine, two apps" milestone (`ARCHITECTURE.md` step 5, BUILD-WORKFLOW §5).

> **This is the #1 schedule risk (rsdroid build chain).** Several values (NDK version) must be read from the repo at build time, not assumed. Each task includes the grounding command. Emulator (x86_64) is acceptable for the gate.

### Current state (grounded 2026-06-29)
- `repos/Anki-Android-Backend` is cloned; its `anki` submodule points at **upstream `ankitects/anki`** and is **uninitialized** (`git submodule status` shows a leading `-`). We must point it at our fork's Phase-1 commit.
- rsdroid `gradle.properties`: `VERSION_NAME=0.1.65-anki26.05b1`.
- Android Rust targets + cargo-ndk already installed per `docs/STATE.md`; NDK itself is installed via Android Studio.

### Task 2.1: Point the rsdroid `anki` submodule at our forked engine

**Files:**
- Modify: `repos/Anki-Android-Backend/.gitmodules`
- Submodule checkout: `repos/Anki-Android-Backend/anki`

- [ ] **Step 1: Repoint the submodule URL to our fork**

Run from `repos/Anki-Android-Backend`:
```bash
git config -f .gitmodules submodule.anki.url https://github.com/spinkicks/anki
git submodule sync
git submodule update --init --recursive
```
Expected: the `anki/` submodule populates from `spinkicks/anki`.

- [ ] **Step 2: Check out the exact Phase-1 commit inside the submodule**

Run from `repos/Anki-Android-Backend`, using the SHA recorded in Task 1.9 Step 4:
```bash
cd anki
git fetch origin feat/speedrun-coverage-rpc
git checkout <PHASE1_HEAD_SHA>
git log --oneline -1   # confirms the SpeedrunService commit is checked out
test -f proto/anki/speedrun.proto && echo "speedrun.proto present in submodule"
cd ..
```
Expected: submodule HEAD is our Phase-1 commit; `speedrun.proto present in submodule`.

- [ ] **Step 3: Match the submodule's Rust toolchain**

Run from `repos/Anki-Android-Backend`:
```bash
cat anki/rust-toolchain.toml   # expect channel = "1.92.0"
cat rust-toolchain.toml 2>/dev/null || echo "(rsdroid uses submodule toolchain)"
```
Expected: the anki submodule pins 1.92.0; ensure rsdroid's own `rust-toolchain.toml` (if present) does not conflict. If it pins a different channel, align it to `1.92.0`.

- [ ] **Step 4: Commit the submodule pointer**

```bash
git add .gitmodules anki
git commit -m "build(rsdroid): point anki submodule at Speedrun fork w/ SpeedrunService"
```

### Task 2.2: Install/confirm the exact NDK + Android Rust targets

**Files:** none (toolchain).

- [ ] **Step 1: Ground the required NDK version from the repo** (do NOT hardcode)

Run from the workspace root:
```bash
grep -rin "ndk" repos/anki-android/gradle/libs.versions.toml repos/Anki-Android-Backend/build.gradle.kts repos/Anki-Android-Backend/build-rust.gradle 2>/dev/null
```
Record the resolved NDK version string (e.g. `27.x.y`). If absent from `libs.versions.toml`, check `repos/Anki-Android-Backend/gradle.properties` and the rsdroid `README.md`.

- [ ] **Step 2: Install that NDK**

```bash
sdkmanager --install "ndk;<RESOLVED_NDK_VERSION>"
```
Expected: NDK installed under the Android SDK `ndk/<version>/`.

- [ ] **Step 3: Confirm the 4 Android Rust targets + cargo-ndk are present**

```bash
rustup target add aarch64-linux-android x86_64-linux-android armv7-linux-androideabi i686-linux-android
cargo ndk --version
```
Expected: targets report "installed/up to date"; `cargo ndk` prints a version. ABI→jniLibs mapping (must be exact): `aarch64-linux-android→arm64-v8a`, `armv7a-linux-androideabi→armeabi-v7a`, `i686-linux-android→x86`, `x86_64-linux-android→x86_64`.

### Task 2.3: Build the AAR from our `rslib` (build.sh BEFORE cargo check)

**Files:** produces `repos/Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`.

- [ ] **Step 1: Run the rsdroid build script FIRST** (generates submodule artifacts; running `cargo check` before this fails with "path not found")

Run from `repos/Anki-Android-Backend`. On Windows use `build.bat`:
```bash
cmd.exe /c build.bat
```
(MSYS2/Linux equivalent: `./build.sh`.) Expected: cross-compiles the `.so` for the configured ABIs and generates Kotlin protobuf, producing the release AAR. First build is slow.

- [ ] **Step 2: Confirm the AAR exists**

```bash
ls -la rsdroid/build/outputs/aar/rsdroid-release.aar
```
Expected: the file exists with a recent timestamp.

> Troubleshooting: relocation/ELF errors ⇒ cargo-ndk linker not used (check NDK env). Banned cross-compile traps: OpenSSL / vendored C deps — our `rslib` uses rustls, so this should not arise.

### Task 2.4: Wire AnkiDroid to the local AAR + version alignment

**Files:**
- Create/modify: `repos/anki-android/local.properties`
- Verify: `repos/anki-android/Anki-Android/build.gradle` (`ext.ankidroid_backend_version`) vs `repos/Anki-Android-Backend/gradle.properties` (`VERSION_NAME`)

- [ ] **Step 1: Align the backend version strings** (UnsatisfiedLinkError / version-mismatch guard)

Run from the workspace root:
```bash
grep -i "VERSION_NAME" repos/Anki-Android-Backend/gradle.properties           # expect 0.1.65-anki26.05b1
grep -rin "ankidroid_backend_version\|ankiBackend" repos/anki-android/Anki-Android/build.gradle repos/anki-android/gradle/libs.versions.toml
```
Ensure AnkiDroid's expected backend version equals rsdroid's `VERSION_NAME`. If they differ, set AnkiDroid's `ext.ankidroid_backend_version` (or the `ankiBackend` value in `libs.versions.toml`) to match `0.1.65-anki26.05b1`.

- [ ] **Step 2: Enable the local backend**

Append to `repos/anki-android/local.properties` (create if absent):
```properties
local_backend=true
```
This makes AnkiDroid consume `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar` (per `AnkiDroid/build.gradle` + `buildSrc/.../BackendDependencies.kt`).

- [ ] **Step 3: Commit the AnkiDroid wiring** (local.properties is usually gitignored — commit only if tracked; otherwise record the change in the task tracker)

```bash
cd repos/anki-android && git status --short local.properties
```

### Task 2.5: GATE — AnkiDroid calls `get_coverage`; assert matching backend version

**Files:**
- Create: a minimal Kotlin wrapper in `repos/anki-android/libanki/` (mirror an existing `libanki` backend call), invoked from a debug entry point or an instrumentation/unit test.

- [ ] **Step 1: Ground the Kotlin backend-call pattern**

Run from `repos/anki-android`:
```bash
grep -rin "fun all_tags\|allTags\|backend\." libanki/src/main/java/anki/ 2>/dev/null | head
```
Locate how `libanki` exposes a generated backend RPC (the Kotlin backend has a generated `getCoverage(...)` from the same proto). Mirror that pattern.

- [ ] **Step 2: Add a Kotlin call + assertion** (in a `libanki` instrumentation test or a debug action — keep it minimal)

Pseudocode contract to implement against the generated Kotlin API:
```kotlin
// Calls the SAME engine RPC the desktop uses.
val resp = backend.getCoverage(requiredTags = listOf("calc", "linear_algebra"))
val androidVersion = resp.backendVersion
// DESKTOP_VERSION is the string desktop returned in Phase 1 (== contents of repos/anki/.version, "26.05").
check(androidVersion == DESKTOP_VERSION) {
    "engine mismatch: android=$androidVersion desktop=$DESKTOP_VERSION"
}
```
Where `DESKTOP_VERSION` is obtained from the desktop run (Task 1.7 asserts `resp.backend_version` is non-empty; print it once and confirm it equals `repos/anki/.version` = `26.05`).

- [ ] **Step 3: Build & run AnkiDroid against the local AAR (emulator OK)**

Run from `repos/anki-android`:
```bash
./gradlew :AnkiDroid:assembleDebug
```
Then launch on an x86_64 emulator (Android Studio AVD) and trigger the coverage call.
Expected: the app launches loading our engine; the `get_coverage` call returns `backend_version == "26.05"` (same as desktop) — the assertion passes. **This is the one-engine-two-apps gate.**

- [ ] **Step 4: Commit the Kotlin wrapper/test**

```bash
git add libanki/ Anki-Android/
git commit -m "test(speedrun): AnkiDroid calls SpeedrunService.GetCoverage; assert backend version == desktop (one engine, two apps)"
```

---

## Self-review against `docs/PRD.md`

**Spec coverage (Phases 0–2 scope only — Friday/Sunday items are intentionally out):**

| PRD requirement | Covered by | Notes |
|---|---|---|
| §10.1 Desktop forked Anki builds & runs; checks green | Phase 0 (Tasks 0.1–0.3) | `just run` + `just check`. |
| §10.2 / §4B Read-only RPC end-to-end (proto→Rust→Python) | Phase 1 (Tasks 1.1–1.8) | `SpeedrunService.GetCoverage`; PRD names `GetCoverage` as the Wed RPC. |
| §1 "real change to Anki's Rust backend" (50% cap risk) | Phase 1 | New `rslib` module + service reading live collection state — not a constant. |
| §8 ≥3 Rust unit + 1 Python integration test | Tasks 1.2/1.3 (3 unit) + 1.4/1.5 (1 Rust integration) + 1.7/1.8 (1 Python integration) | 4 Rust + 1 Python; exceeds the floor. |
| §3 hierarchical taxonomy (`calc::single_var::integration`) | Task 1.3 `coverage()` prefix logic | `::` descendant match implements the tag DAG membership read. |
| §5 coverage % vs exam profile | `CoverageResponse.percent` | Coverage is the Wed-scoped honest signal (readiness is Fri). |
| §4 additive protobuf, never renumber | Task 1.1 + 1.9 Step 3 | New file, field numbers 1–4 on new messages only. |
| §11.4 / invariant: no corruption, undo intact | Read-only by construction + `pragma integrity_check` assert (Task 1.7) | No `transact`/`Op` needed for a read RPC. |
| §10.5 / §2 Rebuild AAR from forked rslib; `local_backend=true`; same engine | Phase 2 (Tasks 2.1–2.5) | Submodule repointed to our fork; version-string gate. |
| §9 cargo-ndk / NDK alignment runbook | Tasks 2.2–2.4 | NDK version grounded at build time; ABI→jniLibs mapping stated. |
| §11.1 rsdroid build chain de-risked first | Phase 2 ordering (build.sh before cargo check; AAR before Kotlin) | Matches `repos/Anki-Android-Backend/AGENTS.md`. |

**Explicitly deferred (NOT in this plan, per cadence + STEP-3 scope):** §7 self-hosted sync server & two-way sync (Friday — Wed only needs both apps reviewing the same deck), §5 Performance/Readiness scores (Friday), §6 AI/RAG content pipeline (Friday — *no AI before Wednesday* is a hard spec rule), §8 3-build ablation + held-out evals (Sunday). The queue-ordering Rust change (PRD §4A, the *mutating* `intersperser`/`sorting` work) is deferred to the Friday plan; this walking skeleton deliberately lands the **read-only** RPC first to prove the seam with zero corruption risk.

**Placeholder scan:** No TBD/TODO/"handle errors"/"similar to" — every code step shows full content; every command shows expected output. The only intentionally late-bound values are Phase-2 build-time facts (NDK version, the Phase-1 commit SHA, the Kotlin generated-API exact signature), each with an explicit grounding command rather than a guess — appropriate because they cannot be known until earlier tasks run.

**Type/name consistency:** `coverage(all_tags, required) -> (u32, u32)` is referenced identically in `mod.rs` (Task 1.3) and `service.rs` (Task 1.5). Proto message/field names (`GetCoverageRequest.required_tags`, `CoverageResponse.{covered,total,percent,backend_version}`) match across proto (1.1), Rust impl (1.5), Rust test (1.4), Python wrapper (1.8), Python test (1.7), and Kotlin gate (2.5). `col.speedrun.coverage(...)` is defined in 1.8 and used in 1.7. Service pairing (`SpeedrunService` + `BackendSpeedrunService {}`) satisfies the `get_services` length assertion.

**Verdict:** The plan fully covers the Phase 0–2 walking-skeleton requirements of the PRD with grounded paths/symbols, lands a genuine (not no-op) read-only engine change via strict Red→Green→Refactor→Commit TDD, honors all hard invariants (additive proto, no transact for reads, integrity_check gate, one forked engine feeding both bridges), and stops exactly at the Wednesday MVP line (no AI, no sync, no scores beyond coverage).
