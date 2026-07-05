# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Speedrun one-command launcher (Windows / PowerShell 5.1+).
#
# Replaces the manual multi-terminal setup documented in docs/DEMO-VIDEO-SCRIPT.md
# with a single command. It starts the pieces an operator wants and reports
# readiness:
#   -Ai      the external AI generation service (services/speedrun-ai, port 8000)
#   -Sync    the self-hosted Anki sync server (repos/anki, port 8088)
#   -App     the desktop app (`just run` in repos/anki) in its own window, launched
#            with SPEEDRUN_AI_ENABLED=1 in its env so the AI "Generate" button works
#   -All     AI + Sync + desktop app (this is also the no-flag default)
#   -Stop    cleanly stop the background services THIS launcher started
#   -Status  show what is currently up (ports 8000/8088 + /health)
#
# WHY the app needs SPEEDRUN_AI_ENABLED in its OWN env: the desktop button's
# enable check (qt/aqt/speedrun_ai.py `env_enabled`) reads SPEEDRUN_AI_ENABLED
# from Anki's process environment, not from services/speedrun-ai/.env. Starting
# the service alone is not enough; the app process must also see the flag. This
# launcher sets it before `just run` (without editing repos/anki).
#
# This is an ADDITIVE convenience — the manual steps still work unchanged.
# It builds on Anki (https://github.com/ankitects/anki); the sync server binary
# and desktop app are Anki's, invoked here without modification.
#
# Design notes:
#   * Idempotent: it will NOT double-start a service whose port is already
#     listening, and only stops services it started itself (tracked by PID).
#   * Offline: no new runtime network dependencies. `uv sync` on an already
#     provisioned venv is offline; a first-ever `uv sync` is the only step that
#     needs the network (one-time setup).
#   * Collision-safe: prefers a prebuilt `anki-sync-server.exe` so the common
#     path does NOT recompile inside repos/anki. It never EDITS anything under
#     repos/anki or repos/anki-android — it only invokes documented commands.

[CmdletBinding()]
param(
    [switch]$Ai,
    [switch]$Sync,
    [switch]$App,
    [switch]$All,
    [switch]$Stop,
    [switch]$Status,
    [int]$AiPort = 8000,
    [int]$SyncPort = 8088
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$ScriptRoot = $PSScriptRoot
$RepoRoot   = Split-Path -Parent $ScriptRoot
$AiDir      = Join-Path $RepoRoot 'services\speedrun-ai'
$AnkiDir    = Join-Path $RepoRoot 'repos\anki'

if ($env:LOCALAPPDATA) {
    $StateDir = Join-Path $env:LOCALAPPDATA 'SpeedrunLaunch'
} else {
    $StateDir = Join-Path $env:TEMP 'SpeedrunLaunch'
}
$StateFile  = Join-Path $StateDir 'state.json'
$AiLog      = Join-Path $StateDir 'ai.log'
$AiErrLog   = Join-Path $StateDir 'ai.err.log'
$AiSyncLog  = Join-Path $StateDir 'ai-uvsync.log'
$SyncLog    = Join-Path $StateDir 'sync.log'
$SyncErrLog = Join-Path $StateDir 'sync.err.log'

# ---------------------------------------------------------------------------
# Small console helpers (avoid clobbering built-ins: Write-Warn/-Err/-Info/-Ok)
# ---------------------------------------------------------------------------
function Write-Section([string]$m) { Write-Host ""; Write-Host ("== " + $m + " ==") -ForegroundColor Cyan }
function Write-Ok([string]$m)      { Write-Host ("  [OK]   " + $m) -ForegroundColor Green }
function Write-Warn([string]$m)    { Write-Host ("  [WARN] " + $m) -ForegroundColor Yellow }
function Write-Err([string]$m)     { Write-Host ("  [ERR]  " + $m) -ForegroundColor Red }
function Write-Info([string]$m)    { Write-Host ("  [..]   " + $m) -ForegroundColor Gray }

function Initialize-StateDir {
    if (-not (Test-Path $StateDir)) {
        New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    }
}

# ---------------------------------------------------------------------------
# State (JSON in %LOCALAPPDATA%\SpeedrunLaunch\state.json). Only services this
# launcher STARTED are tracked, so -Stop never kills something it didn't spawn.
# ---------------------------------------------------------------------------
function Get-LaunchState {
    if (Test-Path $StateFile) {
        try {
            $obj = Get-Content $StateFile -Raw | ConvertFrom-Json
            $h = @{}
            foreach ($p in $obj.PSObject.Properties) { $h[$p.Name] = $p.Value }
            return $h
        } catch {
            return @{}
        }
    }
    return @{}
}

function Set-LaunchState($state) {
    Initialize-StateDir
    ($state | ConvertTo-Json -Depth 6) | Set-Content -Path $StateFile -Encoding UTF8
}

function Record-Service([string]$name, [int]$procId, [int]$port, [string]$log, [string]$cmd) {
    $state = Get-LaunchState
    $state[$name] = @{
        pid     = $procId
        port    = $port
        log     = $log
        cmd     = $cmd
        started = (Get-Date).ToString('s')
    }
    Set-LaunchState $state
}

# ---------------------------------------------------------------------------
# Port / process helpers
# ---------------------------------------------------------------------------
function Test-PortListening([int]$Port) {
    try {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        if ($c) { return $true }
    } catch { }
    # Fallback for hosts without Get-NetTCPConnection: try a loopback connect.
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        $connected = $ok -and $client.Connected
        $client.Close()
        return [bool]$connected
    } catch {
        return $false
    }
}

function Get-PortPid([int]$Port) {
    try {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($c) { return [int]$c.OwningProcess }
    } catch { }
    return $null
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 5 -ErrorAction Stop
        } catch {
            Start-Sleep -Milliseconds 800
        }
    }
    return $null
}

function Stop-Tree([int]$ProcId) {
    & taskkill /PID $ProcId /T /F *> $null
    return ($LASTEXITCODE -eq 0)
}

function Show-SyncEndpoints {
    Write-Host "         Desktop URL : http://127.0.0.1:$SyncPort/"
    Write-Host "         Emulator URL: http://10.0.2.2:$SyncPort/   (Android emulator -> host PC)"
    Write-Host "         Login       : test / test"
}

# ---------------------------------------------------------------------------
# Start: AI service
# ---------------------------------------------------------------------------
function Start-AiService {
    Write-Section "AI service (port $AiPort)"

    $envFile = Join-Path $AiDir '.env'
    if (-not (Test-Path $envFile)) {
        Write-Warn "No .env at $envFile."
        Write-Warn "Create it with OPENAI_API_KEY=<key> and SPEEDRUN_AI_ENABLED=1 (else /generate returns 503)."
    } else {
        $envText = Get-Content $envFile -Raw
        $hasKey  = $envText -match '(?m)^\s*OPENAI_API_KEY\s*=\s*\S'
        $enabled = $envText -match '(?m)^\s*SPEEDRUN_AI_ENABLED\s*=\s*(1|true|yes|on|y|t)\b'
        if (-not $hasKey)  { Write-Warn "OPENAI_API_KEY missing/empty in .env -> /generate will 503." }
        if (-not $enabled) { Write-Warn "SPEEDRUN_AI_ENABLED not truthy in .env -> /generate will 503." }
    }

    if (Test-PortListening $AiPort) {
        Write-Ok "Port $AiPort already listening -> not starting a second AI service."
        Report-AiHealth
        return
    }

    Write-Info "Ensuring Python deps (uv sync); offline when the venv is already provisioned..."
    $code = 0
    Push-Location $AiDir
    try {
        & uv sync *>> $AiSyncLog
        $code = $LASTEXITCODE
    } catch {
        $code = 1
        $_ | Out-String | Add-Content -Path $AiSyncLog
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Err "uv sync failed (exit $code). See $AiSyncLog."
        return
    }

    try {
        $proc = Start-Process -FilePath 'uv' `
            -ArgumentList 'run', 'uvicorn', 'app:app', '--port', "$AiPort" `
            -WorkingDirectory $AiDir -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $AiLog -RedirectStandardError $AiErrLog
    } catch {
        Write-Err "Failed to launch uvicorn: $($_.Exception.Message)"
        return
    }
    Record-Service 'ai' $proc.Id $AiPort $AiLog "uv run uvicorn app:app --port $AiPort"
    Write-Info "Launched AI service (pid $($proc.Id)); waiting for /health..."

    $health = Wait-Http "http://127.0.0.1:$AiPort/health" 60
    if ($health) {
        if ($health.ai_enabled) {
            Write-Ok "AI up: ai_enabled=true  (http://127.0.0.1:$AiPort/health)"
        } else {
            Write-Warn "AI up but ai_enabled=false -> set OPENAI_API_KEY + SPEEDRUN_AI_ENABLED=1 in $envFile."
        }
    } else {
        Write-Warn "AI did not answer /health within 60s. See $AiLog / $AiErrLog."
    }
}

function Report-AiHealth {
    $health = $null
    try { $health = Invoke-RestMethod "http://127.0.0.1:$AiPort/health" -TimeoutSec 4 } catch { }
    if ($health) {
        if ($health.ai_enabled) { Write-Ok "  /health -> ai_enabled=true" }
        else { Write-Warn "  /health -> ai_enabled=false (check .env)" }
    }
}

# ---------------------------------------------------------------------------
# Start: self-hosted sync server
# ---------------------------------------------------------------------------
function Start-SyncService {
    Write-Section "Self-hosted sync server (port $SyncPort)"

    if (Test-PortListening $SyncPort) {
        Write-Ok "Port $SyncPort already listening -> not starting a second sync server."
        Show-SyncEndpoints
        return
    }

    $syncBase = Join-Path $AnkiDir 'out\syncserver-data'
    if (-not (Test-Path $syncBase)) { New-Item -ItemType Directory -Force -Path $syncBase | Out-Null }
    $env:SYNC_USER1 = 'test:test'
    $env:SYNC_PORT  = "$SyncPort"
    $env:SYNC_BASE  = $syncBase

    $binary = Join-Path $AnkiDir 'target\release\anki-sync-server.exe'
    $waitSec = 30
    try {
        if (Test-Path $binary) {
            Write-Info "Using prebuilt binary (no recompile): $binary"
            $proc = Start-Process -FilePath $binary -WorkingDirectory $AnkiDir `
                -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput $SyncLog -RedirectStandardError $SyncErrLog
            $cmd = "$binary"
        } else {
            Write-Warn "No prebuilt binary found; falling back to 'cargo run --release -p anki-sync-server'."
            Write-Warn "First run COMPILES the server (several minutes) and may contend with an active repos/anki build."
            $proc = Start-Process -FilePath 'cargo' `
                -ArgumentList 'run', '--release', '-p', 'anki-sync-server' `
                -WorkingDirectory $AnkiDir -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput $SyncLog -RedirectStandardError $SyncErrLog
            $cmd = "cargo run --release -p anki-sync-server"
            $waitSec = 240
        }
    } catch {
        Write-Err "Failed to launch sync server: $($_.Exception.Message)"
        return
    }
    Record-Service 'sync' $proc.Id $SyncPort $SyncLog $cmd
    Write-Info "Launched sync server (pid $($proc.Id)); waiting up to $waitSec s to listen on $SyncPort..."

    $up = $false
    $deadline = (Get-Date).AddSeconds($waitSec)
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            Write-Err "Sync process exited early (code $($proc.ExitCode)). See $SyncLog / $SyncErrLog."
            break
        }
        if (Test-PortListening $SyncPort) { $up = $true; break }
        Start-Sleep -Milliseconds 1000
    }
    if ($up) {
        Write-Ok "Sync server listening on $SyncPort."
        Show-SyncEndpoints
    } else {
        Write-Warn "Sync server not listening yet (still compiling?). Re-check with -Status or see $SyncLog."
    }
}

# ---------------------------------------------------------------------------
# Start: desktop app (visible window so the operator can watch the build)
# ---------------------------------------------------------------------------
function Start-DesktopApp {
    Write-Section "Desktop app (just run)"
    Write-Warn "This BUILDS the desktop app in repos/anki (can take a while), then opens Speedrun Home."

    # CRITICAL setup-gap fix (the reason the AI "Generate practice" button looks
    # broken): the desktop app reads SPEEDRUN_AI_ENABLED from its OWN process
    # environment (qt/aqt/speedrun_ai.py `env_enabled`, ~L68-72) -- NOT from
    # services/speedrun-ai/.env. Launching `just run`/the MSI without this flag
    # leaves the button permanently disabled even when the service is up. We set
    # it in THIS PowerShell context so the child `just run` (and the app it
    # spawns) inherit it -- no repos/anki edit. Only the flag is set; the OpenAI
    # key stays in the service's env (the app never needs the key). We also pin
    # SPEEDRUN_AI_URL to the chosen AI port so a custom -AiPort still resolves.
    $env:SPEEDRUN_AI_ENABLED = '1'
    $env:SPEEDRUN_AI_URL = "http://127.0.0.1:$AiPort"
    Write-Info "Set SPEEDRUN_AI_ENABLED=1 + SPEEDRUN_AI_URL=http://127.0.0.1:$AiPort for the app process."

    try {
        $proc = Start-Process -FilePath 'just' -ArgumentList 'run' `
            -WorkingDirectory $AnkiDir -PassThru
    } catch {
        Write-Err "Failed to launch 'just run': $($_.Exception.Message)"
        return
    }
    Record-Service 'app' $proc.Id 0 '(visible window)' 'just run'
    Write-Ok "Launched 'just run' (pid $($proc.Id)) in its own window; Speedrun Home opens when the build finishes."
    Write-Ok "Generate button will enable once you pick a covered leaf topic AND the AI /health reports ai_enabled:true."
}

# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------
function Stop-Services {
    Write-Section "Stopping launcher-started services"
    $state = Get-LaunchState
    $any = $false
    foreach ($name in @('ai', 'sync', 'app')) {
        if ($state.ContainsKey($name) -and $state[$name].pid) {
            $procId = [int]$state[$name].pid
            Write-Info "Stopping $name (pid $procId)..."
            if (Stop-Tree $procId) { Write-Ok "Stopped $name (pid $procId)." }
            else { Write-Warn "$name (pid $procId) was not running / already stopped." }
            $any = $true
        }
    }
    Set-LaunchState @{}
    if (-not $any) { Write-Info "No launcher-tracked services to stop." }

    foreach ($p in @($AiPort, $SyncPort)) {
        if (Test-PortListening $p) {
            $owner = Get-PortPid $p
            Write-Warn "Port $p still listening (pid $owner) but was NOT started by this launcher; leaving it alone."
        }
    }
}

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
function Show-Status {
    Write-Section "Status"

    if (Test-PortListening $AiPort) {
        $owner = Get-PortPid $AiPort
        $health = $null
        try { $health = Invoke-RestMethod "http://127.0.0.1:$AiPort/health" -TimeoutSec 4 } catch { }
        if ($health) { Write-Ok "AI service : listening on $AiPort (pid $owner), ai_enabled=$($health.ai_enabled)" }
        else { Write-Ok "AI service : listening on $AiPort (pid $owner), /health not answering yet" }
    } else {
        Write-Info "AI service : not running (port $AiPort free)."
    }

    if (Test-PortListening $SyncPort) {
        $owner = Get-PortPid $SyncPort
        Write-Ok "Sync server: listening on $SyncPort (pid $owner)"
        Show-SyncEndpoints
    } else {
        Write-Info "Sync server: not running (port $SyncPort free)."
    }

    $state = Get-LaunchState
    if ($state.Keys.Count -gt 0) {
        Write-Info "Launcher-tracked (state: $StateFile):"
        foreach ($k in $state.Keys) {
            Write-Host ("         " + $k + " -> pid " + $state[$k].pid + ", log " + $state[$k].log)
        }
    }
}

# ---------------------------------------------------------------------------
# Final consolidated summary
# ---------------------------------------------------------------------------
function Show-FinalSummary([bool]$startedAi, [bool]$startedSync, [bool]$startedApp) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " SPEEDRUN IS COMING UP - here's what's running" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    if ($startedAi) {
        $health = $null
        try { $health = Invoke-RestMethod "http://127.0.0.1:$AiPort/health" -TimeoutSec 4 } catch { }
        if ($health) { $st = "ai_enabled=$($health.ai_enabled)" } else { $st = "starting... (check -Status)" }
        Write-Host ""
        Write-Host " AI service    http://127.0.0.1:$AiPort/health   ($st)"
        Write-Host "               log: $AiLog"
    }
    if ($startedSync) {
        Write-Host ""
        Write-Host " Sync server   http://127.0.0.1:$SyncPort/   (desktop)"
        Write-Host "               http://10.0.2.2:$SyncPort/   (Android emulator)"
        Write-Host "               login: test / test"
        Write-Host "               log: $SyncLog"
    }
    if ($startedApp) {
        Write-Host ""
        Write-Host " Desktop app   building + launching Speedrun Home in its own window"
        Write-Host "               SPEEDRUN_AI_ENABLED=1 set for the app -> the (lightning) Generate"
        Write-Host "               button enables once the AI /health reports ai_enabled:true."
    }

    Write-Host ""
    Write-Host " NEXT CLICKS" -ForegroundColor White
    if ($startedSync) {
        Write-Host "  Desktop : Preferences > Syncing > Self-hosted sync server >"
        Write-Host "            http://127.0.0.1:$SyncPort/ > close > Sync > login test/test > Upload to server"
        Write-Host "  Emulator: AnkiDroid > Settings > Sync > Custom sync server >"
        Write-Host "            http://10.0.2.2:$SyncPort/ > Sync > login test/test > Download from server"
    }
    if ($startedAi) {
        Write-Host "  AI      : desktop app > THE MAP > a covered leaf topic > (lightning) Generate practice"
    }
    Write-Host ""
    Write-Host " STOP ALL   powershell -ExecutionPolicy Bypass -File scripts\speedrun-launch.ps1 -Stop" -ForegroundColor White
    Write-Host " STATUS     powershell -ExecutionPolicy Bypass -File scripts\speedrun-launch.ps1 -Status" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
Initialize-StateDir

if ($Stop)   { Stop-Services; return }
if ($Status) { Show-Status;   return }

# No flags == -All. -All is the full one-command bring-up: AI + Sync + the
# desktop app (launched with SPEEDRUN_AI_ENABLED=1 so the Generate button works).
# Individual flags (-Ai / -Sync / -App) bring up only that piece.
$noneSpecified = -not ($Ai -or $Sync -or $App -or $All)
$doAi   = $Ai   -or $All -or $noneSpecified
$doSync = $Sync -or $All -or $noneSpecified
$doApp  = $App  -or $All -or $noneSpecified

Write-Host ""
Write-Host "  SPEEDRUN LAUNCHER" -ForegroundColor White
Write-Host "  (repo root: $RepoRoot)" -ForegroundColor DarkGray

if ($doAi)   { Start-AiService }
if ($doSync) { Start-SyncService }
if ($doApp)  { Start-DesktopApp }

Show-FinalSummary $doAi $doSync $doApp
