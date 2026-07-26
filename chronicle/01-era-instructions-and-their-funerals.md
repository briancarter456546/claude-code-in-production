# Era One: Instructions and Their Funerals (Mar–Apr 2026)

**Sessions:** 1–4 concurrent · **Enforcement:** an instructions file, growing fast · **Signature failure:** plausible, silent, discovered late

The first era is the one every agent-driven shop lives through, whether they write it down or not: the period when you believe the model just needs to be *told*.

The workload scaled faster than the discipline. Trading research wanted backtests; backtests wanted data pipelines; pipelines wanted deployment; and every piece was authored conversationally, shipped optimistically, and monitored by vibes. The era's two founding catastrophes both fit that shape:

- **The silent year-offset** ([PM-001](../postmortems/001-silent-data-misalignment-broke-every-backtest.md)): a 252-trading-day index misalignment that made months of backtests quietly wrong — results plausible enough that nothing prompted a look. The fix wasn't vigilance; it was a *contract* — an alignment assertion that must appear in every simulator, which is the era's real lesson in embryo: correctness you can't skip beats correctness you remember.
- **The SSH flood** ([PM-002](../postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md)): concurrency's first bill. Hooks and sessions each opening their own connections looked fine individually and, in aggregate, looked exactly like an attack — 8 hours locked out of production. The relay that fixed it ([ADR-001](../adr/001-local-http-relay-instead-of-raw-ssh.md)) established the era-defining move: *replace a convention ("be gentle with SSH") with an architecture (one multiplexed channel, raw SSH blocked).*

Deploy hygiene produced the era's quieter classics: the scp'd fix reverted by the sync cron thirty minutes after hash-verification ([PM-029](../postmortems/029-deploy-verified-then-reverted-thirty-minutes-later.md)); the version bump whose cron kept running the old file; the cherry-picks on an auto-resetting host that stranded 17 commits into a four-day outage. Each one a two-writers-one-truth story; none yet recognized as a *class*.

The instructions file, meanwhile, absorbed every lesson as prose. By era's end it held rules about SSH, deploys, data sanctity, day-of-week computation, API discipline — and the operator was personally re-teaching them to every fresh session that drifted. The era closes on the realization the whole repo is named for: **the model usually complied, and "usually" was the whole problem.** The funerals in this era's title are the rules' — each one died as an instruction and was reborn as a mechanism in the eras that follow.

**What survived unchanged into later eras:** the relay, the price-matrix contract, the append-only knowledge base's earliest discipline (data is sacred; nothing deletes).
