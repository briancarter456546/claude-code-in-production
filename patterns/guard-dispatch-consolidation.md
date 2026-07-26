# Pattern: Guard-Dispatch Consolidation — One Process Per Event, Not One Per Guard

**Problem:** Guard fleets grow additively: each incident ships another standalone hook, each hook spawns interpreters and subshells, and nobody owns the sum. At ~44 shell guards ours added **~3.0 seconds to every Bash call and ~4.7 to every edit** — on every action, in every session, all day ([PM-019](../postmortems/019-when-the-safety-layer-became-the-outage.md)).

**Mechanism:** One **dispatcher per hook event** (PreToolUse, PostToolUse, Stop). The harness invokes the dispatcher once; the dispatcher loads a registry of guard modules and runs them **in-process** — one interpreter startup total, shared parsing (the tool payload is decoded once), one merged verdict out. Individual guards become plain Python functions with a tiny contract.

## Sanitized skeleton

```python
#!/usr/bin/env python3
"""guard_dispatch.py -- single PreToolUse entrypoint."""
import importlib, json, sys, time

REGISTRY = ["git_hygiene", "path_policy", "secret_scan"]   # ordered guard modules

def main():
    payload = json.load(sys.stdin)                # decoded ONCE for all guards
    ctx = build_context(payload)                  # shared parse: cmd, files, session
    for name in REGISTRY:
        mod = importlib.import_module(f"guards.{name}")
        t0 = time.perf_counter()
        verdict = mod.check(ctx)                  # pure function: ctx -> verdict
        audit(name, verdict, ms=(time.perf_counter()-t0)*1000)   # per-guard timing
        if verdict.block:
            print(verdict.message, file=sys.stderr)
            sys.exit(2)                           # first block wins; rest skipped
    sys.exit(0)

main()
```

## Failure modes of this pattern

- **The dispatcher is a single point of failure with root-level power.** A crash blocks (or waves through) *everything*. It needs its own self-test, absolute-path discipline (a cwd-relative resolution once blocked every tool call in a session), and a fail-mode decision made consciously per event type.
- **Consolidation surfaces the dead.** Porting guards into the dispatcher forced reading them — and found one that had *never fired* (reading env vars its event never populates). Treat that as a feature: migration is an audit ([PM-016](../postmortems/016-the-classifier-that-never-ran.md)'s class).
- **Ordering becomes policy.** First-block-wins means guard order decides which message the agent sees; put the most specific, most teachable block first.
- **Shared context drift:** guards coupling to the shared parse's internals break together when it changes. Keep the ctx contract small and versioned.
- **Per-guard timing is non-negotiable** — without it the fleet regrows its latency invisibly, one "cheap" guard at a time. The dispatcher's audit line is where the [gate audit](../adr/016-guards-are-audited-against-their-own-fire-logs.md) gets its cost column.

**Measured result in our stack:** PreToolUse chain ~3.0s → sub-second; worst single hook ~1,140ms → ~150ms; per-guard fire/latency telemetry as a side effect.
