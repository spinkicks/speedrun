<!--
Copyright: Speedrun contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
Builds on Anki (https://github.com/ankitects/anki).
-->

# Quickstart — one command to bring up Speedrun

This replaces the manual multi-terminal ceremony (Terminals A/B/E in
`docs/DEMO-VIDEO-SCRIPT.md`) with a **single PowerShell command**. It is an
additive convenience — every manual step still works unchanged.

## TL;DR

From the repo root (`c:\Users\davir\Ultra\Alpha\Speedrun`), in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\speedrun-launch.ps1 -All
```

That brings up **everything** and prints a consolidated "here's what's running +
the exact next clicks" summary:

- **AI service** on `http://127.0.0.1:8000` — runs `uv sync` if needed, validates
  `.env`, waits for `/health` to report `ai_enabled:true`.
- **Self-hosted sync server** on `http://127.0.0.1:8088` (emulator:
  `http://10.0.2.2:8088`), login `test` / `test`.
- **Desktop app** (`just run`) in its own window — **launched with
  `SPEEDRUN_AI_ENABLED=1` in its environment so the ⚡ Generate button is
  enabled** once you pick a covered leaf topic (see "Why the AI button" below).

When you're done:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\speedrun-launch.ps1 -Stop
```

## Flags

| Command | What it starts |
| --- | --- |
| *(no flags)* or `-All` | AI service **+** sync server **+** desktop app (`SPEEDRUN_AI_ENABLED=1`) |
| `-Ai` | Only the AI generation service (port 8000) |
| `-Sync` | Only the self-hosted sync server (port 8088) |
| `-App` | Only the desktop app (`just run`), with `SPEEDRUN_AI_ENABLED=1` set for it |
| `-Status` | Show what's currently up (ports 8000/8088 + `/health`) — starts nothing |
| `-Stop` | Cleanly stop the background services this launcher started |

Optional: `-AiPort <n>` / `-SyncPort <n>` to override the default ports (the app
launch also pins `SPEEDRUN_AI_URL` to the chosen AI port).

It is **idempotent**: re-running never double-starts a service whose port is
already listening, and `-Stop` only kills processes this launcher started
(tracked by PID in `%LOCALAPPDATA%\SpeedrunLaunch\state.json`; logs live in the
same folder).

## Why the AI button needs the launcher (setup gap, not a bug)

The desktop app decides whether to enable the ⚡ **Generate practice** button by
reading `SPEEDRUN_AI_ENABLED` **from its own process environment**
(`qt/aqt/speedrun_ai.py` `env_enabled`), then probing the service's `/health`.
It does **not** read `services/speedrun-ai/.env`. So starting the AI service
alone is not enough — if you launch `just run` (or the MSI) without
`SPEEDRUN_AI_ENABLED=1` in the app's own environment, the button stays disabled
even though the service is up.

`-All` / `-App` fix this by setting `SPEEDRUN_AI_ENABLED=1` in the launching
PowerShell context **before** invoking `just run`, so the app inherits it. (The
OpenAI key is **not** propagated to the app — it stays in the service's env,
where it belongs; the app only needs the flag + a reachable `/health`.)

To enable the button when starting the app yourself, set the flag first:

```powershell
$env:SPEEDRUN_AI_ENABLED = "1"
cd repos\anki; just run
```

## Prerequisites

- `uv`, `just`, and `cargo` on `PATH` (see `docs/BUILD-PREREQS.md`).
- `services\speedrun-ai\.env` with `OPENAI_API_KEY=<key>` and
  `SPEEDRUN_AI_ENABLED=1` (only needed for the AI service to report
  `ai_enabled:true`; the study app scores fully without it).

## Notes

- **Offline / no new runtime deps.** `uv sync` on an already-provisioned venv is
  offline; only a first-ever `uv sync` touches the network. The launcher adds no
  runtime network dependency.
- **Sync server first run compiles.** If a prebuilt
  `repos\anki\target\release\anki-sync-server.exe` exists, the launcher uses it
  directly (no recompile). Otherwise it falls back to
  `cargo run --release -p anki-sync-server`, which compiles the server on first
  run (several minutes) and may contend with an active `repos/anki` build.
- **The launcher never edits `repos/anki` or `repos/anki-android`** — it only
  invokes the same documented commands (`uv run uvicorn`, `anki-sync-server`,
  `just run`).

## Manual fallback

The original per-terminal steps (including the Android emulator boot / APK
install / deck push, which the launcher does not automate) remain in
`docs/DEMO-VIDEO-SCRIPT.md` (Setup section) and `docs/SYNC-SELFHOST.md`.
