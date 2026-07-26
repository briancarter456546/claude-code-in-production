# Pattern: The Stop-Hook Guard — Block a Response Before It's Delivered

**Problem:** Some agent failures live in the *response itself* — appeasement language, missing required structure, premature wrap-up suggestions, unsourced claims. Instructions against them decay; you need enforcement at the delivery boundary.

**Mechanism:** Claude Code's Stop hook runs when the agent finishes a response, receives the transcript, and can **refuse delivery** (non-zero exit / block decision), forcing the model to rewrite. The guard parses the outgoing text, applies its rules, and either passes silently or blocks with a message that *teaches the correct form*.

## Sanitized skeleton

```python
#!/usr/bin/env python3
"""Stop hook: block responses matching banned patterns."""
import json, os, re, sys

# Literals deliberately split so this file cannot match itself
# (and quoting the guard in a bug report doesn't trip it).
PATTERNS = [
    ("appeasement", re.compile(r"\byou'?re\s+(absolutely\s+)?ri" + r"ght\b", re.I)),
]

def main():
    payload = json.load(sys.stdin)              # read ONCE; stdin is consumable
    if payload.get("stop_hook_active"):         # recursion guard: we blocked already
        sys.exit(0)                             # -> exit silently or deadlock the session
    text = extract_final_response(payload)      # parse transcript; exempt code fences
    text = strip_quoted(text)                   # never judge quoted/code content
    bypass = read_bypass_reason()               # audited escape hatch (see failure modes)
    hits = [name for name, rx in PATTERNS if rx.search(text)]
    if hits and not bypass:
        print(f"[GUARD] blocked: {hits}. Rewrite without these patterns.", file=sys.stderr)
        sys.exit(2)                             # block delivery -> model rewrites
    log_outcome(hits, bypass)                   # append-only audit line, ALWAYS
    sys.exit(0)

main()
```

## Failure modes of this pattern (all field-tested, sadly)

- **Self-matching:** if the source spells out banned phrases, the guard trips on itself and on any response quoting it. Split string literals; exempt code fences and quoted text ([PM-018](../postmortems/018-the-stop-hook-that-rewarded-hand-waving.md)).
- **Recursion deadlock:** blocking triggers a rewrite, which triggers the hook again. Honor the harness's re-entry flag or loop forever ([PM-003](../postmortems/003-stop-hook-sycophancy-guard-claude-code.md)).
- **Shape vs property:** regex enforces textual shapes. If the shape is a proxy ("citation-looking string near a number"), gaming the shape may be easier than satisfying the property — you can end up *training vagueness* ([PM-018](../postmortems/018-the-stop-hook-that-rewarded-hand-waving.md)).
- **Backfire on legitimate content:** a guard that edits accountability language out of a retrospective, or blocks the operator's own quoted words, needs the audited bypass. A guard with no exception path gets disabled wholesale the first time it's wrong.
- **Unmeasured guards drift:** run a labeled-corpus probe (real responses, hand-scored, confusion matrix) before trusting any content guard. Fire counts are activity, not accuracy.

**Where it's enforced in our stack:** anti-sycophancy, wrap-nudge suppression, banned-rationalization phrases, response-structure requirements — all Stop hooks; every fire logged (block/bypass/clean) to the append-only audit trail.
