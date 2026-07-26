# NaN Prices Made Backtest Positions Immortal: Every Exit Rule Silently Skipped

**Keywords:** NaN comparison bug, backtest data integrity, delisted tickers, silent data corruption, pandas NaN handling, zombie positions, quantitative backtesting bugs

**Incident date:** discovered 2026-06 during simulator forensics · **Internal refs:** simulator bug-pattern record; related contract in [PM-001](001-silent-data-misalignment-broke-every-backtest.md) · **Status:** fixed; NaN-delisting handling + data-sanity gates in the loaders

---

## What broke

A portfolio simulator held positions in stocks that got delisted mid-backtest. After delisting, the price series goes NaN. Every exit rule in the simulator was a comparison against price: stop hit? `close < stop`. Target hit? `close > target`. Time exit? checked against an indexed price.

In IEEE floating point, **every comparison with NaN is False**. Stop not hit (False), target not hit (False), trailing exit not triggered (False) — forever. The position became a zombie: un-exitable, carried on the books at its last real value, silently distorting portfolio weights, cash accounting, and every metric computed over them, until the end of the backtest.

No exception. No warning. NaN propagation through comparison operators is *silent by specification*.

## How it was detected

Forensic review of position ledgers during a broader simulator audit: positions with entry dates and no exit dates, in tickers whose price history visibly ends mid-sample. Once one was found, a scan for "positions open at end-of-backtest in delisted names" enumerated the rest.

## Root cause

Surface: exit logic written as `if price_condition:` with no NaN branch.

Deeper: **the simulator's model of the world had no concept of "this asset stopped existing."** Delisting isn't an edge case in long-horizon equity backtests — it's a survivorship-bias-critical feature. A simulator that only handles assets that live forever will be wrong in exactly the direction that flatters results (the dead ones are disproportionately the losers).

Deeper still: NaN was performing double duty — "no data yet" before listing and "gone" after delisting — and no code distinguished the two.

## Blast radius

Every backtest that crossed a delisting boundary carried phantom exposure. Combined with the index-misalignment bug ([PM-001](001-silent-data-misalignment-broke-every-backtest.md)) found in the same audit era, it forced the full revalidation sweep of recorded findings — weeks of recompute — and contributed several entries to the knowledge base's corrections record.

## The fix

- **Explicit delisting semantics:** on the first NaN after valid history, the position force-exits at the last real price (with a haircut policy decided explicitly, not by accident of float semantics).
- **Data sanity gate at load time:** the price-loading path runs a checker that, among other things, maps each ticker's valid-data window, so simulators receive "this asset exists from A to B" as data, not as a NaN puzzle.
- **The general contract:** any simulator loop indexing a price matrix must assert matrix/date alignment up front (the PM-001 contract) — the two bugs share the "indexing silently means something else" signature.

## Has the guard fired since?

The load-time sanity gate runs on every backtest data load as a matter of course. The forced-exit path triggers on every backtest that spans a delisting — which, in a 1,700-symbol universe over multi-year windows, is every serious run. What hasn't recurred is the signature this postmortem exists for: no end-of-run zombie positions since the semantics shipped.

## Lessons for agent-driven development

1. **NaN comparisons are False, and False means "keep holding."** Any control flow where inaction is the False branch will treat missing data as a decision to do nothing — silently, forever.
2. **Model non-existence explicitly.** "The asset is gone" must be a state your system represents, not a data artifact it trips over.
3. **Silent-by-specification failures need structural detection.** Nothing will ever throw. Your only options are invariants (no open positions in dead tickers) checked at boundaries.
4. **Bias direction matters as much as bug size.** Zombie positions flattered results by construction — delisted names skew toward losers whose losses stopped accruing. Bugs that flatter survive longest.
