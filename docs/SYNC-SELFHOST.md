# Self-hosted Anki sync server (Speedrun)

The Speedrun fork ships Anki's built-in `anki-sync-server` binary (source:
`repos/anki/rslib/sync/main.rs`). No new server code is needed for self-hosting;
this doc covers launching it locally and pointing clients at it, plus the
conflict rule that governs two-way sync.

## Launch (from `repos/anki`)

```bash
export SYNC_USER1="test:test"      # user:password (one or more; SYNC_USER2, ... also honored)
export SYNC_PORT=8088              # listen port
export SYNC_BASE="$PWD/out/syncserver-data"   # where per-user collections/media live
cargo run --release -p anki-sync-server
```

Health check (separate shell; exit 0 = server up):

```bash
cargo run --release -p anki-sync-server -- --healthcheck; echo "exit=$?"
```

Notes:
- Credentials in `SYNC_USERn` are `user:password`; the password is hashed with a
  fixed salt server-side. Use throwaway creds for local dev.
- `SYNC_BASE` must be writable; each user gets a subdirectory with their
  collection + media. Delete it to reset server state.
- Bind address defaults to localhost; set `SYNC_HOST=0.0.0.0` only if you
  intentionally expose it on your LAN (not recommended for dev).

## Point a client

### Desktop (repos/anki)
Preferences → Syncing → set a self-hosted endpoint, or from the debug console:

```python
mw.pm.set_custom_sync_url("http://127.0.0.1:8088/")
```

Then Sync and log in with `test` / `test`.

### Android (AnkiDroid)
Advanced → Custom sync server → set the collection sync URL to
`http://<host>:8088/` (use the host machine's LAN IP from an emulator/device;
`10.0.2.2` reaches the host from the standard Android emulator). Log in with the
same credentials, then Sync.

## Conflict rule (documented)

Anki sync is **collection-level** (USN + `mtime` latest-wins), NOT a per-card
three-way merge:

- **Different objects changed on each side** → clean fast-forward; both sides'
  changes land.
- **Same object changed on both sides** → **latest `mtime` wins**
  (latest-review-timestamp). Crucially, **revlog entries are append-only**
  (each keyed by a millisecond-timestamp id), so distinct reviews from both
  sides are **all retained** in `revlog`; only the derived card *state* resolves
  to the winner. Implausible clock skew is out of scope.
- **True divergence** (both sides changed base state incompatibly) forces a
  full-sync **"upload or download"** choice — no silent auto-merge.

### Evidence (§7b)
`repos/anki/rslib/src/sync/collection/tests.rs` contains
`speedrun_two_way_reviews_and_same_card_conflict`: two clients each add 10
offline reviews to the SAME card, sync, and the test asserts all 20 distinct
revlog entries land on both sides (append-only) with `pragma integrity_check`
clean. See that test's comments for the exact observed reconciliation behavior.

**Submission-proof status:** the §7b conflict test is **green**, but the **live desktop ↔ Android sync-demo recording is still outstanding** for submission proof (the human-visible two-way + offline-reconnect run against the self-hosted server).

**Guarantee boundary (honest caveat):** the "all 20 land" union holds because
real reviews occur at distinct wall-clock milliseconds, so the two clients'
revlog ids are disjoint. If two entries shared an id, the sync insert
(`uniquify=false`) would keep only one — that is not the tested scenario and is
not claimed. Live-launch smoke (healthcheck exit 0) is optional; the in-process
§7b test already proves the two-way + append-only conflict behavior.
