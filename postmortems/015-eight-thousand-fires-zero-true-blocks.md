# We Audited Our Guard Hooks Against Their Own Logs: 8,000 Fires, Zero True Catches

**Keywords:** guard hook effectiveness, gate audit, false positive rate hooks, AI agent guardrails cost, hook latency, net-negative guards, alarm fatigue automation, kill list

**Incident date:** audit 2026-07 (task #1794) · **Internal refs:** #1794 gate-audit kill list; #1594; runtime-history classifier · **Status:** both gates rebuilt on measured signals; audit is now a standing practice

---

## What broke

Nothing crashed. That's the point: two guards ran for weeks looking exactly like working infrastructure, and an audit of their own fire logs showed they had **never once done their job**.

- A **pre-run speed check** was supposed to block scripts that would run unacceptably long, judging by static code analysis (AST heuristics: nested loops, no parallelism). Logged history: **~6,900 fires — zero cases where it blocked a genuinely slow run.** Its false positives were textbook: bounded `range(10)` loops flagged as bottlenecks. Meanwhile the actually-slow runs sailed through, because slowness lives in data volume and call-graph depth, which the static score couldn't see (see [PM-042](042-fifteen-hours-and-eighty-four-minutes.md) for what it missed).
- A **worker-count guard** was supposed to prevent CPU oversubscription from concurrent backtests. It ran a full process-table scan on **every Bash call** — 1.6 seconds median, 17.5 seconds worst case, added to every command in every session — and in ~1,000 fires blocked nothing real. It counted processes per command while the actual thrash (aggregate CPU/RAM saturation across 7–12 concurrent sessions) was invisible to a per-command process count. An earlier version had also miscounted idle shells as active workers.

Combined: ~8,000 enforcement events, measurable latency on every tool call, zero true positives.

## How it was detected

Deliberately, and that's the reusable part: a **gate audit** (task #1794) scored every hook in the stack against its own append-only fire log — fire count, block rate, false-positive rate estimated from bypass/override patterns, latency cost, and blast radius when wrong. The two gates above topped the kill list. Nothing about normal operation would ever have surfaced this; a guard that blocks wrong things *looks identical* to a guard that blocks right things unless someone reads the ledger.

## Root cause

Both gates measured **proxies chosen for implementability, not signal**: code shape instead of measured runtime; per-command process counts instead of system-wide saturation. The deeper cause is an incentive: when you *want* a guard to exist, any implementable heuristic feels better than nothing. It isn't. A guard with zero true positives is pure tax — latency, false blocks, and alarm fatigue that degrades trust in every *other* guard.

## Blast radius

Weeks of 1.6s+ added latency per Bash call across all sessions; false blocks and retry churn feeding the session-degradation problem ([PM-021](021-alarm-fatigue-by-the-numbers.md)); and unearned confidence that the runaway-script problem was "handled."

## The fix

- Both gates were rebuilt around **measured signals**: a shared classifier keyed to recorded runtime history (what did this script/pattern actually cost last time?) and live system saturation, replacing shape-guessing. The speed gate demoted itself to advisory ("a guess never blocks" is now in its banner).
- The meta-fix became policy and then an ADR ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)): **every gate is periodically scored against its own logs, and net-negative gates are killed or demoted.** The kill list from #1794 is a standing artifact, not a one-time cleanup.

## Has the guard fired since?

The *audit* has — it's the guard now. The rebuilt gates fire rarely and advisorily, which matches reality better than 8,000 confident wrongs. The honest scoreboard from a recent window shows the replacement behavior: a handful of yellow-flag advisories on genuinely heavy operations, no blanket blocks.

## Lessons for agent-driven development

1. **A guard that has never caught anything is not neutral — it's negative.** It costs latency, false blocks, and credibility, and it occupies the slot where a working guard should be.
2. **Audit gates against their own fire logs on a schedule.** Fire count, true-catch count, FP estimate, latency. If you can't produce these numbers, you don't know if your guardrails work. Ours didn't.
3. **Static shape is a terrible proxy for runtime cost.** Measured history beats clever heuristics; if you have no measurement, instrument first and guard second.
4. **Per-unit checks can't see aggregate problems.** Twelve sessions each under their own limit will still saturate the box. Guard the resource, not the command.
5. **"A guess never blocks."** Advisory-by-default for heuristic signals; blocking is earned by measurement.
