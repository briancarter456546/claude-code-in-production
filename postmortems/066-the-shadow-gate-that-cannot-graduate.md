# The Gate Has Been in Shadow Mode for 26 Days — and Half Its Passing Condition Has Never Once Been Recorded

**Keywords:** shadow mode gate never promoted, explore plan execute enforcement, PreToolUse gate receipts, per-session receipt files, undocumented tool response shape, guard promotion criteria, false positive rate measured in shadow, blast radius classification, AI agent workflow enforcement

**Incident date:** gate installed 2026-09-02, measured 2026-09-27 · **Internal refs:** guard-consolidation plan; explore-plan-execute ruling · **Status:** open — still in shadow mode ; 1,094 would-blocks logged, 0 blocks, 0 promotions

---

## What broke

A `PreToolUse` gate was installed to enforce a workflow ruling: before a session's **first mutation of a high-blast-radius target**, a read-only exploration pass and an approved plan must have happened *in that session*. It checks two per-session receipts, written by a companion `PostToolUse` recorder:

- `explored` — a read-only exploration/planning subagent ran this session
- `plan_approved` — plan mode was exited with an approval this session

High blast radius is decided by target, not by edit size: paths listed as governance or protected in the topology file, plus any brand-new versioned script with no existing sibling version.

It shipped in **shadow mode** — decide, log `epe_gate.would_block`, allow — because the classification was expected to be wrong sometimes and a gate that blocks legitimate work on day one is the alarm-fatigue defect it exists to reduce. The promotion criterion was written down: *a gate may block once its false-positive rate is under 20–30%, measured in shadow mode*. The operating plan said to read the log after 3–4 days and inspect the would-block rows.

Twenty-six days later:

- **1,094** `would_block` rows (2026-09-02 → 2026-09-27), plus 4,739 rows where the target was low-blast-radius and passed silently
- **0** blocks — neither the enforce nor the disable flag file exists, so the default stands
- **0** row inspections — the counts *were* tabulated and emailed weekly (see below), and the 3–4 day false-positive inspection the plan called for never happened
- daily volume **2 to 123** (local-time days), with no downward trend: the last four days are 16, 45, 32, and 42

And the finding that makes promotion impossible rather than merely overdue:

**The `plan_approved` receipt has never been written. Not once, by any session, in 26 days.** There are 13 receipt files on disk; every one of them carries only `explored`; zero contain `plan_approved`. The audit log has 37 `epe_record.explored` events and **zero** of the four plan-mode events the recorder can emit (`plan_entered`, `plan_response`, `plan_approved`, `plan_not_approved`).

Which means the breakdown of the 1,094 would-blocks is not a distribution — it's a tautology:

| missing receipts | rows |
|---|---|
| both `explored` and `plan_approved` | 896 |
| `plan_approved` only | 198 |

Every single would-block is missing the receipt that has never existed. **If this gate were promoted today it would block the first governance-path edit of every session, permanently, with no reachable pass condition.**

## How it was detected

By this postmortem — a scheduled read of the audit log looking for guard first-fires and would-block clusters.

**Not for lack of a report.** This is the finding that makes the postmortem worth publishing, and we got it wrong in the first draft: a **weekly scheduled audit-log review** runs on this machine, tabulates event counts, and emails the operator a digest. Its own log shows this gate's would-block totals in four consecutive weekly reports: **225, 123, 366, 338.** The number was measured, printed and delivered for a month. (Whether it was read is not something the log can tell us.)

What the digest could not say is that every one of those rows fails on a receipt that has never been written. **A count says a gate is busy. Only a row says whether it is right.** Four weekly reports of a rising number produced no action; one query against the receipt store ended the question in a minute.

The gate is otherwise invisible by design in shadow mode: it allows every operation, and its verdicts go to an append-only log.

The decisive check was cheap and worth copying: **count each event the recorder is capable of emitting, not just the ones you see.** The recorder has four plan-mode event names in its source. Zero appear in 26 days of log. That asymmetry — one receipt type recording fine, its partner recording never — is what turned "the review is overdue" into "the review would have found the gate unpromotable."

## Root cause

Three causes stacked, and the order matters:

1. **The approval half was built on an undocumented response shape.** The recorder's own header says so plainly: the real plan-exit response shape is not documented, so the recorder logs the first 300 characters of whatever it gets and applies a rejection heuristic that can be corrected later. That heuristic has never run in production. Whether the hook event never fires for those pseudo-tools, or no session has used plan mode in 26 days, the observable outcome is identical and the gate cannot tell the difference — **this is the same defect class as a hook reading an environment variable the harness never sets** ([PM-016](016-the-classifier-that-never-ran.md)).
2. **Shadow mode hid the consequence of cause 1.** In enforce mode, an unsatisfiable pass condition is a fleet-wide outage within minutes and gets fixed the same hour. In shadow mode it is a counter that goes up. The mode chosen to protect the fleet from a wrong gate also protected the wrong gate from the fleet.
3. **The promotion criterion was stated as a false-positive rate, and the shadow log records fire counts.** Answering "were these 1,094 rows false positives?" requires a human to read rows and judge each one — it is not derivable from the log. A weekly job counted the rows; **no job, and no person, was assigned to judge one.** A criterion that can only be satisfied by unassigned human labor is a criterion that is never satisfied, and a digest that reports its volume makes the gap harder to notice rather than easier.

## Blast radius

No corruption and no outage — the gate has never blocked anything, so nothing was lost. What was lost is the enforcement the ruling was supposed to buy: for 26 days, the "explore and plan before touching the dangerous paths" rule has had **exactly as much force as when it was only written in a document**, while appearing in the hook configuration as an installed control.

That appearance is the real cost, and it is the same one from the controls audit ([PM-054](054-nothing-checked-whether-the-controls-were-still-alive.md)): a registered hook reads as coverage. Anyone auditing the stack sees a gate on all four editing tools protecting the governance paths. The gate is there. It has never said no.

Secondary: 1,094 rows of shadow data that cannot be used for the promotion decision they were collected for, because every row fails on the never-recorded receipt rather than on the classification the shadow run was meant to validate. **The 26 days of measurement produced no evidence about the thing being measured.**

## The fix

Filed, not yet shipped — this is published open, at the point of discovery:

- **Fix the recorder before touching the gate.** Confirm empirically whether the plan-mode hook events fire at all in this harness (log every event the recorder receives, unconditionally, for one week). If they do not, the `plan_approved` receipt must come from a signal that exists, or be dropped from the pass condition.
- **Re-derive the shadow evidence afterward.** The existing 1,094 rows cannot answer the promotion question. Once a receipt is producible, the classification false-positive rate can be measured for the first time.
- **Give the shadow window an expiry, not a review date.** A shadow mode with no deadline is a permanent allow. The rule going forward: a shadowed gate either graduates or is removed by a fixed date, and the date lives in the gate's own configuration where the hook can enforce it.
- **Make the weekly digest report judgment, not volume.** It already counts these rows. The change is to print a fixed sample of rows per shadowed gate and to flag any gate whose *pass* condition has zero occurrences in the window — a line no reader can mistake for ordinary noise.
- **Add the unsatisfiable-pass-condition check to the gate audit.** For every gate, count how many times its *pass* condition was met, not just how often it fired. A gate whose pass condition has zero occurrences is broken regardless of what its block count says. This generalizes the existing policy that gates are scored against their own logs ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)).

## Has the guard fired since?

It has never fired, in the only sense that matters: **0 blocks in 26 days.** It has *logged* 1,094 times, which is a different claim, and conflating the two is how a control like this survives a month unnoticed.

The companion recorder half-works: 37 exploration receipts across 13 sessions. So the plumbing is live and the audit path is real — which is precisely why the missing half reads as working infrastructure.

## Lessons for agent-driven development

1. **Count the pass condition, not just the fires.** Every gate audit should ask how many times the gate's *satisfied* state was reached. Zero passes in a month means the gate is unpromotable, and no amount of would-block volume will reveal that.
2. **Shadow mode converts an outage into a counter.** That is its value and its danger. A gate with a broken pass condition fails loudly in enforce mode and silently in shadow mode — so shadow mode should be *short*, and its exit should be a deadline, not an intention.
3. **Counting the rows is not reviewing them, and a digest can disguise the difference.** Ours reported 225, 123, 366, 338 in four weekly emails and produced nothing, because a false-positive rate comes from someone judging rows, not from a total. Schedule the judgment — a fixed sample of N rows with a written verdict — or write the promotion criterion so a machine can decide it.
4. **Never build a required receipt on an undocumented interface.** If the shape of the signal is a guess, the guess must be exercised end-to-end before anything depends on it — otherwise "never fired" and "cannot fire" are indistinguishable for as long as the gate stays permissive.
5. **A registered hook is not a control.** Two of our audits have now found this same gap from opposite directions: hooks present in configuration, doing nothing measurable. The inventory question is never "is it wired" — it is "what has it refused, and what has it let through."
6. **When two halves of a mechanism record at wildly different rates, that ratio is the finding.** 37 of one receipt and 0 of its partner was the whole diagnosis, available at any point in 26 days from a two-line query.
