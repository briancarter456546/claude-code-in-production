# Every Documented Bypass for Our Guard Hooks Was a Silent No-Op

**Keywords:** Claude Code hooks environment variables, hook bypass mechanism, inline env var subprocess, guard escape hatch, silent no-op, hook process environment, Windows Git Bash hooks

**Incident window:** in effect for weeks across many guards; confirmed 2026-06 · **Internal refs:** tasks #1680, #1742, #1252, #1270, #1136, #871 · **Status:** fixed (parser ported to a channel that actually arrives); bypasses now audit-logged with reasons

---

## What broke

Every guard hook in the stack documents an escape hatch — an environment variable with a mandatory reason string:

```bash
SKIP_SOME_GUARD="reason:false positive on doc example" git commit -m "..." -- notes.md
```

The convention is load-bearing: a guard with no legitimate-exception path gets disabled wholesale the first time it blocks something important. The audit trail of bypass reasons is also the guard's report card.

The discovery: **the inline form had never worked. On this platform, the hook subprocess never received the variable.** Claude Code spawns hook processes from the harness, not from within the Bash tool's subshell — an inline `VAR=x cmd` sets the variable for `cmd`'s environment, but the guard evaluating that command runs in a *different process tree* that inherits the harness environment, not the command's. Every documented inline bypass, across dozens of guards, for weeks: a no-op. One hook contained a fully-implemented bypass parser, defined at line 102, that no code path had ever called.

## How it was detected

This class of bug is nearly undetectable from the outside, which is the real story. A failed bypass looks exactly like a working guard: the block message appears, the agent assumes the bypass was rejected on the merits (wrong reason format? policy?), rephrases, retries, eventually complies with the block. **The guard being stricter than designed produces no error signal anywhere.** It surfaced only when a session, blocked on a case that was unambiguously legitimate, escalated instead of complying — and instrumentation showed the variable simply absent from the hook's environment.

## Root cause

Surface: a wrong assumption about process ancestry — "the hook sees the command's environment" — untested because bypasses are, by design, rarely used.

Deeper: **the escape hatch was the one code path with no test and no telemetry.** Guards logged blocks and passes; nobody logged bypass *attempts*, so zero successful bypasses read as "nobody needed one" rather than "the mechanism is dead." The rarest path is the least-tested path is the most-likely-broken path.

## Blast radius

Weeks of over-blocking across the whole guard fleet: legitimate work rerouted, delayed, or abandoned because the documented exception didn't function. Unmeasurable exactly — which is itself the lesson — but the retry churn from over-strict guards shows up in the session-degradation analysis ([PM-021](021-alarm-fatigue-by-the-numbers.md)). Trust cost: every guard's documentation had been wrong together.

## The fix

- Bypass evaluation moved to channels that verifiably reach the hook process (parsing the command string itself for the inline prefix, and/or session-scoped bypass files) — with a self-test that asserts end-to-end arrival, not just parser correctness.
- **Every bypass attempt is now audit-logged** — accepted or rejected, with its reason string. The mechanism finally has telemetry, and the logs now double as guard report cards (a guard with a high bypass rate is a guard with a false-positive problem — see [ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md)).
- One residual, documented honestly: certain sandboxed execution paths still can't deliver inline env vars, and the affected guards say so in their block messages rather than documenting fiction.

## Has the guard fired since?

Inverted question for this one: the *bypasses* now fire. Recent 12-day audit window: 14 reason-logged bypasses on the stranger-file guard alone, each with a human-readable justification in the log. The silence that hid this bug is structurally gone — a dead bypass mechanism would now show up as a flatline in a log that's supposed to have traffic.

## Lessons for agent-driven development

1. **A broken escape hatch is invisible because its failure mode is the guard "working."** Over-blocking produces compliance, not errors. Only telemetry on bypass attempts distinguishes strict from broken.
2. **Test the paths designed to be rare.** The bypass is exercised least, trusted most at the worst moment, and was the only untested branch in every guard that had it.
3. **Verify delivery, not just parsing.** The parser was correct. The variable never arrived. End-to-end tests through the real process topology or it doesn't count.
4. **Documentation of a mechanism is a claim; log traffic is the evidence.** Dozens of README-documented bypasses with zero logged uses should have been the alarm, if anything had been counting.
