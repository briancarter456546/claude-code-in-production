# The agent diagnosed a bug from the code's comments, built a repair tool, and nearly deleted 20 other sessions' staged work

**Keywords:** AI agent misdiagnosis, stale code comments, comment block vs executable code, git index corruption, per-session git index, repair tool blast radius, human approval gate, adversarial review caught the premise, retraction

**Incident date:** 2026-09-05 (claim 15:05, retraction 15:48) · **Internal refs:** #2584, #2586, #2061 · **Status:** never executed against live state — blocked by an approval gate, then retracted; the misleading log message behind the six-week version of this is fixed with a regression assertion

---

## What broke

Concurrent sessions in this system share one repository, so each session gets its **own git index file**, re-seeded from HEAD by a wrapper on every git call. For six weeks the operator's standing complaint was that "git keeps eating work."

On 2026-09-05 at 15:05 a session committed what looked like the answer, with measurements attached: **20 of 28 live session index files permanently frozen**, pinned by 115 unrecoverable entries that reduced to only 13 distinct files, holding 3,597 paths at a pre-HEAD version. The mechanism cited: the wrapper's re-seed is all-or-nothing, so one entry it cannot safely drop makes it skip the whole index forever. A repair tool was written, defaulted to dry-run, and **rehearsed twice against copies of all 28 live indexes** (20 frozen to 0 frozen, 115 entries dropped, 13 blobs saved to disk first, 225 KB). The live run — which writes into 20 *other sessions'* index files — was blocked by the approval gate, pending the operator.

At 15:48, 43 minutes later, the same session retracted all of it.

**The diagnosis had been read out of the wrapper's comment block, not its executable code.** That comment block documents the previous two versions' decision table, which really does say *any entry unrecoverable, skip and warn*. The live version does the opposite: its preserve-and-re-seed branch advances the index to HEAD and puts the unrecoverable entries straight back, so their blob keeps its only index reference. That branch had been added under **the very task the session had checked out**, and its own comment names, as the disease it exists to cure, the exact stale-index case the session cited as evidence.

## How it was detected

The operator asked for an external adversarial review of the direction change before approving the live run. The file-reading review seat returned **REJECT with 8 findings**, one of which was the premise itself.

The session then ran the check it should have run first — a *triggered* proof rather than a reasoned one: copy the worst-classified index (193 commits behind, 11 unrecoverable entries) to a synthetic session id and run the real wrapper against it. Output: *"11 staged entries hold a blob that is in neither HEAD nor the worktree. PRESERVING them across the re-seed"*, then *"your session index was stale; advanced it."* Verified after: the marker equalled HEAD and all 11 entries were still present with their original blob hashes.

Those 20 indexes were never frozen. They belong to **idle or dead sessions that have not made a git call since** — and the classifier could not distinguish *stuck* from *untouched*.

## Root cause

Three layers, each worth separating.

1. **Comments document a past version; only the executable branch is the system.** The wrapper carries a long, well-written, versioned comment history — which is exactly what made it credible enough to diagnose from. The more thorough a file's comments, the better the trap: they are fluent, structured, and describe a system that no longer exists.
2. **The classifier had no negative control.** "Index behind HEAD" was read as "index cannot advance." An index that is behind because nothing has run is observationally identical until you *make* something run. The fix for a state claim is to trigger the transition, not to measure the state harder.
3. **The six-week prior misdiagnosis had the same shape one level down: a log message that misdescribed its own behavior.** The old re-seed printed *"N path(s) held staged content and were unstaged"* — which reads as *another session's work landed in yours*. It never meant that; it meant *your* index's older copy of a file someone else had since committed. That phrasing is the likeliest reason the original report sat misdiagnosed for six weeks, and it misled a fresh investigation again on 2026-09-01 until the hashes were checked against the seed commit (6 of 6 matched it; zero foreign blobs).

## Blast radius

**Counterfactual, and large.** The repair tool would have deleted, across 20 other concurrent sessions' index files, precisely the entries the wrapper deliberately preserves. Rehearsal did not catch it: rehearsal validated that *the tool did what its author intended*, against copies — the wrong question when the intent rests on a false premise. The two things that actually stopped it were the **approval gate on writes into other sessions' state** and the **external review**.

Actual cost: about a day of investigation aimed at the wrong mechanism, and one confidently-worded commit that a future reader would have believed.

What the same investigation *did* establish, verified afterward with a separate script, is the real and much smaller harm: the re-seed sends every modified staged entry through its re-add path and drops it whenever HEAD moves — and with 7-12 concurrent sessions, HEAD moves constantly. The drop log holds 2,346 lines / 367 distinct blob-path pairs since 2026-09-01; cross-checked against all 90,252 reachable objects, **24 of those 367 blobs exist in no commit anywhere**, of which roughly 21 are other sessions' real staged content. Precision matters here: every one of those paths is **still on disk**. What was silently lost is the *staging* — the recorded intent to commit that exact version — not the bytes. The harm is a session believing something is staged when it is not, and committing without it.

And the contrast that killed the scarier theory: a scan of the last 900 non-merge commits (2026-07-21 to 09-05) found **zero** commits setting a path back to an older blob and **zero** resurrections of a recently deleted path. The silent-revert story everyone believed has no instance in the history. Separately, 803 of 825 evaluations by the relevant guard were pathspec-scoped commits — the project rule requiring pathspec commits had already removed the path the revert theory depends on.

## The fix

- **The repair tool was disarmed in place** rather than deleted, with the retraction written into the commit message that carries it, so the wrong diagnosis and its refutation are adjacent in the history.
- **The misleading message was reworded** in the wrapper, and its self-test now asserts the ownership clause of the new wording, so the phrasing cannot silently regress.
- **The all-or-nothing re-seed was already fixed** by the preserve-and-re-seed branch — the thing the session had misread as broken.
- **The strategic conclusion changed direction.** The residual harm is a property of the shared-HEAD design, not of any index file, so it cannot be repaired by rewriting indexes. It is an argument for finishing the migration to isolated worktrees rather than for maintaining the mechanism being retired.

## Has the guard fired since?

The approval gate that blocked the live run is the guard in this story, and it fired once, correctly, against a tool its own author had rehearsed twice and believed in. That is the only clean data point here. The reworded-message assertion passes in the self-test and has not been exercised by a real regression yet — an untested assertion is a hypothesis.

## Lessons for agent-driven development

1. **Agents diagnose from the most readable artifact, and comments read better than code.** Point the agent at the branch that executes, and treat any diagnosis whose only citation is a comment block as unsourced.
2. **A state measurement is not a mechanism claim.** "20 of 28 are behind" does not imply "20 of 28 cannot advance." Trigger the transition on one instance and observe it; a triggered proof beats any amount of counting.
3. **Rehearsal validates the tool, not the premise.** Two clean dry-runs against copies produced total confidence in a tool built on a false diagnosis.
4. **Put the human gate where the blast radius is, not where the risk feels high.** The gate that saved this was scoped to a structural property — *writes into other sessions' state* — and evaluated it regardless of how confident the author was.
5. **An error message that misdescribes its own behavior costs weeks.** This one cost six, then nearly caused a destructive repair. Message wording is a diagnostic input and deserves the same regression test as behavior.

Related: [PM-011](011-bare-commit-swept-the-shared-index.md) and [PM-008](008-broad-git-add-swept-another-sessions-files.md) are the shared-index collisions this wrapper exists to prevent; [PM-004](004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md) is the wrapper's own near-miss, and its amendment is the same "the class was not closed" shape. [PM-038](038-the-validation-that-never-happened.md) and [PM-048](048-the-agent-audited-itself-and-got-the-headline-numbers-wrong.md) are the same family: confident, measured-sounding claims that nobody had triggered.
