# Pattern: Profile-Based Hook Self-Gating — Guards That Know When They're Irrelevant

**Problem:** A guard fleet built for trading work fires during content-writing sessions; dashboard guards nag infrastructure sessions. Every irrelevant fire costs latency and attention, and attention is the budget that alarm fatigue spends ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)).

**Mechanism:** Sessions carry a **profile** (trading / dashboard / ops / content / all) in their per-session state, set at session start (auto-classified, operator-overridable). Every hook's first move is a cheap self-gate: *does my profile apply here?* If not, exit 0 before doing any work — no parsing, no subprocesses, no output.

## Sanitized skeleton

```python
#!/usr/bin/env python3
import json, sys

MY_PROFILES = {"trading", "all"}     # this guard only matters for trading work

def main():
    payload = json.load(sys.stdin)
    profile = read_session_profile(payload)     # from per-session state file
    if profile not in MY_PROFILES:
        sys.exit(0)                             # FIRST line of real logic: bow out
    # ... expensive checks only for sessions that need them ...

main()
```

## Failure modes of this pattern

- **The profile itself can be wrong — then gating compounds the error.** Our lane/profile classifier silently no-opped for two months, freezing every session on a stale label ([PM-016](../postmortems/016-the-classifier-that-never-ran.md)); profile-gated hooks faithfully mis-gated the whole time. The classifier needs fire-count telemetry *more* than the hooks it feeds.
- **Self-gating hides guard death.** A hook that exits early for profile reasons is indistinguishable in silence from a hook that's broken. Log the gate decision (one audit field: `skipped_profile`) so "never fires" can be distinguished from "never applies."
- **Profile sprawl:** every new profile doubles the matrix someone has to reason about. Keep the set small and boring; "all" is the honest default for cross-cutting guards.
- **Gating what should be universal:** git hygiene, secret scanning, and destructive-op guards apply to *every* profile — the temptation to profile-gate them for speed is how a content session leaks a key. Universal guards stay universal; speed comes from [dispatcher consolidation](guard-dispatch-consolidation.md) instead.

**Where it's enforced in our stack:** the session-state file carries `hooks_profile`; trading-methodology guards, dashboard-deploy guards, and content-format guards self-gate on it; the audit log records skip reasons so the gate audit ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)) can score relevance, not just fires.
