# Our Anti-Fabrication System Certified Fabricated Numbers While All Its Tests Passed

**Keywords:** LLM fabricated results, results integrity verification, AI agent test fabrication, partial validation bypass, backtest result verification, smoke tests false confidence, adversarial review AI

**Incident date:** 2026-07-25 · **Internal refs:** trust-architecture initiative P1; execbreak findings N1/F1 · **Status:** fix in progress at time of writing (round 2+); bypass reproduced and regression-tested

---

## What broke

After a season of result-integrity incidents (see [PM-036](036-compaction-ate-the-doubt.md), [PM-038](038-the-validation-that-never-happened.md)), we built a **results ledger**: before a research finding is recorded, the ledger independently recomputes what it can from the underlying artifacts and blocks recording when the claimed metrics don't reproduce. An anti-fabrication gate for agent-produced numbers.

The execbreak (adversarial re-test) found the hole: the recompute step **skipped any metric it couldn't derive from available artifacts, and its fallback check only fired when *no* metrics could be derived.** So a submission with one honest, derivable metric (a trade count) and several fabricated, non-derivable ones (growth and drawdown figures) passed: the honest metric verified, the fabricated ones were "skipped, not failed," and the fallback never triggered.

Reproduced live: a synthetic finding claiming **0.99 CAGR (99% annual growth), −0.05 MaxDD, Calmar 19.8** — numbers no real strategy produces — reached `recorded` status through the integrity gate. The ledger's own smoke suite was green — 25 of 25 — the entire time.

## How it was detected

Not by the builder, and not by the tests. The fixing session had declared the prior round's holes closed ("the sidecar bypass is genuinely dead") with the smoke suite passing. A **separate session with fresh context** was pointed at the same code with one instruction: break it. It found the partial-observation bypass within its first pass. The finder's advantage wasn't skill — it was distance: no investment in the fix being right, no context inherited from writing it.

## Root cause

Surface: a fail-open default in the per-metric loop — "can't check" was treated as "no objection."

Deeper: **"fail-closed" had been implemented as "reject only if NOTHING verifies," when the correct semantic is "reject if ANY declared item fails to verify."** The two are identical in single-metric tests — which is exactly what the smoke suite contained. The gap only exists for mixed submissions, and no test submitted a mixed one.

Deepest: the smoke suite was written by the same process that wrote the gate, so it encoded the same blind spot. Tests written by the author verify the author's model of the system, and the author's model was the bug.

## Blast radius

Caught pre-damage: the first real ledger entry was still blocked pending fixes, so no fabricated finding entered the permanent record through this hole. Cost: the fix round-trip, plus the sharpest lesson in the whole record about what green test suites are worth.

## The fix

- The per-metric semantics inverted: any *declared* metric that cannot be re-derived is a **failure**, not a skip. Verification coverage must be total over the claim, not over the checkable subset.
- Mixed submissions (honest + unverifiable metrics) added to the regression suite — the exact shape that slipped through.
- Process fix, arguably the bigger one: **adversarial re-test by a fresh-context session is now a standing step** for integrity-critical fixes. The builder's own green suite is treated as necessary, never sufficient.

## Has the guard fired since?

The regression now catches the reproduced bypass (that's what regression means). The honest current status: the fix cycle was still underway at time of writing, in round 2+ — this postmortem documents an active repair, and the repo's policy is to say so rather than backdate a tidy ending.

## Lessons for agent-driven development

1. **"Reject unless everything passes" and "reject if anything fails" differ exactly where fabrication lives** — in mixed claims. Specify fail-closed at the per-item level or you haven't specified it.
2. **One honest number can launder several fabricated ones** if verification skips what it can't reach. Coverage must be over the *claim*, not the *checkable*.
3. **A green suite written by the gate's author certifies the author's assumptions, including the wrong ones.** Adversarial fresh-context review is the cheapest decorrelation available.
4. **Integrity systems deserve their own postmortems most of all.** A broken guard is worse than no guard: it converts "unverified" into "certified."
