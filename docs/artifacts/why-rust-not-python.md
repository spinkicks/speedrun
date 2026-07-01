<!-- DRAFT for Cursor to review/place. Produced by the Wednesday-MVP execution
     (Claude Code). Not committed by Claude per the umbrella-docs ownership split. -->

# Why the Speedrun engine change belongs in Rust (`rslib`), not Python

**The change:** two read-only `SpeedrunService` RPCs in the shared Rust core —
`GetCoverage` (topic coverage vs the exam profile) and `GetTopicMastery`
(per-topic FSRS retrievability → mastered proportion with a Wilson 95% range +
an abstain/give-up rule).

## 1. It must run on BOTH apps from ONE implementation
Desktop (PyO3) and Android (rsdroid JNI) share exactly one engine: `rslib`. A
Python/Qt add-on does not exist on Android. Anything cross-device must live in
the shared Rust core (or in synced data). Implementing the mastery aggregate in
Python would force a second Kotlin implementation for the phone — two code
paths, two sets of bugs, guaranteed drift. In Rust it is written once and both
apps call the identical proto RPC. (The walking skeleton already proved both
apps return the same engine version from this service.)

## 2. It reads engine-internal FSRS state that only Rust owns
`GetTopicMastery` calls `FSRS::current_retrievability_seconds` over each card's
`memory_state`/`decay` and reads the revlog for graded-review counts. These are
`pub(crate)` internals of `rslib` (`Card.memory_state`, `Card.decay`,
`Card::seconds_since_last_review`, `RevlogEntry::has_rating_and_affects_scheduling`).
Python only sees what the backend chooses to expose; doing this in Python would
mean exporting raw FSRS state across the PyO3 boundary and reconstructing the
scheduler's retrievability math in Python — slower and forked from the source of
truth.

## 3. Performance & correctness at the data layer
Aggregation runs next to SQLite via the storage layer (`search_cards`,
`get_card`, `get_revlog_entries_for_card`) with no per-card IPC round-trip. The
PRD §10 targets (dashboard refresh < 500 ms on a 50k deck) are reachable because
the loop stays in-process in Rust; the same loop in Python would pay a PyO3
crossing per card.

## 4. Correctness/safety guarantees are strongest here
Read-only by construction — no `transact`, no `Op`, no DB writes — so undo stays
intact and `pragma integrity_check == ok` (asserted in the Python integration
test). The proto is additive (new rpc + messages, new field numbers only;
`GetCoverage` untouched), keeping the wire contract forward-compatible for both
bridges.

## 5. What we deliberately did NOT put in Rust
IRT/calibration, RAG, and AI generation live in an external Python/FastAPI
service (off until Friday) — they are not engine concerns and must not bloat the
native lib shipped to phones. The honest score's **UI** (the Svelte/TS memory
dashboard) is likewise the desktop/TS layer's job; the Rust change stops at a
clean data seam (proto RPC + a thin `col.speedrun` Python wrapper). The
Rust/Python line is drawn where it belongs: engine-state math in Rust,
model/AI orchestration and presentation outside it.
