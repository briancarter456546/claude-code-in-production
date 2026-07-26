# ADR-006: Concurrent sessions coordinate through task-checkout leases and a collision guard

**Status:** Active · **Date:** 2026-06 (reconstructed) · **Internal refs:** task-checkout state injector + collision guard hooks

## Context

Two Claude Code sessions editing the same file don't conflict loudly — they conflict *silently*: the later save wins, the earlier session keeps reasoning about code that no longer exists, and both proceed confidently. With 7–12 sessions on one repo, the failure rate went from theoretical to weekly. Worse were the near-misses: double-commits to a shared branch and wrap-up commits colliding, where two sessions' closing rituals interleaved.

## Decision

A **lease-based checkout system** on top of the shared task database:

- A session claims work with `checkout <task-id> --paths "<pipe-delimited file globs>" --note "<scope>"`. The lease carries the session id, a heartbeat, and an optional TTL.
- A **UserPromptSubmit injector** prints every other session's active leases into every turn, so each session sees the occupied territory without asking.
- A **PreToolUse collision guard** blocks Write/Edit calls that touch paths inside *another* session's lease. Bypass requires a logged reason (the standard escape-hatch convention from [ADR-002](002-hooks-as-enforcement-not-instructions.md)).
- Release on completion; stale leases expire via heartbeat/TTL.

## Alternatives considered

- **Git branch per session.** Rejected: the repo has an auto-sync pull loop on the droplet keyed to the main branch, and 12 long-lived branches on one working tree means a merge queue nobody staffs. The shared dirty tree is a known cost we chose over merge hell.
- **OS-level file locks.** Rejected: stale locks after crashed sessions, no visibility into *why* a file is locked, and no scope narration for the operator.
- **Operator memory** ("I'll just remember what each window is doing"). The baseline. It failed at exactly the rate you'd expect.

## Consequences

- Coordination is visible and narratable — the injected lease table doubles as a "what is everyone doing" dashboard in every window.
- **The checkout call does not validate that the task id exists.** Discovered embarrassingly: sessions checked out phantom task numbers for days and the leases "worked" (the path protection held; the task linkage was fiction). Known gap, tracked.
- Lease hygiene is real overhead: forgotten releases block other sessions until TTL expiry; over-broad path globs claim more territory than the work needs.
- The guard only protects leased paths. Unleased files remain last-write-wins — the system protects *declared* intent, it doesn't infer it.

## What we'd do differently

Validate task existence at checkout, and require leases (not merely allow them) for edits to any file matched by another session's recent activity. Both were deferred as "polish" and both bit us.
