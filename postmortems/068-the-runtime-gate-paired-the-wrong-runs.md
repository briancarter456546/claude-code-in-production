# We Rebuilt the Speed Gate to Block on Measured Runtime — the Measurement Paired the Wrong Runs

**Keywords:** measured signal instead of heuristic, runtime history keyed by content hash, PreToolUse PostToolUse pairing, start marker newest file mtime, concurrent sessions measurement contamination, guard never blocked, allowlist share of gate fires, gate audit follow-up, wall clock attribution bug

**Incident date:** measured 2026-09-27 over the log's 74-day span, 73 of which carry rows · **Internal refs:** gate-audit kill list; runtime-history classifier · **Status:** open — gate is advisory-only in practice ; 17,750 fires, 0 blocks, and its one threshold crossing is a mispaired record

---

## What broke

This is the sequel to [PM-015](015-eight-thousand-fires-zero-true-blocks.md). That audit found a pre-run speed gate that judged cost from **code shape** — nested loops, no parallelism — and in ~6,900 fires had never once blocked a genuinely slow run. The fix was to stop guessing and start measuring: the gate was rebuilt to block **only** on recorded median runtime over 10 minutes, advise between 2 and 10 minutes, and treat the static score as an advisory guess that can never block. A companion `PostToolUse` hook records actual wall-clock time so the gate "gets smarter over time."

PM-015 closed by saying the rebuilt gates "fire rarely and advisorily." Measured across the current audit log's 74-day span (73 days carry rows), the first half of that sentence is wrong and the second half is more literal than intended:

All counts below were read on 2026-09-27; the log is live and still growing.

- **17,750 fires** — **median 138 per day**, mean 243, range 2 to 1,336. Not "rarely"
- **0 blocks.** Every row in this log carries the rebuilt gate's schema; the old gate's ~6,900 fires predate the log's first record and are inherited from PM-015, not re-verified here
- **4 fires** ever reached even the 2-minute advisory. 618 more produced the static-guess advisory
- **9,444 fires (53%)** resolved to `bypass` — and every one of them is an **allowlist** hit, not a human exception. The top three are internal CLIs called constantly: a task-tracking CLI (5,735), a knowledge-base CLI (2,798), a project-state CLI (464)
- **0 of 9,444** bypasses came from the documented inline environment variable — the same silence [PM-014](014-the-escape-hatches-that-never-existed.md) explains

The gate is cheap (median 0 ms, p90 100 ms, 608 seconds of hook time across all fires), so this is not the latency tax PM-015 found. It is something else: **the measured signal the rebuild depends on does not measure what it claims.**

## How it was detected

By reading the runtime-history store directly instead of trusting the gate's decisions, during a scheduled guard-ledger review. Two queries did it.

First, the store's shape. 3,967 recorded runs, **1,160 distinct content hashes**, **399 distinct script names**:

- **223 of the 399 scripts have more than one hash** — one has 43. History is keyed by file content, so *every edit starts that script's history over from nothing*. The scripts the gate exists to catch are the ones under active development.
- **760 of the 1,160 hashes have exactly one recorded run.** The gate takes a median of the last 10 runs; for two-thirds of hashes that median is a single sample.
- **13 hashes** have a median above the 2-minute advisory line. **Exactly one** is above the 10-minute block line.

Second, the outliers. Five recorded runs exceed 1,000 seconds. Four are impossible and the fifth is implausible:

| recorded wall time | what it was attributed to |
|---|---|
| 36,968 s (10.3 h) | a session-bookkeeping writer |
| 34,978 s (9.7 h) | a mail-notification module |
| 32,988 s (9.2 h) | a second session-bookkeeping writer |
| 11,218 s (3.1 h) | the same mail-notification module |
| 8,716 s (2.4 h) | a long-lived service script |

The mailer takes seconds. And the single hash whose median crosses the 10-minute block line is one of these rows — the 8,716-second one. Its script has **seven recorded runs across three content hashes: 1.65 s, 2.97 s, 3.45 s, 8.50 s, 13.84 s, 18.52 s — and 8,716.22 s.** The two records sharing the crossing hash are 3.45 s (02:05 UTC) and 8,716.22 s (04:32 UTC, i.e. exactly 2h27m later), giving a median of 4,359.8 s.

**The gate's only block path has been armed exactly once in 74 days, by a number that is almost certainly a mispaired marker.** Had it fired, it would have been a false positive on a script that runs in seconds.

## Root cause

The pairing rule. The pre-run hook writes a start marker at `runtime_marks/<content-hash>.start`. The post-run hook then does this:

```python
def _newest_unconsumed_mark():
    """Most recently written .start mark that hasn't been recorded yet."""
    candidates = list(RUNTIME_MARKS_DIR.glob("*.start"))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]
```

It takes **the newest unconsumed marker on disk** — not the marker belonging to the command that just finished. There is no session scoping, no match against the finished command, no correlation id.

On a single-session machine that is almost always right. On a machine running 7–12 concurrent agent sessions it is routinely wrong:

- Session A starts script X → marker X written
- Session B starts script Y → marker Y written, now newest
- Session A's script X finishes → the recorder consumes marker **Y** and writes `now - Y.started_at` as **Y's** runtime

The wrong duration lands against the wrong script. Worse, an unconsumed marker can sit for hours until some unrelated completion picks it up — which is exactly how a mailer that runs in seconds acquires a 9.7-hour record. A secondary defect compounds it: the marker path is keyed by content hash and **overwritten**, so two concurrent runs of the *same* script destroy the first one's start time.

The deeper cause is the one worth transferring. PM-015's correct lesson was *replace the proxy with a measurement*. What went unexamined was **whether the measurement pipeline was sound under the concurrency the system actually runs at.** A start/finish pairing is a distributed-systems problem the moment more than one thing runs at a time, and "newest file wins" is the same defect that let a test file win a latest-file glob and get emailed as production output ([PM-031](031-the-smoke-test-that-emailed-the-boss.md)). We replaced a bad heuristic with a good metric collected by a bad heuristic.

## Blast radius

- **The routing rule the gate enforces is unenforced.** The standing rule — anything over 10 minutes moves to the heavy-compute host — has never once been enforced by this gate in 74 days. Routing has been entirely manual, while a control that looks like it covers routing sat in the configuration.
- **The history store is contaminated, not merely thin.** Any future tuning built on it inherits the bad pairings. The 13 "slow" hashes cannot be trusted without re-derivation.
- **A published claim of ours was wrong.** PM-015 said the rebuilt gates "fire rarely and advisorily." They fire a median of 138 times a day, 17,750 times over 73 days. That sentence is superseded by this measurement, and the correction belongs here rather than quietly in an edit.
- No wrong results, no data loss, no false blocks — the gate has never blocked anything. The cost is the same one this repo keeps finding: **unearned confidence that a class of problem is handled.**

## The fix

Filed, published open at the point of discovery:

- **Pair by identity, not recency.** The start marker must carry a correlation id (session id + invocation nonce), and the post-run hook must consume *that* marker or none at all. An unmatched completion should record nothing and log a miss — a missing record is honest; a mispaired record is a lie that gets averaged in.
- **Never overwrite a live marker.** One marker file per invocation, not per content hash.
- **Quarantine the existing store.** Records whose wall time is implausible for their script (and every record written while more than one marker was outstanding) cannot be repaired after the fact; they can only be set aside before anything else reads them.
- **Then re-ask whether content-hash keying can work at all.** With 223 of 399 scripts carrying multiple hashes, a measured-runtime gate may be structurally blind on actively edited code. If so, the honest answer is that the gate stays advisory and the routing rule is enforced somewhere it can be — at dispatch, not at launch.
- **Add to the gate audit:** a gate whose block path has never been reached needs its *threshold* checked against the distribution of its own signal, not just its fire count. Ours had exactly one crossing in 74 days and it was noise.

## Has the guard fired since?

Never, in the blocking sense — 0 blocks in 17,750 fires. It has produced 4 measured-slow advisories and 618 static-guess advisories.

The honest scoreboard against PM-015: the old gate was ~6,900 fires and zero true blocks. The rebuilt gate is **17,750 fires and zero blocks**, at much lower latency, with a measured signal that is mis-attributed under concurrency. We fixed the cost and the reasoning; we did not fix the outcome, and the audit that was supposed to catch that had already been run once and closed.

## Lessons for agent-driven development

1. **"Replace the heuristic with a measurement" is only half a fix — audit the measurement pipeline too.** We validated the decision rule and never validated the data collection feeding it.
2. **Any start/finish pairing needs a correlation id.** "Newest file wins" and "latest by mtime" are the same bug in two costumes, and both break the instant two things run at once. This is the third time that shape has appeared in our record.
3. **An unmatched measurement should be dropped, not guessed.** A missing runtime record leaves the gate honestly ignorant. A mispaired one puts a 10-hour number on a 10-second script and arms a block path with it.
4. **Keying history by content hash means every edit erases the evidence.** For a gate whose targets are under active development, that can make the block path structurally unreachable — check the distribution of your own signal before claiming the threshold works.
5. **Re-audit the fixes, not just the originals.** Our standing policy scores guards against their own logs; this gate had already passed through that audit once, been rebuilt, and then went 74 days without anyone asking the same question again. **A guard is not permanently redeemed by the audit that fixed it.**
6. **Publish the correction where the claim lives.** PM-015's closing line calls the rebuilt gate's firing rare; it runs 2.6x the fire volume of the gate that audit condemned, at a median of 138 a day. Saying so in the follow-up is cheaper than being quietly right later.
