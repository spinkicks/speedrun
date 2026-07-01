# Wednesday MVP (remaining deliverables) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **STATUS: ✅ EXECUTED & MERGED (2026-06-30/07-01).** All phases complete on `feat/speedrun-wed-mvp`, FF-merged to anki `main` @ `92f4ebd` (13 commits over `b8b5369`). Execution corrections: Briefcase templates turned out to be git submodules (fixed via SyncSubmodule init — later superseded by wed-plus vendoring); Windows fixes (`render.rs` OS-separator, out-of-tree uv venv) folded in. Historical document — kept for the record.

**Goal:** Complete the remaining Wednesday MVP items on top of the finished walking skeleton (Phases 0–2): (1) a topic-tagged GRE calc+LA seed deck + exam-profile config + a deterministic open-licensed scraper, (2) a read-only `SpeedrunService.GetTopicMastery` RPC that surfaces an honest per-topic memory score with a Wilson range + abstain rule, (3) a fixed clean-machine Briefcase installer, (4) the §7a "why Rust not Python" + upstream-files artifacts, and (5) the four proof recordings — all with **NO AI** (hard spec rule for Wednesday).

**Architecture:** Content is data that rides in the synced collection (`Speedrun::Declarative` notes with hierarchical `calc::…` / `linear_algebra::…` tags + a `Source` field) plus a collection-config exam-profile JSON (topic taxonomy/DAG + ETS weights); it is authored by a standalone deterministic Python toolchain in the `repos/anki` fork under a new isolated `speedrun/` directory (zero upstream files touched → trivial future merge). The memory model is an **additive** read-only RPC method added to the existing `SpeedrunService` (landed at `b8b5369`): a new `GetTopicMastery` that reads live FSRS retrievability per topic, aggregates it, and returns a Wilson 95% interval on the mastered proportion plus an abstain flag — read-only, so no `transact`/`Op`, no corruption risk. Cursor owns the Svelte/TS dashboard; this plan stops at a clean data seam (proto RPC + Python wrapper).

**Tech Stack:** Rust 1.92.0 (`rslib`; `fsrs` crate already a dependency); prost/protobuf-es/protobuf-python codegen via `just`; Python 3.9+ via `uv`; `genanki` (pinned) + `pyyaml` for deterministic `.apkg` authoring; Briefcase (vendored cookiecutter templates) for the desktop installer. Windows host (MSVC + MSYS2); builds via `just` recipes inside `repos/anki`.

---

## Build-system note (READ FIRST)

All `repos/anki` builds/checks go through **`just` recipes** (per `repos/anki/CLAUDE.md` — do not invoke `./ninja`/`./run`/`./tools/*` directly). Commands below are for **MSYS2 bash** unless a PowerShell block is shown; Windows-native equivalents are given where they differ.

| Need | Command (inside `repos/anki`) |
|---|---|
| Build + all checks | `just check` |
| Rust tests only | `just test-rust` |
| Python tests only | `just test-py` |
| Fast Rust iteration | `cargo check` |
| Single Rust test module | `cargo test -p anki speedrun::` |
| Format | `just fmt` / `just fix-fmt` |

**Commit target:** ALL code lands on the **forks in `repos/`** (`spinkicks/anki` mainly; nothing in this plan touches the Android forks). Strategy/writeup docs (§7a) land in the **private umbrella** `docs/` (per the STATE.md repo boundary — strategy docs stay OUT of the public forks). Never push AGENTS.md/strategy to the public forks.

**Invariants honored throughout (AGENTS.md):** additive proto with NEW field numbers, never renumber/reuse; read-only RPCs need no `transact`; ground every API via Serena/ast-grep/`cargo check` before editing; AGPL-3.0-or-later headers on every new source file; **NO AI / no model calls anywhere in this plan**.

**Grounding already done (2026-06-30/07-01, recorded so the implementer trusts the code below):**
- Retrievability: `fsrs::FSRS::new(None).unwrap().current_retrievability_seconds(state.into(), seconds_elapsed, decay)` — pattern from `rslib/src/stats/graphs/retrievability.rs:34` and `rslib/src/stats/card.rs:56`.
- Card fields (all `pub(crate)`, in-crate usable): `Card.memory_state: Option<FsrsMemoryState>` (`rslib/src/card/mod.rs:96`), `Card.decay: Option<f32>` (`:98`), `Card::note_id()` (`:162`), `Card::seconds_since_last_review(&SchedTimingToday) -> Option<u32>` (`rslib/src/browser_table.rs:132`).
- Default decay constant: `fsrs::FSRS5_DEFAULT_DECAY`.
- Graded-review filter: `RevlogEntry::has_rating_and_affects_scheduling()` (`rslib/src/revlog/mod.rs:126`); revlog fetch: `self.storage.get_revlog_entries_for_card(cid)` (used in `rslib/src/stats/card.rs:29`).
- Card-by-tag enumeration: `Collection::search_cards<N>(search, SortMode) -> Result<Vec<CardId>>` (`rslib/src/search/mod.rs:158`); card fetch `self.storage.get_card(cid)`.
- Timing: `self.timing_today()?` (`rslib/src/stats/card.rs:32`).
- Existing service seam (from Phase 1): `proto/anki/speedrun.proto`, `rslib/src/speedrun/{mod.rs,service.rs}`, `rslib/proto/src/lib.rs` has `protobuf!(speedrun, "speedrun");`, `pylib/anki/speedrun.py` (`SpeedrunManager`), `col.speedrun`.
- Installer (**CORRECTED via grounding 2026-07-01 — supersedes the original hypothesis**): the "template-clone failure" is an **uninitialized git submodule**, NOT a Briefcase/beeware network clone. `qt/installer/windows-template` and `qt/installer/mac-template` are **git submodules** (`.gitmodules`: win→`https://github.com/ankitects/briefcase-windows-app-template` branch `anki`; mac→`https://github.com/ankitects/briefcase-macOS-app-template` branch `anki`), both currently **uninitialized** (`git submodule status` shows a leading `-`: win `e995756449d4b4de27365c5c97b5c571d141ea08`, mac `8ef2200fb3f94f180faddd9fdc8b6ea251110910`). The installer build (`build/configure/src/installer.rs` → `SyncSubmodule { path: "qt/installer/windows-template", offline_build: false }`, lines 54-66; driven by `qt/tools/build_installer.py`) tries to sync these submodules and fails when they can't be populated. `linux-template/` is the odd one out — it is vendored **in-tree** (real files, NOT a submodule), which is why it never fails. **Fix direction:** initialize the pinned submodules (Option A) and, if a clean/offline machine can't clone them at build time, vendor the Windows template in-tree like linux (Option B). The `[tool.briefcase.app.anki.windows]` pyproject key is NOT the lever.

---

## Critical-path vs flex

| Phase | Item | Priority |
|---|---|---|
| A1 | Exam-profile JSON (taxonomy/DAG + ETS weights) | **CRITICAL** |
| A2 | Hand-authored calc+LA seed deck (`.apkg`) | **CRITICAL** (satisfies "exam deck" alone) |
| A3 | Deterministic open-licensed scraper | **FLEX** (skip/trim if it runs long; A2 already unblocks the review loop) |
| B | `GetTopicMastery` RPC + honest score/range/abstain | **CRITICAL** |
| C | Clean-machine installer fix | **CRITICAL** (50%-cap risk if a clean device can't run) |
| D | §7a artifacts | **CRITICAL** (low effort; feeds the 20% Rust-fit rubric) |
| E | Proof recordings | **CRITICAL** |

Recommended execution order: **A1 → A2 → B → C → D → E**, with **A3 slotted in only if time remains before Wednesday** (it is the sole FLEX item). A2 (curated deck) alone satisfies "both apps review the same deck," so B/C/D/E never block on the scraper.

---

## File structure

**New isolated directory in the `repos/anki` fork (zero upstream files touched — clean merge boundary):**
```
repos/anki/speedrun/                       # our namespace; NOT shipped in the wheel
  README.md                                # what this is, how to run, license
  pyproject.toml                           # uv project: genanki + pyyaml (pinned), dev-only
  exam_profiles/
    schema.md                              # documents the exam-profile JSON contract
    gre_math.json                          # taxonomy/DAG + ETS content weights (A1)
  seed/
    cards_calc.yaml                        # hand-authored declarative cards (A2)
    cards_linear_algebra.yaml              # hand-authored declarative cards (A2)
    build_seed_deck.py                     # deterministic YAML -> .apkg builder (A2)
  scraper/                                 # FLEX (A3)
    topic_rules.yaml                       # keyword -> topic-tag rules (rule-based)
    scrape_openstax.py                     # deterministic HTML/LaTeX parser, no LLM
  tests/
    test_exam_profile.py                   # validates gre_math.json against the schema
    test_seed_deck.py                      # validates the built deck's notes/tags/sources
    test_topic_rules.py                    # FLEX: validates the scraper's tagging rules
  out/                                     # build outputs (gitignored EXCEPT the shipped .apkg)
    gre_math_seed.apkg                     # committed: the portable deck both apps import
```

**Modified/created in the engine (memory model, Phase B):**
```
repos/anki/proto/anki/speedrun.proto                 # MODIFY: add GetTopicMastery rpc + 3 messages (additive)
repos/anki/rslib/src/speedrun/mod.rs                 # MODIFY: add pure wilson_interval + mastery_aggregate fns + tests
repos/anki/rslib/src/speedrun/service.rs             # MODIFY: add get_topic_mastery impl on Collection
repos/anki/pylib/anki/speedrun.py                    # MODIFY: add topic_mastery() to SpeedrunManager
repos/anki/pylib/tests/test_speedrun.py             # MODIFY: add Python integration test
```

**Installer (Phase C):**
```
repos/anki/qt/installer/windows-template/            # NEW: vendored Briefcase Windows template (mirrors linux-template/)
repos/anki/qt/installer/app/pyproject.toml           # MODIFY: pin template for [tool.briefcase.app.anki.windows]
```

**§7a artifacts (Phase D) — private umbrella `docs/`:**
```
docs/artifacts/why-rust-not-python.md
docs/artifacts/upstream-files-touched.md
```

**Proof recordings (Phase E) — private umbrella:**
```
docs/proof/                                          # recordings + a PROOF.md index
```

---

# Phase A — Content: exam-profile + seed deck (+ FLEX scraper)

**Outcome:** an `exam_profiles/gre_math.json` DAG with ETS weights, a hand-authored calc+LA `.apkg` (`Speedrun::Declarative` notes, hierarchical topic tags, per-note `Source`) that both apps can import, and (flex) a deterministic scraper that emits the same note shape from open-licensed sources. This unblocks "both apps review the same deck" and feeds the coverage/mastery RPCs.

### Task A0: Scaffold the content toolchain

**Files:**
- Create: `repos/anki/speedrun/README.md`
- Create: `repos/anki/speedrun/pyproject.toml`
- Create: `repos/anki/speedrun/.gitignore`

- [ ] **Step 1: Create the uv project manifest** (dev-only tooling; pinned deps for determinism)

`repos/anki/speedrun/pyproject.toml`:
```toml
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
[project]
name = "speedrun-content"
version = "0.1.0"
description = "Deterministic (non-AI) GRE-Math content tooling for Speedrun: exam profile, seed deck, scraper."
requires-python = ">=3.9"
dependencies = [
    "genanki==0.13.1",
    "pyyaml==6.0.2",
]

[dependency-groups]
dev = ["pytest==8.3.4"]
```

- [ ] **Step 2: Create the gitignore** (ignore build outputs EXCEPT the shipped deck)

`repos/anki/speedrun/.gitignore`:
```gitignore
out/*
!out/gre_math_seed.apkg
.venv/
__pycache__/
```

- [ ] **Step 3: Create the README**

`repos/anki/speedrun/README.md`:
```markdown
# Speedrun content tooling (deterministic, NO AI)

Builds the GRE-Math exam profile and seed deck used by both desktop and Android.
Everything here is rule-based / hand-authored — no LLM or model calls.

## Setup
    cd repos/anki/speedrun
    uv sync

## Build the seed deck
    uv run python seed/build_seed_deck.py
    # -> out/gre_math_seed.apkg  (import into Anki desktop or AnkiDroid)

## Validate
    uv run pytest tests/ -v

## Scraper (FLEX)
    uv run python scraper/scrape_openstax.py --help
    # Emits YAML in the seed/ note shape from open-licensed sources only.
    # Every emitted note carries a Source citation and rule-based topic tags.

## License
All content shipped here is open-licensed (OpenStax CC-BY, public domain).
ETS released forms are NOT redistributed; used only for our own benchmarking.
```

- [ ] **Step 4: Verify uv resolves the environment**

Run from `repos/anki/speedrun`:
```bash
uv sync
```
Expected: `.venv/` created, `genanki` + `pyyaml` + `pytest` resolved, exit 0.

- [ ] **Step 5: Commit**

```bash
cd repos/anki
git checkout -b feat/speedrun-wed-mvp
git add speedrun/README.md speedrun/pyproject.toml speedrun/.gitignore
git commit -m "feat(speedrun/content): scaffold deterministic content toolchain (genanki+pyyaml, no AI)"
```

### Task A1: Exam-profile JSON (taxonomy/DAG + ETS weights) — CRITICAL

**Files:**
- Create: `repos/anki/speedrun/exam_profiles/schema.md`
- Create: `repos/anki/speedrun/exam_profiles/gre_math.json`
- Create: `repos/anki/speedrun/tests/test_exam_profile.py`

- [ ] **Step 1: Write the schema doc** (the contract the RPC's `required_tags`/`topics` are drawn from)

`repos/anki/speedrun/exam_profiles/schema.md`:
```markdown
# Exam-profile JSON schema

One JSON object per exam, keyed by `exam_id`. Rides in the synced collection config later.

- `exam_id` (string): e.g. "gre_math".
- `name` (string): human title.
- `version` (int): bump on any topic/weight change.
- `topics` (array of objects):
  - `id` (string): hierarchical tag, e.g. "calc::single_var::integration". Uses `::`.
  - `name` (string): human label.
  - `ets_weight` (number): fraction of the exam (all weights sum to 1.0 +/- 0.001).
  - `prereqs` (array of string): topic ids that are prerequisites (DAG edges; must be acyclic and reference existing ids).

Invariants (enforced by tests/test_exam_profile.py):
1. All `id` values are unique.
2. Sum of `ets_weight` == 1.0 (within 1e-3).
3. Every `prereqs` entry references an existing topic `id`.
4. The prereq graph is acyclic (a DAG).
```

- [ ] **Step 2: Write the exam-profile** (ETS GRE-Math published bands: Calculus ~50%, Algebra ~25% incl. linear algebra, "additional" ~25%; we scope Wed to calc + linear algebra and renormalize the two we author so weights sum to 1.0 — documented as a Wed subset)

`repos/anki/speedrun/exam_profiles/gre_math.json`:
```json
{
  "exam_id": "gre_math",
  "name": "GRE Mathematics Subject Test (Wed subset: Calculus + Linear Algebra)",
  "version": 1,
  "topics": [
    { "id": "calc", "name": "Calculus", "ets_weight": 0.0, "prereqs": [] },
    { "id": "calc::limits", "name": "Limits & continuity", "ets_weight": 0.10, "prereqs": ["calc"] },
    { "id": "calc::single_var::differentiation", "name": "Differentiation", "ets_weight": 0.14, "prereqs": ["calc::limits"] },
    { "id": "calc::single_var::integration", "name": "Integration", "ets_weight": 0.16, "prereqs": ["calc::single_var::differentiation"] },
    { "id": "calc::sequences_series", "name": "Sequences & series", "ets_weight": 0.10, "prereqs": ["calc::limits"] },
    { "id": "calc::multivar", "name": "Multivariable calculus", "ets_weight": 0.15, "prereqs": ["calc::single_var::integration"] },
    { "id": "linear_algebra", "name": "Linear algebra", "ets_weight": 0.0, "prereqs": [] },
    { "id": "linear_algebra::vector_spaces", "name": "Vector spaces", "ets_weight": 0.08, "prereqs": ["linear_algebra"] },
    { "id": "linear_algebra::matrices", "name": "Matrices & linear systems", "ets_weight": 0.09, "prereqs": ["linear_algebra::vector_spaces"] },
    { "id": "linear_algebra::eigen", "name": "Eigenvalues & eigenvectors", "ets_weight": 0.10, "prereqs": ["linear_algebra::matrices"] },
    { "id": "linear_algebra::linear_maps", "name": "Linear maps & rank", "ets_weight": 0.08, "prereqs": ["linear_algebra::vector_spaces"] }
  ]
}
```
(The two container topics `calc` and `linear_algebra` carry `ets_weight` 0.0 — they are DAG roots for coverage/interleaving, not scored leaves; the ten leaf weights sum to 1.00.)

- [ ] **Step 3: Write the validation test** (RED — file exists but assert the invariants; this is a data-quality gate, not TDD-of-code)

`repos/anki/speedrun/tests/test_exam_profile.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
from pathlib import Path

PROFILE = Path(__file__).resolve().parent.parent / "exam_profiles" / "gre_math.json"


def _load():
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def test_ids_unique():
    ids = [t["id"] for t in _load()["topics"]]
    assert len(ids) == len(set(ids))


def test_leaf_weights_sum_to_one():
    total = sum(t["ets_weight"] for t in _load()["topics"])
    assert abs(total - 1.0) < 1e-3


def test_prereqs_reference_existing_ids():
    topics = _load()["topics"]
    ids = {t["id"] for t in topics}
    for t in topics:
        for p in t["prereqs"]:
            assert p in ids, f"{t['id']} references missing prereq {p}"


def test_prereq_graph_is_acyclic():
    topics = _load()["topics"]
    edges = {t["id"]: list(t["prereqs"]) for t in topics}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in edges}

    def visit(n):
        color[n] = GRAY
        for m in edges[n]:
            if color[m] == GRAY:
                raise AssertionError(f"cycle via {n}->{m}")
            if color[m] == WHITE:
                visit(m)
        color[n] = BLACK

    for tid in edges:
        if color[tid] == WHITE:
            visit(tid)
```

- [ ] **Step 4: Run the validation to verify GREEN**

Run from `repos/anki/speedrun`:
```bash
uv run pytest tests/test_exam_profile.py -v
```
Expected: 4 passed. (If `test_leaf_weights_sum_to_one` fails, the leaf `ets_weight`s were edited off 1.0 — re-normalize.)

- [ ] **Step 5: Commit**

```bash
cd repos/anki
git add speedrun/exam_profiles/ speedrun/tests/test_exam_profile.py
git commit -m "feat(speedrun/content): GRE-Math exam profile (calc+LA DAG + ETS weights) + validation tests"
```

### Task A2: Hand-authored seed deck (.apkg) — CRITICAL

**Files:**
- Create: `repos/anki/speedrun/seed/cards_calc.yaml`
- Create: `repos/anki/speedrun/seed/cards_linear_algebra.yaml`
- Create: `repos/anki/speedrun/seed/build_seed_deck.py`
- Create: `repos/anki/speedrun/tests/test_seed_deck.py`

- [ ] **Step 1: Author the calculus cards** (start with these real cards; the CRITICAL floor is **≥30 declarative notes total across calc+LA** — add more entries in this exact YAML shape. Each note: `front`, `back`, `topic` (must be a leaf `id` from `gre_math.json`), `source` (open-licensed citation).)

`repos/anki/speedrun/seed/cards_calc.yaml`:
```yaml
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Declarative GRE-Math cards. Content authored from open-licensed / public-domain
# sources; each note cites its Source. NO AI generated any of this.
- front: "State the epsilon-delta definition of \\(\\lim_{x\\to a} f(x)=L\\)."
  back: "For every \\(\\varepsilon>0\\) there is \\(\\delta>0\\) such that \\(0<|x-a|<\\delta \\Rightarrow |f(x)-L|<\\varepsilon\\)."
  topic: "calc::limits"
  source: "OpenStax Calculus Vol. 1, §2.5 (CC BY 4.0)"
- front: "What does the Squeeze Theorem state?"
  back: "If \\(g(x)\\le f(x)\\le h(x)\\) near \\(a\\) and \\(\\lim g=\\lim h=L\\), then \\(\\lim_{x\\to a} f(x)=L\\)."
  topic: "calc::limits"
  source: "OpenStax Calculus Vol. 1, §2.3 (CC BY 4.0)"
- front: "Definition of the derivative \\(f'(a)\\) as a limit."
  back: "\\(f'(a)=\\lim_{h\\to 0}\\dfrac{f(a+h)-f(a)}{h}\\)."
  topic: "calc::single_var::differentiation"
  source: "OpenStax Calculus Vol. 1, §3.1 (CC BY 4.0)"
- front: "Product rule for \\((fg)'\\)."
  back: "\\((fg)' = f'g + fg'\\)."
  topic: "calc::single_var::differentiation"
  source: "OpenStax Calculus Vol. 1, §3.3 (CC BY 4.0)"
- front: "Chain rule for \\(\\frac{d}{dx} f(g(x))\\)."
  back: "\\(f'(g(x))\\,g'(x)\\)."
  topic: "calc::single_var::differentiation"
  source: "OpenStax Calculus Vol. 1, §3.6 (CC BY 4.0)"
- front: "Fundamental Theorem of Calculus, Part 2."
  back: "If \\(F'=f\\) and \\(f\\) continuous on \\([a,b]\\), then \\(\\int_a^b f(x)\\,dx = F(b)-F(a)\\)."
  topic: "calc::single_var::integration"
  source: "OpenStax Calculus Vol. 1, §5.3 (CC BY 4.0)"
- front: "\\(\\int \\frac{1}{x}\\,dx = ?\\) (x>0)"
  back: "\\(\\ln|x| + C\\)."
  topic: "calc::single_var::integration"
  source: "OpenStax Calculus Vol. 1, §5.6 (CC BY 4.0)"
- front: "Integration by parts formula."
  back: "\\(\\int u\\,dv = uv - \\int v\\,du\\)."
  topic: "calc::single_var::integration"
  source: "OpenStax Calculus Vol. 2, §3.1 (CC BY 4.0)"
- front: "Ratio test: the series \\(\\sum a_n\\) converges absolutely if ...?"
  back: "\\(\\lim_{n\\to\\infty}\\left|\\frac{a_{n+1}}{a_n}\\right| = L < 1\\)."
  topic: "calc::sequences_series"
  source: "OpenStax Calculus Vol. 2, §5.6 (CC BY 4.0)"
- front: "Taylor series of \\(e^x\\) about 0."
  back: "\\(\\sum_{n=0}^{\\infty}\\frac{x^n}{n!}\\)."
  topic: "calc::sequences_series"
  source: "OpenStax Calculus Vol. 2, §6.3 (CC BY 4.0)"
- front: "Gradient \\(\\nabla f\\) of \\(f(x,y)\\)."
  back: "\\(\\left(\\frac{\\partial f}{\\partial x}, \\frac{\\partial f}{\\partial y}\\right)\\)."
  topic: "calc::multivar"
  source: "OpenStax Calculus Vol. 3, §4.6 (CC BY 4.0)"
- front: "Statement of Clairaut's theorem (equality of mixed partials)."
  back: "If \\(f_{xy}\\) and \\(f_{yx}\\) are continuous near a point, they are equal there."
  topic: "calc::multivar"
  source: "OpenStax Calculus Vol. 3, §4.3 (CC BY 4.0)"
```

- [ ] **Step 2: Author the linear-algebra cards** (same shape; add more to reach the ≥30 total floor)

`repos/anki/speedrun/seed/cards_linear_algebra.yaml`:
```yaml
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
- front: "Definition of a vector space (the two closure axioms)."
  back: "Closed under vector addition and scalar multiplication, with the eight axioms (associativity, identity, inverses, distributivity)."
  topic: "linear_algebra::vector_spaces"
  source: "Hefferon, Linear Algebra (public domain / free license), Ch. 1"
- front: "Definition: a set of vectors is linearly independent iff ...?"
  back: "The only solution to \\(c_1 v_1 + \\dots + c_k v_k = 0\\) is \\(c_1=\\dots=c_k=0\\)."
  topic: "linear_algebra::vector_spaces"
  source: "Hefferon, Linear Algebra, Ch. 2"
- front: "What is a basis of a vector space?"
  back: "A linearly independent set that spans the space."
  topic: "linear_algebra::vector_spaces"
  source: "Hefferon, Linear Algebra, Ch. 2"
- front: "Condition for a square matrix A to be invertible (determinant)."
  back: "\\(\\det(A) \\neq 0\\)."
  topic: "linear_algebra::matrices"
  source: "Hefferon, Linear Algebra, Ch. 4"
- front: "\\(\\det\\begin{pmatrix}a&b\\\\c&d\\end{pmatrix} = ?\\)"
  back: "\\(ad - bc\\)."
  topic: "linear_algebra::matrices"
  source: "Hefferon, Linear Algebra, Ch. 4"
- front: "Rank-nullity theorem."
  back: "For \\(T:V\\to W\\), \\(\\dim(\\ker T) + \\dim(\\operatorname{im} T) = \\dim V\\)."
  topic: "linear_algebra::linear_maps"
  source: "Hefferon, Linear Algebra, Ch. 3"
- front: "Definition: \\(\\lambda\\) is an eigenvalue of A iff ...?"
  back: "There is a nonzero \\(v\\) with \\(Av = \\lambda v\\); equivalently \\(\\det(A-\\lambda I)=0\\)."
  topic: "linear_algebra::eigen"
  source: "Hefferon, Linear Algebra, Ch. 5"
- front: "Characteristic polynomial of A."
  back: "\\(p(\\lambda) = \\det(A - \\lambda I)\\)."
  topic: "linear_algebra::eigen"
  source: "Hefferon, Linear Algebra, Ch. 5"
- front: "A is diagonalizable iff ...? (eigenvector condition)"
  back: "It has a basis of eigenvectors (n linearly independent eigenvectors for an n x n matrix)."
  topic: "linear_algebra::eigen"
  source: "Hefferon, Linear Algebra, Ch. 5"
- front: "Definition of the image (range) of a linear map \\(T:V\\to W\\)."
  back: "\\(\\operatorname{im} T = \\{ T(v) : v \\in V \\} \\subseteq W\\)."
  topic: "linear_algebra::linear_maps"
  source: "Hefferon, Linear Algebra, Ch. 3"
```

- [ ] **Step 3: Write the deterministic builder** (fixed model/deck GUIDs so the deck is byte-stable across runs and identical on both apps; genanki, no AI)

`repos/anki/speedrun/seed/build_seed_deck.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Deterministic YAML -> .apkg builder for the Speedrun GRE-Math seed deck.

No AI: cards are hand-authored in seed/*.yaml. Fixed IDs make output stable and
importable identically on desktop and AnkiDroid.
"""
from __future__ import annotations

import json
from pathlib import Path

import genanki
import yaml

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "seed"
OUT = ROOT / "out" / "gre_math_seed.apkg"
PROFILE = ROOT / "exam_profiles" / "gre_math.json"

# Fixed IDs (chosen once; do not change or existing imports will duplicate).
MODEL_ID = 1607392319
DECK_ID = 2059400110

MODEL = genanki.Model(
    MODEL_ID,
    "Speedrun::Declarative",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
        {"name": "TopicID"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}'
            '<div style="font-size:12px;color:#888;margin-top:8px">'
            "Topic: {{TopicID}} &middot; Source: {{Source}}</div>",
        }
    ],
    # Bundled MathJax rendering is handled by Anki's built-in MathJax on \\( \\).
)


def _leaf_topic_ids() -> set[str]:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    return {t["id"] for t in profile["topics"] if t["ets_weight"] > 0.0}


def load_notes() -> list[dict]:
    notes: list[dict] = []
    for name in ("cards_calc.yaml", "cards_linear_algebra.yaml"):
        data = yaml.safe_load((SEED_DIR / name).read_text(encoding="utf-8"))
        notes.extend(data)
    return notes


def build() -> Path:
    valid_topics = _leaf_topic_ids()
    deck = genanki.Deck(DECK_ID, "Speedrun::GRE Math")
    for n in load_notes():
        topic = n["topic"]
        if topic not in valid_topics:
            raise ValueError(f"note topic {topic!r} is not a scored leaf in gre_math.json")
        note = genanki.Note(
            model=MODEL,
            fields=[n["front"], n["back"], topic, n["source"]],
            tags=[topic],  # hierarchical tag == topic id; :: preserved
            guid=genanki.guid_for(n["front"], topic),  # stable across runs
        )
        deck.add_note(note)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(deck).write_to_file(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path} ({len(load_notes())} notes)")
```

- [ ] **Step 4: Write the deck validation test** (RED first — imports `build` which exists, then asserts the built deck has the expected notes, valid topics, and non-empty sources)

`repos/anki/speedrun/tests/test_seed_deck.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "seed"))

import build_seed_deck as bsd  # noqa: E402


def test_min_note_count():
    notes = bsd.load_notes()
    assert len(notes) >= 30, "Wednesday floor is >=30 declarative notes"


def test_every_note_has_source_and_valid_topic():
    valid = {t["id"] for t in json.loads(bsd.PROFILE.read_text("utf-8"))["topics"]}
    for n in bsd.load_notes():
        assert n["front"].strip()
        assert n["back"].strip()
        assert n["source"].strip(), f"missing Source on {n['front']!r}"
        assert n["topic"] in valid, f"unknown topic {n['topic']!r}"


def test_build_produces_apkg():
    path = bsd.build()
    assert path.exists()
    assert path.stat().st_size > 0
```

- [ ] **Step 5: Build the deck and run the tests**

Run from `repos/anki/speedrun`:
```bash
uv run python seed/build_seed_deck.py
uv run pytest tests/test_seed_deck.py -v
```
Expected: builder prints `wrote .../out/gre_math_seed.apkg (N notes)`; tests pass. If `test_min_note_count` fails, author more cards in the YAML files until ≥30.

- [ ] **Step 6: Manually import & eyeball once** (sanity: MathJax renders, tags nest)

Import `repos/anki/speedrun/out/gre_math_seed.apkg` into the dev desktop Anki (`just run` → File → Import). Confirm cards render MathJax and the browser shows nested `calc::…` / `linear_algebra::…` tags. (This is also captured later in Phase E.)

- [ ] **Step 7: Commit** (including the built `.apkg` so both apps import the identical deck)

```bash
cd repos/anki
git add speedrun/seed/ speedrun/tests/test_seed_deck.py speedrun/out/gre_math_seed.apkg
git commit -m "feat(speedrun/content): hand-authored calc+LA seed deck (>=30 notes, tagged, sourced) + builder + tests"
```

### Task A3: Deterministic open-licensed scraper — FLEX

> **FLEX — build only if time remains before Wednesday.** A2 already satisfies "exam deck." Skip cleanly (leave the directory absent) if the schedule is tight; nothing downstream depends on it.

**Files:**
- Create: `repos/anki/speedrun/scraper/topic_rules.yaml`
- Create: `repos/anki/speedrun/scraper/scrape_openstax.py`
- Create: `repos/anki/speedrun/tests/test_topic_rules.py`

- [ ] **Step 1: Write the rule-based topic-tagging rules** (keyword → topic id; deterministic, no ML)

`repos/anki/speedrun/scraper/topic_rules.yaml`:
```yaml
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Ordered rules: first matching keyword set wins. Keywords are lowercased substrings.
rules:
  - topic: "calc::limits"
    any: ["limit", "continuity", "squeeze theorem", "epsilon-delta"]
  - topic: "calc::single_var::differentiation"
    any: ["derivative", "differentiate", "chain rule", "product rule"]
  - topic: "calc::single_var::integration"
    any: ["integral", "antiderivative", "integration by parts", "fundamental theorem"]
  - topic: "calc::sequences_series"
    any: ["series", "sequence", "ratio test", "taylor", "convergence"]
  - topic: "calc::multivar"
    any: ["gradient", "partial derivative", "multivariable", "clairaut"]
  - topic: "linear_algebra::vector_spaces"
    any: ["vector space", "linearly independent", "basis", "span"]
  - topic: "linear_algebra::matrices"
    any: ["determinant", "invertible matrix", "linear system", "row reduction"]
  - topic: "linear_algebra::eigen"
    any: ["eigenvalue", "eigenvector", "characteristic polynomial", "diagonaliz"]
  - topic: "linear_algebra::linear_maps"
    any: ["linear map", "rank", "nullity", "kernel", "image of"]
```

- [ ] **Step 2: Write the deterministic scraper** (HTML → notes; open-licensed sources ONLY; every note gets a `Source`; rule-based tags; refuses untagged content)

`repos/anki/speedrun/scraper/scrape_openstax.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Deterministic (NO AI) scraper for open-licensed math sources.

Given a local HTML/LaTeX file from an OpenStax CC-BY book (or a public-domain
text), it extracts definition/theorem blocks, assigns a topic tag by keyword
rules, and emits YAML in the seed/ note shape. Every emitted note carries a
Source citation. Content whose topic cannot be determined is DROPPED (never
guessed) and reported, so the deck never contains mis-tagged or unsourced notes.
"""
from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path

import yaml

RULES = yaml.safe_load(
    (Path(__file__).resolve().parent / "topic_rules.yaml").read_text("utf-8")
)["rules"]


def tag_for(text: str) -> str | None:
    low = text.lower()
    for rule in RULES:
        if any(kw in low for kw in rule["any"]):
            return rule["topic"]
    return None


class _BlockExtractor(HTMLParser):
    """Collects text inside <div class="definition|theorem"> blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.capturing = False
        self.blocks: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            cls = dict(attrs).get("class", "")
            if any(k in cls for k in ("definition", "theorem", "key-equation")):
                self.capturing = True
                self._buf = []

    def handle_endtag(self, tag):
        if tag == "div" and self.capturing:
            self.capturing = False
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.blocks.append(text)

    def handle_data(self, data):
        if self.capturing:
            self._buf.append(data)


def scrape(html: str, source: str) -> tuple[list[dict], int]:
    parser = _BlockExtractor()
    parser.feed(html)
    notes, dropped = [], 0
    for block in parser.blocks:
        topic = tag_for(block)
        if topic is None:
            dropped += 1
            continue
        # Split "Front. Back" heuristically on the first sentence boundary.
        head, _, tail = block.partition(". ")
        notes.append(
            {
                "front": head.strip() + ("?" if not head.strip().endswith("?") else ""),
                "back": (tail or head).strip(),
                "topic": topic,
                "source": source,
            }
        )
    return notes, dropped


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic open-licensed scraper (no AI).")
    ap.add_argument("html_file", type=Path, help="Local HTML from a CC-BY/public-domain source")
    ap.add_argument("--source", required=True, help="Citation string, e.g. 'OpenStax Calculus Vol.1 (CC BY 4.0)'")
    ap.add_argument("--out", type=Path, required=True, help="Output YAML path")
    args = ap.parse_args()
    notes, dropped = scrape(args.html_file.read_text("utf-8"), args.source)
    args.out.write_text(yaml.safe_dump(notes, allow_unicode=True, sort_keys=False), "utf-8")
    print(f"wrote {len(notes)} notes to {args.out}; dropped {dropped} untaggable blocks")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the tagging-rule tests** (deterministic behavior; refusal on unknown content)

`repos/anki/speedrun/tests/test_topic_rules.py`:
```python
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import scrape_openstax as sc  # noqa: E402


def test_keyword_tagging():
    assert sc.tag_for("The derivative of a product") == "calc::single_var::differentiation"
    assert sc.tag_for("An eigenvalue satisfies Av = lambda v") == "linear_algebra::eigen"


def test_unknown_content_is_dropped_not_guessed():
    notes, dropped = sc.scrape(
        '<div class="definition">The capital of France is Paris.</div>', "PD text"
    )
    assert notes == []
    assert dropped == 1


def test_scraped_notes_carry_source():
    html = '<div class="theorem">The determinant of a 2x2 matrix. It equals ad-bc.</div>'
    notes, _ = sc.scrape(html, "Hefferon LA (free license)")
    assert notes and all(n["source"] == "Hefferon LA (free license)" for n in notes)
    assert notes[0]["topic"] == "linear_algebra::matrices"
```

- [ ] **Step 4: Run the scraper tests**

Run from `repos/anki/speedrun`:
```bash
uv run pytest tests/test_topic_rules.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd repos/anki
git add speedrun/scraper/ speedrun/tests/test_topic_rules.py
git commit -m "feat(speedrun/content): FLEX deterministic open-licensed scraper + rule-based tagging + tests (no AI)"
```

---

# Phase B — Memory model: `GetTopicMastery` RPC (TDD) — CRITICAL

**Outcome:** an additive read-only `SpeedrunService.GetTopicMastery` that, per requested topic, aggregates live FSRS retrievability into `cards_with_data`, `mastered_count`, `avg_recall`, a **Wilson 95% interval** (`mastered_lower`/`mastered_upper`) on the mastered proportion, `graded_reviews`, and an **`abstained`** flag (true below `min_reviews` graded reviews or with no data). ≥3 Rust tests + 1 Python integration test; read-only ⇒ no `transact`, `pragma integrity_check == ok`. The Svelte/TS dashboard is Cursor's job — this stops at the RPC + Python wrapper seam.

**Why a Wilson interval (honesty design):** the honest "memory score" is *what fraction of this topic's cards you currently retain*, a binomial proportion (mastered vs not). The Wilson score interval is the standard, well-behaved CI for a proportion at small `n` (unlike the normal approximation it never leaves [0,1] and behaves near 0/1) and is **fully deterministic** — no RNG — so tests are exact. Bootstrap would need a seed and adds nondeterminism; Wilson is the right tool here.

### Task B1: Extend the proto contract (additive) — `GetTopicMastery`

**Files:**
- Modify: `repos/anki/proto/anki/speedrun.proto`

- [ ] **Step 1: Add the RPC + messages to the existing service** (additive: new rpc on `SpeedrunService`, new messages with fresh field numbers — never renumber existing `GetCoverage`/`CoverageResponse`)

In `repos/anki/proto/anki/speedrun.proto`, add the new rpc inside `service SpeedrunService { … }` directly after the `GetCoverage` line:
```proto
  // Per-topic FSRS memory aggregate: mastered proportion (Wilson 95% range),
  // average recall, and an abstain flag when graded reviews are too few.
  rpc GetTopicMastery(GetTopicMasteryRequest) returns (TopicMasteryResponse);
```

Append these messages at the end of the file (do not touch existing messages):
```proto
message GetTopicMasteryRequest {
  // Topic ids (hierarchical tags) to score, e.g. "calc::single_var::integration".
  repeated string topics = 1;
  // Retrievability threshold to count a card as "mastered"; 0 => default 0.9.
  double mastery_threshold = 2;
  // Minimum graded reviews before a topic reports a score; 0 => default 20.
  uint32 min_reviews = 3;
}

message TopicMastery {
  // The requested topic id, echoed back.
  string topic = 1;
  // Cards under this topic that have an FSRS memory state (usable data points).
  uint32 cards_with_data = 2;
  // Cards whose current retrievability >= mastery_threshold.
  uint32 mastered_count = 3;
  // Mean current retrievability across cards_with_data (0.0 if none).
  double avg_recall = 4;
  // Wilson 95% lower bound on the mastered proportion.
  double mastered_lower = 5;
  // Wilson 95% upper bound on the mastered proportion.
  double mastered_upper = 6;
  // Total graded (rated, scheduling-affecting) reviews across the topic's cards.
  uint32 graded_reviews = 7;
  // True => below min_reviews or no data; the honest UI withholds the score.
  bool abstained = 8;
}

message TopicMasteryResponse {
  repeated TopicMastery topics = 1;
  // rslib version; proves which engine answered.
  string backend_version = 2;
}
```

- [ ] **Step 2: Verify the proto/anki_proto crate compiles** (types generate; `anki` crate will not compile until the impl lands — expected)

Run from `repos/anki`:
```bash
cargo check -p anki_proto 2>&1 | tail -20
```
Expected: compiles; the generated trait `anki_proto::speedrun::SpeedrunService` now has a `get_topic_mastery` method and the new message types exist. (`cargo check -p anki` will now fail with `E0046`/`E0277` — the `Collection` impl is missing the new method — that is the impl-level RED, resolved in B3.)

- [ ] **Step 3: Commit**

```bash
git add proto/anki/speedrun.proto
git commit -m "feat(speedrun): additive GetTopicMastery proto (per-topic mastery + Wilson range + abstain)"
```

### Task B2: RED → GREEN — pure aggregation + Wilson functions

**Files:**
- Modify: `repos/anki/rslib/src/speedrun/mod.rs`

- [ ] **Step 1: Add the failing unit tests** (append to the existing `mod test` in `mod.rs`, below the coverage tests; references `wilson_interval` + `topic_aggregate` which do not exist yet → compile RED once the `anki` crate can build at B3, but written now to lock the contract)

Add these imports to the top of `mod test` (next to the existing `use super::coverage;`):
```rust
    use super::topic_aggregate;
    use super::wilson_interval;
    use super::MASTERY_THRESHOLD_DEFAULT;
```

Add these tests inside `mod test`:
```rust
    #[test]
    fn wilson_bounds_are_inside_unit_interval_and_ordered() {
        let (lo, hi) = wilson_interval(3, 10, 1.96);
        assert!(lo >= 0.0 && hi <= 1.0);
        assert!(lo < hi);
        // Known value: 3/10 Wilson 95% ~ (0.108, 0.603).
        assert!((lo - 0.1078).abs() < 1e-3, "lo={lo}");
        assert!((hi - 0.6032).abs() < 1e-3, "hi={hi}");
    }

    #[test]
    fn wilson_zero_n_is_full_uncertainty() {
        assert_eq!(wilson_interval(0, 0, 1.96), (0.0, 1.0));
    }

    #[test]
    fn topic_aggregate_counts_mastered_and_averages() {
        // retrievabilities for 4 cards; threshold 0.9 => 2 mastered.
        let rs = vec![0.95_f64, 0.91, 0.5, 0.2];
        let (n, mastered, avg) = topic_aggregate(&rs, 0.9);
        assert_eq!(n, 4);
        assert_eq!(mastered, 2);
        assert!((avg - 0.64).abs() < 1e-9);
    }

    #[test]
    fn topic_aggregate_empty_is_zero() {
        let (n, mastered, avg) = topic_aggregate(&[], MASTERY_THRESHOLD_DEFAULT);
        assert_eq!((n, mastered), (0, 0));
        assert_eq!(avg, 0.0);
    }
```

- [ ] **Step 2: Implement the pure functions** (add above the `#[cfg(test)] mod test` block in `mod.rs`)

```rust
/// Default retrievability at/above which a card counts as "mastered".
pub(crate) const MASTERY_THRESHOLD_DEFAULT: f64 = 0.9;
/// Default minimum graded reviews before a topic reports a (non-abstained) score.
pub(crate) const MIN_REVIEWS_DEFAULT: u32 = 20;
/// z for a 95% two-sided interval.
pub(crate) const WILSON_Z_95: f64 = 1.96;

/// Aggregate per-card retrievabilities into (cards_with_data, mastered_count,
/// avg_recall). `retrievabilities` contains one entry per card that HAS an FSRS
/// memory state. `avg_recall` is 0.0 when the slice is empty.
pub(crate) fn topic_aggregate(retrievabilities: &[f64], threshold: f64) -> (u32, u32, f64) {
    let n = retrievabilities.len() as u32;
    if n == 0 {
        return (0, 0, 0.0);
    }
    let mastered = retrievabilities.iter().filter(|r| **r >= threshold).count() as u32;
    let avg = retrievabilities.iter().sum::<f64>() / n as f64;
    (n, mastered, avg)
}

/// Wilson score interval for a binomial proportion `successes / n` at the given
/// z. Returns (lower, upper) clamped to [0, 1]. `n == 0` => (0.0, 1.0) (total
/// uncertainty), which the caller treats as an abstain signal.
pub(crate) fn wilson_interval(successes: u32, n: u32, z: f64) -> (f64, f64) {
    if n == 0 {
        return (0.0, 1.0);
    }
    let n = n as f64;
    let p = successes as f64 / n;
    let z2 = z * z;
    let denom = 1.0 + z2 / n;
    let center = (p + z2 / (2.0 * n)) / denom;
    let margin = (z / denom) * ((p * (1.0 - p) / n) + z2 / (4.0 * n * n)).sqrt();
    ((center - margin).max(0.0), (center + margin).min(1.0))
}
```

- [ ] **Step 3: Run the pure-function tests via the full module** (the real in-crate GREEN gate lands with B3, since declaring the new proto method forces the `Collection` impl before `anki` compiles; run after B3 and confirm these pass. To sanity-check the math in isolation before B3, a scratch `rustc` build of the two fns + asserts is acceptable but is NOT the GREEN gate.)

- [ ] **Step 4: Commit**

```bash
git add rslib/src/speedrun/mod.rs
git commit -m "feat(speedrun): pure topic_aggregate + wilson_interval fns + unit tests (4)"
```

### Task B3: RED → GREEN — `get_topic_mastery` on `Collection` + Rust integration test

**Files:**
- Modify: `repos/anki/rslib/src/speedrun/service.rs`
- Modify: `repos/anki/rslib/src/speedrun/mod.rs` (add the integration test)

- [ ] **Step 1: Add the failing Rust integration test** (append inside `mod test` in `mod.rs`; drives a real `Collection` — asserts abstain + read-only, achievable without simulating FSRS)

Add these imports to `mod test` if not already present from the coverage tests:
```rust
    use crate::collection::Collection;
    use crate::decks::DeckId;
    use crate::error::Result;
    use crate::services::SpeedrunService;
```

Add this test:
```rust
    #[test]
    fn topic_mastery_abstains_without_enough_reviews() -> Result<()> {
        let mut col = Collection::new();

        // Add a note tagged calc::limits but never reviewed => no memory state.
        let nt = col.get_notetype_by_name("Basic")?.unwrap();
        let mut note = nt.new_note();
        col.add_note(&mut note, DeckId(1))?;
        note.tags = vec!["calc::limits".into()];
        col.update_note(&mut note)?;

        let resp = col.get_topic_mastery(anki_proto::speedrun::GetTopicMasteryRequest {
            topics: strs(&["calc::limits", "linear_algebra::eigen"]),
            mastery_threshold: 0.0, // => default 0.9
            min_reviews: 0,         // => default 20
        })?;

        assert_eq!(resp.topics.len(), 2);
        let limits = &resp.topics[0];
        assert_eq!(limits.topic, "calc::limits");
        assert_eq!(limits.cards_with_data, 0); // reviewed 0 times => no FSRS state
        assert_eq!(limits.graded_reviews, 0);
        assert!(limits.abstained); // below min_reviews
        // Full-uncertainty Wilson when no data.
        assert_eq!((limits.mastered_lower, limits.mastered_upper), (0.0, 1.0));
        assert!(!resp.backend_version.is_empty());
        Ok(())
    }
```

- [ ] **Step 2: Run to verify RED** (method not yet implemented)

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -25
```
Expected: FAIL — `anki` crate does not compile (`Collection` is missing `get_topic_mastery`, `E0046`).

- [ ] **Step 3: Implement `get_topic_mastery`** (append the method to the existing `impl crate::services::SpeedrunService for Collection` in `service.rs`)

First add the imports at the top of `service.rs` (below the existing `use` lines):
```rust
use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;

use crate::search::SortMode;
```

Add this method inside the existing `impl crate::services::SpeedrunService for Collection` block (after `get_coverage`):
```rust
    fn get_topic_mastery(
        &mut self,
        input: anki_proto::speedrun::GetTopicMasteryRequest,
    ) -> error::Result<anki_proto::speedrun::TopicMasteryResponse> {
        use crate::speedrun::{
            topic_aggregate, wilson_interval, MASTERY_THRESHOLD_DEFAULT, MIN_REVIEWS_DEFAULT,
            WILSON_Z_95,
        };

        let threshold = if input.mastery_threshold <= 0.0 {
            MASTERY_THRESHOLD_DEFAULT
        } else {
            input.mastery_threshold
        };
        let min_reviews = if input.min_reviews == 0 {
            MIN_REVIEWS_DEFAULT
        } else {
            input.min_reviews
        };

        let timing = self.timing_today()?;
        let fsrs = FSRS::new(None).unwrap();

        let mut out = Vec::with_capacity(input.topics.len());
        for topic in &input.topics {
            // Cards tagged exactly `topic` OR any hierarchical descendant `topic::*`.
            let search = format!("(\"tag:{topic}\" OR \"tag:{topic}::*\")");
            let cids = self.search_cards(search.as_str(), SortMode::NoOrder)?;

            let mut retrievabilities: Vec<f64> = Vec::new();
            let mut graded_reviews: u32 = 0;
            for cid in cids {
                let card = match self.storage.get_card(cid)? {
                    Some(c) => c,
                    None => continue,
                };
                if let Some(state) = card.memory_state {
                    let elapsed = card.seconds_since_last_review(&timing).unwrap_or_default();
                    let decay = card.decay.unwrap_or(FSRS5_DEFAULT_DECAY);
                    let r = fsrs.current_retrievability_seconds(state.into(), elapsed, decay);
                    retrievabilities.push(r as f64);
                }
                graded_reviews += self
                    .storage
                    .get_revlog_entries_for_card(cid)?
                    .iter()
                    .filter(|e| e.has_rating_and_affects_scheduling())
                    .count() as u32;
            }

            let (cards_with_data, mastered_count, avg_recall) =
                topic_aggregate(&retrievabilities, threshold);
            let (mastered_lower, mastered_upper) =
                wilson_interval(mastered_count, cards_with_data, WILSON_Z_95);
            let abstained = graded_reviews < min_reviews || cards_with_data == 0;

            out.push(anki_proto::speedrun::TopicMastery {
                topic: topic.clone(),
                cards_with_data,
                mastered_count,
                avg_recall,
                mastered_lower,
                mastered_upper,
                graded_reviews,
                abstained,
            });
        }

        Ok(anki_proto::speedrun::TopicMasteryResponse {
            topics: out,
            backend_version: crate::version::version().to_string(),
        })
    }
```

- [ ] **Step 4: Run the full speedrun test module — real GREEN gate** (all coverage tests + the 4 new B2 unit tests + this integration test now compile & run)

Run from `repos/anki`:
```bash
cargo test -p anki speedrun:: 2>&1 | tail -25
```
Expected: `test result: ok.` with the coverage tests (4) + B2 unit tests (4) + B3 integration test (1) all passing (≥9 speedrun tests total).

- [ ] **Step 5: Clippy clean on the new code**

```bash
cargo clippy -p anki 2>&1 | grep -i "warning\|error" | grep -i speedrun || echo "no speedrun clippy issues"
```
Expected: `no speedrun clippy issues`.

- [ ] **Step 6: Commit**

```bash
git add rslib/src/speedrun/service.rs rslib/src/speedrun/mod.rs
git commit -m "feat(speedrun): read-only GetTopicMastery on Collection (FSRS retrievability -> Wilson range + abstain) + Rust integration test"
```

### Task B4: Regenerate bindings + Python wrapper + Python integration test

**Files:**
- Modify: `repos/anki/pylib/anki/speedrun.py`
- Modify: `repos/anki/pylib/tests/test_speedrun.py`

- [ ] **Step 1: Full build so codegen adds the Python method** (`.proto` change needs a full build)

Run from `repos/anki`:
```bash
just check 2>&1 | tail -20
```
Expected: exit 0. Confirm the generated backend method exists (read-only inspection; do not edit generated files):
```bash
grep -n "def get_topic_mastery" out/pylib/anki/_backend_generated.py
```
Expected: one match.

- [ ] **Step 2: Add the wrapper method** (append to `SpeedrunManager` in `pylib/anki/speedrun.py`; also export the response type)

Add the export near the existing `CoverageResponse = speedrun_pb2.CoverageResponse` line:
```python
TopicMasteryResponse = speedrun_pb2.TopicMasteryResponse
```

Add the method inside `class SpeedrunManager`:
```python
    def topic_mastery(
        self,
        topics: list[str],
        mastery_threshold: float = 0.9,
        min_reviews: int = 20,
    ) -> TopicMasteryResponse:
        """Per-topic FSRS memory aggregate: mastered proportion (Wilson 95%
        range), average recall, and an abstain flag when graded reviews are too
        few. Read-only. The dashboard/UI for this score is the desktop/TS
        layer's responsibility; this is the data seam."""
        return self.col._backend.get_topic_mastery(
            topics=topics,
            mastery_threshold=mastery_threshold,
            min_reviews=min_reviews,
        )
```

- [ ] **Step 3: Add the Python integration test** (append to `pylib/tests/test_speedrun.py`)

```python
def test_topic_mastery_abstains_and_is_read_only():
    col = getEmptyCol()
    try:
        # A note tagged calc::limits, never reviewed => no memory state.
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"] = "definition of a limit"
        note["Back"] = "epsilon-delta"
        note.tags = ["calc::limits"]
        col.add_note(note, DeckId(1))

        resp = col.speedrun.topic_mastery(["calc::limits", "linear_algebra::eigen"])
        assert len(resp.topics) == 2
        limits = resp.topics[0]
        assert limits.topic == "calc::limits"
        assert limits.cards_with_data == 0
        assert limits.graded_reviews == 0
        assert limits.abstained is True
        assert (limits.mastered_lower, limits.mastered_upper) == (0.0, 1.0)
        assert resp.backend_version  # proves OUR rslib answered

        # Read-only RPC must not have touched the DB.
        assert col.db.scalar("pragma integrity_check") == "ok"
    finally:
        col.close()
```

- [ ] **Step 4: Run the Python integration test to verify GREEN**

Run from `repos/anki`:
```bash
just test-py 2>&1 | grep -A3 topic_mastery
```
Expected: `test_topic_mastery_abstains_and_is_read_only PASSED`.

- [ ] **Step 5: Commit**

```bash
git add pylib/anki/speedrun.py pylib/tests/test_speedrun.py
git commit -m "feat(speedrun): Python topic_mastery() wrapper + integration test (abstain + integrity_check ok)"
```

### Task B5: Full verification gate + invariant re-assertion

**Files:** none (verification only).

- [ ] **Step 1: Format**

Run from `repos/anki`:
```bash
just fmt
```
Expected: exit 0 (or run `just fix-fmt`, re-review, amend).

- [ ] **Step 2: Full green gate**

Run from `repos/anki`:
```bash
just check 2>&1 | tail -20
```
Expected: exit 0 — Rust (≥9 speedrun tests), Python (2 speedrun integration tests), TS, lint all pass. (The two known environmental groups — complexipy-diff, installer — are addressed in Phase C; they are not part of this gate's success criterion. Note them if they appear.)

- [ ] **Step 3: Re-assert invariants**
  - Read-only: `service.rs` `get_topic_mastery` contains no `transact`, no `Op`, no DB writes — only `search_cards` + `storage.get_card`/`get_revlog_entries_for_card`. ✅ by construction.
  - Additive proto: `GetTopicMastery` added as a new rpc; new messages use fresh field numbers 1–8; `GetCoverage`/`CoverageResponse` untouched. ✅
  - Integrity: Python test asserts `pragma integrity_check == "ok"`. ✅
  - No AI: no model/network calls anywhere. ✅

- [ ] **Step 4: Push the branch to the fork**

```bash
git push -u origin feat/speedrun-wed-mvp
git rev-parse HEAD   # record SHA for the §7a artifacts (Phase D)
```

---

# Phase C — Clean-machine installer fix — CRITICAL

**Outcome:** the Briefcase desktop installer builds on a clean machine and the produced app launches. This clears the 50%-cap "must run on a clean device" risk. **Root cause is now grounded (see below): the installer templates are uninitialized git submodules, not a Briefcase beeware clone.**

> Use **superpowers:systematic-debugging** for C1 — reproduce and root-cause the exact failure before changing anything. Do not guess-patch.

### Task C1: Root-cause the template failure — GROUNDED & CONFIRMED (2026-07-01)

**Files:** none (diagnosis). **This task is essentially DONE — the root cause was confirmed during execution grounding. The C2 fix below supersedes the original beeware-clone approach.**

**CONFIRMED root cause (supersedes both the original hypothesis AND Cursor's placeholder-dir note):**
- `qt/installer/windows-template` and `qt/installer/mac-template` are **git submodules**, declared in `repos/anki/.gitmodules`:
  - `briefcase-windows-template` → url `https://github.com/ankitects/briefcase-windows-app-template`, branch `anki`, shallow.
  - `briefcase-mac-template` → url `https://github.com/ankitects/briefcase-macOS-app-template`, branch `anki`, shallow.
- Both are **uninitialized** locally — `git submodule status` shows a leading `-`:
  - `-e995756449d4b4de27365c5c97b5c571d141ea08 qt/installer/windows-template`
  - `-8ef2200fb3f94f180faddd9fdc8b6ea251110910 qt/installer/mac-template`
- The installer build wires them via `build/configure/src/installer.rs` (lines 52-77): two `SyncSubmodule { path: "qt/installer/windows-template" | "mac-template", offline_build: false }` actions (`installer:template:win` / `installer:template:mac`), then `BuildCommand`/`PackageCommand` run `qt/tools/build_installer.py` (Briefcase). The `BuildCommand.files()` depends on `:installer:template` (both submodules) + `glob!["qt/installer/**"]`.
- `linux-template/` is **NOT** a submodule — it is vendored in-tree (real files), which is why Linux never hits this failure.
- ∴ the "template-clone failure" = the **submodule populate/clone failing** (the submodules were never initialized in Phase 0, and/or a build-time `SyncSubmodule` network fetch fails). It is NOT `[tool.briefcase.app.anki.windows]` / beeware.

- [ ] **Step 1: Re-confirm the submodule state** (fast sanity check before fixing)

Run from `repos/anki`:
```bash
git submodule status | grep -E 'installer|template'
git config -f .gitmodules --get-regexp 'briefcase'
```
Expected: the two template submodules show a leading `-` (uninitialized) at the SHAs above; `.gitmodules` shows the two `ankitects/briefcase-*-app-template` urls on branch `anki`.

- [ ] **Step 2: Confirm the Briefcase template mechanism** (GROUNDED — read to understand, likely no change here)

`qt/tools/build_installer.py` is the driver: `get_briefcase_template_path()` (lines 49-56) returns the **local** `qt/installer/windows-template` dir, and `get_briefcase_config_args()` (line 109) passes it to Briefcase as `-C template="<abs path>"`. So Briefcase points at the local submodule dir and treats it as a **git repo** — it does NOT fetch a beeware template. Critically, `build_installer.py` does **NOT** pass `--template-branch`, so Briefcase defaults to checking out a branch named after **its own version** (the memory-recorded error was branch **`v0.4.2`**). The ankitects submodule only has branch `anki` — and while uninitialized it's empty — hence "Unable to clone application template."

∴ the fix has **two parts**: (1) initialize the submodule (C2 Option A Step 1), AND (2) reconcile the briefcase-version↔template-branch mismatch. Options for part 2, in preference order: (a) pass `--template-branch anki` (or the branch the ankitects template actually provides) — but that means editing `build_installer.py`'s `briefcase build`/`package` argv (an upstream file); (b) pin the installed `briefcase` version to one whose version-branch exists in the ankitects template; (c) check out the matching version branch inside the submodule. **Reproduce first** (C2 Option A Step 2) and read Briefcase's actual error + `git branch -a` inside the initialized submodule to pick the minimal correct option.

### Task C2: Initialize (and, if needed, vendor) the installer template submodules

**Approach:** Option A first (initialize the pinned submodules — minimal, keeps upstream parity). Only if a clean/offline machine cannot fetch them at build time, fall back to Option B (vendor in-tree).

**Files (Option A):** none tracked change needed (submodules already pinned in the superproject index) — this is an environment/init fix. **Files (Option B fallback):** `.gitmodules` + de-submoduled template contents.

#### Option A — initialize the pinned submodules (try this first)

- [ ] **Step 1: Initialize both template submodules at their pinned commits**

Run from `repos/anki`:
```bash
git submodule update --init qt/installer/windows-template qt/installer/mac-template
git submodule status | grep -E 'installer|template'
```
Expected: the leading `-` disappears (submodules populated at `e995756…` / `8ef2200…`); `qt/installer/windows-template/` now contains real template files (cookiecutter). **If the clone fails** (network/auth/branch `anki` missing), capture the exact error and go to Option B — do NOT guess-patch. If it fails only due to environment (no network), that is a David/admin item — STOP and ask.

- [ ] **Step 2: Build the installer** (the real gate — this is what was failing)

Run from `repos/anki` (ground the exact recipe first with `just --list | grep -i install`; if no recipe, invoke the driver directly as `build_installer.py` is invoked by `installer.rs`):
```bash
just --list | grep -i install || true
# then either the discovered recipe, or the direct driver the build uses:
uv run python qt/tools/build_installer.py --version $(cat .version) build
```
Expected: the `SyncSubmodule` step finds the submodules already populated (no failing clone), Briefcase `build` completes, and a build artifact appears under the Briefcase output dir. Capture the output.

- [ ] **Step 3: Package + smoke-launch** (produce the installable artifact and confirm it opens)

```bash
uv run python qt/tools/build_installer.py --version $(cat .version) package
```
Then launch the produced installer/app from its output dir and confirm the Anki window opens. (Captured in Phase E clean-machine recording.)

- [ ] **Step 4: Commit only if something tracked changed** (Option A usually changes nothing tracked — the pins already exist). If the build required re-pinning a submodule to a working commit, commit the gitlink + `.gitmodules`:

```bash
cd repos/anki
git add .gitmodules qt/installer/windows-template qt/installer/mac-template
git commit -m "fix(installer): initialize/pin briefcase template submodules so the installer builds"
```
If nothing tracked changed, record in the task tracker that C2 was an init/environment fix (no commit) and note it for the clean-machine step (C3 must run `git submodule update --init` as part of setup, OR use Option B so the clean machine needs no network).

#### Option B — vendor the Windows template in-tree (fallback, for offline/clean-machine robustness)

Only if Option A's submodule clone cannot be relied on at build time on a clean machine.

- [ ] **Step 1: Populate then de-submodule the Windows template**
```bash
cd repos/anki
git submodule update --init qt/installer/windows-template   # get the files once (needs network here)
git rm --cached qt/installer/windows-template               # remove the gitlink
rm -rf qt/installer/windows-template/.git
# remove the [submodule "briefcase-windows-template"] block from .gitmodules
```
Then `git add qt/installer/windows-template/` (now real files) so the template ships in-tree like `linux-template/`. Do the same for `mac-template` only if a mac installer build is in scope (Wed is Windows desktop — mac can stay a submodule if it isn't built).

- [ ] **Step 2: Adjust the build if it still expects a submodule** — `build/configure/src/installer.rs` calls `SyncSubmodule` for the win template. A vendored (non-submodule) path makes `SyncSubmodule` a no-op or error; if it errors, change that action to a plain file dependency (mirror how `linux-template` is handled — grep `installer.rs`/`build/` for how linux is fed, since linux is in-tree and builds). Ground the exact edit against the linux path before changing `installer.rs`.

- [ ] **Step 3: Build + package + smoke-launch** (same commands as Option A Steps 2-3), then commit:
```bash
git add .gitmodules qt/installer/windows-template/ build/configure/src/installer.rs
git commit -m "fix(installer): vendor Windows briefcase template in-tree (clean-machine build, no submodule clone)"
```

### Task C3: Clean-machine verification

**Files:** none (verification).

- [ ] **Step 1: Verify on a genuinely clean environment** (fresh Windows VM or a new user profile with no Anki/dev state, no Briefcase template cache at `%LOCALAPPDATA%\BeeWare\briefcase\Cache\`)

Copy the built installer artifact to the clean machine, install, and launch. Expected: installs and opens the Anki window with no missing-DLL / no network-dependency errors. If it fails, return to C1 (systematic-debugging) — do not patch blindly.

- [ ] **Step 2: Import the seed deck on the clean install** (proves the full loop end-to-end)

In the clean-installed Anki: File → Import → `gre_math_seed.apkg`. Confirm cards appear and review runs. (Captured in Phase E.)

- [ ] **Step 3: Record the outcome** in the task tracker (pass/fail + environment description).

---

# Phase D — §7a artifacts — CRITICAL (low effort)

**Outcome:** two short docs in the private umbrella that make the Rust-fit case (20% rubric) and honestly inventory upstream impact. These are documentation → they live in the umbrella `docs/` (per the STATE.md repo boundary), NOT the public forks.

> **Coordination note for Cursor:** Cursor owns `docs/`. These artifacts are drafted here for review; Cursor merges/relocates as it sees fit.

### Task D1: "Why this belongs in Rust, not Python" one-pager

**Files:**
- Create: `docs/artifacts/why-rust-not-python.md`

- [ ] **Step 1: Write the note** (grounded in the actual change — `GetCoverage` + `GetTopicMastery` reading FSRS state in `rslib`)

`docs/artifacts/why-rust-not-python.md`:
```markdown
# Why the Speedrun engine change belongs in Rust (`rslib`), not Python

**The change:** read-only `SpeedrunService` RPCs — `GetCoverage` (topic coverage vs
exam profile) and `GetTopicMastery` (per-topic FSRS retrievability -> mastered
proportion with a Wilson 95% range + abstain rule).

## 1. It must run on BOTH apps from ONE implementation
Desktop (PyO3) and Android (rsdroid JNI) share exactly one engine: `rslib`. A
Python/Qt add-on does not exist on Android. Anything cross-device must live in
the shared Rust core (or synced data). Putting the mastery aggregate in Python
would mean re-implementing it in Kotlin for the phone — two code paths, two sets
of bugs, guaranteed drift. In Rust it is written once and both apps call the
identical proto RPC. (Proven Wed by both apps returning the same engine version.)

## 2. It reads engine-internal FSRS state that only Rust owns
`GetTopicMastery` calls `FSRS::current_retrievability_seconds` over each card's
`memory_state`/`decay` and reads the revlog for graded-review counts. These are
`pub(crate)` internals of `rslib` (`Card.memory_state`, `Card.decay`,
`RevlogEntry::has_rating_and_affects_scheduling`). Python only sees what the
backend chooses to expose; doing this in Python would require exporting raw FSRS
state across the PyO3 boundary and reconstructing the scheduler's math in Python
— slower, and forked from the source of truth.

## 3. Performance & correctness at the data layer
Aggregation runs next to SQLite via the storage layer (`search_cards`,
`get_card`, `get_revlog_entries_for_card`) with no per-card IPC round-trip. The
§10 targets (dashboard refresh < 500ms on a 50k deck) are reachable because the
loop stays in-process in Rust; the same loop in Python would pay PyO3 crossing
cost per card.

## 4. Correctness/safety guarantees are strongest here
Read-only by construction (no `transact`, no `Op`, no DB writes) ⇒ undo intact,
`pragma integrity_check == ok` (asserted in tests). Additive proto (new field
numbers only) keeps the contract forward-compatible for both bridges.

## 5. What we deliberately did NOT put in Rust
IRT/calibration, RAG, and AI generation live in an external Python/FastAPI
service (off until Friday) — they are not engine concerns and must not bloat the
native lib shipped to phones. The Rust/Python seam is drawn at exactly the right
place: engine-state math in Rust, model/AI orchestration in Python.
```

- [ ] **Step 2: Commit** (umbrella repo)

```bash
cd C:/Users/davir/Ultra/Alpha/Speedrun
git add docs/artifacts/why-rust-not-python.md
git commit -m "docs(artifacts): §7a — why the engine change belongs in Rust not Python"
```

### Task D2: Upstream files touched + merge-difficulty inventory

**Files:**
- Create: `docs/artifacts/upstream-files-touched.md`

- [ ] **Step 1: Generate the actual touched-file list from git** (ground it — do not hand-wave)

Run from `repos/anki`:
```bash
git diff --stat upstream/main...feat/speedrun-wed-mvp 2>/dev/null || git diff --stat main...feat/speedrun-wed-mvp
```
Record the file list. Classify each as **NEW (ours)** vs **MODIFIED (upstream)**.

- [ ] **Step 2: Write the inventory** (fill the table from Step 1's output — every path, additive vs modified, and merge risk)

`docs/artifacts/upstream-files-touched.md`:
```markdown
# Upstream files touched & future-merge difficulty

Fork: `spinkicks/anki`. Branch: `feat/speedrun-wed-mvp` (+ prior `b8b5369`).

## New files (ours; zero merge conflict risk — upstream never touches these)
- `proto/anki/speedrun.proto` — new service contract.
- `rslib/src/speedrun/mod.rs`, `rslib/src/speedrun/service.rs` — new module.
- `pylib/anki/speedrun.py`, `pylib/tests/test_speedrun.py` — new wrapper + tests.
- `speedrun/**` — content toolchain (isolated directory).
- `qt/installer/windows-template/**` — vendored installer template.

## Modified upstream files (the ONLY merge-conflict surface)
| File | Change | Merge difficulty |
|---|---|---|
| `rslib/src/lib.rs` | +1 line: `pub mod speedrun;` | Trivial — one additive line in a module list. |
| `rslib/proto/src/lib.rs` | +1 line: `protobuf!(speedrun, "speedrun");` | Trivial — one additive, alphabetized line. |
| `pylib/anki/collection.py` | +2 lines: import + instantiate `SpeedrunManager` | Trivial — additive near other managers. |
| `qt/installer/app/pyproject.toml` | +1 line: `template = "../windows-template"` under `[...windows]` | Low — a single key in a section upstream rarely edits. |

## Assessment
All engine/logic changes are **new files**; upstream contact is **4 additive
lines + 1 installer key**, no edits to existing function bodies. Rebasing onto a
new Anki release is expected to be conflict-free or a one-line re-application.
The additive-proto rule guarantees the wire contract stays compatible.
```

- [ ] **Step 3: Commit** (umbrella)

```bash
cd C:/Users/davir/Ultra/Alpha/Speedrun
git add docs/artifacts/upstream-files-touched.md
git commit -m "docs(artifacts): §7a — upstream files touched + merge-difficulty inventory"
```

---

# Phase E — Proof recordings — CRITICAL

**Outcome:** the four required proofs captured to the private umbrella `docs/proof/`, indexed in `PROOF.md` with commit SHAs. (Recordings are binary/manual; commit the index + links; store large videos where the team keeps media.)

### Task E1: Capture the four proofs

**Files:**
- Create: `docs/proof/PROOF.md`
- Add: recording files (or links) under `docs/proof/`

- [ ] **Step 1: Clean-build recording** — screen-record `just check` from a clean tree passing (Rust + Python speedrun tests visibly green). Save as `docs/proof/01-clean-build.mp4` (or link).

- [ ] **Step 2: Test-results capture** — save the terminal output of `cargo test -p anki speedrun::` and `just test-py 2>&1 | grep -A3 speedrun` to `docs/proof/02-test-results.txt`.

- [ ] **Step 3: Clean-machine install recording** — screen-record the Phase C3 clean-machine install + launch + seed-deck import. Save as `docs/proof/03-clean-install.mp4`.

- [ ] **Step 4: Phone review-session recording** — on the AnkiDroid emulator (the Phase-2 `Pixel_10` AVD) running our engine: import `gre_math_seed.apkg`, then screen-record a real review session (flip cards, grade several, MathJax rendering visible). Save as `docs/proof/04-phone-review.mp4`.

- [ ] **Step 4b: Honest-score demonstration (REQUIRED — Wednesday grades "a memory model running, with an honest score: a range + give-up rule").** Capture the memory model actually reporting the honest score. Minimum: in the desktop Debug Console against the imported seed deck, call `col.speedrun.topic_mastery(["calc::single_var::integration", "linear_algebra::eigen"])` and record the output showing `avg_recall`, the Wilson range (`mastered_lower`/`mastered_upper`), and the **`abstained`** give-up flag (a fresh unreviewed deck should abstain — that IS the honest behavior). Save as `docs/proof/05-honest-score.(mp4|txt)`. **Preferred:** capture Cursor's minimal Svelte/TS memory-score panel instead/additionally (built on this RPC seam — coordinate with Cursor). This proof, not just the RPC's existence, is what satisfies the requirement.

- [ ] **Step 5: Write the index**

`docs/proof/PROOF.md`:
```markdown
# Wednesday MVP — proof index

| Proof | Artifact | Engine SHA (spinkicks/anki) |
|---|---|---|
| Clean build (checks green) | 01-clean-build.mp4 | <feat/speedrun-wed-mvp HEAD> |
| Test results (Rust + Python) | 02-test-results.txt | <same> |
| Clean-machine install + import | 03-clean-install.mp4 | <same> |
| Phone review session on seed deck | 04-phone-review.mp4 | <same> |

Deck: speedrun/out/gre_math_seed.apkg. NO AI used in any Wednesday deliverable.
```

- [ ] **Step 6: Commit** (umbrella)

```bash
cd C:/Users/davir/Ultra/Alpha/Speedrun
git add docs/proof/
git commit -m "docs(proof): Wednesday MVP proof index + recordings (clean build, tests, install, phone review)"
```

---

## Self-review against the Wednesday scope

**Requirement coverage:**

| Wednesday requirement | Covered by | Notes |
|---|---|---|
| 1. Topic-tagged calc+LA seed deck (hand-authored core) | A2 | ≥30 `Speedrun::Declarative` notes, hierarchical tags, `Source` per note; committed `.apkg`. |
| 1. Deterministic non-LLM scraper, open-licensed only, Source + rule tags | A3 (FLEX) | HTML/LaTeX parser, keyword rules, drops untaggable content; OpenStax CC-BY / public-domain only. |
| 1. Exam-profile config (taxonomy/DAG + ETS weights) | A1 | `gre_math.json` + schema + acyclicity/weight tests. |
| 2. Read-only `GetTopicMastery` RPC (FSRS retrievability aggregate + mastered count + avg recall) | B1–B3 | Grounded in `rslib` FSRS APIs; read-only, no transact. |
| 2. Honest score with RANGE (Wilson/bootstrap) | B2 | Wilson 95% interval (deterministic; chosen over bootstrap for exact tests). |
| 2. Give-up/abstain rule (below N graded reviews) | B2/B3 | `abstained = graded_reviews < min_reviews \|\| cards_with_data == 0`. |
| 2. ≥3 Rust tests + 1 Python integration test | B2 (4 unit) + B3 (1 Rust integration) + B4 (1 Python) | 5 Rust + 1 Python; exceeds floor. |
| 2. Clean data seam for Cursor's UI; no Svelte here | B4 | Proto RPC + `col.speedrun.topic_mastery()` wrapper only. |
| 3. Fix Briefcase clean-machine installer | C1–C3 | Root-cause (unvendored template) → vendor+pin → clean-machine verify. |
| 4. §7a "why Rust not Python" + upstream-files/merge list | D1, D2 | Grounded in the actual diff. |
| 5. Proof checklist (build, tests, install, phone review) | E1 | Four artifacts + index. |

**Invariants:** additive proto (new rpc + messages, fields 1–8, `GetCoverage` untouched) ✅; read-only RPC, no `transact`/`Op`, `integrity_check` asserted ✅; APIs grounded via Serena/grep + `cargo check` before edits ✅; AGPL headers on every new source file ✅; NO AI anywhere ✅; code → forks, docs → umbrella ✅.

**Placeholder scan:** no TBD/"handle errors"/"similar to". The only intentionally late-bound values are Phase-C build-time facts (exact Briefcase invocation, upstream template URL/tag) and Phase-D/E capture values (diff output, SHAs, recordings) — each with an explicit grounding command, appropriate because they cannot be known until the earlier step runs. The seed-card YAML provides a complete runnable starter set with an explicit "author more in this exact shape to reach ≥30" data-entry instruction (data authoring, not a code placeholder).

**Type/name consistency:** `topic_aggregate(&[f64], f64) -> (u32,u32,f64)` and `wilson_interval(u32,u32,f64) -> (f64,f64)` are defined in `mod.rs` (B2) and called identically in `service.rs` (B3). Proto field names (`GetTopicMasteryRequest.{topics,mastery_threshold,min_reviews}`, `TopicMastery.{topic,cards_with_data,mastered_count,avg_recall,mastered_lower,mastered_upper,graded_reviews,abstained}`, `TopicMasteryResponse.{topics,backend_version}`) match across proto (B1), Rust impl (B3), Rust test (B3), Python wrapper (B4), and Python test (B4). `col.speedrun.topic_mastery(...)` defined in B4, used in B4's test. Constants `MASTERY_THRESHOLD_DEFAULT`/`MIN_REVIEWS_DEFAULT`/`WILSON_Z_95` defined once in `mod.rs`, used in `service.rs`.

**Verdict:** the plan covers every Wednesday requirement with grounded paths/symbols, lands a genuine additive read-only engine change via strict TDD, honors all hard invariants, keeps AI out, correctly splits code (forks) from docs (umbrella), and marks the single FLEX item (scraper). Ready for Cursor's review.

---

## ~~STOP — awaiting Cursor review~~ (RESOLVED)

Reviewed by Cursor, approved, executed, and merged to `main` @ `92f4ebd`. See the STATUS banner at the top.
