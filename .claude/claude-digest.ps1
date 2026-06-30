# Claude Code Stop/SubagentStop hook -> appends a compact digest line to a
# watch file that Cursor (mission control) tails for near-real-time updates.
# Reads the hook JSON payload from stdin; never blocks; always exits 0.
param([string]$EventName = "Stop")

$ErrorActionPreference = "SilentlyContinue"
$watch = "C:\Users\davir\Ultra\Alpha\Speedrun\.claude\watch.log"

# Let Claude Code finish flushing the transcript (it appends the assistant
# message + bookkeeping lines around when Stop fires) to avoid a mid-write race.
Start-Sleep -Milliseconds 600

$raw = [Console]::In.ReadToEnd()
$j = $null
try { $j = $raw | ConvertFrom-Json } catch { }

$ev = if ($j.hook_event_name) { $j.hook_event_name } else { $EventName }
$tp = $j.transcript_path
$ts = Get-Date -Format "HH:mm:ss"

$summary = ""
$fallback = ""
if ($tp -and (Test-Path $tp)) {
    $lines = Get-Content $tp -Tail 200
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        $o = $null
        try { $o = $lines[$i] | ConvertFrom-Json } catch { continue }
        if ($o.type -eq 'assistant' -and $o.message.content) {
            $t = ($o.message.content | Where-Object { $_.type -eq 'text' } | ForEach-Object { $_.text }) -join " "
            if ($t -and $t.Trim().Length -gt 0) { $summary = $t; break }
            # tool-only assistant turn: remember the tool(s) as a fallback
            if (-not $fallback) {
                $tools = ($o.message.content | Where-Object { $_.type -eq 'tool_use' } | ForEach-Object { $_.name }) -join ", "
                if ($tools) { $fallback = "(tool turn: $tools)" }
            }
        }
    }
}
if (-not $summary) { $summary = $fallback }

$summary = ($summary -replace '\s+', ' ').Trim()
if ($summary.Length -gt 400) { $summary = $summary.Substring(0, 400) + " ..." }
if (-not $summary) { $summary = "(no assistant text found in transcript tail)" }

Add-Content -Path $watch -Value ("[{0}][{1}] {2}" -f $ts, $ev, $summary)
exit 0
