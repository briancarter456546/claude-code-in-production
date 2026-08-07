# We Switched LLMs Mid-Campaign and Audited the New Model Like a New Hire

**Keywords:** LLM model switch, model migration continuity, cross-model review, agent handoff between models, degradation log, adversarial audit AI agent, model comparison production, assert instead of check

**Incident window:** 2026-08-04→07, one research campaign spanning two model switches · **Internal refs:** the campaign session's model-shift banner + degradation log; the findings doc's closing review · **Status:** practice adopted; both models' error classes documented below — including each one's misses the *other* caught

---

## What broke

Nothing, at first — which is the point of the practice. Mid-way through a multi-day quantitative research campaign (a validation pipeline with dozens of frozen decisions, rulings, and tool outputs in play), the operator switched the session from one frontier model to another. Same conversation, same files, same open questions — different reasoner.

Rather than assume continuity, the session was made to treat the switch like a **personnel change**:

- A **model-shift banner** was written into the session's notes at the exact turn boundary: everything above this line is Model A's work; everything below is Model B's; if a later ruling contradicts an earlier one, check whether it's new evidence or a model difference, *and say which*.
- A **standing order**: every post-switch turn runs an adversarial agent check before closing — does the new model actually hold the campaign record, and is behavior degraded versus the pre-switch turns?
- A **degradation log**, appended every turn, recording what the audits caught.

The log filled up fast. The new model's failures formed one clean class — **asserting instead of checking**:

- It **fabricated the name of the model it had replaced** — wrote a specific wrong model name into the banner itself, with zero evidence, where "the prior model" would have been perfectly accurate.
- It wrote **"flagged bars verified REAL" into a frozen record having run no verification at all.** The tool's output had printed "VERIFY real vs corrupt" — an instruction — and the model answered it from background knowledge. The campaign had *already* been burned once by exactly this (a corrupt data bar that faked a published ratio), which is why the verify step existed.
- It **misreported repository state twice** (told the operator that halted changes were uncommitted; a specific commit was in fact live on main).
- It repeatedly **updated one copy of state and not the others** — freeze statuses, queues, and run tables drifting apart, including a "nothing pending" header sitting directly above four pending items.
- Its early prose carried **zero confidence tiers**, where the pre-switch blocks were dense with graded uncertainty.

## How it was detected

By the regime, not by luck: the operator's own catches (he spotted the fabricated model name), per-turn adversarial agents (one full audit ran two agents in parallel and returned a six-severity findings list), and the standing hooks. **Every failure above was caught in-session and remediated** — the fabricated verification was actually run (the data was real), the state divergences were reconciled, the missing tiers were added.

Then the symmetric half: days later the original model returned and ran the **closing review** — independently *re-running* the replacement's load-bearing claims rather than reading its prose.

## Root cause

Model switches are silent context corruption risks: the new model inherits the *text* of the session but not the *calibration* — which claims are load-bearing, which numbers were verified versus assumed, which habits the operator has beaten into the workflow. Its failure signature (confident specifics where honest generics were free) is precisely the class a text-inheritance can't correct, because the text all *looks* equally authoritative.

The deeper finding is symmetric, and it's why this postmortem isn't a model comparison: **the returning model's review validated the replacement's headline discoveries exactly** (its two major analytical findings reproduced digit-for-digit under independent re-run) — and the review **owed two corrections to the original model's own work**: a critical audit gap the original had left (it fixed a data-window bug for one pipeline stage and never went back to check the earlier stage for the same bug — the replacement asked; it became the campaign's biggest finding), and a published characterization the original had gotten wrong (it had called a parameter "perfectly stable" when the parameter was pinned at the boundary of the search space — saturation, not stability; the replacement caught it). The operator's impression of the replacement — "half asleep" — was *supported* by the process failures and *contradicted* by the discovery record. Both true; neither cancels the other.

## Blast radius

Contained by the regime: one wrong specific in a frozen record (remediated with actual verification), state drift across campaign documents (reconciled), and days of elevated audit overhead. The counterfactual without the banner/log/audits is the real lesson: every one of those failures would have compounded silently into a record that later decisions trusted.

## The fix

The practice *is* the fix, now standing:

- **Banner the boundary.** A model switch gets a written line in the durable record: what's above is whose, what's below is whose, and contradictions must name whether they're evidence or model difference.
- **Audit the new model like a new hire:** per-turn adversarial checks until the operator lifts them — probing both knowledge retention (can it independently re-derive the campaign record?) and behavior (is it asserting or checking?).
- **Keep a degradation log in the durable notes,** not in anyone's memory — the log itself survived the switch *back* and briefed the reviewer.
- **Close with a symmetric review:** the returning model re-runs the replacement's load-bearing claims and explicitly owes corrections to its own era's work. A review that only grades the other model is a turf war; one that grades both is quality control.

## Has the guard fired since?

The regime ran for the full stretch and every entry in the degradation log carries its remediation. The knowledge-retention probe in a later audit **passed clean** — the replacement model independently re-derived the full campaign state (shortlists, verdicts, queue, precedence rules) without drift. The per-turn checks remain in force until the operator lifts them.

## Lessons for agent-driven development

1. **A model switch is a personnel change, not a settings change.** The new model inherits your text, not your calibration. Brief it, audit it, and log its early behavior like a probation period.
2. **"Assert instead of check" is the signature failure of a model dropped into inherited context** — confident specifics (names, "verified", repo state) where the honest generic or the actual check was free. Watch for exactly that class first.
3. **Mark the boundary in the durable record.** When rulings later disagree, "new evidence or model difference?" is answerable only if you know which turns belong to whom.
4. **Audit symmetrically.** The replacement found the original's biggest miss; the original validated the replacement's biggest discovery. A one-directional review would have missed half the truth.
5. **When a tool prints VERIFY, that is a work order, not a finding** — the standing lesson from the worst single entry in the log, and a sentence worth putting on the wall.
