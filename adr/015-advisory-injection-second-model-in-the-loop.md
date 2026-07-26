# ADR-015: A second model's advisory opinions are injected into the loop — as opinions, never as facts

**Status:** Active · **Date:** 2026-07 · **Internal refs:** advisory-mode Stop hook + scorer

## Context

[ADR-013](013-solution-validation-loop-external-adversary.md) puts an external adversary in front of *explicitly gated* decisions. But most drift doesn't announce itself as a decision: a session gradually commits to an approach that contradicts a recorded finding, or misses a risk that's obvious from outside the tunnel. The operator can't watch twelve windows for drift, and the agent inside the tunnel is the wrong party to detect it. Wanted: a cheap, continuous outside glance — without handing a second model the steering wheel.

## Decision

An opt-in per-session **advisory mode**:

- A **Stop hook scores each turn** (signal heuristics: decision density, contradiction markers, risk keywords). Below threshold, nothing happens — most turns fire nothing.
- Above threshold, the hook calls an external advisor model that sees **the transcript and the knowledge base — but not tool outputs or the file system.** The asymmetry is disclosed to the agent rather than hidden.
- The advisory is injected into the next turn inside a clearly labeled block, and the agent's contract has exactly three legal responses: **acknowledge in one sentence**, **factor it in**, or **override with stated reasoning**. Silent dismissal is a violation; so is treating the advisory as an order.
- Hard boundaries: the advisor is not the decider (the operator is), advisories never enter the knowledge base (they're opinions; KB writes stay curator-mediated per [ADR-008](008-append-only-knowledge-base-with-curator-writes.md)), and the agent must not echo the advisor's prior advice back at it (feedback loops between models amplify, not correct).

## Alternatives considered

- **Advisor on every turn.** Rejected on cost and, worse, attention: a constant second voice becomes noise the agent learns to ritually acknowledge — the scoring threshold *is* the design.
- **Advisor with full tool/file visibility.** Rejected for cost and coupling; the partial view is also a feature — the advisor critiques the *reasoning as narrated*, which is exactly where drift lives.
- **Autonomous advisor that can act.** Rejected outright. Two models with write access is a coordination problem nobody here wants; one writes, one kibitzes.

## Consequences

- Real per-fire cost; the threshold needs tuning, and a per-session kill switch exists for when the advisor is wrong-shaped for the work.
- The advisor's blindness to tool outputs means some advisories attack things the agent can see are fine — the override-with-reasoning path handles this, and the overrides get logged for threshold tuning.
- Mild but real: forced acknowledgment keeps the agent honest about *having considered* the outside view, which was the actual goal — the advisory's content is sometimes less valuable than the interruption of tunnel momentum.

## What we'd do differently

Define the advisory-quality feedback loop (which advisories led to changed action?) before turning it on, not after. Without it, threshold tuning is vibes about vibes.
