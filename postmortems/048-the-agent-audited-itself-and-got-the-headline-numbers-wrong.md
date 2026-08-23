# The Agent Measured Its Own Session and Got Three Headline Numbers Wrong — One Reviewer Believed Them, One Re-Counted From the Raw Transcript

**Keywords:** AI agent self-measurement, transcript JSONL usage duplication, token accounting error, context compaction efficiency, independent audit raw data, reviewer given summary vs raw, churn estimate, Stop hook cost, multi-model review disagreement, measurement artifact

**Incident date:** 2026-08-20 · **Internal refs:** session efficiency audit bundle + two reviewer verdicts (archived in the private inbox); the operating-facts file it produced · **Status:** corrected same night; the measurement method (count usage once per API response, not once per content block) is now the standing rule for any transcript-derived number; no hook yet — an untested rule is a hypothesis.

---

## What broke

The operator asked a long-running session to audit its own efficiency before and after a context compaction, and to send the audit to two independent reviewers. The session computed its numbers from the harness's transcript file (one JSON record per content block) and wrote the bundle. Its headline findings:

- Pre-compaction output: **2,190,078 tokens** in 7.33 hours; post-compaction 196,229 in 6.1 hours — a **9.3x** rate gap.
- **67 consecutive identical tool calls** pre-compaction ("retries_same_tool").
- **25 Stop-hook blocks** pre-compaction versus 7 post.
- 27 operator messages pre, 18 post.

All four were wrong, and every error flattered the same story: the pre-compaction phase had been a thrashing, loop-prone token furnace.

**Reviewer 1** received the bundle and the session's data table. It accepted the numbers and reasoned from them with confidence: "We know for a fact that 67 consecutive identical tool calls occurred... a catastrophic loop." It estimated 40–50% of pre-compaction spend was churn, declared the Stop-hook guards "a massive token tax... absolutely not paying for themselves," and recommended downgrading them to warnings and adding a hard loop-breaker after three identical failures.

**Reviewer 2** was given the raw transcript instead of the summary and recomputed everything. Its verdict opened: "three of the bundle's headline numbers are wrong, and all three flatter the pre-compaction phase's apparent productivity or exaggerate the gap."

## How it was detected

By reviewer 2, only because it had the raw record. Nothing in the session's pipeline could have caught it: the session's own count was internally consistent, the reviewer fed the summary agreed with it, and the conclusions (thrashing, loops, hooks too expensive) were exactly the kind of thing an operator running a large hook stack is primed to believe.

## Root cause

Three independent measurement errors, each a property of the instrument rather than the session:

1. **Per-block usage duplication.** The harness writes one transcript record per content block, and every record from the same API response carries an identical copy of that response's `usage` object. Summing `output_tokens` over records multiplied each response by its block count. 264 of 342 API responses were split across 2–20 records. Real pre-compaction output was **501,817 tokens** (inflation 4.36x); real post was **81,171** (2.42x). The inflation was *uneven* because pre-compaction responses carried more tool calls per response (2.00 vs 1.12), so the artifact alone roughly doubled the apparent gap.
2. **"Identical" meant same tool name.** The session counted runs of consecutive calls to the same tool — Bash after Bash — and labeled them retries. Runs of consecutive calls with byte-identical input: **zero**, in either phase. The 67 was a description of normal sequential shell work.
3. **Counting the wrong record type.** Stop-hook *blocks* are the records that force a re-issue of the closing message. Counted correctly: **6 pre, 7 post** — the post phase was blocked more often while doing one-fifth the tool calls (19% vs 32% per stop). The session's 25 had counted something else; its operator-message count had included background task-completion notifications and the compaction summary itself.

Corrected decomposition of the "9x": remove the duplication artifact → 4.5x; remove the operator's idle time (3.98 of 7.28 pre hours, 5.16 of 6.02 post) → 1.62x; normalize by tool-call throughput → **1.07x**. Output tokens per tool call were 996 pre and 933 post. None of the 9x was pre-compaction being less efficient per action.

Fair churn, recounted by sorting all 504 pre-compaction tool calls by what happened to their output: 22 blocked before running, 7 failed on real bugs, ~15 retried with a tweak, 19 on work later invalidated — **63 of 504, 12.5%**. Reviewer 1's 40–50% had been built on the phantom loop.

What reviewer 2 *did* find that the session had missed: cache reads per tool call rose from 39k at 09:00 to 728k at 15:00 — an 18x increase in the price of each action as context grew; the last three hours before compaction consumed ~60% of the phase's context bill for 36% of its tool calls. And the post-compaction phase had silently filed seven tasks into the wrong database ([PM-047](047-the-phantom-database-had-five-months-of-real-work-in-it.md)). Context size, not phase, was the efficiency variable — and compaction had cost one correctness regression nobody had noticed.

## Blast radius

Had only reviewer 1 been consulted, the operator would have had a confident, well-argued recommendation to weaken the Stop-hook guards and add a loop-breaker for loops that did not exist, grounded in numbers off by 4x. Actual cost: one evening, two reviewer runs, and the re-filing of seven tasks. The near-miss is the story.

## The fix

- **Corrected numbers on the record:** the session's operating-facts file (the document a post-compaction continuation is told to read first) now carries the recounted figures and the finding that context size, not phase, drives cost — so the refuted numbers cannot be re-derived from the summary and re-believed.
- **Measurement rule, stated here because it is not yet enforced anywhere:** any number derived from the transcript counts `usage` once per API response (dedupe by response id), distinguishes identical-input retries from same-tool sequences, and counts Stop-hook blocks by the re-issue record, not by hook output. Prose only; no script or hook.
- **Review rule, already in force for design critiques, now extended to self-audits:** a reviewer that only receives the summary can only review the summary. For any claim about the session's own behavior, at least one reviewer gets the raw record.
- **The seven tasks** were re-filed through the correct path the same night.

## Has the guard fired since?

There is no guard yet; the rule is prose. The one subsequent test is that this postmortem's numbers were taken from reviewer 2's raw-transcript recount, cross-checked against the session's bundle for the *claimed* values, and not recomputed by the session that wrote them. An instrument that has been wrong once is not trusted on its own word about having been fixed.

## Lessons for agent-driven development

1. **An agent measuring itself uses the same instruments that misled it.** The transcript's record shape is a harness detail the agent had no reason to know; the error it produced was invisible from inside the count. Self-measurement needs an outside recount, not a second summary.
2. **Give at least one reviewer the raw data.** Two reviewers with the same summary are one reviewer with two voices. The only reviewer that refuted the numbers was the one that could not see the session's conclusions about them.
3. **Suspect errors that all point the same way.** Four independent counts were wrong and all four exaggerated the same narrative. Correlated error is a fingerprint of a shared cause — here, one record schema — not of four coincidences.
4. **"Identical" is a claim about inputs, not names.** Loop detection keyed on tool name will find loops in any session that does sequential shell work. Byte-compare the input or do not call it a loop.
5. **Measured cost of guards beats felt cost.** The Stop-hook "tax" was 13 blocks across two phases, not 32, and the phase that was blocked more was the cheaper one. Guard-cost arguments get the same evidence standard as guard-benefit arguments ([ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)).
