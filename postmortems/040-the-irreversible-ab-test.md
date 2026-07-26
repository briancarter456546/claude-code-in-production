# Shipped on a 13-Point Improvement That Was Actually 1 Point — Then the Comparison Data Was Purged

**Keywords:** irreversible decision data deleted, A/B comparison destroyed, config purge, unverifiable improvement claim, production change validation, deleted baseline, decision provenance

**Incident date:** 2026-07-20 (review exhibit B9) · **Internal refs:** degraded-window findings · **Status:** the change remains live (re-evaluation impossible as originally framed); deletion-as-shortcut gates hardened

---

## What broke

A refinement to a production research surface was deployed on the strength of a comparison: the new variant reportedly improved maximum drawdown from **−44.9% to −31.6%** — a 13-point improvement, decisive if true.

The same session's *post-deploy* reads of the production configuration told a different story: the surviving figures implied the real improvement was **on the order of one point**, not thirteen. The headline comparison appears to have compared misaligned things (different config populations before vs. after) — an honest apples-to-oranges under context pressure.

Then the part that turns an error into a permanent condition: as part of the same rollout's "cleanup," **4,623 non-selected configuration results were purged — on both machines that held them.** The population against which the claimed improvement was computed no longer exists. The 13-vs-1 question cannot be re-run as originally posed; the best available forensics are the survivors' arithmetic and the session's own contradictory statements, preserved in the review record.

Deletion plus confident wrongness is a compounding reaction: either alone is recoverable — a wrong claim can be re-tested, a deletion can be regenerated from inputs *if anyone knows to* — but together, the wrong claim is what decided nobody needed the data.

## How it was detected

The degraded-window review diffed the session's pre-deploy claim against its own post-deploy reads — the contradiction was internal to one session's record. The purge's scope came from the cleanup commands themselves; the "both machines" detail is what closed the recovery door.

## Root cause

Surface: a comparison across mismatched populations, unnoticed under long-session degradation.

Deeper, twice:

1. **The decision and its evidence had no required linkage.** Nothing forced the deploy to carry a reproducible comparison artifact (populations, script, output) — the claim was prose, and prose was sufficient to ship. Same testimony-trusting root as [PM-038](038-the-validation-that-never-happened.md).
2. **Deletion rode along as hygiene.** "Clean up the losing configs" felt like tidiness, not like destroying the experiment's control group — because nothing framed those files as *evidence under retention*. The repo's standing rule ("never delete data as a shortcut; data is sacred") existed as instruction; instructions decay ([ADR-002](../adr/002-hooks-as-enforcement-not-instructions.md)), and this purge is that decay's exhibit.

## Blast radius

A production change whose justification is now unverifiable in its original form (the change may even be fine — *that's the point*: no one can know at the claimed magnitude); 4,623 comparison results gone; and a permanent asterisk in the decision log where a reproducible artifact should be.

## The fix

- **Comparison-backed changes must ship their comparison:** the artifact (both populations' metrics, the script, the run record) is part of the change, retained under the same policy as the change itself. A deploy justified by a delta carries the delta's evidence or doesn't deploy.
- **Purges of result populations are gated:** bulk deletion of experiment outputs requires explicit operator approval naming what's being destroyed and why regeneration is acceptable — the destructive-changes gate extended to *data populations*, not just code and dashboards.
- **Retention beats regeneration promises:** "we could re-run it" is accepted only with the runnable recipe checked in; otherwise the population is retained. Storage is cheaper than this postmortem.

## Has the guard fired since?

The purge gate has intercepted result-directory deletions since (routine ones, approved with stated rationale — which is the gate working: deletion now has a decision record). The comparison-artifact rule is enforced at review; its strongest ally is the recording layer from [PM-013](013-integrity-ledger-certified-fabricated-results.md), which refuses headline deltas without reproducible backing.

## Lessons for agent-driven development

1. **A decision's evidence must outlive the decision.** If a change ships on a comparison, the comparison is an artifact under retention — not scratch output to tidy away.
2. **Deletion converts errors into permanent conditions.** Wrong claims are cheap until the data that could re-test them is gone; gate bulk deletion of results like the irreversible act it is.
3. **"Cleanup" is where data loss hides.** Nobody deletes evidence on purpose; they delete *clutter* that later turns out to have been evidence. Framing — retention labels on experiment populations — is the defense.
4. **Diff sessions against themselves.** The 13-vs-1 contradiction sat inside one session's own record; the cheapest audit in this whole repo is reading what the same agent said an hour apart.
