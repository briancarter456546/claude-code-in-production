# Pattern: The PreToolUse Gate — Make the Dangerous Call Impossible, With an Audited Escape Hatch

**Problem:** Some actions must not happen — broad `git add`, raw SSH from hooks, writes to canonical paths, scp onto git-owned files. Telling the agent "don't" works until it doesn't; the failure is always discovered after the tool ran.

**Mechanism:** A PreToolUse hook receives the pending tool call (name + arguments) *before execution* and can block it. The gate parses the call, applies policy, and blocks with a message teaching the compliant form. Every gate ships with a **bypass that requires a logged reason** — the escape hatch is part of the pattern, not a weakening of it.

## Sanitized skeleton

```python
#!/usr/bin/env python3
"""PreToolUse gate: block dangerous Bash invocations."""
import json, re, sys

def main():
    call = json.load(sys.stdin)
    cmd = call.get("tool_input", {}).get("command", "")
    cmd_active = strip_quoted_and_heredocs(cmd)   # judge live shell, not quoted prose

    bypass = parse_inline_bypass(cmd)             # e.g. SKIP_THIS_GUARD="reason:..." prefix
    if bypass:
        audit("bypass", cmd, reason=bypass)       # bypasses are DATA about the guard
        sys.exit(0)

    if re.search(r"\bgit\s+add\s+(-A|--all|\.)(\s|$)", cmd_active):
        print("[GATE] Broad 'git add' sweeps other sessions' files.\n"
              "Use:  git add -- <paths you touched>\n"
              "Bypass once: SKIP_THIS_GUARD=\"reason:<text>\" <command>",
              file=sys.stderr)
        audit("block", cmd)
        sys.exit(2)
    audit("pass", cmd)
    sys.exit(0)

main()
```

## Failure modes of this pattern

- **The bypass channel may not exist.** Inline `VAR=x cmd` env vars can fail to reach the hook process entirely (the hook runs in the harness's process tree, not the command's). Ours were silent no-ops for weeks — parse the command *string* or use session-scoped bypass files, and self-test end-to-end delivery ([PM-014](../postmortems/014-the-escape-hatches-that-never-existed.md)).
- **Quoted-prose false positives:** a heredoc documenting a dangerous command is not the dangerous command. Strip quotes/heredocs before matching, or the gate blocks documentation ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)'s churn is partly this).
- **TOCTOU blindness:** PreToolUse sees the call, not the state at execution. For git, a second enforcement layer at the durable boundary (native pre-commit) catches what the gate can't ([PM-030](../postmortems/030-the-secret-the-hooks-could-not-see.md)).
- **Exemption/trigger regex intersection:** an exemption that matches the violation silently kills the guard — run every exemption against the known-bad corpus ([PM-017](../postmortems/017-the-guard-that-suppressed-itself.md)).
- **Latency at scale:** dozens of per-call shell guards added seconds to every action; consolidate into one dispatcher process per event ([guard-dispatch-consolidation](guard-dispatch-consolidation.md)).
- **Bypass-rate blindness:** a guard whose bypass rate exceeds its true-positive rate is a false-positive machine wearing a badge. Watch the ratio ([ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md)).

**Where it's enforced in our stack:** git hygiene (broad-add, pathspec, stranger-file), SSH/scp policy, dashboard source-of-truth, host placement, production-glob protection, KB write policy — the largest guard family we run.
