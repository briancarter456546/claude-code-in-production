# The log we grade our guards with could not be counted correctly — and a recommendation had already shipped off the bad numbers

**Keywords:** audit log schema drift, timestamp field naming, timezone naive datetime, self-test contamination in production logs, guard block frequency analysis, telemetry hygiene, external review caught measurement error, absence of evidence

**Incident date:** 2026-09-05 · **Internal refs:** #2662 · **Status:** measurement tool repaired; the analysis built on the bad numbers is superseded in place with an amendments section and one claim withdrawn

---

## What broke

This system audits its own guards from a single append-only event log — roughly 95,000 lines — and kills the ones that turn out to be net-negative ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)). An audit ran, produced block-frequency numbers per guard, and shipped a recommendation off them.

The numbers were wrong three ways, and every error pushed in a direction that made a guard look *quieter* than it was.

**1. The log has two names for time.** Most hooks write their timestamp under one key, timezone-aware. A subset writes it under a different, shorter key, timezone-**naive**. A script reading only the first key scores every hook in the second group as **zero events in any time window** — the exact reading that gets a guard classified as dead. Corrected 30-day counts for three guards that had been reported as "gone quiet": **62 blocks, 29 blocks (12 of one cause, 17 of another), and 22 blocks.**

Re-checked a day later, the split is wider than the three guards originally named: **at least ten distinct hooks log only the short key**, and the top three of them account for 6,100, 6,098, and 3,288 events. Any window query that reads one field is wrong by thousands.

**2. The dispatcher's own self-tests land in the production log.** The guard dispatcher runs its regression cases through the same guard functions, which write the same audit events, with nothing marking them as synthetic. Consequences, measured: **all 8 blocks of one guard in the 30-day window were the self-test case** — exactly **one** real block of that guard exists in the entire log. For another guard, **24 of 26 blocks were three self-test cases repeated in 8-8-8 triplets**; 2 were real.

**3. A guard can fire under the dispatcher's generic event name instead of its own.** One guard appears **142 times** in-window that way, after having been declared "never logged an event." The generic dispatcher event is in fact the single most common line in the whole log (8,269 occurrences), so a name-based search that misses it misses the largest bucket.

Net effect: **friction is overstated on every guard the dispatcher self-tests, and understated on guards that use the other time key.** Both errors feed a policy that decides which guards to kill.

## How it was detected

An external review seat (file-reading, different vendor) was dispatched against the audit document under the tiered review law and returned **REJECT**. The parse-level defect the document described was real and survived review; the *measurement* that followed it did not, and the treatment recommended on top of the measurement was backwards.

Worth stating plainly: the audit's author had the log, wrote the query, and read the output. The error was invisible from inside because **a missing field returns nothing, not an error** — a query for events that were logged under a different key returns an empty result that looks exactly like a quiet guard.

## Root cause

**Schema drift in an append-only log with no writer contract.** Guards were added over months by different sessions; two conventions for the timestamp key both persisted because nothing ever validated a written line. Append-only storage hides this especially well — old lines are never rewritten, so the drift accumulates as strata.

**No provenance field for synthetic events.** A self-test that exercises real code paths through real logging is otherwise good practice; it becomes a data-integrity problem the moment the log is used as evidence. There was no flag to filter on, and no way to reconstruct one after the fact except by matching the literal self-test payloads.

**And the interpretive error underneath both:** *absence in a query was read as absence in the world.* "This guard has no events" is a claim about the query, and needs a positive control — search the guard's name across every line, in every field, before concluding silence.

## Blast radius

One shipped analysis with every block-count conclusion invalidated, and one claim — that the guard layer's friction "pushes sessions toward evasion" — **withdrawn outright**, since it rested on inflated block counts for guards whose blocks were mostly the dispatcher testing itself.

Nothing was killed on the bad numbers, which is luck of timing rather than process: the recommendation was written and reviewed before it was executed. Had it executed, the guards most likely to be retired would have been the ones whose real activity the query could not see.

Wider: any prior reasoning in this repo that leans on block frequency inherits the caveat. That is why this file exists.

## The fix

- **The measurement tool normalizes both time keys** (and localizes the naive one) before any windowing, and **searches guard names across all fields and the generic dispatcher event**, not just the guard's own event name.
- **Absence now requires a positive control.** Before any "this guard never fired" claim, the tool greps the raw log for the guard's name and reports the raw hit count alongside the parsed count. A mismatch is a parser bug, not a finding.
- **Self-test contamination is documented at the point of use** — the amendments section of the audit names the affected guards and their real counts — and tagging synthetic events at the writer is filed as the durable fix.
- **The rejected analysis was not deleted or quietly rewritten.** It carries a warning banner at the top, an amendments section at the bottom, and its superseded numbers in place. A future session that finds the document finds the correction attached to it.

## Has the guard fired since?

There is no new guard here — the artifact is a repaired measurement tool, and its evidence is that its corrected counts reproduce: the three "quiet" guards reappear with real block counts, and the field split reproduced independently a day later on a log that had grown by about 2,700 lines. The durable fix (tagging synthetic events at write time) has **not** shipped; until it does, every analysis of this log needs the self-test filter applied by hand, which is a fragile arrangement and is recorded as such.

## Lessons for agent-driven development

1. **A missing field returns silence, not an error — and silence reads as evidence.** Any query whose negative result would trigger an action needs a positive control against the raw data first.
2. **Append-only logs accumulate schema strata.** Without a written contract validated at the writer, two conventions will coexist for months, and every window query will be wrong in a way no exception ever announces.
3. **Never let self-tests write to the evidence store unlabeled.** Exercising the real path is the right test design; the fix is a provenance flag at the writer, not a weaker test.
4. **When a policy kills things based on a metric, the metric needs its own review pass.** The audit doctrine here retires net-negative guards; the counting code behind it deserved the same adversarial scrutiny as the guards, and got it only because a reviewer was pointed at the analysis.
5. **Supersede in place, with the old numbers visible.** A rewritten document teaches nothing; a document carrying its own rejection teaches the next reader what kind of error to look for.

Related: [PM-015](015-eight-thousand-fires-zero-true-blocks.md) and [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md) are the audit doctrine that depends on these counts; [PM-054](054-nothing-checked-whether-the-controls-were-still-alive.md) is the companion sweep that asked whether controls bite at all; [PM-048](048-the-agent-audited-itself-and-got-the-headline-numbers-wrong.md) is the same shape at session scale — a self-audit whose headline numbers only a second reader caught; [PM-016](016-the-classifier-that-never-ran.md) is a guard that really had gone silent, which is why the false positives here matter.
