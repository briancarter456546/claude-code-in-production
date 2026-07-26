# Pattern: Per-Session State — Key Everything by Session ID; Share Only by Explicit Design

**Problem:** Concurrent agent sessions sharing any mutable file — skill phase state, status JSON, journals, config — collide: last-writer-wins clobbers, cross-session gate blocks, one session's truth displayed as another's.

**Mechanism:** All hook-visible state is stored in per-session files keyed by the **harness-issued session ID**, managed through one small library/CLI. Hooks resolve *this* session's ID, read *this* session's file, and ignore everyone else's. Cross-session workflows opt into shared state explicitly — isolated is the default, shared is the design decision.

## Sanitized skeleton

```python
# _session_lib.py -- the ONLY way any hook learns who it is
import json, os, pathlib

STATE_DIR = pathlib.Path(__file__).parent / "session_state"   # anchored, not cwd

def session_id(payload) -> str:
    sid = payload.get("session_id")        # ISSUED by the harness. Never derive
    if not sid:                            # from paths/times/env -- derivation
        raise RuntimeError("no session id") # collides under concurrency.
    return sid                             # No fallback that guesses: fail closed.

def state_path(payload) -> pathlib.Path:
    p = STATE_DIR / f"{session_id(payload)}.json"
    return p

def write_state(payload, obj):
    p = state_path(payload)
    tmp = p.with_suffix(".tmp")            # atomic write: tmp -> rename
    tmp.write_text(json.dumps(obj), encoding="utf-8")
    os.replace(tmp, p)
```

## Failure modes of this pattern

- **Derived identity collides.** Two windows computing their own ID from ambient facts (launch time, path) *will* eventually compute the same one — then each reads the other's state as its own ([PM-022](../postmortems/022-two-sessions-one-identity.md)). The ID must be issued, single-sourced, and never re-derived by a second implementation.
- **Fallbacks that guess are impersonation.** A degraded-mode lookup that returns "probably my session" acquired a wrap lock as a *sibling* in our stack. If identity can't be established, identity-requiring operations fail closed.
- **Orphan accumulation.** Crashed sessions leave state files; because each file names its owner, pruning is mechanical (owner absent from live-session registry + age threshold). This is the good side of the trade vs. stale global locks.
- **Path handling bites cross-platform.** A backslash-mangling join once produced state files nobody could find — same lesson as [sh-py-shim](sh-py-shim.md): path code is contract code.
- **The shared exceptions need the most care.** Anything that *must* be shared (config, registries) inherits the full collision problem — serialize writers via leases and detect losses ([PM-025](../postmortems/025-sessions-erased-each-others-hook-registrations.md)).

**Where it's enforced in our stack:** skill phase state, session status, touched-file journals, checkpoints — per-session by default since the collision era ([ADR-014](../adr/014-per-session-skill-state.md)); identity via one shared library after three escalating identity incidents.
