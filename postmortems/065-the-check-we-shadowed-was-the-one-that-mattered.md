# The Check We Put in Shadow Mode Was Counting the Exact Complaint We Got by Hand

**Keywords:** shadow mode guardrail, log-only enforcement mode, would-block logging, AI agent output contract, Stop hook enforcement, false positive rate before blocking, agent report quality, guard promotion criteria, enforcement telemetry nobody reads

**Incident date:** shadow window 2026-09-18 → 2026-09-25 (confirmed 2026-09-27) · **Internal refs:** turn-report contract workstream · **Status:** shadowing retired 10 days early, all four checks blocking again ; 39 blocks on the previously-shadowed reasons in the first 2 days back

---

## What broke

A Stop-hook guard enforces the shape of the agent's end-of-turn report — the block the operator actually reads when he switches between concurrent sessions. In late September its four **shape** checks were put into **shadow mode**: still evaluated, still logged, but no longer blocking — for the sessions that resolved the flag, which turned out not to be all of them. The reason was sound on its face. A block at Stop costs a *reprinted report*, and the reprints were the bigger problem — measured at a 3,580-character median, 116 re-emitted reports in three days.

So the four checks were bundled by the cost of their remedy and switched off together:

```
missing_turn_report
incomplete_turn_report
report_not_cumulative
decisions_hollow
```

One of those four is not a cosmetic shape check. `incomplete_turn_report` fires when the report is missing the sections that carry the content — what was decided, what happens next, what the human has to decide. It is the check that detects the report being *hollow*, not merely *malformed*.

Over the next seven days that check was suppressed **211 times** and blocked **21** — a 91% suppression rate. (Why it blocked at all is the second finding; see *Root cause*.) In **140 of the 211 suppressed cases**, the report that went out contained exactly one section: the goal check. Nothing decided, nothing next, nothing for the operator to answer.

Meanwhile the operator reported the defect by hand, twice, in his own words:

> "now sometimes all i'm getting is goal checks but nothing about 'what's next'" — 2026-09-23

> "i get the goal stuff, but i'm not getting end of turn decisions, or enough info to answer questions" — 2026-09-25

**2026-09-23 is also the ledger's peak day: 116 `incomplete_turn_report` would-blocks.** The guard and the human were describing the same failure on the same day, in two places that never met.

## How it was detected

Not by the shadow data. By the operator noticing, complaining twice, and new rules being written by hand in response to his complaints. Its counts were emailed weekly (see root cause 3); **no individual row was read until this postmortem**, and the rows turned out to have been keeping an exact account the whole time.

All counts below are from the audit log over the shadow window **2026-09-18 18:38 UTC → 2026-09-25 15:31 UTC** (the moment enforcement came back), with day buckets in the operator's local time (Eastern). Both suppressions and blocks, side by side:

| reason | suppressed (`would_block`) | blocked anyway |
|---|---|---|
| `incomplete_turn_report` | 211 | 21 |
| `missing_turn_report` | 50 | 113 |
| `report_not_cumulative` | 14 | 13 |
| `decisions_hollow` | 7 | 13 |
| **total** | **282** | **160** (of 205 blocks on all reasons) |

Four more suppressions arrive *after* the retirement timestamp, which is itself a clue about how the flag was read.

And what the 211 incomplete reports actually contained:

| sections present | count |
|---|---|
| goal check only | 140 |
| goal check + findings | 29 |
| goal check + next | 25 |
| goal check + decided | 10 |
| everything else (incl. 1 with no sections at all) | 7 |

A section naming the human's own pending decisions appeared in **2 of 211**.

## Root cause

### 1. Shadow mode was never a state we were in — it was a gradient we drifted along

The experiment reads, in the flag file and in every summary written afterward, as a switch: the four checks were blocking, then they were not, then they were again. The ledger says otherwise. Restricted to those four reasons, by day, in the operator's local time:

| day | blocked | suppressed |
|---|---|---|
| 09-18 | 25 | 6 |
| 09-19 | 11 | 0 |
| 09-20 | 14 | 0 |
| 09-21 | 68 | 23 |
| 09-22 | 24 | 63 |
| 09-23 | 18 | 127 |
| 09-24 | 0 | 36 |
| 09-25 | 0 | 27 |

**Two full days in the middle of a shadow experiment show zero suppression and 25 blocks.** The crossover is gradual, and it tracks the flag file's own history rather than any decision: the retired file's mtime is 2026-09-21 16:35 local — the day suppressions first arrive in volume — and the flag was an untracked working-tree file until it was committed on **2026-09-23 09:40** local. Split the window at that commit: **before it, 142 blocks against 101 suppressions; after it, 18 blocks against 181.**

(The 6 suppressions on 09-18 predate the flag file's own timestamp and are unexplained by anything measurable here. Stated rather than hypothesized.)

What this rules out is worth recording, because it was our first hypothesis and it was wrong. The flag's path is computed from the hook file's own location, which *looks* like it would make the mode per-checkout:

```python
REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
SHADOW_FLAG = Path(os.environ.get("IRONFRAME_TURN_REPORT_SHADOW_FLAG",
                                  str(REPO_ROOT / ".claude" / "turn_report_shadow.flag")))
```

But the audit path is derived from the *same* `REPO_ROOT` and is **not** overridable, so any hook copy that wrote a row into this log necessarily resolved the flag against this same directory. A second checkout would have written to its own log — and the surviving per-worktree logs contain no rows from this guard. **The per-checkout resolution is a real latent fragility and an untested risk; it is not what these rows show.** ([PM-057](057-the-isolated-worktree-was-isolated-from-the-fixes-too.md) is the version of that risk we *have* measured, from the other direction.)

The consequence either way is the one that matters: for a week, **no one could say which mode was in force**, and the answer changed day to day. An operator seeing occasional blocks has every reason to believe the check is on.

### 2. The shadow list was chosen by the cost of the block, not by the severity of the violation

All four checks shared one remedy — reprint the report — so all four were treated as one class. But they do not share a failure: three are about form, and one is about whether the report says anything. Bundling by remedy put the substantive check in the same bucket as the cosmetic ones.

### 3. The would-block counts *were* delivered to a human, weekly, and nothing happened

This is the part we got wrong when first drafting this postmortem, and the correction is the most useful thing in the file. The initial draft claimed the shadow rows went nowhere. They did not: a **weekly scheduled audit-log review** on this machine tabulates event counts and emails the operator a digest, and its own log shows `turn_report_would_block` appearing with counts of **6** and then **280** in consecutive weekly reports.

So the sensor was wired to a light, the light was on, and the report landed in an inbox — and the shadowing still ran to its end without anyone connecting it to the complaint. **A count in a weekly digest is not a review.** It tells you a number went up. It does not tell you that 140 of those rows were reports containing only a goal check, which is the fact that matters and the only one that would have ended the experiment early.

Two smaller contributors, both worth naming:

- **The experiment had a review date and no owner.** The flag file carried `Review date: 2026-10-05` in its own text. Nothing was scheduled to read it on that date. It ended on 09-25 because a human got annoyed, not because a review ran.
- **The end of the experiment is not yet in version control.** Turning shadowing *on* was a commit. Turning it *off* was renaming the tracked flag file aside to `*.flag.retired_2026-09-25`; as of this writing the resulting deletion and the guard's in-force version are both uncommitted working-tree state, and the guard's own file header still announces an older version than the one it runs. Enforcement state that only exists in a working tree cannot be reconstructed later — the same class of defect as a stale version banner producing false "not installed" reads ([PM-062](062-the-staging-area-reported-live-files-as-deleted.md)).

## Blast radius

Seven days of turns in which the report the operator reads could be a goal check and nothing else, across a fleet of 7–12 concurrent sessions — with the suppression rate climbing from zero to total over the week. 140 reports measurably went out carrying only a goal check; *what each of those cost him* is an inference, not a measurement, but he named the cost himself twice in the quotes above. Two rounds of hand-written rules were spent re-specifying a contract that was already being enforced-in-theory and measured-in-fact.

No data was corrupted and nothing was lost. This is a *communication* outage, which is exactly why it ran for a week: nothing failed loudly, the instrument that noticed had been told to stay quiet for most sessions, and the one place its count did surface was a weekly digest where a number going up means nothing in particular.

## The fix

- **The shadowing was retired** on 2026-09-25, ten days before its own review date, and all four checks block again.
- **The three content sections are now required by name** — decided / next / your-decisions — and their absence is a distinct, non-shadowable block reason each. The old rule counted labels and passed a report at 5 of 7, which is precisely how a report could satisfy the check while carrying none of the three.
- **The retired flag was kept, not deleted**, with its reason text intact, so re-shadowing any single check is a deliberate act that names the check.
- **Bundling is no longer allowed by remedy.** A check may be shadowed on its own; the four can no longer be switched off as a class.
- **Still open: nothing makes a suppression mode atomic or self-reporting.** The flag is an ordinary working-tree file resolved relative to the hook's own directory, no fire records which mode produced it, and no version of the guard refuses to run until the mode is unambiguous. Until that lands, any future shadow experiment here crosses over the same way.

What did *not* need fixing is the reason shadow mode was reached for. The block-costs-a-reprint problem was real. It was fixed separately and correctly: every Stop guard now instructs the agent to **append** a correction rather than re-emit the whole report, so a block costs one appended block instead of a 3,580-character reprint. Once the remedy was cheap, the argument for shadowing evaporated — which is the honest sequence. **The remedy was the problem, not the check.**

## Has the guard fired since?

Yes, immediately. In the two days after the 2026-09-25 15:31 UTC retirement, the audit log shows **69 blocks** on this guard, of which **39 are the four formerly-shadowed reasons** (14 missing, 12 incomplete, 12 not-cumulative, 1 hollow-decisions), plus **5** on the newly-named section checks that did not exist during the shadow window.

For calibration: over the guard's whole life before retirement it had blocked 306 times for a missing report and 88 for an incomplete one. Twelve `incomplete_turn_report` blocks in two days is a higher rate than that lifetime average, but **12 events is too few to claim a drift effect** — and the report contract itself changed the same day, which moves agent behavior independently. The honest reading is that the check is live and catching, not that a week of shadowing has been measured.

## Lessons for agent-driven development

1. **Never shadow a group of checks because they share a remedy.** Group by what the violation costs the human, not by what the block costs the agent. One of our four was load-bearing and three were cosmetic; the bundling hid that distinction completely.
2. **When the block's remedy is worse than the violation, fix the remedy.** Reaching for log-only mode because blocking hurts is treating the symptom. Our reprint problem had a cheap fix — append instead of restate — and once it landed, the case for shadowing was gone.
3. **A count in a digest is not a review.** Our would-block totals *were* emailed weekly and changed nothing, because the number carried no judgment. What ends a bad experiment is a row someone read: "140 of these reports contained only a goal check." Route the *example*, not the count.
4. **An enforcement mode carried by a working-tree file is not a mode, it's a gradient.** Ours crossed over across four days -- 142 blocks against 101 suppressions before the flag was committed, 18 against 181 after, and two days in the middle with zero suppression at all. Intermittent enforcement is worse than either state, because it reads as working. Resolve the mode from one place every session agrees on, and record the mode on every fire so the ledger can say what was in force.
5. **Put the end of an experiment under version control, not just the beginning.** Ours started as a commit; its end is still only a working-tree change. The git history says shadowing was switched on and does not yet say it stopped.
6. **Two independent reports of the same defect should meet somewhere.** The human's complaint and the guard's counter were four days and one directory apart. Cross-referencing operator complaints against would-block reasons is a five-minute query that would have ended this in a day.

The general form of the trap — and the two other ways it has bitten us — is in [patterns/shadow-mode-gates](../patterns/shadow-mode-gates.md); the 26-day version is [PM-066](066-the-shadow-gate-that-cannot-graduate.md).
