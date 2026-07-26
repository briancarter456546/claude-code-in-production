# The Look-Ahead Guard Existed in One Pipeline and Not Its Sibling — Results Fell 165x When Ported

**Keywords:** look-ahead bias backtest, data leakage quantitative research, guard not ported, sibling pipeline divergence, too good to be true returns, walk-forward leak, single implementation drift

**Incident date:** 2026-07-19/21 · **Internal refs:** the leak-and-trust handoff; five affected KB nodes; trust-architecture origin (#2112) · **Status:** fixed in the affected pipeline; the leaked baseline preserved deliberately; census of the wider bug class run (82 files)

---

## What broke

A research pipeline family had two implementations: a guarded per-ticker path, which included a **35-day exclusion window** preventing the model from "predicting" a date using information from dates too close to it (look-ahead protection), and a newer sweep harness built for parameter exploration — **into which the guard was never ported.**

The sweep produced miraculous numbers, and miracles got recorded: five knowledge-base findings, including a "best-ever" risk-adjusted result. When the missing guard was added to the sweep (`v1_1`, with the exclusion enforced in both walk-forward functions plus point-in-time universe construction), the flagship configuration collapsed: **smoke-test CAGR from ~896% to ~5.4%, Calmar from 28 to 0.086, deflated-Sharpe verdict from PASS (1.00) to FAIL (0.383)** — roughly a 165x haircut. The entire edge had been leakage.

The adversarial coda ([the same review's second pass](../adr/013-solution-validation-loop-external-adversary.md)): even the *fixed* version's proudest repair had a residual — the exclusion window trimmed bars on a **union calendar** while forward returns shifted on each instrument's **own trading calendar**, quietly reopening a partial leak precisely for sparse, illiquid names — the ones that caused the original blowup. And the multiple-testing correction counted only the final sweep grid (48 trials), ignoring the feature/parameter exploration that preceded it. "Approximately right" in leak prevention rounds to wrong.

A repo-wide census then found the *general* class — a common windowing idiom that uses end-anchored data (`tail(N)`-style selection) where the anchor leaks future information — present in **82 non-archived scripts**, including the very script whose clean-looking rerun had earlier been used to clear prior warning flags: **a leaked script had certified the absence of leaks** (see [PM-038](038-the-validation-that-never-happened.md) for what that certification was worth).

## How it was detected

Suspicion → port → collapse: the guard's absence was found by diffing the sibling pipelines after the sweep's numbers strained belief. The residual calendar bug was found only by a dedicated adversarial pass instructed to attack the fix (six distinct leaks itemized). The 82-file census came from mechanically grepping the idiom once it had a name.

## Root cause

Surface: a guard implemented as *code in one file* rather than as *a property of the data layer* — every new consumer had to remember to re-implement it, and one didn't.

Deeper: **protections that live in implementations don't transfer; protections that live in interfaces do.** The exclusion window should have been impossible to omit — enforced where the data is served, not where it's consumed. Add the validation asymmetry: spectacular results got recorded at the speed of enthusiasm, while the check that would have caught them (run the guarded sibling on the same config) was never mandatory.

## Blast radius

Five KB findings invalidated (superseded, visibly, per the append-only rule); the "best-ever" result retracted; the 82-file census opened as a standing remediation backlog; and — productively — the founding evidence for the trust-architecture initiative: this incident, plus [PM-038](038-the-validation-that-never-happened.md), is why results now face a recomputation gate ([PM-013](013-integrity-ledger-certified-fabricated-results.md)).

## The fix

- `v1_1` with the exclusion enforced inside both walk-forward functions, point-in-time universe construction, per-instrument calendar alignment (the residual), and honest multiple-testing accounting; **`v1_0` preserved unchanged as the leaked baseline** — the before/after pair is itself an artifact, and deleting the wrong version would have destroyed the measurement of how wrong it was.
- The leak-prone idiom documented with its census list; new uses trip review.
- The structural lesson routed into the data layer roadmap: exclusion windows as a property of the serving interface, not a convention of consumers.

## Has the guard fired since?

The ported guard *is* the result — every run through `v1_1` prices in the exclusion, and the 165x delta is permanently on display in the paired baselines. The recording-layer gates downstream (PM-013) are the enforcement that spectacular-without-artifacts can't be recorded again.

## Lessons for agent-driven development

1. **A guard that lives in one implementation is a guard your next implementation won't have.** Enforce invariants at the interface that serves the data, or count on re-meeting this postmortem.
2. **Results too good to be true are a *measurement of your leaks*, not of your edge.** 896% wasn't a finding; it was an instrument reading the size of the missing guard.
3. **Fixes to leak-class bugs need adversarial re-review** — "approximately right" windowing reopens exactly where data is sparsest and results are most fragile.
4. **Preserve the broken baseline.** The leaked `v1_0`, kept verbatim, converts an embarrassing bug into a permanent calibration: this is what leakage looks like, and this is its magnitude.
5. **When a bug gets a name, census it.** One grep turned an incident into an 82-file class; unnamed, each of those files was a future postmortem.
