# The Lock Protecting Local Git Needed a Network Round Trip: 749 Timeouts in One Week

**Keywords:** distributed lock local operation, git mutex concurrent AI agents, fail closed lock service unreachable, PreToolUse gate latency, curl timeout 28 hook, coordination channel failure, concurrent session git contention, lock acquisition retry, remote lock for local resource

**Incident date:** measured 2026-09-27 over the window 2026-07-15 → 2026-09-27 · **Internal refs:** git mutex workstream; relay architecture · **Status:** open — degrading ; 2,389 timeout-retries and 61 hard refusals for an unreachable lock service, against 92 refusals for the contention it exists to prevent

---

## What broke

With 7–12 agent sessions sharing one working tree, concurrent `git` writes are the sharpest edge in the system — one session's `add` or `commit` silently harvests another's staged work ([PM-008](008-broad-git-add-swept-another-sessions-files.md), [PM-011](011-bare-commit-swept-the-shared-index.md)). The fix was a mutex: a `PreToolUse` hook classifies every `git` invocation as read-path or write-path, and write-path commands must acquire a repo-scoped lock before running. Read-path commands (`status`, `diff`, `log`, `show`, `fetch`, …) skip it entirely.

The lock itself lives on the **always-on remote host** — reused deliberately, because an existing lock service was already there and a cross-machine lock also covers the scheduled jobs that run on that host. Every write-path `git` command therefore costs a round trip: local hook → local relay process → SSH → remote lock script → back. Budget: **4 seconds**, one retry at 8 seconds. The contract is **fail closed** — if the lock cannot be reached, the git command is refused.

Measured over 74 days of the audit log, whose first record is 2026-07-14 (nothing earlier is retained on this machine, so the guard's first weeks are outside the window):

| outcome | count |
|---|---|
| lock acquired, command allowed | 2,807 |
| read-path, no round trip | 1,997 |
| **first attempt timed out, retried** | **1,867** (plus 522 on the release side) |
| **blocked: another session holds the lock** | **92** |
| **blocked: lock service unreachable** | **61** |

**2,377 of the 2,389 retries are the same error: the 4-second budget expired** (`curl rc=28`). Not a refusal, not an error response — no answer in time.

And it is getting worse. Every ISO week in the window, no rows omitted:

| week | acquired | timeout-retries | retries per acquire | contention blocks | refused, service unreachable |
|---|---|---|---|---|---|
| W29 (partial) | 14 | 4 | 0.29 | 0 | 0 |
| W30 | 197 | 31 | 0.16 | 0 | 2 |
| W31 | 95 | 36 | 0.38 | 0 | 0 |
| W32 | 359 | 40 | 0.11 | 0 | 1 |
| W33 | 197 | 29 | 0.15 | 0 | 1 |
| W34 | 280 | 209 | 0.75 | 1 | 5 |
| W35 | 204 | 209 | 1.02 | 9 | 3 |
| W36 | 426 | 267 | 0.63 | 7 | 3 |
| W37 | 243 | 182 | 0.75 | 11 | 8 |
| W38 | 405 | 633 | 1.56 | 22 | 9 |
| **W39 (partial)** | **387** | **749** | **1.94** | **42** | **29** |

Two things in that table. The **inflection is W34** — the per-acquire retry rate steps from 0.11–0.38 to 0.75 and never comes back. And the last row: **roughly two timeout-retries for every successful acquisition**, with git commands refused *because the lock service could not be reached* (29) reaching two-thirds of those refused *for the contention the mutex exists to prevent* (42).

What the table does **not** support is a clean "degraded N times faster" ratio, and an earlier draft of this postmortem claimed one. Contention blocks start at zero, so their growth rate is undefined, and over W36→W39 contention actually grew faster (7→42) than retries (267→749). The defensible statement is the per-acquire column: **the cost of using the lock rose twelve-fold per use (0.16 to 1.94, and 17x against the window's 0.11 minimum) while the lock's useful work was still ramping up from zero.**

## How it was detected

By a scheduled read of the guard ledger, not by anyone noticing. This failure is close to invisible in normal use: the retry usually succeeds, so from inside a session a `git commit` is simply **slow**, and slow is what everything is when a dozen sessions share a machine. Nobody attributes four seconds to a lock.

The 61 hard refusals *were* visible — a session gets a block message saying the lock service is unreachable — but they arrived one at a time, across many sessions and weeks, each looking like a transient blip rather than a trend line.

## Root cause

**A lock for a local resource was placed behind a network hop.** The working tree is on one machine. The contention is between processes on that machine. The lock that arbitrates it requires a local HTTP call, an SSH session, and a remote script — every time.

That choice was not careless; it bought something real (cross-machine coverage, and reuse of a lock service that already existed and was already correct). But it couples the availability of local git to the availability of a remote round trip, and it does so on the **hot path of the single most frequent write operation in the system**.

The deeper cause is a scaling asymmetry that only shows up in the ledger:

- Contention blocks — the mutex doing its job — grew from 0 to 42 per week. Good: the fleet got busier and the lock started earning its place.
- Timeout-retries grew from 31 to 749 per week, and per successful acquisition from 0.16 to 1.94. **Paying for the lock got twelve times more expensive per use, while the lock's useful work was still ramping up from zero.**

The likely mechanism is that the relay serializes its round trips, so as concurrent sessions multiplied, the queue in front of a 4-second budget grew — *labelled as a hypothesis, at medium confidence*: the ledger proves the timeouts and their timing, not their internal cause. What the ledger does prove is the shape: the errors are all budget-expiry, not refusals, and they scale with fleet activity rather than with lock contention.

One thing the design got right, and it should be said: **fail-closed was the correct call — and it is a deliberate exception to the standing rule for this transport.** The general rule is that hooks reading *informational* state from the relay degrade gracefully and return empty rather than obstruct work ([ADR-001](../adr/001-local-http-relay-instead-of-raw-ssh.md)). A lock is not informational: "I could not determine whether another session holds this" is not a safe basis for letting a shared-index write proceed. The same transport is known to answer HTTP 200 while putting a failure in the body ([PM-064](064-http-200-for-a-command-that-failed.md)), so a mutex that treated an unreachable lock as "probably fine" would be worse than no mutex at all. The 61 refusals are the contract working. The problem is not the contract; it is that the contract is invoked by a transport that misses its budget 749 times a week.

## Blast radius

- **Latency, everywhere, for months.** Each timeout costs at least the full 4-second budget before the retry begins. 749 in one week is **≈50 minutes of pure waiting** (749 × 4 s = 2,996 s), paid on write-path git commands only, spread across every session that commits.
- **61 refused git commands** over the window — work stopped mid-task, with a message about a lock service rather than about anything the session did.
- **Trust erosion in the retry path.** A retry-after-flake that usually succeeds teaches the fleet that lock errors are noise. That is exactly the conditioning that makes the 61 real refusals read as blips.

Nothing was corrupted, and the ledger contains no record of the mutex failing *open*. That is weaker than it sounds and should be labelled as such: the guard logs only its own decisions, so a write-path command that somehow reached git without an acquire attempt would leave no row. **Absence of evidence, not evidence of absence** — the honest claim is that every logged attempt was resolved, refused, or retried.

## The fix

Not yet shipped; published open with the measurement, because the fix is an architecture decision and not a patch:

- **Move the local half of the lock local.** The arbitration that matters for the shared working tree can be done with a local lock file with an owner record and a TTL — no network, microseconds, no fail-closed dilemma. The remote lock stays for what actually needs cross-machine coverage: the scheduled jobs on the remote host.
- **Then keep fail-closed, cheaply.** A local lock that cannot be read is a real failure and should still refuse. The point is not to weaken the contract; it is to stop paying a network round trip for a local guarantee.
- **Instrument the budget, not just the outcome.** The hook logs the retry; it does not log how long the successful acquisitions took. Recording the acquire latency would have made this visible in week 30 instead of week 39.
- **Add a coordination-channel health rule to the gate audit:** for any guard that depends on a remote call, compare *transport failures* against *true blocks*. When transport failures approach or exceed true positives, the guard's dependency is the bug, not the guard. This is the availability analogue of the existing bypass-rate rule ([ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md)).

## Has the guard fired since?

Continuously, and in both senses. In the most recent week it blocked **42** write-path git commands for genuine contention — that is real protection against the exact failure that produced two earlier postmortems, and the count rising from zero is evidence the concurrency problem is real and growing.

In the same week it also produced **749** timeout-retries and **29** refusals caused by its own transport. A guard can be simultaneously load-bearing and mis-architected; this one is both, which is why the fix is to keep the enforcement and move the mechanism rather than to weaken the rule.

## Lessons for agent-driven development

1. **Put the lock where the contention is.** If the resource is local, the primary lock must be local. Cross-machine coverage is a second, separate lock — not a reason to route local arbitration through a network hop on the hot path.
2. **A guard that depends on a remote call inherits that call's availability as its own failure rate.** Fail-closed makes that inheritance visible (refusals); fail-open makes it invisible (silent gaps). Neither makes it go away. The only real fix is to remove the dependency.
3. **Track transport failures against true positives for every remote-dependent guard.** Ours ran 2,389 transport failures against 92 true blocks over the window — a ratio no one would have accepted if it had ever been computed.
4. **A retry that usually works is a trend hiding in plain sight.** Successful retries convert an architectural defect into ambient slowness, which nobody attributes to anything. Log the latency of the *successful* path or you will only learn about the failure when it stops retrying successfully.
5. **Growth curves matter more than levels.** Contention blocks 0 → 42 per week is the system working. Timeout-retries 31 → 749 in the same period is the system failing. Both numbers only mean something as a slope, and both were in the same append-only log the whole time.
