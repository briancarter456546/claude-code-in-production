# [Pattern name, stated as the search query: "claude code <mechanism> pattern"]

**Keywords:** [search terms]
**Problem class:** [one sentence: when you need this]

## Problem
[The failure or risk this pattern addresses. Link the postmortem that birthed it if one exists.]

## Mechanism
[How it works, harness-agnostic where possible. Note which Claude Code hook event it binds to (PreToolUse / Stop / UserPromptSubmit / SessionStart) and what the exit-code / stdout contract is.]

## Code
[Sanitized, runnable example. Paths genericized. No secrets, no internal hostnames.]

## Failure modes of the pattern itself
[Every guard has them: false positives, recursion, single-point-of-failure, bypass abuse. State them or the pattern is oversold.]

## Where we run it
[What it protects in our stack, and how often it actually fires.]
