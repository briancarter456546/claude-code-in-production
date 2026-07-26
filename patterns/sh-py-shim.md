# Pattern: The .sh → .py Shim — Cross-Platform Hooks With All Logic in Testable Python

**Problem:** Claude Code invokes hooks through a POSIX-ish shell on every platform — including Windows (Git Bash), where bash scripting accumulates quoting bugs, cp1252 encoding traps, and process-spawn costs. Hook logic written in shell is untestable and platform-fragile.

**Mechanism:** Every hook is a **pair**: a `.sh` shim whose only job is to locate the Python interpreter and `exec` a `.py` of the same name; and the `.py`, where all logic lives. The shim is generated boilerplate — *if a shim contains an `if`, it's wrong.*

## Sanitized skeleton

```bash
#!/usr/bin/env bash
# my-guard.sh -- shim only. Logic lives in my-guard.py. Do not add logic here.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # anchor to THIS file's dir,
exec python "$DIR/my-guard.py" "$@"                    # never to the session's cwd
```

```python
#!/usr/bin/env python3
# my-guard.py -- all logic. Contract:
import io, json, sys
sys.stdin.reconfigure(encoding="utf-8")           # Windows defaults to cp1252 --
payload = json.load(sys.stdin)                     # declare UTF-8 on EVERY I/O edge
# ... logic, unit-testable without a shell ...
print("[OK] pass")                                 # ASCII-only output: [OK] / [FAIL] / -->
sys.exit(0)                                        # console codepages garble unicode
```

## Failure modes of this pattern

- **Shim drift:** a `.sh` pointing at a renamed/moved `.py` fails at invocation time. A self-test that walks all pairs (every shim resolves, every `.py` has a shim or is a library) catches it mechanically.
- **cwd anchoring:** a shim (or its Python) that resolves paths relative to the working directory inherits the session's wanderings — this class blocked *every tool call* in one session ([PM-019](../postmortems/019-when-the-safety-layer-became-the-outage.md)) and silently killed five hooks in another ([PM-034](../postmortems/034-windows-kills-guards-quietly.md)).
- **The exec bit doesn't survive Windows authorship:** scripts committed from NTFS carry mode `100644` and won't execute after a Linux pull — enforce `100755` on `*.sh` at commit time ([PM-034](../postmortems/034-windows-kills-guards-quietly.md)).
- **Per-hook process cost:** one python spawn per hook per event is fine at 5 hooks and a disaster at 100 — pair this pattern with a [consolidated dispatcher](guard-dispatch-consolidation.md) once the fleet grows.
- **Encoding by default:** any file I/O without explicit UTF-8 will eventually mangle content on Windows. The rule is *every* edge, not just the ones that broke last time.

**Where it's enforced in our stack:** the entire hooks directory (~62 shim pairs plus consolidated dispatchers); pair-walk in the hook self-test; exec-bit check in pre-commit.
