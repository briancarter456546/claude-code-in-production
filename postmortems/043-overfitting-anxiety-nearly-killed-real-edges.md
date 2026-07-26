# Our AI Was So Afraid of Overfitting That It Nearly Killed Five Real Edges

**Keywords:** overfitting anxiety, Type II error backtesting, Bonferroni over-correction, effective trials collinearity, deflated Sharpe ratio, dividend adjusted prices bug, LLM prudence bias, adversarial execbreak, curve fitting vs overfitting

**Incident window:** 2026-07-25/26, one research thread end-to-end · **Internal refs:** the retest/walk-forward workstream; execbreak findings doc; the effective-frontier methodology adoption · **Status:** methodology adopted; verdicts reversed on re-run; round-2 adversarial break pending per policy (stated, not hidden)

---

## What broke

Every quant postmortem you've ever read is about believing a fake edge. This one is about the mirror failure, which almost nobody documents: **manufacturing prudence until real edges test as dead.**

A retest of six single-name timing systems produced survivors; an adversarial critique (correctly) flagged multiple-testing risk; and the agent's response was to reach for maximum sternness — with three compounding errors hiding inside the sternness:

1. **Wrong prices made a real edge look fake.** The harness read raw closing prices where production uses dividend/split-adjusted ones. For a steady dividend payer, every ex-dividend date registered as a small loss that never happened. One system's verdict **flipped from KILL to KEEP** when dividends stopped being counted against it. A *data-integrity bug wearing a statistical verdict's clothing* — the kill looked like rigor.
2. **The multiplicity penalty treated near-duplicates as independent sins.** Six rule variants per name were Bonferroni-corrected as six independent trials. But the variants were heavily collinear — measured effective trials ≈ **2.1, not 6** — so the correction over-penalized by roughly 3x. Under the inflated penalty, "only one survivor" was the arithmetic's verdict, not the data's.
3. **Binary significance gates converted healthy degradation into death sentences.** Out-of-sample performance *should* come in below in-sample — a degradation ratio around 0.4–0.7 is the expected signature of a real edge under honest validation. A binary p<0.05-or-kill gate reads that healthy degradation as failure, while reserving its mercy for the occasional lucky collapse. Genuine collapse (an edge whose out-of-sample significance evaporates entirely) *is* disqualifying — one name showed exactly that and stayed dead — but the gate couldn't tell collapse from degradation.

Re-run with corrected prices, effective-trials deflation, and degradation-based validation: **five of six names showed real (modest, honestly-sized) edges.** The prior verdict — one survivor — had been mostly anxiety, not evidence.

## How it was detected

By running the adversarial process in *both* directions — which is the part worth stealing:

- A **plan-level adversary** attacked first, in the overfitting direction: it called the original survivor set "a textbook overfitting cascade" (uncorrected multiplicity, single split). It was right about the risk and became part of the fix — but its recommended posture (stack every penalty) fed the anxiety.
- A **fresh-context execbreak agent** then attacked the implementation, with no stake in either conclusion. It killed the author-session's own favorite explanatory theory by *computing it directly* (the claimed mechanism predicted a specific statistic near 7; the direct computation returned ~1.05 — theory retracted, not argued). It found the dividend bug. It found a panic-filter accidentally disabled in a winning configuration — an error in the *optimistic* direction, caught by the same pass. And it found the harness **calling its own sanity-checker and discarding the result** — a smoke detector installed but never wired to the alarm.
- An operator-supplied methodology note named the disease: Type I (believe a fake edge) and Type II (discount a real one) both cost money, and LLMs lean Type II *as a safety reflex* — shrinking real numbers toward "probably noise" to appear prudent.

## Root cause

**Skepticism is a parameter, and nobody was calibrating it.** The system had guards, adversaries, and instructions against overconfidence — and nothing at all against over-*hedging*. So every ambiguous call resolved toward kill: stack another penalty, round another number down, prefer the sterner gate. Prudence-flavored errors passed review precisely because they *look like* rigor — the same camouflage that let the dividend bug masquerade as a statistical kill.

Deeper: **penalty stacking is the anxious version of rigor.** Correct multiplicity control is *one* coherent deflation sized to the effective search (budget the test count up front; deflate by effective trials; take one explicit haircut). Stacking Bonferroni + deflation + informal "further discounts" isn't extra safety — it's triple-charging for the same sin until nothing real survives.

## Blast radius

Verdict-level: multiple real edges falsely killed for a day, one fake survivor pattern ("sole survivor") nearly canonized, and a production-relevant system mislabeled dead by a pricing bug. Process-level, the durable cost this repo exists to record: **an agent that over-hedges is exactly as untrustworthy as one that over-claims** — its outputs just fail in the direction reviewers pat it on the back for.

## The fix

- **Test budgets up front, not penalties after:** compute how many configurations the data can support *before* sweeping; pre-register the grid; sweep for robustness plateaus, never argmax peaks.
- **Deflate by effective trials** (collinear variants counted via their correlation, not their count) — using the deflation infrastructure that, it turned out, already existed in the stack and had precedent (a prior 576-config sweep had measured effective trials of ~1.9).
- **Degradation ratios replace binary gates:** out-of-sample-to-in-sample around 0.4–0.7 = healthy KEEP; collapse or sign-flip = kill. One explicit haircut on the survivor, not a penalty stack.
- **Trade-count floors** (thin-sample "survivors" flagged, not celebrated) and **signal-vs-portfolio separation** (overfit-police the entry/exit search; don't FDR-tax portfolio construction).
- **Both-directions adversarial review as standing policy:** every material harness change gets a fresh-context break, and the break brief explicitly includes *"find where prudence manufactured a false kill"* alongside "find where enthusiasm manufactured a false edge."
- The disconnected sanity-checker: reconnected (its warnings print), and "calls checker, ignores result" joined the review checklist as a named anti-pattern.

## Has the guard fired since?

The re-run itself is the first fire: five verdicts changed under corrected data and calibrated deflation, and one name's edge stayed dead (genuine collapse) — the method kills as well as resurrects, which is the point. Honest status: per the same policy this postmortem praises, the corrected harness was slated for its own round-2 break before the new verdicts are trusted — at time of writing that break was pending, and these numbers are treated accordingly.

## Lessons for agent-driven development

1. **Overfitting-anxiety is the mirror bug of overfitting, and only one of them gets guards.** Audit your review culture: if hedging always survives review and confidence never does, your agent is being trained to bury real results.
2. **Deflate by effective trials, not nominal counts.** Six near-identical rules are two hypotheses, not six sins; Bonferroni on collinear variants is a 3x tax on truth.
3. **Binary significance gates can't distinguish healthy degradation from collapse** — and healthy degradation is what real edges look like out-of-sample. Measure the ratio; reserve the kill for collapse and sign-flips.
4. **Data-integrity bugs masquerade as statistical verdicts.** Dividends counted as losses read as "no edge." Before trusting any kill, check what the prices actually were.
5. **Point the adversary both ways.** A fresh-context breaker briefed only on "find the overclaiming" will bless over-hedging. Brief it to attack false kills with the same appetite as false edges.
