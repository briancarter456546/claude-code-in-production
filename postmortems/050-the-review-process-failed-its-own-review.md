# We made external review mandatory for AI-agent work — the review process failed its own review, twice

**Keywords:** adversarial review, LLM code review, review governance, tiered review process, review budget caps, fail-closed expiry, quota ledger, SQLite concurrency, check-then-act race, quoted-text false positive, self-application, dogfooding governance

**Incident date:** 2026-08-28/29 · **Internal refs:** #2527, #2528 · **Status:** shipped and governing in measure mode; cap enforcement begins 2026-09-11 and is untested as of this writing

---

## What broke

Nothing was down. The "incident" is that the system's new review law — the document defining how external adversarial reviews are tiered, routed, and budget-capped — was itself put through the review ladder it defines, on the day it shipped. Both external reviewers **rejected it**: 16 numbered modifications from a file-reading code reviewer (different model vendor), 10 from a prose-only deep-research reviewer (third vendor, $0.65 for the pass). After same-day repairs, the mandatory re-review of the repaired build produced a **second rejection** (4 items) from the file-reading seat.

Two reject-and-repair cycles is exactly the threshold at which the new law's own escalation rule arms: any further external pass on that artifact now requires the operator's explicit ack. The first artifact the escalation rule ever armed against was the law that created it.

Separately, the new dispatch-counting guard shipped with a day-one defect this repo had already published a pattern about: of its first five blocks, **four were false positives** — git commit messages and a ledger CLI call that *mentioned* reviewer names and a retired review command were blocked as if they were review dispatches. Mentions judged as uses ([quoted-prose stripping](../patterns/quoted-prose-stripping.md)). Having the pattern documented did not prevent shipping the bug.

## How it was detected

By the process itself, on purpose. The law classifies governance artifacts as review-requiring, so the session that wrote it dispatched two external reviewers against the full file set the same afternoon — files, not summaries, per the law's own first invariant. The re-review of the repairs was likewise required by the ladder ("repair of a rejected build" is an explicit trigger for a two-family review). No part of the detection path was improvised.

## Root cause

The defects the reviewers caught share one mechanism: **rules written from the happy path, with polarity and accounting errors that only show under adversarial or concurrent load.**

The four load-bearing catches:

1. **Fail-closed was aimed at the wrong tier.** The design said: when the 14-day measurement window expires with no caps set, block all review dispatches until caps are written from measured data. Correct for routine reviews; catastrophic for the emergency tier — the highest-stakes reviews (operator rulings, deploy gates) would be the first thing the safety mechanism bricked. Repair: the ruling tier is exempt from caps *and* from the expiry block, always logged, never blocked. Fail-closed now applies only to the routine tiers.
2. **Partial caps silently un-capped everything else.** Enforce mode originally activated per-seat: populating one seat's weekly cap left every other seat uncapped, silently. Repair: enforce mode requires *all* governed seats to carry valid non-negative integer caps; partial or wrong-typed configs stay fail-closed.
3. **Cap admission was check-then-act.** The guard checked remaining capacity, then appended a ledger row — so two concurrent sessions could both pass the check on the last slot. Repair: a `reserve` operation counts capacity and inserts the dispatch row inside one immediate-mode SQLite transaction. Race test: 40 concurrent reservations against a cap of 20 with 4 slots already consumed → exactly 16 admitted, 24 blocked, 0 anomalies.
4. **The escalation rule counted labels, not mechanisms.** "Two REJECTs escalate to the operator" creates an incentive to relabel a rejection as "adopt-with-modifications." Repair: a cycle is defined as *any review pass that produced blocking findings followed by a repaired revision* — verdict label irrelevant, so relabeling buys nothing.

The deeper cause of the false-positive cluster: a content-matching guard was pointed at a stream (shell commands) where the guarded strings legitimately appear as data — in commit messages describing the work, and in the arguments of the very ledger CLI the process introduced. The guard's second live false positive was blocking the process's own bookkeeping.

## Blast radius

Near zero in production — which is the point of reviewing a control system before it enforces anything. Costs actually paid: one working day of repair across two rounds, three external review dispatches, under a dollar of metered spend plus quota draw. The four false-positive blocks each cost one retry with a reworded command. The counterfactual blast radius is the interesting number: defect 1 would have blocked the highest-stakes reviews on day 15; defect 3 would have made the caps leak exactly when review pressure was highest, since concurrent dispatch is the busy-week case.

## The fix

All repairs above, shipped as two same-day increments with self-tests (15/15) and the concurrency race test as evidence. Beyond the code: the law text now records every adopted, declined, and deferred reviewer item inline — including what was declined and why (a distributed lock server for a one-PC system; numeric risk scores with no data to calibrate them; cryptographic receipt signing when the threat model is self-error, not adversaries). The declined list is enforcement against silent scope creep: a future session proposing "add risk scores" finds the prior decline and its reason in the governing document.

## Has the guard fired since?

28 audit events in the first three days of measure mode: 18 review dispatches counted, 1 ruling-tier exemption honored (logged, not blocked), 4 subagent-mediated dispatches measured through a log-only matcher (a named gap — that path is counted, not yet blockable), and the 5 blocks described above. After the same-day quoted-text repair, false-positive blocks in the following two days: zero. One tier-0 classification override was recorded on the close-time verdict gate with a written justification — the ladder's "no review needed" path being used explicitly rather than silently.

What has *not* fired yet: cap enforcement. Measure mode runs to 2026-09-11; until caps are set from the measured data and the first over-budget dispatch is actually blocked, the enforcement half of this system is a hypothesis.

## Lessons for agent-driven development

1. **A review process that has never been reviewed is an untested guard.** Running the law through its own ladder surfaced 30 numbered defects before it enforced anything. If your process can't survive its own tiers, it isn't ready to gate anyone else's work.
2. **Fail-closed is a per-tier decision, not a philosophy.** Applied uniformly, "block when unconfigured" turns the safety system into the thing that bricks the highest-stakes path. Scope fail-closed to routine work; exempt-and-log the emergency tier.
3. **Escalation rules must count mechanisms, not labels.** Any threshold keyed to a verdict word will be evaded by renaming the verdict. Key it to the observable: blocking findings followed by a repair.
4. **Quota admission under concurrency is a reservation, not a check.** Check-then-log leaks exactly at the cap boundary, under exactly the load the cap exists for. Count and insert in one transaction, then prove it with a concurrent race test.
5. **Published patterns don't self-apply.** The quoted-text false-positive class was already documented in this repo when the new guard shipped with it. A pattern catalog is retrieval material, not immunity — new guards need the catalog run against them as a checklist.

Related: [ADR-018](../adr/018-tiered-adversarial-review-with-budget-caps.md) records the decision this incident stress-tested. [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md) and [ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md) are the audit doctrine the ledger extends to review spend. [PM-014](014-the-escape-hatches-that-never-existed.md) is why the bypass env var here is audit-logged with a mandatory written reason.
