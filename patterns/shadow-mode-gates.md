# Pattern: Shadow Mode for New Gates — and the Three Ways It Goes Permanent

**Keywords:** shadow mode hook, log only enforcement, would-block logging, guard promotion criteria, false positive rate before blocking, dry run gate, measure mode, enforcement expiry date
**Problem class:** you want to ship a new gate without breaking the fleet on day one, so you ship it in log-only mode first.

## Problem

A gate that blocks legitimate work on its first day does more damage than the thing it guards against: every false block teaches the fleet that bypassing is normal, and alarm fatigue degrades trust in every *other* gate ([PM-021](../postmortems/021-alarm-fatigue-by-the-numbers.md)). So the sensible move is to ship the gate deciding-but-not-blocking, watch its would-blocks for a week, and promote it once you can see what it would have done.

That is correct and we do it. It has also failed three separate times in our stack, each time for a different reason, and the failures are more instructive than the pattern.

## Mechanism

Three modes, resolved per invocation from flag files on disk — never from an environment variable, which does not reach the hook process ([PM-014](../postmortems/014-the-escape-hatches-that-never-existed.md)):

| mode | selector | behavior |
|---|---|---|
| shadow (default) | neither flag present | decide, log `<gate>.would_block`, **exit 0** |
| enforce | `enforce.flag` present | decide, log, **exit 2** with a message |
| off | `disabled.flag` present | log `disabled`, exit 0 |

Binds to `PreToolUse` (exit 2 = refuse) or `Stop` (block the turn). Every would-block row carries: the reason code, the target, the session id, and enough context to *judge* the row later — not just to count it.

```python
mode = "enforce" if ENFORCE_FLAG.exists() else "off" if DISABLED_FLAG.exists() else "shadow"
verdict = decide(ctx)                      # same code path in every mode
if verdict.blocks:
    audit(f"{NAME}.would_block" if mode == "shadow" else f"{NAME}.block",
          reason=verdict.reason, target=verdict.target, session=sid,
          shadow=(mode == "shadow"))
    if mode == "enforce":
        sys.stderr.write(verdict.message); sys.exit(2)
sys.exit(0)
```

**Two requirements that are not optional, learned the hard way:**

1. **The mode carries an expiry, in the gate's own configuration**, and the gate says so on every fire after it:
   ```python
   EXPIRY = date(2026, 10, 5)                 # written in the flag file itself
   if mode == "shadow" and date.today() > EXPIRY:
       audit(f"{NAME}.shadow_expired", days_over=(date.today() - EXPIRY).days)
       # loudly: this gate is now an allow-everything hook with a decision tree
   ```
2. **Count the pass condition, not just the fires.** A gate whose satisfied state has occurred zero times is broken regardless of its would-block volume.

## The three ways it goes permanent

**1. The promotion criterion is unanswerable from shadow data.** Ours is stated as *"may block once its false-positive rate is under 20–30%, measured in shadow mode."* Shadow logs give you a **fire count**. A false-positive rate requires a human to read rows and judge each one. If that reading has no owner and no date, it never happens: one of our gates reached 1,094 would-blocks over 26 days with **zero rows ever judged** ([PM-066](../postmortems/066-the-shadow-gate-that-cannot-graduate.md)).

**2. Shadow mode hides a broken pass condition.** That same gate requires two per-session receipts, and one of them **has never been written once** — it was built on an undocumented tool-response shape that has never fired. In enforce mode that is a fleet-wide outage inside an hour and gets fixed the same day. In shadow mode it is a counter going up. *The mode that protects the fleet from a wrong gate also protects a wrong gate from the fleet.*

**3. Checks get shadowed as a group because they share a remedy.** Four checks on our turn-report guard were shadowed together because they all cost the same thing when they blocked — a reprinted report. Three were cosmetic. The fourth detected reports that carried no content, and it was suppressed **211 times in seven days, 140 of those on reports containing exactly one section**, while the human it protects complained about that precise defect twice, by hand ([PM-065](../postmortems/065-the-check-we-shadowed-was-the-one-that-mattered.md)).

Corollary to 3: **when the block's remedy is worse than the violation, fix the remedy.** We did — the guard now instructs an *append* instead of a full re-emit — and the case for shadowing disappeared with it.

## Failure modes of this pattern itself

- **A count is not a review, and a digest that carries the count hides that.** We *did* route would-block totals into a weekly emailed digest — it printed this gate's counts as 225, 123, 366, 338 in four consecutive reports, and another gate's as 6 then 280 — and both experiments still ran to their ends unexamined. A rising number reads as ambient. What ends a bad experiment is a **row**: "140 of these were reports containing only a goal check." Route examples and the pass-condition count, not volume.
- **Registered ≠ enforcing.** A shadowed gate appears in the hook configuration exactly like a live one. Two of our audits found controls that were wired and doing nothing measurable ([PM-054](../postmortems/054-nothing-checked-whether-the-controls-were-still-alive.md)).
- **The end of the experiment needs to be in version control.** Ours turned shadowing *on* in a commit; turning it *off* was moving the tracked flag file aside, and that deletion is still uncommitted working-tree state. The history says it started and does not yet say it stopped.
- **Shadow data can be about the wrong thing.** 26 days of rows that all fail on a never-recorded receipt say nothing about the classification the shadow run was meant to validate. Check that your would-blocks vary before you trust them as evidence.
- **Graduating is not the finish line — the thresholds can be neutralized afterward.** Our review-budget guard did this correctly: it opened a 14-day measure window and was promoted to enforce **from its own ledger data** (caps set at the observed peak week plus ~50% headroom) on day 3 — eleven days *ahead of* the window's expiry, by operator ruling rather than by the deadline. Two days after that, every cap was raised to a flat 100 by operator ruling — "the caps are hurting not helping" — superseding the data-derived numbers ([ADR-018](../adr/018-tiered-adversarial-review-with-budget-caps.md)). The gate enforces. It rarely binds. Track the threshold's provenance as carefully as the mode.

- **A mode carried by an ordinary working-tree file crosses over gradually, and the ledger will not tell you when.** One of our experiments went 142 blocks / 101 suppressions before its flag file was committed and 18 / 181 after, with two days in the middle at zero suppression — while every summary of it, including the flag's own text, described a switch. Resolve the mode from one place all sessions agree on, make each fire record the mode it ran in, and treat an ambiguous mode as a reason to refuse rather than to guess.

## Where we run it

Three gates have used it:

| gate | outcome |
|---|---|
| review-budget caps | graduated to enforce in 3 days, from its own measure data — then its thresholds were raised to a flat 100 by ruling two days later |
| explore-plan receipts | **shadowed 26 days against an intended 3–4 day window**, 1,094 rows none of them judged, pass condition never once satisfiable |
| end-of-turn report shape | retired **10 days early** — not by review, but because the human noticed the defect the shadowed check had been counting all along |

Scoreboard: **1 of 3 exited on its own evidence — and none of the three was ended by the scheduled review that was supposed to end it** (that one graduated eleven days early on a ruling, not on its deadline). Shadow mode is still the right default for a new gate. Ship it with an expiry the gate itself enforces, a mode all sessions resolve identically, per-check granularity, and a scheduled reading of rows — not counts — or it is just a decision tree that exits 0.
