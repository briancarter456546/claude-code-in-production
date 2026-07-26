# Our 44 Guard Hooks Added 3 Seconds to Every Command — Then Blocked Every Tool Call Outright

**Keywords:** Claude Code hook latency, hook performance overhead, guard consolidation, hook dispatcher, PostToolUse overhead, hooks blocking all tools, Windows Git Bash process spawn cost

**Incident window:** latency chronic through 2026-06; total-blockage incident 2026-06-12; consolidation #1677–#1679 · **Internal refs:** tasks #1677, #1678, #1679 · **Status:** fixed via dispatcher consolidation; measured ~3.0s → sub-second per event

---

## What broke

Two failures, same root: the enforcement layer itself became the system's biggest reliability and performance problem.

**Chronic:** by mid-2026 the stack had grown to ~34 standalone PreToolUse bash guards plus ~10 PostToolUse ones — each an independent shell script, each spawning 1–8 child processes (python interpreters, subshells, greps) per evaluation. Under Git Bash on Windows, where process spawn is expensive, the measured toll was **~3.0 seconds added to every Bash call and ~4.7 seconds per file edit** — before the actual command ran. One prompt-time hook, looping per registered tool nickname with a subshell each, added **~8.4 seconds** on its own. Every session paid this tax on every action, all day.

**Acute (2026-06-12):** several hooks located their helpers by *relative* path, resolved against the session's current working directory. A session legitimately `cd`-ed elsewhere; every relative-path hook began erroring, and because PreToolUse hook errors block the tool call, **every tool call in the session was blocked** — by the safety layer, with the underlying tools perfectly healthy. A related chronic variant: a persisted `cd` left 5 hooks failing *silently* for days (task #981).

**Bonus discovery during the rebuild:** one PostToolUse hook had been reading env vars (`CLAUDE_TOOL_OUTPUT`) that its event never populates. It had **never fired once** — same silent-no-op class as [PM-016](016-the-classifier-that-never-ran.md), found only because consolidation forced reading every hook.

## How it was detected

The latency: measured deliberately, once sessions "feeling slow" was taken seriously — timing harness around hook dispatch, per-hook cost table. The blockage: catastrophically obvious the moment it happened; the diagnosis (cwd-relative paths) took the forensics.

## Root cause

**Additive guard growth with no architectural budget.** Each guard was individually cheap-ish and individually justified; nobody owned the *sum*. The N-processes-per-guard × M-guards × every-tool-call multiplication was never anyone's line item. The blockage adds the second law: hooks inherit session state (cwd, env) that sessions legitimately change — a guard that assumes stable session state is a time bomb with a legitimate-user trigger.

## Blast radius

Weeks of ~3–8s overhead on every action across 7–12 sessions (a large, real fraction of total wall-clock); one full-session outage; and the discovery cost of auditing 44 scripts nobody had read end-to-end in months.

## The fix

- **One dispatcher per event type** ([pattern](../patterns/guard-dispatch-consolidation.md)): a single Python process receives the event, runs all applicable guard logic in-process from a registry, and returns one verdict. Measured result: the 34-guard PreToolUse chain dropped from ~3.0s to sub-second; the worst single hook went from ~1,140ms to ~150ms.
- **Absolute paths only** in hook internals, resolved from the hook file's own location, never from cwd — encoded in the dispatcher's contract and checked by its self-test.
- The never-fired hook was rewired to its event's actual data channel — and became the poster child for fire-count telemetry ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)).

## Has the guard fired since?

The dispatcher runs on every tool call in every session — it *is* the enforcement layer now, and its per-event timing is logged, so regression would be a visible number rather than a vibe. The cwd blockage class has not recurred; the dispatcher's self-test covers it.

## Lessons for agent-driven development

1. **Guards are a system with a budget, not a pile of good ideas.** Sum their latency; the aggregate is a feature nobody asked for.
2. **Process spawns are the hidden currency of shell-based hooks** — on Windows especially. In-process consolidation buys back seconds per action.
3. **Hooks must not trust session state.** cwd and env belong to the session and change legitimately; a hook that resolves anything relative to them will eventually block everything or fail silently.
4. **The safety layer needs its own SLO.** "Can block every tool call" is root-level power; anything with that power needs self-tests, timing telemetry, and a postmortem culture of its own.
