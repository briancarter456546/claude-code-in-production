# We Measured Our Evidence-Citation Guard: 10/10 Fires on the Wrong Rule, 0/10 on Its Target

**Keywords:** Stop hook precision recall, guard measurement, evidence citation enforcement, LLM output validation, hook probe testing, regex hedge matching, guard perverse incentives

**Incident date:** probe audit 2026-07 · **Internal refs:** tasks #1654, #1820, #1839; evidence-required-guard v1.0→v1.1 · **Status:** rebuilt after measurement; the probe method is the reusable artifact

---

## What broke

A Stop hook was built to enforce evidence discipline: responses making numerical claims must cite their sources; unsourced numbers get blocked and rewritten. Reasonable goal, plausible implementation, shipped.

A probe audit — replaying a corpus of real responses through the guard and scoring every decision — returned a report card nobody expected:

- **Block rate:** 10 of 57 responses blocked.
- **Of the 10 blocks: all 10 fired on one incidental sub-rule.** Zero fired on the guard's designed target (unsourced quantitative claims).
- **Perverse incentive found:** the pattern logic *rewarded vagueness*. "Per the script output" (hand-waving) passed; "per `tier0b_ceiling.py`" (a precise, checkable citation) could trip the format patterns. The guard was training the agent to cite *less* precisely.
- **Dead letter found:** the guard's own header documented `~` as an accepted hedge marker — the regex, as written, could never match it. Documentation described a feature the code structurally lacked.
- **Fragility found:** the guard could not survive being *described*. A bug report that quoted the guard's own regex inside a response was parsed as a violating claim and blocked — the guard censored discussion of itself.

## How it was detected

Not by incident — by **measurement on suspicion**. After the gate-audit era began ([PM-015](015-eight-thousand-fires-zero-true-blocks.md)), a session ran a structured probe: N real responses, hand-labeled for what *should* block, replayed through the live guard, confusion matrix out the other side. An afternoon of work; it ended the guard's credibility in one table.

## Root cause

The guard enforced **textual shapes, not epistemic properties.** "Has a citation-looking string near a number" is a shape; "the number is traceable to a source" is a property. Shapes are what regex can see, so shapes are what got enforced, and the gap between shape and property is exactly where the perverse incentive lived. The deeper cause repeats PM-015's: implementability substituted for signal, and no one measured until the probe.

## Blast radius

Weeks of miscalibrated enforcement: real unsourced claims passing, precise citations occasionally punished, and marginal training pressure *toward* vagueness — the exact opposite of the guard's purpose. Plus the blocked-bug-report absurdity, which cost an afternoon of confusion.

## The fix

- v1.1 narrowed the guard to the sub-rules that measurably work, demoted the rest to advisory, and fixed the self-description fragility (quoted/code-fenced content is exempt from claim parsing — the same quoted-prose lesson as the false-positive family in the guard fleet).
- The unmatchable hedge documentation was deleted rather than implemented — measurement first, features second.
- **The probe became the practice:** hand-labeled corpus + replay + confusion matrix is now the acceptance test for any Stop hook that judges response *content*. A content guard without a measured precision/recall is a hypothesis wearing a uniform.

## Has the guard fired since?

The rebuilt, narrowed version fires modestly (16 blocks in a recent 12-day window) on its measured-effective rules. Honest caveat: enforcement of the *property* (traceable numbers) remains partly procedural — the trust-architecture work ([PM-013](013-integrity-ledger-certified-fabricated-results.md)) attacks it at the recording layer instead, where properties are checkable.

## Lessons for agent-driven development

1. **Measure content guards with a labeled corpus before trusting them.** Fire counts tell you activity; only a confusion matrix tells you direction.
2. **Regex enforces shapes; check what property the shape is standing in for** — and whether gaming the shape is easier than satisfying the property. If yes, you've built a vagueness trainer.
3. **A guard must survive being quoted.** Exempt code fences and quoted text, or the guard censors its own bug reports.
4. **Docs that describe unimplemented behavior are worse than no docs** — they anchor everyone's mental model to a fiction. Delete or implement; never leave the gap.
