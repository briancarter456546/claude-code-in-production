# ADR-014: Phase-gated workflow state is per-session, keyed by session id — never shared

**Status:** Active · **Date:** 2026-07 · **Internal refs:** skill-state CLI; phase-gate hooks

## Context

Several complex workflows ("skills") are phase-gated: a multi-step procedure — triage → diagnose → propose → approve → capture → prevent, for example — where hooks block skipping ahead, and a human-approval phase is a hard stop. The gating needs state: which skill is active, which phase it's in. The first implementation stored that in a **single shared state file**. With one session, fine. With 7–12 concurrent sessions, immediate collision: session A activates a skill and session B — doing unrelated work — starts getting *blocked by A's phase gates*, because the hooks read the shared file and concluded B was mid-skill. Sessions were also clobbering each other's phase progress on write. The bug class is the oldest one in concurrency: global mutable state.

## Decision

Skill state is **per-session**: one state file per session, keyed by the harness-issued session id, managed through a small CLI that hooks and skills call instead of touching files directly. Gate hooks resolve *this* session's id, read *this* session's state, and ignore everyone else's. Orphaned state (from crashed or expired sessions) is prunable by inspection since each file self-identifies its owner.

One deliberate carve-out: workflows that are *supposed* to span sessions (a build pipeline handed from one session to the next) opt into shared state explicitly, rather than shared being the accident default.

## Alternatives considered

- **Locking on the shared file.** Rejected: locks serialize the wrong thing — sessions don't need to take turns being in a skill; they need entirely independent state. Also stale locks from dead sessions.
- **Embedding state in the conversation context.** Rejected: hooks run outside the model and need to read state without asking it; also context compaction can silently eat in-conversation state.
- **A state server.** Overweight; files keyed by session id deliver isolation with zero moving parts.

## Consequences

- Windows path quirk, learned the annoying way: session ids and path joining had a backslash-mangling interaction in the CLI that produced state files nobody could find. Cross-platform path handling is part of the contract now ([ADR-003](003-sh-to-py-wrapper-convention-for-windows-hooks.md) energy, same lesson).
- Orphan files accumulate and need pruning — the trade against stale-lock hell, and the better side of that trade.
- The pattern generalized: per-session keying became the default for *any* hook-visible state (status headers, checkout leases already worked this way). "Shared unless proven otherwise" flipped to "isolated unless explicitly shared."

## What we'd do differently

Ask the concurrency question at design time, every time: *what happens when twelve of these run at once?* This subsystem was designed against a mental model of one session, in a system that had been running ten for months. The seven-question design gate ([ADR-011](011-designer-ack-and-seven-question-design-gate.md)) exists partly because of misses like this.
