# Wednesday MVP — deliverables & proof tracker

> **Historical Wednesday checkpoint. For full ship status see `docs/STATE.md` / `docs/PROGRESS.md`.**

> Maps the Wednesday rubric to status + owner + action. Updated 2026-07-01. Legend: ✅ done · ⚠️ partial · ⬜ not started. **Honesty:** proofs are only "done" once actually captured.

## Desktop
| Requirement | Status | Owner | Action |
|---|---|---|---|
| Anki forked + building from source | ✅ | — | `just run`/`just build` green |
| Rust change e2e (diff + 3 Rust unit + 1 Python) | ✅ exceeded | — | 5 RPCs incl. mutating reorder; ~15 Rust + Python tests |
| Review loop on exam deck | ✅ | — | seed deck imports; START RUN launches reviewer |
| Memory model honest score (range + give-up) | ✅ | — | Wilson 95% + abstain, in Home + Memory |
| **Installer runs on a clean machine** | ✅ | David | ✅ Claude packaged the release MSI: `repos/anki/out/installer/dist/anki-26.05-win-x64.msi` (627,602,302 B ≈599 MiB, release engine, built offline from `main` @ `af1138428`, `test_installer.py` 27/27). ✅ Clean-machine install captured — `CleanTestInstall.mp4` (see PROOF-INDEX). |

## Mobile
| Requirement | Status | Owner | Action |
|---|---|---|---|
| Builds + runs on emulator | ✅ | — | Pixel_10 |
| Loads exam deck + real review session (shared engine) | ⚠️ | David | import `gre_math_seed.apkg` on emulator, run a real review, record |

## Proof artifacts (all David to capture; some blocked)
| Proof | Status | Note |
|---|---|---|
| Commit hashes | ✅ | anki/backend/android `main` SHAs in STATE.md |
| Clean-build recording | ⬜ | `just run` / `just build` from clean checkout |
| Test results | ✅ producible | `cargo test -p anki speedrun::` + `just check` output |
| Clean-machine install recording | ✅ | captured as `CleanTestInstall.mp4` (per PROOF-INDEX) — installer runs on a pristine machine |
| Phone review-session recording | ⬜ | pairs with the demo video |

## Correct installer rebuild command (grounded 2026-07-01)
The single `uv run python qt/tools/build_installer.py … build` line is **wrong** — it omits our fork wheels and pulls upstream Anki from PyPI (needs network). Canonical, offline path (from `repos/anki`, Windows): set `RELEASE=1`, run the `installer:build` ninja target, then `build_installer.py … package`. Artifact lands at `out/installer/dist/anki-26.05-win-x64.msi`. (~599 MiB: WiX LZX compresses the Qt6+Chromium payload poorly; slimming to ~150 MiB via symbol-strip/prune is a separate optional task.)

## Installer / .dmg decision (2026-07-01)
- **Decision:** ship + record the **Windows installer** — satisfies "an installer that runs on a clean machine." No `.dmg` this cycle.
- **.dmg is macOS-only** and cannot be built on the Windows dev machine. If a `.dmg` is later required: build an **unsigned `.dmg` on a macOS GitHub Actions runner** (no Apple Developer account needed; Gatekeeper-warns but runs). Documented fallback, not built.

## Clean-machine proof — easiest path
1. **Windows Sandbox** (Win Pro/Enterprise): enable in "Turn Windows features on/off" → launch → drag the installer in → run → confirm Speedrun launches → record. Disposable, pristine, ~5 min.
2. Fallback (Win Home / no Sandbox): a throwaway Hyper-V/VirtualBox Windows VM (Cursor can guide setup).
