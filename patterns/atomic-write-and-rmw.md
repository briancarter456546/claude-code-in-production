# Pattern: Atomic Writes and Read-Merge-Write — Multi-Writer Files That Don't Eat Each Other

**Problem:** Multiple producers (sessions, crons, backends) writing one file. Two classic corruptions: the torn write (reader sees a half-written file) and the overwrite-clobber (writer B's `json.dump` erases the fields writer A added an hour ago).

**Mechanism:** Two disciplines, composed:

1. **Atomic replace** for every write: write to a temp file in the same directory, then `os.replace()` — readers see the old version or the new one, never a torn middle.
2. **Read-merge-write** for every shared document: load current contents, merge *your* fields into it, write the merged whole. A producer that writes a fresh payload over a shared file is erasing everyone else — even if it does so atomically.

## Sanitized skeleton

```python
import json, os, tempfile

def atomic_write_json(path, obj):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")   # SAME filesystem as target
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)                              # atomic on POSIX and NTFS

def update_shared_sidecar(path, my_fields: dict):
    try:
        current = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        current = {}
    current.update(my_fields)          # merge MY keys; everyone else's survive
    atomic_write_json(path, current)   # atomic on top of merged
```

## Failure modes of this pattern

- **Atomic-but-overwriting is still data loss.** Our worst instance: a backend `json.dump`-ed a fresh payload over shared per-ticker sidecar files, wiping four other producers' fields — *hourly*, on a cron, self-healing overnight so the damage window kept closing before anyone investigated. Atomicity was never the problem; the missing merge was.
- **RMW without serialization is a race.** Two merges with interleaved reads: last writer drops the other's keys — the settings-file incident exactly ([PM-025](../postmortems/025-sessions-erased-each-others-hook-registrations.md)). Under real concurrency add a lock file, a lease ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)), or per-writer key namespaces.
- **Temp file on the wrong filesystem:** `os.replace` across filesystems isn't atomic (or fails). Create the temp in the target's directory.
- **Schema-less merges rot.** `dict.update` merges keys, not meaning; producers must own disjoint key namespaces or the merge itself becomes the conflict.
- **The pattern needs enforcement, not documentation:** a PreToolUse guard flags whole-file `json.dump` onto registered multi-writer paths — because the next producer's author won't have read this page.

**Where it's enforced in our stack:** sidecar-RMW guard on shared per-ticker files; atomic replace in the session-state library; per-writer key ownership documented in the producers' registry.
