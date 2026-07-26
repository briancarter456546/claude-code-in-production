# Pattern: Bypass-Rate Auditing — Every Escape Hatch Is a Sensor

**Problem:** Guards need escape hatches (a guard with no legitimate-exception path gets disabled wholesale), but ungoverned bypasses rot the fleet: ~60 bypass variables accumulated in our stack, bypassing normalized culturally, and one audit found "2 of 3 blocks were false" on a busy guard. Nobody could say which guards earned their keep.

**Mechanism:** Three rules that turn bypasses from leakage into telemetry:

1. **Every bypass demands a reason string** (`SKIP_X="reason:<text>"`) — free-text, human-readable, mandatory.
2. **Every bypass attempt is audit-logged** — accepted or rejected, with its reason, guard, session ([passive-audit-log](passive-audit-log.md)).
3. **The ratio is reviewed on a schedule:** for each guard, compare bypass rate against estimated true positives. **A guard whose bypass rate exceeds its true-positive rate is a bug report on the guard** — its blocks are mostly false, and every false block re-teaches the fleet that bypassing is normal.

## Sanitized skeleton

```python
# inside any gate, after parse:
bypass = parse_bypass(cmd, var="SKIP_THIS_GUARD")     # None | reason-string
if bypass:
    audit("bypass", guard=NAME, reason=bypass)        # the sensor reading
    sys.exit(0)

# the scheduled review (offline, reads the audit ledger):
for guard, rows in events_by_guard(window):
    blocks   = count(rows, "block")
    bypasses = count(rows, "bypass")
    if bypasses > est_true_positives(guard, rows):    # bypass reasons + spot checks
        flag(f"{guard}: bypass-rate exceeds value -- narrow, demote, or kill")
```

## Failure modes of this pattern

- **The channel itself can be dead** — our inline bypasses were silent no-ops for weeks, and zero logged bypasses read as "nobody needs one" instead of "the mechanism is broken." A bypass log that flatlines is a finding, not a comfort ([PM-014](../postmortems/014-the-escape-hatches-that-never-existed.md)).
- **Reason strings degrade into noise** ("reason:test" × 40). Tolerable — even lazy reasons carry the count and the guard name; periodic spot-reads keep the culture honest. Rejecting weak reasons at the gate just re-manufactures the friction that causes evasion.
- **Recurring bypass reasons are a spec** — the same reason 14 times ("nested-repo commit, all paths authored by this session") isn't noise; it's the false-positive class named precisely, filed by the people who hit it ([PM-023](../postmortems/023-blocked-from-committing-its-own-file.md)). Mine the reasons; they're pre-written bug reports.
- **Review without teeth:** flagging net-negative guards means nothing unless someone kills or narrows them. Pair with the standing gate audit and its kill list ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md), [PM-015](../postmortems/015-eight-thousand-fires-zero-true-blocks.md)).
- **Bypass ≠ approval.** For genuinely destructive actions the escape hatch is a *marker-file ack* ([marker-file-acks](marker-file-acks.md)), not a self-serve env var. Match the hatch to the blast radius.

**Where it's enforced in our stack:** the `reason:` convention fleet-wide; audit-logged since the escape-hatch resurrection; ratio review inside the periodic gate audit; formalized as [ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md).
