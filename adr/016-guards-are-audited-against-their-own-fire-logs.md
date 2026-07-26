# ADR-016: Guards are periodically audited against their own fire logs, and net-negative guards are killed

**Status:** Active · **Date:** 2026-07 (the gate-audit era, task #1794) · **Internal refs:** #1794 kill list; #1594; the probe method

## Context

The guard fleet grew incident by incident to ~100 enforcement hooks, each individually justified — and nobody could answer the only questions that matter: which guards catch real things, what each costs (latency, false blocks, attention), and which are net-negative. The audit that finally asked found two gates with ~8,000 combined fires and **zero true catches** ([PM-015](../postmortems/015-eight-thousand-fires-zero-true-blocks.md)), a hook that had **never fired** ([PM-016](../postmortems/016-the-classifier-that-never-ran.md)), and a content guard firing 10/10 on the wrong rule ([PM-018](../postmortems/018-the-stop-hook-that-rewarded-hand-waving.md)). Working infrastructure and dead infrastructure had been indistinguishable for months.

## Decision

**Every guard is scored against its own append-only fire log on a schedule.** The scorecard per guard: fire count, true-catch estimate, false-positive estimate (from bypass reasons and overrides), latency cost, token cost of its block messages, and blast radius when wrong. Consequences have teeth:

- **Net-negative guards are killed or demoted to advisory** — a standing kill list is maintained as an artifact, not a one-time cleanup.
- **Zero-fire guards are findings** — either the guarded behavior is extinct (retire the guard) or the guard is dead (fix it); silence is never assumed to be health.
- **Heuristic signals don't block:** "a guess never blocks" — blocking status is earned by measured signal, not by good intentions.
- Content-judging guards additionally require a **labeled-corpus probe** (real responses, hand-scored, confusion matrix) before being trusted.

## Alternatives considered

- **Trust guards because they were born from real incidents.** The default, disproven: incident-born guards measured proxies chosen for implementability, and proxies rot.
- **Audit only on complaint.** Rejected: false *negatives* generate no complaints, and false positives generate bypasses, not tickets — both invisible without the ledger.
- **Delete aggressively without measurement.** Rejected: the same audit that killed two gates confirmed others were doing heavy, real work (the git-hygiene family's weekly catches). Measurement cuts both ways; that's the point.

## Consequences

- The audit itself is recurring work — a real cost, budgeted, and repaid the first time it found the 8,000-fire nulls.
- Guards now need telemetry at birth (fire logging, timing) — enforced by the dispatcher pattern, which emits both as side effects.
- Cultural shift with a sharp edge: **a safeguard that catches nothing is not neutral** — it spends latency and credibility that working guards need. The same logic later narrowed a human-ack step that had caught nothing ([ADR-008](008-append-only-knowledge-base-with-curator-writes.md)).

## What we'd do differently

Instrument from the first guard. The ledger existed before the audit did; the audit could have been running from month one, and two of this repo's worst silent failures would have been week-one findings instead.
