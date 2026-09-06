# Three governance controls, measured on one day: one never ran, one never blocked, one was ignored 857 times

**Keywords:** control liveness, inert security gate, tamper-resistant audit log, ambient environment token, advisory vs blocking hook, zero-block gate, enforcement efficacy measurement, AI agent governance, guard telemetry

**Incident date:** measured 2026-09-05; the oldest defect dates to 2026-04-18 · **Internal refs:** #2672 · **Status:** measured and published; two of the three repairs are operator decisions and are open

---

## What broke

Nothing visibly. That is the finding.

An enforcement-efficacy sweep asked a question the system had never asked: **for each control, is there evidence it is alive and that it has ever refused anything?** Three answers landed the same day.

**1. The tamper-resistant audit collector had ingested zero events in four and a half months.** The design (its own architecture note) is a collector running on the always-on server under a *separate operating-system user*, so that the machine sending events cannot alter the record — the external-enforcement property any real governance control needs. Checked: the service reports **inactive**; its canonical log file is **0 bytes**, owned by the dedicated user, created **2026-04-18 16:50**, never written; the ingest log is also 0 bytes. Meanwhile the sender-side advisory cache on the workstation holds **91,931 lines** (94,644 a day later). Everything downstream that treats "the audit log" as authoritative has been reading the copy the sender can rewrite.

**2. A privileged-path gate logged 1,347 allows and zero blocks.** Its detail records show the pattern matching and the token check *passing* — because the token it checks is **ambient in every session environment**. The gate is inert while appearing enforced, and it appears enforced in exactly the way a working gate would: high traffic, clean logs, no incidents. Re-verified 2026-09-06: 1,369 allows, 0 blocks.

**3. An advisory injection fired 857 times carrying four rules that had been overturned.** A per-prompt context block was injecting a list of retired approaches, four of which an operator ruling on 2026-09-05 had explicitly reclassified. Across **857 exposures, zero sessions flagged the contradiction** — the number is now 941. The injection is doing its job mechanically and changing nothing.

## How it was detected

By deliberately inverting the usual telemetry question. Guard analysis in this repo has historically asked *"is this guard too noisy?"* ([PM-015](015-eight-thousand-fires-zero-true-blocks.md), [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)). This sweep asked *"does this control bite at all?"* — and a **zero-block gate is indistinguishable from a working gate** unless something specifically checks.

For the collector, the check was one command against the service and a file listing on the server. For the gate, it was grouping its own log lines by outcome. Neither is clever. Neither had ever been run.

## Root cause

**Deployment was treated as completion.** Each of the three was built, reviewed, shipped, and recorded as done. None had a liveness assertion, and nothing anywhere in the stack answers "has this control refused anything in the last N weeks?"

The three failure modes are worth naming separately because they are not the same bug:

- **Never started.** A service that was deployed but not enabled, whose output file exists (created at install) and is empty. The empty file is what made it look installed.
- **Structurally inert.** A token-based gate whose token is present in every environment it guards. It cannot fail; therefore it cannot enforce. Same family as [PM-016](016-the-classifier-that-never-ran.md), inverted: there a hook read a variable that is never set, here a hook reads one that is always set.
- **Advisory mistaken for control.** Text injected into the model's context is a suggestion. Several controls in this system are named like refusals but only *inform*: a would-block dry-run counter (214 events), a warn-mode policy scope, an advisory freshness gate.

That last one got its own measurement. In a single session, **five blocking guards changed the session's output 5 out of 5 times; one advisory hook fired 4 times and changed behavior 0 out of 4.** Across the whole log: 7,466 block-class events across 20 types versus 5,948 advisory-class events across 11. The blocking half is the half that does anything.

## Blast radius

No incident is attributable to these three — which is the honest and slightly unsatisfying accounting, and also the point. The cost is **false assurance**: for four and a half months, "we have a tamper-resistant audit record" was in the architecture and not in reality, and any efficacy analysis built on the sender-side copy is built on a record the sending host can rewrite. The privileged-path gate has been counted as a control in design reviews since July.

The one measurable, bounded cost is the advisory injection: 857 firings of a per-prompt block, paid for in tokens on every prompt, carrying content that was wrong for part of that window and acted on zero times.

## The fix

- **A liveness question is now part of the control's definition**, not an afterthought: every governance control must be able to answer *when did you last refuse something?* A control with zero refusals over a defined window is flagged as either unnecessary or broken — the two are not distinguished automatically, and shouldn't be, because the remedy differs.
- **The inert gate is an operator decision, deliberately not self-served.** Making it bite means removing the ambient token, which turns a silent allow-all into a real block on a governance path used daily. That is a policy change with an operational cost, and the audit's job was to surface it, not to ship it. It is open.
- **The collector is open too**, and stated as such: activating it is not enough — it needs an ingest heartbeat, because a running collector receiving nothing looks exactly like the four-and-a-half-month silence it just came out of.
- **The stale advisory content was corrected** the same day the ruling landed, and the general lesson recorded: injected context needs the same supersession discipline as any stored fact.

## Has the guard fired since?

Deliberately unanswered here, because answering it prematurely would repeat the mistake. The audit produced measurements and two open decisions; no new control was shipped, so there is nothing whose firing would be evidence. The next honest report on this is the first time a liveness check flags a control that has gone quiet — and that check does not exist yet.

## Lessons for agent-driven development

1. **A control with no refusals is not evidence of compliance.** It is one of: unnecessary, misconfigured, or dead — and from the logs alone, all three look identical. Design the liveness check when you design the control.
2. **An empty output file is the signature of "installed but never ran."** It is created at install time, so its existence proves nothing and reads as proof of everything.
3. **Ambient credentials silently disable credential checks.** If the token a gate requires is in the environment of every process it guards, the gate is decorative. Audit *where the secret lives*, not just that the check exists.
4. **Injected context is not an enforcement mechanism, at any salience or timing.** Measured here at 0 for 4 against 5 for 5 for refusal. Use injection to inform; use refusal to enforce; never count injection as a control.
5. **Trust the record that the sending host cannot rewrite — and verify it is receiving.** A tamper-resistant design that was never switched on is strictly worse than an honest local log, because it is cited as though it were the former.

Related: [PM-015](015-eight-thousand-fires-zero-true-blocks.md) is the same audit doctrine pointed at noise instead of silence; [PM-016](016-the-classifier-that-never-ran.md) is the environment-variable twin of the ambient-token defect; [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md) and [ADR-017](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md) are the audit policies this extends from "is it noisy?" to "is it alive?"; [ADR-015](../adr/015-advisory-injection-second-model-in-the-loop.md) is the advisory mechanism whose limits are quantified above; [PM-055](055-the-audit-log-could-not-be-counted.md) is why the counts in this file needed two normalizations before they were trustworthy.
