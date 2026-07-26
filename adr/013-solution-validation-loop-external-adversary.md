# ADR-013: High-stakes proposals are adversarially attacked by an external model before the operator sees them

**Status:** Active · **Date:** 2026-07 · **Internal refs:** solution validation loop protocol

## Context

The operator is the review bottleneck for every proposal the agent makes, and the agent's failure mode is *plausibility*: a proposed solution that reads clean, cites real constraints, and is wrong in a way that only surfaces under adversarial pressure. Self-review doesn't supply that pressure — the same model that missed the flaw while proposing tends to miss it while reviewing, and the sycophancy dynamics of [ADR-005](005-epistemic-integrity-stack-anti-sycophancy.md) apply doubly to a model grading its own work.

## Decision

A **blocking gate**, operator-invoked by a trigger phrase on decisions worth the cost: before the operator reads the agent's proposed solution, the proposal is sent to an **external adversary model** (a different vendor's deep-research model) with instructions to attack it — find the failure modes, the violated assumptions, the cheaper alternative. The critique returns with the proposal; the agent must address the hits or concede them.

Two properties are non-negotiable:

- **Different model, different vendor.** The value is decorrelated blind spots; a second opinion from the same family is mostly the same opinion with different phrasing.
- **If the external adversary is unavailable, HALT.** The loop never degrades to self-review — a self-reviewed proposal wearing a "validated" stamp is worse than an unvalidated one, because the stamp buys unearned trust.

Scope honesty: the loop validates the *prose of a proposal*, not implemented behavior. It's a filter in front of operator attention, not a correctness proof — tests and verification still own the latter.

## Alternatives considered

- **Self-critique pass ("now argue against your own plan").** Cheap, and produces critique-shaped text; measured against the external adversary it reliably found fewer and shallower issues. Correlated errors are the whole problem.
- **Always-on validation of everything.** Rejected on cost and latency; each invocation costs real money and ~minutes. Reserved for the decision classes where a wrong plan is expensive (new production signals, architecture captures, statistical claims about to enter the KB).
- **A second human reviewer.** There isn't one; this is a one-operator system by design.

## Consequences

- Per-invocation cost and latency, paid only on triggered decisions.
- The adversary sees the proposal text, not the codebase — its critiques occasionally attack a misreading. The agent must triage hits honestly rather than either capitulating to all of them (sycophancy toward the critic) or dismissing them wholesale.
- Operator review time on gated decisions dropped in the useful way: proposals arrive pre-shelled, with known weak points labeled, instead of polished and untested.

## What we'd do differently

Log every loop verdict and what the operator ultimately decided, from the first invocation. That record — where the adversary caught real flaws vs. noise — is the calibration data for *which decision classes deserve the gate*, and early invocations went unlogged.
