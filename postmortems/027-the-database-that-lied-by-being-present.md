# The Task CLI Silently Fell Back to a Stale Local Database — Writes "Succeeded" Into a Phantom Store

**Keywords:** silent fallback, split brain database, stale local copy, environment variable unset, task database, fail-open configuration, phantom writes, degraded mode

**Incident date:** found 2026-07-25 — reproduced live during this repo's own source mining · **Internal refs:** task #2133 (the fix task, tracked in the *real* database) · **Status:** open at time of writing; fix specified (fail loud, not local)

---

## What broke

The task database — assignments, priorities, completion state for everything the agents do — lives on the always-on droplet; the CLI reaches it via a connection URL from an environment variable. Design intent: no URL, no service.

Actual behavior: **when the variable is unset, the CLI silently falls back to a local SQLite file** — a stale snapshot from an earlier era containing ~315 tasks, versus ~1,263 live (task numbering in the two stores had even diverged: the same ID names different tasks). Every operation "works": `list` lists, `add` adds, `done` completes — against a phantom store nothing else reads. A session in this state can claim work, complete work, and file new work, all into a database whose only consumer is itself. No warning distinguishes the two worlds; the output format is identical.

A separate wrinkle compounds it: the *checkout* mechanism (file-scope leases) lives in a third store and never validates task existence — so `checkout 2116` "succeeds" whether or not task 2116 exists anywhere ([the phantom-checkout note in PM-011's family](../adr/006-task-checkout-leases-and-collision-guards.md)). Sessions ran for days holding leases against narrative task numbers.

## How it was detected

Twice, embarrassingly:

1. A handoff document asserted two task IDs "do not exist in task_db" — a later session found both, fine, in the remote store. The earlier session had been querying the stale local copy without knowing it.
2. **Reproduced live during the mining run for this very repo:** the agent auditing the task database for incident candidates started against the 315-task phantom before catching the count mismatch against a known-recent task number. The bug audited itself into its own postmortem.

## Root cause

Surface: a well-intentioned fallback branch — "if no URL, use local file" — written for a development convenience that outlived its context.

Deeper: **fallback-to-degraded is fail-open wearing a seatbelt.** The fallback preserved *operation* while silently abandoning *correctness*: worse than an error, because an error would have named the missing variable in one line. Add the second law of this repo's incidents: divergent copies don't announce themselves ([PM-010](010-stale-local-dashboard-forks-diverged-from-production.md)); presence is not validity.

## Blast radius

At least one handoff document published false claims about task state; unknown scattered writes into the phantom store during any session that ever launched without the env var (enumerable only by diffing the stores); investigation time inside the mining run itself. The trust cost is the sharp one: every "task_db says X" claim in the historical record acquired an asterisk.

## The fix

Specified in the fix task (open at time of writing, and this document will not pretend otherwise):

- **No silent fallback.** URL unset → hard error naming the variable. Local mode requires an explicit opt-in flag that prints a banner on every command.
- **Store identity in output:** every CLI response carries which store answered (host or file path), so transcripts self-document their world.
- **Checkout validates existence** against the same store before granting a lease.

## Has the guard fired since?

Not yet — the fix is in flight, and per this repo's policy, an unshipped fix is a hypothesis. What *has* changed already: the mining incident put the store-count check ("does the task count look like the real database?") into the standard opening moves of any session touching task state.

## Lessons for agent-driven development

1. **A fallback that changes which data you're talking to is not a fallback — it's a silent fork.** Degrade capability loudly or fail loudly; never substitute the world quietly.
2. **Print your provenance.** Any client that can talk to more than one store must say which one answered, every time. Transcripts that don't name their world can't be audited.
3. **Leases and registries must validate their referents.** A checkout that succeeds against a nonexistent task is bookkeeping theater.
4. **Presence is the weakest possible evidence of correctness.** The database was there, it answered, it was wrong. "It returned rows" proves availability, not truth.
