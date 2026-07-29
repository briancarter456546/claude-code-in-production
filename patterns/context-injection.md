# Pattern: Context Injection — Push State Into Every Turn Instead of Hoping the Model Asks

**Problem:** The agent needs current operational state — active leases, known corrections, session status, collision taxonomies — but models don't reliably *ask* for state, and instructions to "always check X first" decay. This isn't hypothetical: our subagent prompts carried a "MANDATORY FIRST READ" instruction pointing at a context file, and under tool-use pressure agents were observed skipping it — while, separately, the prompt files carrying that instruction were silently reverted by concurrent sessions. Both failure paths are why the injector hook exists: hook-level injection is the invariant that prompt-level instruction wasn't. Stale beliefs masquerade as knowledge.

**Mechanism:** UserPromptSubmit (and SessionStart) hooks emit text that the harness injects into the turn's context. The model doesn't have to remember to look; the state arrives with every prompt. Injection can be unconditional (session status), keyword-triggered (collision symptoms → taxonomy), or one-time (session-start rules banner).

## Sanitized skeleton

```python
#!/usr/bin/env python3
"""UserPromptSubmit: inject other sessions' active file leases."""
import json, sys

def main():
    payload = json.load(sys.stdin)          # prompt arrives on STDIN as JSON —
    prompt = payload.get("prompt", "")      # NOT in an env var. Verify the contract.
    leases = read_current_leases()          # small, fresh, cheap to render
    if not leases:
        sys.exit(0)                         # inject nothing when there's nothing
    out = render_compact_table(leases)      # BUDGET the tokens; you pay every turn
    print(out)                              # stdout -> injected into context
    bump_fire_counter()                     # prove you're alive; silence = death
    sys.exit(0)

main()
```

## Failure modes of this pattern

- **The input-channel assumption:** ours read an env var the harness never sets and **no-opped for two months** (2 fires in 101k audit lines) — fail-open injectors die silently. Read the documented channel (stdin JSON), self-test non-empty input, and count fires ([PM-016](../postmortems/016-the-classifier-that-never-ran.md)).
- **Staleness masked by liveness:** an injector that faithfully re-injects a *dead* value every turn looks healthy. One of ours re-injected a pre-compaction session goal for 80+ turns because its staleness check keyed on a timestamp the injector itself kept bumping. Check content freshness, not heartbeat.
- **Token tax and nag fatigue:** injection costs context every single turn; an advisory that re-fires per-prompt trains the model to skim past it. Budget aggressively; once-per-session for nudges ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)).
- **Emission-order under pressure:** when context is tight, later-injected blocks survive compaction differently. Order deliberately: dynamic state that must win goes where it outlives the static boilerplate.
- **Keyword triggers fire on quoted history:** a taxonomy injector keyed on symptom words will fire when a postmortem *quoting* those words is discussed (ask us how we know). Acceptable noise if the injection is small; label it as background, not instruction.

**Where it's enforced in our stack:** checkout-lease tables, KB corrections digest, session-status prior state, collision-symptom taxonomy, epistemic-rules banner — the always-on layer that makes 7–12 concurrent sessions legible to each other.
