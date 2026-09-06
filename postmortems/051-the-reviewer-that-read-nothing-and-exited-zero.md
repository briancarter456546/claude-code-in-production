# Our external AI code reviewer read nothing, wrote nothing, and exited 0 — for an unknown number of reviews

**Keywords:** headless agent CLI, AI code review automation, permission mode request-review, silent tool denial, exit code 0 false success, LLM reviewer verification, argv length limit Windows, stream-json stdin, review audit ledger

**Incident date:** 2026-09-05 · **Internal refs:** #2607 · **Status:** fixed (transport rewritten; output size now checked); the historical population of affected reviews is unrecoverable and is documented, not repaired

---

## What broke

One of the external review seats in this system is a third-party coding-agent CLI from a different vendor, driven headless: the orchestrating session writes a review packet, invokes the CLI in print mode, and files the reply as that seat's verdict. Under the tiered review law ([ADR-018](../adr/018-tiered-adversarial-review-with-budget-caps.md)), reviewers must receive **files, not summaries** — so the packet prompt told the reviewer which repository files to read.

The reviewer could not read files. In headless print mode the CLI initializes with its permission mode set to *request-review* and then **soft-denies every tool confirmation**, because there is no human present to approve one. A prompt instructing it to open repository files opens nothing. It then **exits with status 0, having written an empty output file.** The only trace anywhere is a single stderr line naming the denied permission.

So the failure presented as a successful review that happened to have nothing to say.

## How it was detected

Not by the review process. It was found while debugging a *different* symptom — an unrelated dispatch failure — by reading the CLI's own log. The soft-deny line appeared there for a run that the review ledger had already recorded as a **successful dispatch of that seat** (2026-09-05, 09:32).

That is the whole detection story, and it is uncomfortable: the ledger, the tier accounting, and the budget caps were all consistent and all wrong together, because every one of them keys off "the dispatch completed" and none of them off "the reply contains a review."

## Root cause

**Exit status was being used as evidence of work.** The same class as [PM-032](032-exit-zero-wrong-answer.md), one layer up: there the failure was caught, warned about, and ignored under a clean exit; here the failure is *by design* on the vendor's side (deny-when-unattended is the safe behavior for an interactive permission model) and the calling code interpreted the safe behavior as a completed task.

The deeper cause is that the review pipeline had **no output contract**. A verdict artifact was whatever the reviewer wrote. Nothing asserted a floor on size, the presence of the required verdict token, or that the reply mentioned any of the material it was supposed to have read. An empty file satisfied every check that existed, because the only check that existed was the return code.

A second, independent defect fell out of the same discovery. Because the material has to be **inlined** into the prompt rather than read from disk, prompts grow large — and the print flag takes the prompt on the command line, which dies with *"Argument list too long"* above roughly 32 KB on Windows. The obvious workaround (send less material) is exactly what the review law forbids.

## Blast radius

Unknown, bounded, and honestly reported: the review ledger records **42 lifetime dispatches to that seat** (as of 2026-09-06), spread across the campaign, some of them through an older CLI path that has since been retired. Which of those carried real review content cannot be determined after the fact from the ledger alone. The operating rule adopted: **a row for that seat is evidence of a review only where a matching verdict artifact with content exists.** Rows without one are treated as unfilled seats, which under the review law leaves the tier incomplete rather than satisfied.

Nothing shipped on the strength of an empty review that has been identified. That is a statement about what was found, not a guarantee — the reviews at issue were adversarial passes whose *absence* would show up as an unchallenged claim, which is precisely the thing that leaves no trace.

## The fix

- **Transport rewritten.** The CLI's streaming-JSON input mode reads the prompt from stdin, so there is no length limit. The accepted message shape was found by probing the binary — one JSON object per line, a user event carrying a message whose content is the prompt, with the streaming input and output formats set together; the reply arrives on the result event. The wrapper delivered a **71,977-character packet** successfully on the first run.
- **Output size is now checked**, and an empty or undersized reply is a dispatch failure, not a verdict.
- **Timeout raised explicitly.** The print timeout defaults to five minutes and *truncates* long reviews rather than erroring — another silent-loss path. It is now set to twenty.
- **Documented caveat that survived the fix:** in this mode the reviewer sees inlined text with no line numbers, so any line number it cites is unreliable. Every finding from that seat is verified by symbol, never by line.

## Has the guard fired since?

The size check has rejected zero dispatches since it landed, which is the weakest possible evidence and is stated as such: one working transport plus one day is not a test of a failure path. The verifiable change is on the ledger side — seat rows without a matching artifact now read as **abstentions**, and the report prints abstentions as a first-class number precisely so an incomplete tier cannot be mistaken for a satisfied one.

## Lessons for agent-driven development

1. **An agent CLI's exit code describes the process, not the work.** Any headless agent with an interactive permission model will deny-and-continue when unattended. Treat "did it produce output of the expected shape and size?" as the only completion signal.
2. **Every automated reviewer needs an output contract.** Minimum length, required verdict token, and evidence that the material was actually seen — for example, requiring a quotation from the packet. Without it, an empty file is a passing review.
3. **Bookkeeping that counts dispatches counts intentions.** A ledger, a quota, and a tier accounting can all agree with each other and be jointly wrong when they share one unverified input. Count artifacts, not calls.
4. **When a tool forces you to inline material, expect a size cliff, and expect the cheap workaround to be "send less."** That workaround silently repeals the "files, not summaries" rule the review process depends on. Fix the transport instead.
5. **Retired failure modes leave a population, not a bug.** The fix does not repair the reviews that never happened. Publishing the affected window and demoting unverifiable rows is the honest remedy.

Related: [PM-050](050-the-review-process-failed-its-own-review.md) is the review law this seat serves, and [ADR-018](../adr/018-tiered-adversarial-review-with-budget-caps.md) the decision behind it. [PM-032](032-exit-zero-wrong-answer.md) is the same exit-code-as-evidence mechanism inside a compute job. [ADR-013](../adr/013-solution-validation-loop-external-adversary.md) is why an external adversary sits in the loop at all.
