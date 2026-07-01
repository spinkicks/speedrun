# Claude Code UserPromptSubmit hook -> if Cursor's review channel changed since
# Claude last saw it, inject a one-line nudge into Claude's context on David's
# NEXT prompt. Non-interrupting by design: it only rides on a prompt David is
# already sending, never fires mid-thinking, and always exits 0 (never blocks
# the prompt). Stdout from a UserPromptSubmit hook is added as context.
$ErrorActionPreference = "SilentlyContinue"
$review = "C:\Users\davir\Ultra\Alpha\Speedrun\.claude\cursor-review.md"
$marker = "C:\Users\davir\Ultra\Alpha\Speedrun\.claude\.cursor-review.seen"

# Drain stdin (the hook payload) so Claude Code doesn't block on the pipe.
[void][Console]::In.ReadToEnd()

if (-not (Test-Path $review)) { exit 0 }
$mtime = (Get-Item $review).LastWriteTimeUtc.Ticks
$seen = 0
if (Test-Path $marker) { $seen = [int64](Get-Content $marker -Raw).Trim() }

if ($mtime -gt $seen) {
    # Only nudge if there is actually a Pending item (avoid noise on housekeeping edits).
    $body = Get-Content $review -Raw
    $pending = ($body -split "## Resolved")[0]
    if ($pending -notmatch "\(none") {
        Write-Output "[mission-control] .claude/cursor-review.md has new PENDING review feedback from Cursor — read it before continuing this turn."
    }
    Set-Content -Path $marker -Value $mtime
}
exit 0
