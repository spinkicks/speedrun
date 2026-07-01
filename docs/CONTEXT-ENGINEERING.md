# Context Engineering — Speedrun workflow playbook

Keeping agent context lean and high-signal. Grounded in Anthropic's *Effective context engineering for AI agents* + the compaction docs (2026) and installable `context-engineering` skills on skills.sh. Kept short on purpose — bloated guidance files *reduce* success (ETH Zurich).

## The core idea
Bigger windows don't save you: **context rot** means quality degrades *as the window fills* (attention spreads thin; info in the middle gets lost) — a gradual decline, not a cliff. Goal = **the smallest set of high-signal tokens**, not the most. Target compaction/reset around **~60–75%** of the window, not 95%+ (late compaction summarizes *after* reasoning already degraded).

## The 5-level context hierarchy (most persistent → most transient)
| Level | Content | Our files |
|---|---|---|
| 1. Rules | project standards/invariants (always loaded) | root `AGENTS.md`, `repos/anki/CLAUDE.md`, `.cursor/rules/` |
| 2. Memory | cross-session state to resume from | `docs/STATE.md`, `docs/PROGRESS.md` |
| 3. Spec/arch | per-feature scope | `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/plans/*` |
| 4. Source | files loaded **only** for the current task | (just-in-time) |
| 5. Live state | errors, tool output, chat history | (compacts as it grows) |

## What we already do well (keep doing)
- **Subagent isolation** — Claude offloads each task to a fresh-context subagent that returns a ~1–2k-token summary; the orchestrator stays lean. This is the #1 lever and it's why our windows haven't blown up.
- **Fresh window per phase** — new Claude window for the Wednesday work; new Cursor chat when this one gets long.
- **Externalized memory** — STATE.md / PROGRESS.md / plan docs let a fresh agent resume from ~5 files instead of a full history. Compaction is "lossless in practice" when the agent can reconstruct from git + these files.
- **Digests over transcripts** — Cursor reads the small `.claude/watch.log` status lines, not the 1.5 MB transcript, each check.
- **Grounding recorded in plans** — so implementers don't re-derive APIs (burns context + risks drift).

## Rules of thumb (apply per turn)
1. **Compact/reset early**, at task-type transitions or after bulk reads you no longer need — not at the 95% wall.
2. **One task per subagent**, frozen contract, return a distilled summary (cap ~2k chars); max 3–4 parallel agents per wave.
3. **Just-in-time**: read a file right before editing it; don't pre-load whole subtrees. Never read `node_modules`/`out`/`target`/`build`/lockfiles into context.
4. **Clear between unrelated tasks** — the "kitchen-sink session" degrades every later task. Start fresh; load the right rules+memory.
5. **Write it down**: persist decisions to STATE.md/PROGRESS.md *immediately* (tool results may be cleared later).
6. **Rewind beats correction**: drop a failed attempt from context rather than stacking error-fix messages on polluted reasoning.
7. **Keep rules files small**: `AGENTS.md` ≈ 500–1000 tokens; tables over prose; one example beats three; move static data to referenced files.

## Structured compaction template (when compacting a long session)
Require the summary to fill: `## Session intent · ## Files modified (full paths) · ## Key decisions · ## Active goals · ## Next steps`. Structured sections act as a checklist that prevents silent information loss.

## Gaps / TODO for us
- [ ] Cursor: start a fresh mission-control chat (reads STATE.md + PROGRESS.md) when this one is long — dogfood rule #4.
- [ ] Consider a `.claudeignore` / confirm `out/`, `target/`, `node_modules/` are excluded from agent reads.
- [ ] **Friday LangGraph tie-in**: the external AI service should make this explicit — bounded context per node + externalized graph state (checkpointers) = context engineering as architecture. Fold into that plan, not bolted on.

## Optional: installable skills (skills.sh)
Not required (we already do the core practices), but available if we want codified triggers:
- `npx skills add https://github.com/addyosmani/agent-skills --skill context-engineering` (MIT; the concise 5-level-hierarchy skill)
- `muratcankoylan/agent-skills-for-context-engineering` — deeper set (context-degradation, context-compression, harness-engineering) if we productionize the "software factory."

Decision: adopt these *tips* now; evaluate installing a skill only if agent output quality starts drifting.
