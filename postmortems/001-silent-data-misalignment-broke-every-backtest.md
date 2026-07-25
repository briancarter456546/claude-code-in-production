# A Silent One-Year Data Misalignment Invalidated Months of Backtests

**Keywords:** backtest bug, silent data corruption, off-by-one error, data alignment, quantitative trading, pandas index misalignment, AI agent code review, defensive programming

**Incident date:** confirmed 2026-06-13 (bug present for months before) · **Internal refs:** task #1688, #1713 · **Status:** fixed; guard has fired since (including on this document — see below)

---

## What broke

A family of trading-strategy simulators read every price approximately **252 trading days (one calendar year) before the date they thought they were reading**. Every backtest built on those simulators — months of results, dozens of recorded findings — was silently wrong.

No crash. No warning. No obviously absurd numbers. The results were *plausible*, which is the worst possible property for wrong results to have.

## How it was detected

Not by review, and not by the agent noticing. A cross-check during unrelated work compared a simulator's day-zero price for SPY against the raw cached data: the simulator said **$115.53**, the cache said **$91.07** — SPY's price roughly one year earlier. Pulling that thread numerically confirmed a constant 252-column offset across the entire matrix.

A second team of sessions working on a different strategy (internal task #1713) converged on the same bug class independently in the same week. Two independent discoveries of one latent bug class in seven days is a signal about the *class*, not the instance.

## Root cause

The simulators separate two things that must stay in lockstep:

1. a **price matrix** (tickers × trading days), and
2. a **date list** the simulation loop iterates over.

The matrix was built from a data window starting **2002-01-02** (extra history loaded for indicator warm-up). The date list handed to the simulator started **2003-01-02**. The loop variable `d` indexed the date list but was used **directly as a column index into the matrix**. Day `d=0`, labeled 2003-01-02, read the column for 2002-01-02. Every read, shifted one year, forever.

The deeper root cause: **the function signature made the bug possible.** Any function that accepts a matrix and a date list as two separate arguments is one refactor away from this failure, because nothing ties column `i` to date `i`.

## Blast radius

- All backtest results from this simulator family, going back months, invalidated at once.
- Several recorded research findings had to be formally retracted, including a striking one: the strategy's measured correlation to SPY was **−0.001** (beautifully market-neutral!) under the bug, and **+0.70** after the fix. The most publication-worthy result was the most artifactual.
- A documented "catastrophic −15.56% day" that had driven risk-analysis work turned out to be an artifact too. Work had been scheduled to explain a loss that never happened.
- Trust cost: every downstream decision made on the numbers had to be re-derived.

## The fix

Repair was easy (align the windows). The interesting part is the **bug-class kill**, a two-layer contract now mandatory in every simulator:

```python
def simulate(close_mat, all_trading_days):
    # Rule 0: FIRST line of any function taking matrix + dates
    # separately, before any indexing. Refuses to run misaligned.
    assert close_mat.shape[1] == len(all_trading_days), (
        'shape mismatch: %d cols vs %d dates'
        % (close_mat.shape[1], len(all_trading_days)))
    ...
```

**Layer 1 — shape contract** (above, packaged as `assert_matrix_aligned()` in a shared module): column count must equal date-list length. Costs nothing; would have refused to run the original bug on the first call.

**Layer 2 — value spot-check** (`sanity_check_prices()`, once per run): independently re-reads several (ticker, date) cells from the raw data cache and asserts the matrix holds those exact prices. This catches what a shape check cannot: **right shape, wrong column order** — which is precisely what this bug becomes once the windows have equal lengths.

The contract lives in one dependency-free module both strategy teams import, instead of parallel copies. The rule went into the project's always-loaded instruction file — and, because instructions decay, into a **PreToolUse hook** that scans any file being written for the dangerous signature (matrix + date-list as separate args) and blocks the write unless the assert is present at function entry.

## Has the guard fired since?

Yes, three ways:

- A later audit (internal #1999) found **seven scripts** with the dangerous signature and no contract, and retrofitted all seven — seven latent instances of the bug class closed before any produced a wrong result.
- The value spot-check has refused runs where a cache rebuild changed ticker ordering — the exact "right shape, wrong mapping" scenario the shape check alone passes.
- **The hook blocked this very postmortem.** The first draft's code example showed the dangerous signature without the literal assert — and the write was refused until the example carried the contract. The guard cannot tell documentation from code, and that turns out to be the correct default.

## Lessons for agent-driven development

1. **Plausible is worse than broken.** An AI agent (or a human) will happily build months of work on top of numbers that look reasonable. Design data interfaces so misalignment is *loud*.
2. **Kill the class, not the instance.** The fix that mattered wasn't the one-line window alignment; it was making the dangerous function signature safe to hold — then making the safe form mechanically mandatory.
3. **Cross-verify with a second method.** The bug was caught by comparing two independent paths to the same number. That habit is now a standing rule: one query that says "0 rows" is a claim, not a fact.
4. **Independent convergence is a smell worth chasing.** When two unrelated workstreams hit the same bug shape in a week, you've found a class.
