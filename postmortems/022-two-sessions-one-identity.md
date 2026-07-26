# Two AI Sessions Derived the Same Identity and Clobbered Each Other's State

**Keywords:** session identity collision, session id derivation, concurrent agent state, shared state file, session impersonation, multi-session Claude Code, state isolation

**Incident window:** three escalating incidents, 2026-05→06 · **Internal refs:** tasks #1195, #1203, #1497; session-id lib (multiple hardenings) · **Status:** fixed; collision-context injector now fires on symptom keywords

---

## What broke

Everything per-session in this stack — state files, journals, leases, locks — is keyed by session identity. Three incidents, escalating in subtlety, proved identity itself was the weak layer:

1. **Same-ID collision (#1195):** two concurrently-open windows *derived* the same session ID (the derivation used inputs that weren't unique across simultaneous launches). Each session then read the other's injected state as its own and overwrote the other's writes — two agents, one name, interleaved memory. Symptoms were surreal: a session "remembering" work it never did, lanes flipping mid-session.
2. **Shared-file clobber (#1203):** a global state file (session status for the operator's screen) was written by all sessions; last-writer-wins meant the visible status of one session was routinely another session's truth. Fixed by field-splitting and per-session keying — the shared file was the bug, not the writers.
3. **The impersonating fallback (#1497):** the subtlest. A wrap-time heartbeat check, when it couldn't determine its own session cleanly, **fell back to a lookup that returned a sibling session's identity** — and then acquired the wrap lock as that sibling. A safety mechanism (verify liveness before wrap) became an impersonation mechanism under exactly the degraded conditions it existed for.

## How it was detected

Incident 1 by behavioral absurdity (state from nowhere); incident 2 by the operator watching a session's on-screen status describe a different session's work; incident 3 by wrap-lock forensics showing a lock held under an ID whose session was verifiably elsewhere. Each fix exposed the next-deeper layer.

## Root cause

**Identity was derived, not issued.** Sessions computed who they were from ambient facts (paths, times, environment) rather than receiving a unique credential from the one party that knows — the harness. Derivation from shared ambient state collides under concurrency by construction; every fallback that "figures out" identity under failure re-runs the same flawed inference with even less information.

## Blast radius

Cross-contaminated state files, one wrongly-held wrap lock, hours of "which session did this?" forensics per incident — and a design rule that reshaped the whole stack (per-session keying became the default for all hook-visible state, [ADR-014](../adr/014-per-session-skill-state.md)).

## The fix

- Session ID sourced from the harness-issued identifier everywhere, via one shared library — **no local re-derivation**, no alternative code paths computing identity their own way.
- Degraded-mode rule inverted: **if identity can't be established, operations that require identity fail closed** — a wrap that can't prove who it is doesn't wrap, rather than guessing.
- Shared mutable files eliminated or field-split per session; the collision-symptom taxonomy (5 classes, catalogued) is auto-injected into any session whose prompt mentions collision symptoms, so recurrence gets classified instead of re-diagnosed from scratch.

## Has the guard fired since?

The collision-context injector fires whenever symptom keywords appear (it fired on the drafting of this very document — the taxonomy arrived as a system reminder, correctly, if a little proudly). The same-ID derivation class hasn't recurred since single-sourcing; the taxonomy's remaining open class is harness-level and tracked upstream ([PM-024](024-ghost-text-from-another-session.md)).

## Lessons for agent-driven development

1. **Identity must be issued by the layer that can guarantee uniqueness — never derived from ambient state.** Derivation is collision with extra steps.
2. **One library for identity, zero exceptions.** Every independent "figure out who I am" implementation is a future impersonation bug.
3. **Fallbacks that guess identity are worse than failures.** Under degradation, "I don't know who I am, halting" beats "I'll assume I'm someone" every time — the safety path was the attack path.
4. **Shared mutable state is guilty until proven necessary** in concurrent-agent systems. Key everything by session first; share by explicit design only.
