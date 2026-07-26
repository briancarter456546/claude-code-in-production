# ADR-005: Anti-sycophancy is a layered stack, not an instruction

**Status:** Active · **Date:** 2026-05 onward, hardened repeatedly · **Internal refs:** sycophancy Stop hook; incident record in [PM-003](../postmortems/003-stop-hook-sycophancy-guard-claude-code.md)

## Context

The agent's opinions feed real decisions — infrastructure changes and trades with money behind them. A model that flips position when the operator pushes back corrupts every decision built on its analysis, and it does so *pleasantly*, which makes the corruption hard to notice. [PM-003](../postmortems/003-stop-hook-sycophancy-guard-claude-code.md) documents the pattern: confident analysis → operator skepticism → instant reversal with "You're right" — no new evidence anywhere in the exchange. One instruction ("don't be sycophantic") measurably did not fix it.

## Decision

Five layers, each attacking a different link in the appeasement chain:

1. **Input reframing (generation-time).** Before responding to a stated belief ("I think X", "this looks wrong"), the agent internally rewrites it as a neutral question ("Is X true?"). Based on published safety-institute findings that ask-don't-tell reframing reduces sycophancy more than explicit anti-sycophancy instructions do.
2. **Position-change protocol.** Reversing a position held earlier in the conversation requires naming the *specific new fact or logical error* that invalidates the old position. "The operator seems skeptical" is not evidence. Auditable in real time: the operator can call "what new evidence?" on any flip.
3. **Banned-phrase Stop hook.** A Stop hook blocks responses opening with or pivoting on appeasement language ("You're right", "Great point", "That's fair", agreement-then-pivot constructions). The response is regenerated until it either defends the position or names the evidence for changing it.
4. **Explicit confidence tiers.** Substantive claims carry HIGH / MEDIUM / LOW confidence with a one-line justification; presenting LOW as HIGH to match expected certainty is a violation.
5. **Approval inversion (framing).** The instructions state the incentive plainly: operator approval is maximized by being right at the six-month mark, not by agreeing in the next five seconds.

## Alternatives considered

- **A single "be honest" instruction.** Tried; decayed (see [ADR-002](002-hooks-as-enforcement-not-instructions.md)).
- **Only the Stop hook.** Blocks the phrasing but not the flip — the model can capitulate in neutral language. The named-evidence protocol targets the flip itself; the hook targets the tell.
- **Third-party review of every analysis.** Reserved for high-stakes cases (see [ADR-013](013-solution-validation-loop-external-adversary.md)); too slow and costly as a default.

## Consequences

- False positives: legitimately quoting the operator, or genuine agreement, can trip the phrase guard. Handled by a logged bypass variable.
- Occasional stilted phrasing where natural agreement is warranted — the cost of banning the cheap version of it.
- Held-position-under-pressure now reads as a feature, which required operator adjustment too: the system is *designed* to argue back until given evidence.

## What we'd do differently

Build layer 2 (named evidence) first, not layer 3 (banned phrases). We initially over-invested in the surface tell and under-invested in the underlying flip; the protocol turned out to be the load-bearing layer.
