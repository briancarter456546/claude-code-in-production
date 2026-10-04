# The gate meant to enforce task claims could hand a session *another* session's claim — out of a shared cache whose TTL the bug report got wrong by 3,600×

**Keywords:** shared cache cross session leak, single slot cache no identity validation, task checkout gate fallback wrong session, session id mismatch fallback, TTL unit confusion seconds hours, time.time comparison bare float, nondeterministic guard outcome cache age, state file cross leak, verify the number in the bug report, concurrent agent sessions authorization

**Incident date:** observed 2026-10-03 · **Internal refs:** #3043 · **Status:** open — not fixed (claim and ownership semantics are inside a deliberate deferral boundary) ; **one number in the original report is corrected here**

---

## What broke

Before a session edits a file, a `PreToolUse` gate checks that the session holds a task claim covering it ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)). To get the claim list the gate shells out to the task CLI, which costs a subprocess per write, so it caches the result on disk.

The cache is **one shared file** in a shared working tree, written by whichever session last missed it. Its payload is the CLI's whole JSON answer — including the field `session_id`, which is the identity of **the session that happened to populate the cache**, not of the session now reading it.

The reader does no identity validation:

```python
st = json.loads(CHECKOUT_CACHE.read_text(encoding="utf-8"))
if now - float(st.get("ts", 0)) < CHECKOUT_CACHE_TTL:
    return st.get("data")          # whole payload, no session check
```

The gate then filters the rows for its own session id, finds none, and falls back:

```python
cli_sid = data.get("session_id")
sid_mismatch = bool(cli_sid and cli_sid != sid)
if sid_mismatch and not mine:
    mine = [r for r in rows if r.get("session_id") == cli_sid]
```

That fallback was written for a real and narrower problem: the CLI resolves its own session id (environment variable, else a parent-process walkup) while the hook resolves one from the event payload, and when those disagree for **one session reasoning about itself**, the row exists under the other id and the old message sent the reader after the wrong bug. "Trust the CLI's own view" is correct for that case.

With a **shared** cache across 7–12 concurrent sessions, `cli_sid` is no longer "me under my other name." It is whoever warmed the cache. So a session holding **no claim at all** can be handed a stranger's claim and allowed to write.

Observed 2026-10-03: the cache held one session's id while an entirely different session was reading it. The live cache file still shows the shape — a `session_id` belonging to one session and claim rows belonging to others.

## How it was detected

A deliberate subtraction audit — walking the guard set asking what each one would do if it were removed — read this function rather than its fire log. Nothing in the audit log distinguishes "allowed because the session holds a claim" from "allowed because it inherited one," so the log could not have surfaced it.

## Root cause

**A single-slot cache of a per-identity answer.** The cached value is not a fact about the repository; it is a fact about *who asked*. Caching such a value in a shared location makes its correctness depend on which process last ran — the same class as the lane marker in [PM-056](056-three-sessions-ran-for-days-in-the-wrong-lane.md), where one shared file let every session re-stamp everyone's context.

The second-order cause is a **fallback written against a single-session mental model and left in place after the system became multi-session.** The comment explaining it is accurate about the case it was built for and silent about the case that now dominates. Reading it, the fallback looks principled.

A consequence worth naming separately: the gate's verdict is **nondeterministic for an unchanged input**. The same write by the same session is allowed or refused depending on the *age of a file written by a third party*. A guard whose outcome depends on cache age cannot be reasoned about from its own audit rows.

## The number in the bug report was wrong, and this is how we found out

The internal report stated the window as `CHECKOUT_CACHE_TTL=12h`. **It is 12 seconds.**

```python
CHECKOUT_CACHE_TTL = 12.0
now = time.time()
...
tmp.write_text(json.dumps({"ts": now, "data": data}))
```

`ts` is epoch seconds from `time.time()`, and the comparison is in the same unit, so the constant is seconds. `12.0` sitting next to the word `TTL` reads as hours to a human and to an agent; a bare float carries no unit, and nothing in the file states one. The report overstated the exposure by **3,600×**.

That changes the severity assessment, and not the mechanism:

- The **defect is unchanged** — no identity validation, shared slot, stranger's claim adopted. It was *observed*, not theorized.
- The **exposure window per cache fill is 12 seconds**, not half a day. With 7–12 sessions and one gate invocation per write, a 12-second shared window is still reached routinely, and the cache is refilled continuously rather than once.
- The **nondeterminism is sharper, not softer.** A 12-second window means the same write genuinely can be allowed at one moment and refused seconds later.

This correction exists in the published record because this repository's writing protocol requires every mined number to be verified against primary sources before it is published, and this is what that rule is for. The lead was internally generated, confidently stated, and wrong — in the direction that makes the finding sound worse.

## Blast radius

A session with no claim could write to paths another session had claimed, which is the one thing the claim system exists to prevent, and the write would be **logged as allowed** with no indication that the authorization was borrowed. The population of such writes is **not recoverable**, because the audit row for an allow does not record *which* row authorized it — the same unjudgeable-population problem as [PM-066](066-the-shadow-gate-that-cannot-graduate.md).

No corruption has been attributed to it. That is a statement about what the log can show.

## The fix

**Not fixed.** Claim and ownership semantics are inside a deliberate deferral boundary set by the operator, and the adjacent claim-authorization route is under an active containment directive. The repair is recorded for whoever lifts that boundary, and it is small:

1. **Validate identity on read.** If the cached payload's `session_id` is not this session's, the cache is not an answer to this session's question — treat it as a miss. One comparison.
2. **Key the cache by session** rather than keeping one slot, or cache only the session-independent part of the answer.
3. **Delete the `cli_sid` fallback, or gate it on the condition it was written for.** Its premise — "the mismatch means me under another name" — is only true when the data came from this session's own CLI invocation. After (1), that premise is checkable.
4. **Put the unit in the name.** `CHECKOUT_CACHE_TTL_SECONDS = 12.0`. A bare numeric constant beside a conventionally-hours concept misled a careful reader with the source open; it will mislead the next one.

## Has the guard fired since?

The gate runs on every `Write`/`Edit`/`MultiEdit`/`NotebookEdit`. Over the measured week it logged **2,418 invocations**: 1,310 allowed on `has_checkout`, 1,059 allowed on `exempt_path`, **47 blocked** on `no_checkout`, and 2 allowed because the guard itself was degraded.

The relevant row is the first one. **1,310 writes were allowed on the grounds that the session holds a claim, and not one of those rows records which claim** — so the log cannot separate the earned allows from the inherited ones. That is why a code read found this defect and 2,418 rows a week did not. The 2 `guard.degraded` allows are a second, smaller instance of the same blindness: the gate recorded that it had failed open without recording what it failed open *on*.

## Lessons for agent-driven development

1. **Never cache an identity-scoped answer in a shared slot.** The test is one question: *is the cached value a fact about the repo, or a fact about who asked?* If the payload contains a `session_id`, it is the second kind, and sharing it is a cross-leak by construction.
2. **A fallback is a trust assertion. Re-read every one when the concurrency model changes.** This one was correct under a single-session model and became a vulnerability unchanged — and its comment still describes the world it was written for.
3. **Verify the numbers in your own bug reports before acting on them.** A severity figure computed by an agent reading its own code was off by 3,600× in the alarming direction. The mechanism survived verification; the magnitude did not, and the two deserve separate confidence levels.
4. **Units belong in identifiers, not in comments or conventions.** `CHECKOUT_CACHE_TTL = 12.0` is ambiguous to every reader, human or model. Spell the unit.
5. **Log *why* an allow was granted, not just that it was.** An allow row with no authorizing reason makes the affected population permanently unknowable — and makes the guard's own log useless for finding defects in the guard.
6. **Nondeterministic gates cannot be audited from their outcomes.** If the verdict depends on the age of a file written by another process, then two identical writes legitimately disagree, and no amount of row-counting will show you which was right.
