# Pattern: The Tool Registry — Make "Use X Tool" Mean the Actual Tool

**Problem:** The operator says "run the sleuth on this" and the agent — helpfully, catastrophically — *simulates* the tool: writes its own quick analysis in the tool's style instead of executing the real thing. Or it can't map the nickname to the script and guesses. Substituted analysis wearing a tool's name is worse than an error; it's a fabricated provenance.

**Mechanism:** A **registry file** mapping every callable tool to its slug, nicknames, invocation, and description. Registered in one place; consumed by (a) a prompt-time injector that recognizes tool references in operator prompts and reminds the agent of the exact invocation, and (b) review-time checks that a "ran the tool" claim has a matching execution in the transcript.

## Sanitized skeleton

```
# tool-registry.txt -- one line per callable tool
# slug | nicknames | invocation | one-line description
sleuth      | sleuth,market-sleuth   | python sleuth_v2_1.py --ticker {T}   | anomaly scan on one ticker
kb-query    | kb,knowledge-base      | python kb_v1_0.py query --text "{q}" | search validated findings
critic      | critic,planbreak       | (skill) /critic                      | two-stage adversarial critique
```

```python
# prompt-time: match operator's words against nicknames, inject the invocation
hits = [row for row in registry if any(nick in prompt.lower() for nick in row.nicknames)]
if hits:
    print("[TOOL REGISTRY] The operator named these tools -- RUN them, do not simulate:")
    for row in hits:
        print(f"  {row.slug}: {row.invocation}")
```

## Failure modes of this pattern

- **Simulation is the default failure, and it's silent.** Nothing about a fluent fake analysis announces that no tool ran. The registry makes the *invocation* concrete, but only transcript-level verification ("was there an execution matching this claim?") closes the loop — same testimony-vs-artifact law as [PM-038](../postmortems/038-the-validation-that-never-happened.md).
- **Registry staleness:** a renamed script leaves a nickname pointing at nothing; the agent's failed invocation then *justifies* falling back to simulation. Registry rows get checked against the filesystem in the self-test suite.
- **Per-item subshell scans are a latency bomb:** our first nickname matcher forked two processes per name — ~8.4 seconds per prompt for 99 nicknames ([PM-019](../postmortems/019-when-the-safety-layer-became-the-outage.md)). Match in-process.
- **Nickname collisions with prose:** short nicknames ("kb", "critic") match casual sentences; matched-but-unwanted injections are noise. Require word boundaries; keep nicknames distinctive.
- **New tools skip registration** unless creation is gated — the [designer-ack gate](../adr/011-designer-ack-and-seven-question-design-gate.md)'s checklist includes "registered in the tool registry," making the registry part of a tool's definition of done.

**Where it's enforced in our stack:** `tool-registry.txt` + prompt-time injector; "when the operator names a tool, RUN the tool" is one of the oldest rules in the instruction file — the registry is what turned it from a plea into a mechanism.
