# The Holdout Our Screens Were Protecting Had Been Visible All Along

**Keywords:** holdout contamination, look-ahead bias screening, relative date range bug, out-of-sample integrity, backtest data window, half-applied fix, positive negative control validation, calibrate against assumption

**Incident date:** discovered 2026-08-05; root cause dates to the campaign's first session · **Internal refs:** the contamination findings doc §1; the window-check tool; the campaign's two-stage protocol · **Status:** measured and documented; remediation (clean re-screen with explicit dates) decided at operator review

---

## What broke

A two-stage validation campaign: stage 1 *screens* candidate entry/exit families per asset on pre-2020 history only, deliberately reserving 2020-onward as the untouched holdout; stage 2 then walk-forward tests the frozen shortlists — with the holdout period as its out-of-sample proof.

The screens were run in an off-the-shelf backtesting platform whose date control has two modes: explicit start/end dates, and a **relative "most recent N years"** setting. A relative range ends at the *newest bar in the data* — it cannot stop at 2019. The operator, early in the campaign: "I think a lot of them may have been set to last-25-years before I learned about the date-to-date option."

Measurement confirmed it: **10 of 14 screens had run past 2019 into the holdout.** Three more read "clean" but couldn't be trusted (below), and one was a deliberate control. The family-level choice — *which* entry/exit type pair each asset's shortlist froze — had been made while the screen could see the very period stage 2 would later present as out-of-sample. The stage-2 verdicts, including every pass, inherited an unquantifiable optimism.

The sharpest part: **this exact root cause had already been diagnosed and fixed once** — in the campaign's first session, an adversarial review back-solved a mis-loaded chart to the relative-range setting, and the fix (explicit dates) was applied *to stage 2*. Nobody went back to ask whether the already-completed stage-1 screens — same era, same setting — carried the same bug. The fix was applied at the point of discovery, not across the class. The gap sat open for weeks and was found only when a new screen's "set for 27 years" phrasing snagged.

## How it was detected

Three layers, each worth stealing:

- **The trigger was linguistic, not numeric:** "last 27 years" describes a relative range; relative ranges can't end at 2019. One sentence of operator phrasing reopened the case.
- **The instrument was inference from the tool's own outputs:** stage-1 grid exports carry *no dates at all* (which is why the bug was invisible in its own artifact — a mis-set screen leaves no trace). But bar count is derivable from position count × average bars held ÷ exposure. That estimate was **validated against five runs whose true bar counts were independently known** (mean ratio 1.00, spread ±5%) before being pointed at anything.
- **Controls, both directions:** a *blind positive* — the method flagged one screen as running-to-today with no knowledge of the operator's disclosure, which he then confirmed independently — and a *negative control*, a screen deliberately run with explicit dates, which the method correctly read as clean. Detection power and false-alarm rate, both demonstrated before any verdict was published.

Two honesty notes that made the finding trustworthy: an earlier calibration of the instrument had been **back-derived from windows that were themselves assumed** — and nearly issued a false all-clear before being re-validated against known truth ("never calibrate against an assumption"). And for three assets, the two candidate windows differ by 0.6% in bar count — **the instrument cannot distinguish them, and the write-up says so** rather than crediting the "clean" reading: given the operator's disclosure, the honest default for those three is contaminated-but-undetectable.

## Root cause

Surface: a UI convenience (relative date ranges) that silently violates a research protocol's core boundary, in a tool whose screening exports don't record what window they ran on.

Deeper, twice:

1. **A fix applied where the bug was *found* is not a fix applied where the bug *lives*.** The relative-range failure was root-caused in session one and patched forward (stage 2) but never backward (stage 1's completed artifacts). Half-applied fixes are worse than open bugs: they retire the alarm while the damage stands.
2. **Artifacts that don't stamp their own provenance make contamination unfalsifiable.** The stage-2 reports carried dates (which is how the first diagnosis worked); the stage-1 grids carried none, so weeks of downstream work stood on windows nobody could check.

## Blast radius

The family selections behind every frozen shortlist, and therefore an unquantifiable inflation in all ten stage-2 verdicts — the level *parameters* were fit honestly per-fold (that half of the protocol held), but the *types* those fits ran on were chosen with holdout knowledge. Cost of remediation: a full clean re-screen with explicit dates — accepted, and deliberately merged with an independently-motivated library redesign so the campaign only re-screens once.

## The fix

- **Relative date ranges banned by written procedure, for every stage, with both failure modes named** (ends-at-today swallows the holdout; doesn't reliably load what was asked).
- **Every future screen exports a provenance stamp** — the platform's metrics report, whose benchmark dates pin the loaded window — alongside the grid, and the window-check tool runs automatically at ranking time. Screens now carry the evidence stage 2 always had.
- **The class-wide question is now part of the root-cause ritual:** when a setting-caused bug is diagnosed, enumerate *every artifact produced under that setting*, not just the pipeline stage where it surfaced — the same census move as the look-ahead idiom sweep in [PM-039](039-the-guard-that-existed-but-was-never-ported.md), which this incident rhymes with at a different layer.

## Has the guard fired since?

The window-check ran across the full campaign inventory (that's the 10-of-14 table) and its verdicts were independently re-run days later by a second reviewer, reproducing exactly. The explicit-dates procedure produced its first provably-clean screen (the negative control) before this postmortem was written. The re-screen decision — how much of the campaign to unwind — was put to the operator as an explicit judgment call with options, not slipped into a footnote.

## Lessons for agent-driven development

1. **"Fixed going forward" is an unfinished sentence.** A root-caused bug demands a census of everything already produced under the buggy condition — the backward half of the fix is where this one hid for weeks.
2. **Artifacts must stamp their own provenance.** Any research output that doesn't record what data window/config produced it is unauditable by construction — and contamination in it is invisible precisely when it matters.
3. **Validate the instrument before the verdict:** known-truth calibration, a blind positive, a negative control — and never calibrate against an assumption. The near-miss false all-clear came from exactly that.
4. **Report your instrument's blind spots as blind spots.** Three "clean" readings the method couldn't actually distinguish were published as *undetectable*, not as clean — the difference between honest and convenient.
5. **Relative/"most recent" settings are protocol violations wearing a convenience UI.** Anything that anchors to *now* cannot respect a historical boundary; ban it wherever a holdout exists.
