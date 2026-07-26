# Agents Don't Reason About Asymptotics: a 15-Hour Loop, an 84-Minute Silent Subagent, a 20x Estimate Miss

**Keywords:** LLM runtime estimation, computational complexity AI agents, uncached recomputation loop, subagent timeout, runaway wall clock, cost estimation code generation, precompute detection

**Incident window:** three exhibits, 2026-06→07 · **Internal refs:** session 98a219f6 (the 15-hour loop); subagent telemetry (cycle_002); the 20x estimate miss (2026-07-13) · **Status:** guards shipped for two exhibits; the estimation gap itself is managed, not fixed

---

## What broke

Three exhibits of one cognitive gap — **agents write and launch code whose runtime they cannot predict, and then don't notice it's wrong until wall-clock does:**

1. **The 15-hour loop.** An analysis script recomputed a per-instrument data panel *inside* a snapshot loop — a four-deep call chain whose innermost member rebuilt, uncached, what the outer loop had built the previous iteration. Complexity said O(N×M) where O(N+M) was available with a dict. The session that wrote it estimated minutes; it ran **15 hours** before intervention. The agent had reasoned about the code's *correctness* (fine) and never about its *growth rate*.
2. **The 84-minute silent subagent.** Parallel subagents ran a build task; two finished in 9 and 13 minutes. The third ran **84 minutes and never emitted its output contract at all** — no result, no error, just wall-clock. Failing agents don't fail fast; they *wander*, burning 6–10x the time of succeeding ones, and nothing in the orchestration bounded them.
3. **The 20x estimate.** A script's own header promised "7–12 minutes." Real arithmetic — 6 seconds per iteration × 2,153 iterations, discoverable by multiplying two numbers the session already had — said **~3.6 hours.** It ran on the wrong host because the placement rule keys on estimated runtime, and the estimate was fiction. The speed-check hooks of the era validated that *an estimate existed* and that banned rationalization phrases were absent — nothing checked the estimate against arithmetic ([PM-015](015-eight-thousand-fires-zero-true-blocks.md)'s shape-vs-property lesson, again).

## How it was detected

1: a human noticing the job still running at hour N. 2: telemetry comparing sibling agents. 3: the operator killing a "12-minute" job in its second hour. In all three, wall-clock was the detector — the most expensive instrument available.

## Root cause

LLMs generate code by local pattern, and complexity is a **global** property — it lives in the composition of loops across call boundaries, exactly where pattern-completion doesn't look. Runtime estimates, when produced, are *vibes formatted as numbers* unless something forces the multiplication. And orchestration inherited the same optimism: no wall-clock budget on subagents, because why would a 10-minute task need one?

## Blast radius

15 hours of a machine (and the queue behind it); 84 minutes of another; a mis-placed heavy job on the interactive host; and the meta-cost — every "this will take about X" in every transcript acquired a discount factor.

## The fix

- **Precompute detection:** an AST-walk guard flags deep call chains ending in data loaders inside loops with no caching signal — the 15-hour shape specifically. It advises rather than blocks (a guess never blocks), and it names the loop and the loader in its message.
- **Wall-clock caps on subagents:** orchestration observes sibling runtimes; an agent running far past the cohort with no output contract gets flagged (v1 observes and reports — the honest scope note is in the hook header; killing requires harness support).
- **Estimates must show arithmetic:** the estimate discipline changed from "state a number" to "state the per-unit cost × unit count" — the 20x miss was two known numbers never multiplied; the format now forces the multiplication into view where review (human or hook) can check it. Measured runtime history ([PM-015](015-eight-thousand-fires-zero-true-blocks.md)'s classifier) backstops repeat offenders.

## Has the guard fired since?

The precompute detector has flagged genuine recompute-in-loop shapes since shipping (each a would-have-been multi-hour run); the subagent telemetry caught its first wanderer in the cycle after the 84-minute one. Estimate arithmetic is enforced socially and at review — the residual gap (a plausible per-unit cost that's simply wrong) is real, managed by the runtime-history classifier, and stated here rather than rounded away.

## Lessons for agent-driven development

1. **Agents verify correctness and skip complexity.** Growth rate is a global property; local pattern-generation never sees it. Force the question — per-unit cost × units — into a checkable format.
2. **A runtime estimate without shown arithmetic is a mood.** The 20x miss required no new information, only a multiplication nobody performed.
3. **Failing agents burn multiples of succeeding ones.** Budget subagents against their cohort; silence past the cohort's envelope *is* the failure signal.
4. **Wall-clock is your most expensive detector.** Every hour it spends detecting is an hour the guard that should have existed didn't. Shape-detection (advisory) plus measured history (authoritative) is the cheap replacement.
