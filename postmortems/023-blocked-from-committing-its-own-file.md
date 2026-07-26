# The Guard Blocked a Session From Committing a File Named After That Session

**Keywords:** file ownership attribution, first writer wins race, touched files journal, guard false positive, commit attribution, concurrent sessions ownership, authorship inference

**Incident date:** 2026-07-15 · **Internal refs:** tasks #2059, #2060, #1715; touched-files-journal v1.1 · **Status:** partially fixed (attribution window narrowed); the honest residual is documented

---

## What broke

To stop cross-session commit contamination ([PM-008](008-broad-git-add-swept-another-sessions-files.md), [PM-011](011-bare-commit-swept-the-shared-index.md)), each session journals which files it touches; commit guards consult the journal as an authorship oracle.

The oracle had a race. The Bash-side journal inferred ownership by snapshotting `git status` after each command: *whatever became dirty during my command window, I touched.* With ~12 concurrent sessions, that inference is first-writer-wins fiction. Confirmed sequence from the incident log: session E wrote a handoff file at 17:37; session A ran an unrelated command at 17:38, saw the file newly dirty in its snapshot, and journaled it as its own.

Peak absurdity, same week: **session `9f61dd4e` was blocked from committing `notes/trading_2026-07-15_9f61dd4e.md` — a file literally named after it —** because a sibling session's journal had claimed it first, and the pre-commit backstop trusted the sibling's claim. The true author stood at the gate holding a file with its own name on it, refused. Resolution required the *human* to hand-paste a bypass variable with a diff hash. A 14-day journal scan window made it worse by inflating the pool of stale claims a file could be matched against.

## How it was detected

The block itself — loudly. Unlike most entries in this repo, the failure announced itself; the forensics (journal entries with timestamps, the 17:37/17:38 interleave) took the investigation.

## Root cause

**Attribution by observation instead of by declaration.** "It became dirty during my window" measures *when the observer looked*, not *who wrote*. Any concurrency at all breaks it. The deeper irony: the checkout-lease system ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)) already held *declared* ownership — the session had claimed its scope — but the journal didn't consult the leases; it preferred its own flawed observations.

## Blast radius

True authors blocked from their own work (the worst polarity for a guard — it punishes the innocent specifically); manual human bypasses with hand-computed hashes; and eroded trust in the attribution layer that several other guards depend on.

## The fix

- Attribution priority reordered: **declared scope (checkout leases) outranks observed dirtiness**; the journal is a fallback hint, not the primary oracle.
- The stale-claim window shrunk from 14 days toward hours; timestamps disambiguate near-simultaneous observation.
- Direct file operations (Write/Edit tool calls) journal *positively* — those are true declarations; only Bash-side inference carries the race, and it's now labeled as lower-confidence in the guard's decision logic.
- Honest residual, still open at time of writing: a first-writer-wins race remains in a narrowed window (task #2060). The guard family runs in warn-heavy modes where the oracle is weakest — documented rather than papered over.

## Has the guard fired since?

Yes, in both directions — which is exactly the point of publishing this one: 19 stranger-file blocks + 14 reason-logged bypasses in a recent 12-day window. Some of those bypasses are this postmortem's residual false-positive class, each one a logged data point steering the next attribution fix ([ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md)).

## Lessons for agent-driven development

1. **Observation-based ownership is a race condition wearing a lab coat.** "Dirty during my window" attributes by lookup timing. Use declarations (leases, explicit tool calls); observe only as a hint.
2. **If a declared-intent system exists, guards must consult it first.** We had leases and ignored them in favor of a homegrown inference — two sources of truth, the worse one winning.
3. **Watch for guards that specifically punish the innocent.** A false positive that blocks the *true author* is maximally corrosive: it teaches your best-behaved sessions that compliance doesn't pay.
4. **Publish your residuals.** The narrowed race is still there. Saying so keeps the bypass logs meaningful and the next fix honest.
