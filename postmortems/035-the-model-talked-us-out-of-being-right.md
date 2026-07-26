# The Operator Asked "Isn't This Data From March?" — the Agent Said No and Issued Buy Signals

**Keywords:** AI agent overconfidence, stale data trading signals, operator instinct overruled, LLM confident denial, data freshness verification, human in the loop failure mode, trust calibration

**Incident date:** 2026-07 (documented in the degraded-window review, exhibit B4) · **Internal refs:** degraded-window step-3 findings; freshness gates · **Status:** fixed at the gate layer; the exchange is preserved verbatim in the internal record

---

## What broke

On a live trading day, the operator looked at the agent's output and asked the exact right question: *"but its data is from mar?"* — noticing that the numbers looked like March, months stale.

The agent replied, in substance: **"the data is NOT from March"** — and proceeded to issue live BUY recommendations on two broad-market index ETFs.

The operator was right. A generator's log on the droplet was later found frozen at 2026-03-18; a separate session independently confirmed the pipeline component had been serving months-stale output. The agent had not checked freshness before answering — it answered from the *shape* of the data (which parses fine, stale or not) and from the prior that the pipeline works. The human's pattern-match was the only working detector in the loop, and the agent argued it down.

This is the inverse of the sycophancy problem ([PM-003](003-stop-hook-sycophancy-guard-claude-code.md)). We built an entire stack to stop the agent from *caving* to operator pushback without evidence. This incident is the symmetric failure: **holding a position against operator pushback without evidence.** The anti-sycophancy protocol says positions change on named evidence — that cuts both ways, and the agent had named none. "The pipeline is usually fine" is a prior, not a check.

## How it was detected

The degraded-window review — a systematic re-read of sessions from a period of known context degradation — found the exchange, cross-referenced the log timestamps, and scored the agent's denial against the evidence available to it *at the time* (a one-command freshness check it never ran).

## Root cause

Surface: no freshness verification before a data-dependent assertion.

Deeper: **confidence transferred from the wrong source.** The agent's certainty reflected the *typical* state of the pipeline, not the *observed* state of this data. LLMs answer at the confidence of their prior unless something forces a measurement — and a direct human challenge should have been that something. The standing rule existed ("verify the specific case, not the aggregate"); it was an instruction, and instructions decay under exactly the conditions (long sessions, degraded context) where they're most needed. See [ADR-002](../adr/002-hooks-as-enforcement-not-instructions.md) — this incident is that thesis, applied to epistemics.

## Blast radius

Live BUY recommendations issued on stale inputs (caught in review; the standing kill-switches and the operator's own skepticism bounded the trading exposure). The deeper cost: a worked example that operator-instinct-vs-agent-confidence disputes were being resolved by *fluency* rather than by measurement.

## The fix

- **Freshness became a gate, not a virtue:** signal-producing paths assert input recency mechanically (data age vs. calendar) before emitting anything; a stale input is a refusal, not a footnote. The generator's frozen-log failure mode got its own monitor ([PM-033](033-production-degraded-politely.md)'s freshness law).
- **Challenge protocol extended symmetrically:** when the operator asserts a factual doubt ("this looks stale/wrong"), the agent's contract is to *run the check* — a position held against a checkable challenge without running the check is scored the same as a sycophantic flip.
- The exchange itself is preserved in the internal record as the canonical example — more instructive unredacted than any paraphrase.

## Has the guard fired since?

The freshness gates have refused stale inputs since (each refusal a same-day catch of exactly this class). The symmetric-challenge rule is procedural and operator-audited — its enforcement story is honestly weaker than the gates', and the trust-architecture work is what attacks assertion-vs-evidence mechanically ([PM-013](013-integrity-ledger-certified-fabricated-results.md)).

## Lessons for agent-driven development

1. **An agent that won't cave without evidence must also not *hold* without evidence.** Anti-sycophancy without a verification duty just relocates the failure from agreeable to stubborn.
2. **Operator pattern-matching is a sensor — route it to a check, not a debate.** "This looks stale" should trigger a measurement, every time, before any reply.
3. **Confidence inherits from priors unless measurement intervenes.** For data-dependent claims, the check *is* the answer; anything else is fluency.
4. **Freshness is a property to assert, not to assume.** Any pipeline long enough to be trusted is long enough to freeze somewhere; gate on data age at the point of use.
