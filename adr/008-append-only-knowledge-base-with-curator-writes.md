# ADR-008: The knowledge base is append-only, and all writes route through a curator agent

**Status:** Active · **Date:** append-only from early; curator 2026-06; ack-narrowing 2026-07-17 · **Internal refs:** curator agent spec; the six-week false finding

## Context

The knowledge base is where research findings, corrections, and validated rules live — it is the system's long-term memory, and by policy its contents outrank the model's priors. Two failure classes threatened it. First, *destructive writes*: agents "cleaning up" by deleting or overwriting entries destroys the evidence trail (a `DELETE` in a knowledge store is a bug, not a feature). Second, *confabulated writes*: an agent seeding a plausible-sounding but false finding. One false entry about a model's context-window size sat in the KB for six weeks with high confidence, quietly feeding downstream session-management rules.

## Decision

Two rules, separately enforced:

1. **Append-only.** Nothing is deleted. Corrections and supersessions are new nodes linked to the old ones; the wrong entry stays visible as part of the record. Force-updating can refresh a stale entry but never removes one.
2. **Curator-mediated writes.** All KB writes route through a dedicated curator agent whose job is anti-confabulation: it runs a **contradiction scan** against existing validated entries before committing, checks provenance (does the claimed source actually exist?), and enforces schema. Writes from any other context are logged as policy violations to an audit trail.

**Revision (2026-07-17, the interesting part):** originally every curator write also required a human ack. That blanket ack was *narrowed* — the curator now writes genuinely new findings directly, and the human ack is reserved for supersessions, contradictions of validated entries, and forced writes. Reason: audit showed the blanket ack had caught nothing — the six-week false finding sailed through a human ack, and it was the curator's automated contradiction scan that finally flagged it. The scarce resource (operator attention) was being spent where it demonstrably didn't help. Supersession of one's own safeguards, with evidence, is what this ADR system is for.

## Alternatives considered

- **Editable KB with history.** Rejected: history you can rewrite gets rewritten; append-only makes the evidence trail structural instead of disciplinary.
- **Direct writes with post-hoc auditing.** Rejected: by the time an audit runs, downstream decisions have already consumed the false entry.
- **Human ack on everything, forever.** The original design — retired by evidence, as above.

## Consequences

- The KB grows monotonically; queries must prefer newest-superseding nodes, and stale-but-unsuperseded entries are a known hazard requiring periodic staleness audits.
- The curator is a deliberate bottleneck; batch research sessions queue behind it.
- The ack-narrowing decision established a precedent with teeth: **safeguards must show evidence they catch things, or they get narrowed.** Ritual checks that catch nothing aren't neutral — they consume the attention that working checks need.

## What we'd do differently

Instrument safeguards from day one (what did this check actually catch this month?). The blanket ack ran for weeks on assumed value before anyone measured it.
