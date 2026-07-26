# ADR-011: Creating a new tool or hook requires answering seven design questions, enforced by an ack gate

**Status:** Active · **Date:** 2026-07 · **Internal refs:** designer-ack guard v2.x; design-doc spec for high-impact changes

## Context

There are two modes of agent work, and they have different blast radii. *Caller* work invokes existing tools; a mistake costs one session. *Designer* work creates new tools, hooks, CLIs, or durable document structures; a mistake becomes a contract that **every future session inherits**. Agents are eager designers — a new script is the fastest way to look productive — and careless design compounds: a tool with a nonstandard interface, no enforcement, and no canonical home is a permanent tax on every caller that follows. The repo accumulated exactly that sediment.

## Decision

Before designing anything durable, the agent must answer **seven questions**: (1) which lane owns it; (2) what is its source of truth / canonical path; (3) does it match a standard interface pattern, and if not, why — documented in the artifact itself; (4) what *enforcement* ships with it — a nonstandard interface without a guard is an **incomplete design**; (5) how are its destructive actions gated; (6) which downstream artifacts (status docs, topology, task DB, instructions) update in the same change; (7) how is it verified before commit.

Enforcement: a **designer-ack guard** blocks committing new untracked scripts or new hooks until an ack marker exists — produced by a CLI that forces the checklist through the agent's hands. High-impact designs (new core subsystem, new strategy, new dashboard framework) additionally require a full design doc under a separate, heavier spec. Bypass: the standard logged-reason variable.

## Alternatives considered

- **Design review after the fact.** Rejected: by review time the artifact has callers; retrofitting an interface breaks them, so bad designs get grandfathered — which is precisely the compounding this gate exists to stop.
- **Questions as instructions only.** The pre-hook version. Answers were skipped or vibed exactly as [ADR-002](002-hooks-as-enforcement-not-instructions.md) predicts.
- **All designs require full design docs.** Rejected: the heavyweight process applied uniformly would be evaded uniformly. Two tiers — a 7-question everyday filter, a document-level gate for high-impact — match the cost to the blast radius.

## Consequences

- Real friction on the most common agent reflex ("I'll just write a quick script"). Intended: the friction *is* the design pause.
- Question 4 changed system culture most: guards now ship *with* the thing they guard, in the same change, instead of being deferred to a someday-task.
- The ack marker is checkable but gameable — an agent can answer shallowly. The gate guarantees the questions are confronted, not that they're answered well; the operator still audits designs, just fewer and better-framed ones.

## What we'd do differently

Ship the two tiers together from the start. The heavyweight spec existed first and was so rarely triggered that everyday design went ungated for months — the everyday filter is where the volume is.
