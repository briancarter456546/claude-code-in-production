# ADR-018: External adversarial review is tiered and budget-capped — caps limit spend, never evidence

**Status:** Active · **Date:** 2026-08-28 · **Internal refs:** #2527, #2528

## Context

[ADR-013](013-solution-validation-loop-external-adversary.md) put an external adversary in front of high-stakes proposals. It worked — and then it metastasized. By late August the practice had grown into ad-hoc multi-reviewer runs with no upper bound: one build consumed six external review passes; every verdict-producing artifact attracted two or three reviewers by habit rather than by classification. The supply side is hard-capped: three of the four external reviewer pools are weekly quotas shared across 7–12 concurrent sessions (including the primary model's own allowance — the operator's single binding constraint), and the fourth is metered dollars. Spend was tracked nowhere except task notes. The operator's framing: recording intentions in the task database is not enforcement — "task DB only is not enough."

The opposite failure was also live: with no legitimate "no review" category, sessions either over-reviewed mechanical work or skipped review silently, with nothing distinguishing the two.

## Decision

One ladder, four tiers, every dispatch counted:

- **T0 — no external review**, and saying so is a positive classification, not an omission. Deterministic gates (hooks, golden files, known-answer tests) are the adversary for mechanical work — but only when they actually cover the change's failure modes; when in doubt, classify up.
- **T1 — one reviewer, full file access, rotating seat** for any verdict-producing build.
- **T2 — two reviewers from different model families, at least one file-reading**, for repairs of rejected builds and statistical claims entering the knowledge base.
- **T3 — full ensemble** for ruling-grade artifacts only. Caps never thin this tier.

A PreToolUse guard detects review dispatches, and a ledger (SQLite, immediate-mode transactions; JSONL kept as an export view) records every one — including bypassed ones. The policy shipped in a **14-day measure mode**: everything allowed, everything counted; if the window expires with caps still unset, the guard blocks routine-tier dispatches until caps are written *from the measured data*. Enforcement is deliberately downstream of measurement.

The invariants that survived two rounds of external review of this very document:

- **Reviewers get files, never the agent's summaries.** Curated evidence is the one reliable blind-spot generator, and a file handoff costs the dispatching model almost nothing.
- **A prose-only reviewer is never the sole reviewer of executable code.**
- **The authoring model's family can never fill the required independent seat** — otherwise the primary model reviews itself wearing a different hat.
- **Rotation is verdict-blind.** Dropping the reviewer who rejected you last time is survivor bias with a scheduling excuse.
- **An abstention fills no seat.** A two-seat review with one abstention is incomplete and must say so.
- **Caps delay reviews or force an operator ack; they never shrink what a reviewer sees or skip a required tier.**
- **After two reject-and-repair cycles on one artifact, the next pass requires explicit operator ack** — cycles counted by blocking-findings-plus-repair, not by verdict label.
- **Plan critique before compute** (added by operator ruling the next day): any T1+ build whose compute or rework cost exceeds ~15 minutes gets its spec reviewed *before* the run, in addition to the post-execution critique. Evidence for the amendment: a pre-build spec pass caught a condition that would have invalidated an entire compute run after the fact.

## Alternatives considered

- **Status quo (uncapped, habit-routed).** Rejected: spend invisible, quotas shared blind across a dozen sessions, and no legitimate T0 meant over-review was indistinguishable from rigor.
- **Human approval per dispatch.** Rejected: the operator is already the bottleneck; the whole point is spending review budget without a human in the loop until a threshold trips.
- **Numeric risk scoring to pick tiers.** Rejected (was proposed by a reviewer): a scoring bureaucracy with no calibration data. Tier precedence — multiple triggers, highest tier wins, matched triggers recorded — buys the objectivity without the apparatus.
- **A distributed lock service for the ledger.** Rejected: this is one PC. Immediate-mode SQLite transactions with a concurrent race test (40 writers, exact admit/block counts) are sufficient and provable.
- **Cryptographically signed verdict receipts.** Rejected: the threat model is self-error and process drift, not adversaries. Receipts carry ledger row references and artifact hashes; signing them defends against an attacker nobody has.

## Consequences

- Review spend became a measured quantity with per-seat, per-tier reporting — extending the [fire-log audit doctrine](016-guards-are-audited-against-their-own-fire-logs.md) from guard behavior to review economics. Caps will be set from two weeks of data, not from guesses.
- The process was its own first casualty, by design: both reviewers rejected v1.0, the re-review rejected the repairs once more, and the two-cycle escalation armed against the law itself — full account in [PM-050](../postmortems/050-the-review-process-failed-its-own-review.md), including the day-one quoted-text false positives.
- New failure mode accepted knowingly: when the measurement window expires unconfigured, routine reviews brick until someone sets caps. That is the enforcement teeth for "task DB only is not enough," and it will eventually fire on a busy day.
- Named gap: dispatches that go through the subagent path are measured (log-only), not yet blockable. A single dispatch broker owning all reviewer calls is the v2 target; until then that path relies on the ledger's visibility rather than the guard's veto.
- Two older mechanisms (the ADR-013 loop and a two-stage critic checkpoint) are declared in-ladder as seats of the same family, pending an explicit fold-or-keep ruling — nothing was silently deleted.

## What we'd do differently

Too early to say honestly — the decision is days old and cap enforcement has never fired. The first quarterly review owns this section, with one question already queued: whether measure-mode data justified the caps it produced, or whether the caps inherited the measurement fortnight's workload shape.
