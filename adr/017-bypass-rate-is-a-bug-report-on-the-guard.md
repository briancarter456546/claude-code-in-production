# ADR-017: A guard's bypass rate is treated as a bug report on the guard

**Status:** Active · **Date:** 2026-07 (formalized after the bypass census) · **Internal refs:** the ~60-variable census; degradation-plan bypass findings; escape-hatch resurrection (#1680 family)

## Context

Every guard ships with a reason-logged bypass — the escape hatch that keeps a wrong block from becoming a disabled guard ([ADR-002](002-hooks-as-enforcement-not-instructions.md)'s convention). By mid-2026 the stack had accumulated ~60 bypass variables, sessions used them fluently, and an audit of one busy period found **536 human bypasses of a single gate** and guards where **most blocks were false**. Two failure cultures loomed: treat bypassing as sin (and drive it underground), or treat it as normal (and let guards decay into ritual). Both miss what the bypass stream actually is.

## Decision

**Bypasses are sensor data about guard quality.** Formally:

- Every bypass carries a mandatory reason string and is audit-logged, accepted or not ([pattern](../patterns/bypass-rate-auditing.md)).
- On the gate-audit schedule ([ADR-016](016-guards-are-audited-against-their-own-fire-logs.md)), each guard's bypass rate is compared to its true-positive estimate. **Bypass rate exceeding true-positive rate = the guard is mostly blocking legitimate work** — it gets narrowed, demoted, or killed. The operator bypassing a guard is not misbehavior; it's the guard failing review in real time.
- **Recurring identical reasons are a named false-positive class** — a pre-written bug report with a repro count (the nested-repo commit class was diagnosed exactly this way, [PM-023](../postmortems/023-blocked-from-committing-its-own-file.md)).
- Blast-radius matching: self-serve env-var bypasses for friction-class guards; marker-file human acks for destructive-class ones ([pattern](../patterns/marker-file-acks.md)). One convention does not fit both.

## Alternatives considered

- **Punish/forbid bypassing.** Rejected: drives workarounds underground (agents rephrase to dodge patterns instead of declaring intent), destroying the sensor.
- **Frictionless bypassing (no reason required).** Rejected: the reason string *is* the data; without it a bypass is indistinguishable from noise, and the census that motivated this ADR becomes impossible.
- **Approval required for every bypass.** Rejected for friction-class guards: it re-creates re-ack fatigue ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)) and trains rubber-stamping — the failure mode human attention is worst at.

## Consequences

- Guard authors lose the comfortable fiction that blocks equal value; a high-block guard with high bypasses is now *presumptively broken*, and the burden of proof flipped.
- Reason strings are messy free text; mining them is imperfect and requires periodic human spot-reads. Accepted — lazy reasons still carry counts and clusters.
- The bypass channel itself became load-bearing telemetry, which is why its silent death for weeks ([PM-014](../postmortems/014-the-escape-hatches-that-never-existed.md)) is one of this repo's more consequential incidents: a dead sensor reads as a perfect guard.

## What we'd do differently

Adopt the framing before the census forced it. The ~60-variable sprawl and the 536-bypass gate were both visible in the ledger months earlier; nobody had yet decided that bypasses were *about the guards* rather than about the sessions.
