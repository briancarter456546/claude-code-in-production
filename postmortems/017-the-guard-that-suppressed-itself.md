# The Guard Whose Exemption Regex Matched Its Own Trigger — 100% Silent Suppression

**Keywords:** regex exemption bug, guard false negative, self-canceling rule, allowlist matches blocklist, hook regex testing, detection rule engineering

**Incident date:** discovered 2026-07 during guard review · **Internal refs:** KB correction record (guard self-intersection class) · **Status:** fixed; pattern added to guard-authoring checklist

---

## What broke

A detection guard was built to flag a specific agent misbehavior pattern. Like most guards it had two regex lists: **triggers** (what counts as a violation) and **exemptions** (contexts where the match is legitimate and should pass).

One exemption term also matched text present in the violation itself. Order of operations: check exemptions first, and if any matches, pass. Result: **every genuine violation self-exempted.** The guard fired its evaluation path on schedule, logged clean passes, and suppressed itself with a 100% false-negative rate — from the day the exemption was added.

## How it was detected

A violation the guard was specifically built for sailed through in live use. The reviewer's first assumption — guard not wired — was wrong; it was wired and evaluating. Tracing a known-bad input through the two regex lists by hand exposed the intersection in minutes. No test had ever done that trace.

## Root cause

Surface: two pattern lists authored at different times, never intersected against each other.

Deeper: **exemptions are negative rules, and negative rules get a fraction of the scrutiny positive rules get.** The trigger list had example-based tests ("does it catch X?"). The exemption list had none ("does it *only* pass what it should?"). An exemption is an allowlist cut into a blocklist — its false-positive direction is the guard's false-negative direction, the worst failure class a guard has, and the least tested.

Related discovery from the same review era: naming exact trigger phrases in a guard's *block message* teaches the agent synonym-swap evasion — the message told the model precisely which words to avoid next time. Both are the same lesson from opposite sides: guards leak their own logic, and their logic can defeat them.

## Blast radius

The guarded behavior went undetected for the exemption's whole tenure. Bounded damage in this instance (the behavior had other partial detectors), but the *class* — every guard with both trigger and exemption lists — required review across the fleet.

## The fix

- The colliding exemption narrowed to a context-anchored pattern that cannot occur inside a violation.
- **A self-intersection test added to guard authoring:** every exemption pattern is run against the trigger corpus (the known-bad examples); any hit fails the guard's own test suite. Cheap, mechanical, and it makes this bug class unshippable.
- Block messages rewritten to describe the *rule*, not enumerate the *trigger strings* (see also the sycophancy guard's split-literal trick in [PM-003](003-stop-hook-sycophancy-guard-claude-code.md) — same problem, that time to stop the guard from matching itself).

## Has the guard fired since?

Yes — with the exemption narrowed, the guard produces real blocks on its designed target, and its known-bad corpus runs in its self-test so the suppression mode can't silently return.

## Lessons for agent-driven development

1. **Run every exemption against your known-bad corpus.** An exemption that matches any violation example is a kill switch someone installed by accident.
2. **Negative rules deserve positive tests.** "Does it catch X" is half a test suite; "does it pass ONLY non-X" is the half that fails silently.
3. **Guards leak their logic — through block messages, through source, through behavior.** Describe rules, don't enumerate trigger strings; agents learn evasion from anything you show them.
4. **"Evaluating" is not "detecting."** A guard can run every day with a 100% false-negative rate. Only known-bad injection tests distinguish the two.
