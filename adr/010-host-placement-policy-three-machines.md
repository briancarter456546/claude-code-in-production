# ADR-010: New automation must pass a host-placement policy — "build here, move later" is forbidden

**Status:** Active · **Date:** 2026-06 (reconstructed) · **Internal refs:** host-placement gate hooks; topology policy file

## Context

The system spans three machines with distinct roles: a Windows dev PC (authoring, medium workloads), an always-on cloud droplet (production crons, dashboards, source-of-truth data), and a Mac compute worker (heavy long-running jobs, ~3.6× the PC's throughput, dispatch-only). An agent asked to build a scheduled job builds it *where it's standing* — the current machine — because that's the path of least resistance. The result was automation scattered by accident of which machine hosted the authoring session: crons on a PC that sleeps, heavy jobs on the always-on box sized for serving, schedulers nobody remembered existed. Every misplacement eventually demands a migration that costs more than placing it right would have.

## Decision

Host placement is a **policy decision, checked at creation time**:

- Machine roles and placement rules live in a versioned **topology policy file** — which host runs scheduled jobs, which runs heavy compute, what is dispatch-only.
- Any new cron / service / long-running process triggers a required step: list the placement options, recommend one per the policy file, and get an explicit operator ack before scaffolding.
- **"Build here, move later" is forbidden by name.** It is the specific rationalization the gate exists to block — the migration never gets cheaper, it just gets scheduled never.
- A **PreToolUse gate** enforces the protocol on scaffolding actions; bypass takes the standard logged-reason variable ([ADR-002](002-hooks-as-enforcement-not-instructions.md)).
- Every scheduled job, regardless of host, is registered in a single tracked inventory — the anti-scatter measure that makes audits possible at all.

## Alternatives considered

- **Convention plus code review.** Decays; also the operator reviews outcomes, not placement decisions buried inside scaffolding.
- **One machine for everything.** Rejected: the workloads genuinely differ (always-on serving vs. burst compute vs. interactive authoring), and consolidating would just move the placement problem inside one box's resource contention.
- **Full orchestration layer (containers, scheduler).** Overweight for a three-machine, one-operator system; the policy file plus a gate delivers most of the value at ~2% of the complexity.

## Consequences

- Scaffolding friction: an ack round-trip before any new automation exists. Deliberate — this is a decision worth interrupting for, per the design-gate philosophy in [ADR-011](011-designer-ack-and-seven-question-design-gate.md).
- The policy file must track reality; a stale policy misroutes with authority. It gets audited against the live job inventory.
- Placement disputes now resolve by pointing at a file instead of re-arguing topology from scratch each time.

## What we'd do differently

Register the *existing* jobs into the inventory before enforcing placement on new ones. We gated the front door while the house already had undocumented occupants, and the reconciliation audit was tedious.
