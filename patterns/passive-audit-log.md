# Pattern: The Passive Audit Log — Append-Only Event Ledger That Makes Guards Measurable

**Problem:** You can't answer the questions that matter about your enforcement layer — does this guard catch anything? how often is it bypassed? did that policy violation actually occur? — without a durable record. Logs scattered per-hook rot; in-memory counters die with sessions.

**Mechanism:** One **append-only JSONL ledger** for all governance events. Every guard writes one line per decision — block, pass, bypass (with reason), advisory, policy violation — with timestamp, session, guard name, and a compact payload. Nothing edits or deletes lines; analysis is downstream (`grep`/pandas), never in the write path.

## Sanitized skeleton

```python
import json, time, pathlib

AUDIT = pathlib.Path("output/audit.jsonl")     # one file, append-only, everyone writes

def audit(event: str, guard: str, **fields):
    line = {"ts": time.time(), "event": event, "guard": guard,
            "session": current_session_id(), **fields}
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")       # append is the only operation

# usage inside any guard:
audit("block",  "pathspec-commit-guard", cmd=cmd[:200])
audit("bypass", "stranger-file-guard",   reason=reason)     # bypass reasons are gold
audit("policy.violation", "kb-write-policy", writer=ctx)    # passive detection, v1
```

## Failure modes of this pattern

- **Nobody reads it — until it's the hero.** A passive log feels like waste right up to the gate audit that finds **8,000 fires and zero true catches** ([PM-015](../postmortems/015-eight-thousand-fires-zero-true-blocks.md)) or the 2-fires-in-101k-lines dead hook ([PM-016](../postmortems/016-the-classifier-that-never-ran.md)). Schedule the reading (weekly digest + periodic gate audit) or the ledger is a diary.
- **Rotation eats your evidence window.** Ours retains ~12 days at current volume; "has the guard fired since" claims older than that must cite the digest, not the raw log — label evidence windows explicitly or overclaim by accident.
- **Concurrent appends:** single-line appends under the OS pipe-buffer size are effectively atomic; multi-line or oversized writes interleave. Keep lines small; never write batches.
- **The log is observability, not enforcement.** "Passive v1" means violations are *recorded*, not prevented — fine, as long as nobody mistakes the ledger for a gate. Promote to blocking only with measured false-positive rates.
- **Sensitive payloads:** guards see commands and file contents; truncate and scrub before logging, or the audit trail becomes the leak ([PM-030](../postmortems/030-the-secret-the-hooks-could-not-see.md)'s lesson applies to your own ledger).

**Where it's enforced in our stack:** every guard writes to one JSONL; weekly digest summarizes; the gate-audit practice ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)) and every "has the guard fired since" field in these postmortems read from it.
