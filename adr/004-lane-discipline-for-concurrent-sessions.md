# ADR-004: Work is partitioned into lanes with canonical paths, enforced by a write guard

**Status:** Active · **Date:** 2026-06 (reconstructed) · **Internal refs:** lane-discipline guard hook

## Context

With 7–12 concurrent sessions, "where does the status doc live?" stopped being a style question. Sessions wrote status summaries, roadmaps, and architecture maps wherever felt natural in the moment — which meant the same subsystem had three status docs in three directories, each partially true, none authoritative. The operator, switching between a dozen windows, paid the reconciliation cost every time. Duplicated state documents aren't just untidy; they're *actively misleading*, because each one looks canonical.

## Decision

The repo is partitioned into **seven lanes** (infrastructure, code subsystem, trading, design, plus three reserved-but-inactive ones). Rules:

- Every session operates inside one lane, auto-detected at session start from the first prompt (keyword config), overridable explicitly. The session prefixes its plans and summaries with `Lane: <name>`.
- Each lane has **canonical paths** for its status doc and its architecture maps. One home per document type per lane.
- A **PreToolUse guard** blocks any write of a status doc or map outside the canonical paths. The guard's own path table is the source of truth — deliberately *not* duplicated into the instructions file, because a copy would drift.
- Inactive lanes may not have their directory scaffolding created until activated via a tracked task — pre-creating "obvious" structure is how orphan directories are born.
- Cross-cutting work uses an explicit bypass with a logged reason.

## Alternatives considered

- **A single global status doc.** Rejected: merge conflicts across concurrent sessions, and a 7-domain doc is unreadable.
- **Naming conventions without enforcement.** Tried first; decayed within weeks (see [ADR-002](002-hooks-as-enforcement-not-instructions.md) — this is that thesis applied to file placement).
- **Per-session docs.** Rejected: multiplies the reconciliation problem by session count.

## Consequences

- Cross-cutting infrastructure work carries bypass friction — a real cost, paid on purpose, because "this touches everything" was the excuse behind most stray docs.
- The guard's path table needs updating when a lane is added — one place, versioned, testable.
- Session-start lane detection is occasionally wrong and must be overridden; cheap, visible, correctable.

## What we'd do differently

Introduce lanes at 3 sessions, not at 10. The cleanup migration (consolidating stray status docs into canonical homes) cost more than the entire enforcement build.
