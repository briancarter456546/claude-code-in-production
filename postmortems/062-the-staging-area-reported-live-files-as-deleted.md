# Our repository's staging area listed 528 live files as deleted, and grew every night

**Keywords:** git index stale snapshot, staged deletions of files that exist, per-session GIT_INDEX_FILE wrapper, two staging areas one repo, git status disagrees between shells, phantom deletion, 0-byte index.lock stuck, pathspec-scoped commit, pre-commit frozen index guard, stale version banner false negative

**Incident date:** first found 2026-09-14, re-measured nightly through 2026-09-16, still reproducible 2026-09-20 · **Internal refs:** #2738 · **Status:** contained by pre-commit guards and a standing pathspec-only rule; the underlying drift is unfixed

---

## What broke

This repository has **two staging areas**, and one of them believes most of the project has been deleted.

Sessions here run concurrently in one working tree. To keep them from harvesting each other's staged work ([PM-011](011-bare-commit-swept-the-shared-index.md)), a wrapper gives every session its own private index and commits only from that. It worked: sessions stopped colliding. The consequence nobody costed is that **the repository's own index stopped being written to by anybody**, and a git index that is never updated is a snapshot of a moment that recedes.

What that looks like once it has receded far enough:

- **2026-09-14:** the shared index held **415 staged deletions**, 105 staged modifications and 8 files staged from no session's work.
- **2026-09-15:** 462 staged deletions. Measured against the current commit: **578 differences (465 deletions, 105 modifications, 8 additions).**
- **2026-09-16:** **528 staged deletions**; 645 staged entries in total.

Every one of those "deletions" is a file that **exists on disk and exists in the current commit.** The index simply does not know about the commits that created them. A plain commit from that index would have deleted 528 live files, including the guard code that is supposed to prevent exactly that.

**Still true on 2026-09-20.** Asked about two hook files written three days earlier, the shared index reports each of them as *both* `D` — staged for deletion — *and* `??` — untracked and unknown. The same files, in the same working tree, read from a session's private index: clean, no changes. Two staging areas, two irreconcilable answers, one filesystem.

## How it was detected

By a scheduled nightly review reading the staging area directly, three nights running — not by any session, because no session ever looks at an index it does not use.

Two things about the detection path are worth more than the finding:

**An audit was faked out by a phantom deletion.** A review examining recent guard work saw one of the guard files listed as deleted and reasoned about why someone had removed it. Nobody had. The file was on disk, complete, and running. **The stale index is not just a commit hazard; it is a false input to anything that reads repository state to reason about what exists.**

**A stale version banner produced two independent false negatives.** The wrapper printed a version string in its banner and carried the real version in a constant, and the two had drifted. Two separate readings — the operator's and an automated review's — concluded the fix was not installed, because the banner said so. It was installed. **A version string that is printed and a version string that is true must be the same string.**

The lock made it worse. A zero-byte lock file created at midday was still present twelve hours later, long after the last commit in the repository. An abandoned lock on the shared index means the very thing that might have refreshed it cannot run.

## Root cause

**A per-session index is a fork, and the canonical index was left as the one nobody merges.**

The wrapper's design has sessions read from and write to their own index, and there is no step, anywhere, that advances the shared one. This has been the behaviour since an early wrapper revision; the growth is not a bug in the wrapper, it is the wrapper working. What was never designed is a mechanism to keep the abandoned copy either **current or obviously invalid.** Left in between, it is a plausible-looking lie — the most expensive kind of state, and the same failure shape as [PM-027](027-the-database-that-lied-by-being-present.md) and [PM-047](047-the-phantom-database-had-five-months-of-real-work-in-it.md), where a stale store was dangerous precisely because it answered.

Two aggravating properties:

- **Drift presents as deletion.** An index that has not seen newer commits reports their files as removed, because from its point of view they are. So the failure mode of neglect is the most destructive possible commit.
- **Which index answers depends on how you ask.** One shell inherits the session's index; another path uses the repository's. Reading state through two tools is two different truths, and neither reports that the other exists.

## Blast radius

**No mass deletion was committed.** The classification is the reassuring part and was done on a copy of the index rather than the live one: of 578 differences, **all were recoverable** — 465 deletions of files present both in the commit and on disk, 113 modified or added blobs all already in history, **zero unique staged work**, zero unmerged paths.

The costs that were real:

- **A guard audit reached a wrong conclusion** from a phantom deletion, and a version audit reached a wrong conclusion twice from a stale banner. Bad state produces bad reviews, silently.
- **Every session carries a standing restriction:** commit only by naming paths explicitly. That is correct practice anyway, but here it is load-bearing rather than hygienic, and it will be followed imperfectly forever.
- **The repair is blocked on a permission classifier.** A heal script exists and dry-runs clean; the unattended run is refused because resetting a staging area is exactly the shape of destructive operation the fleet is not allowed to perform without a human. Correct, and the consequence is that the drift is still growing.

## The fix

**Containment is in place; the cure is not.**

- **Two pre-commit guards refuse this commit shape** — one that refuses to commit from a frozen index, and a backstop that refuses a commit containing files no session in this working tree touched. Both have **blocked this exact shape in live use**, on 2026-09-05 and 2026-09-10. Residual exposure: a commit that skips hooks.
- **Pathspec-scoped commits only**, for every session, as a standing rule until the drift is gone.
- **The index was backed up before anything touched it**, and the recoverability classification was run against the copy.
- **Proposed durable fix:** a scheduled heal that resets the shared index to the current commit, gated on the recoverability predicate the classification used — refuse to heal if anything unique is staged. It needs review and a human-approved path around the destructive-operation gate before it can run unattended.
- **Not yet done, and the actual root fix:** retire the second index. Per-session isolation is now available through real worktrees ([PM-057](057-the-isolated-worktree-was-isolated-from-the-fixes-too.md)), and keeping both mechanisms live means keeping this failure mode.

## Has the guard fired since?

The two pre-commit guards have each blocked the mass-deletion commit shape in real use, on the two dates above — this is one of the rare entries where the guard's evidence predates the writing.

Against that: the drift they are containing **grew from 415 to 528 staged deletions in three nights** and is still growing as of 2026-09-20, verified by the contradictory `D` and `??` readings on two files created after the last measurement. **A containment whose subject grows monotonically is a deadline, not a fix.**

## Lessons for agent-driven development

1. **Every fork needs an owner or an execution.** Copying state to isolate writers is sound; leaving the original readable, writable and unmaintained is how you get a confident wrong answer. Either keep it current or make reading it fail loudly.
2. **Understand your neglected state's failure direction.** A stale index does not degrade toward "empty" or "unknown" — it degrades toward "delete everything new". Ask of any cache or snapshot: if this goes stale and something acts on it, what does it do?
3. **Two sources of truth for the same question will be consulted by different tools, and neither will mention the other.** If two paths to `status` can disagree, every audit, hook and agent reading that status is sampling at random.
4. **Agents reason from repository state as if it were fact.** A phantom deletion did not cause a bad commit; it caused a bad *conclusion*, which is harder to notice and propagates further.
5. **Print the version you actually are.** A banner that lies about its own version turns every "is the fix installed?" check into a coin flip, and it made two independent auditors wrong in the same way.
6. **When the safe repair is blocked by a safety gate, that is a scheduling problem, not a reason to bypass the gate.** The gate was right. What was missing was an approved path for an operator-sanctioned destructive repair — and without it, containment runs indefinitely.
