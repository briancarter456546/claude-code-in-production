# A Bare `git commit` Harvested 16 Files Another AI Session Had Staged

**Keywords:** git commit shared index, bare commit dangers, concurrent Claude Code sessions, git staging area race, commit misattribution, session wrap collision, multi-agent git

**Incident date:** 2026-05-31, commit 13acae22 · **Internal refs:** task #1316 (this is its 5th distinct mechanism class); pathspec guard · **Status:** fixed by guard family; pathspec guard logged 17 blocks in a recent 12-day window

---

## What broke

[PM-008](008-broad-git-add-swept-another-sessions-files.md) covered the *staging* half of cross-session git contamination: broad `git add` sweeping strangers' files into the index. This is the *commit* half, and it's nastier because the command looks innocent.

Session A, wrapping up its work, ran a plain `git commit -m "notes update"`. No `-A`, no broad add — its own adds had been properly scoped. But **a bare `git commit` commits the entire index**, and the shared index contained 16 files that session B had staged minutes earlier and not yet committed. All 16 landed in session A's commit, under session A's message about an unrelated topic.

Session B, moments later, found its staged work gone — committed by someone else, under a label that would mislead every future reader. Session-end wrap-up rituals made this worse: two sessions wrapping near-simultaneously interleave *their closing commits*, which is exactly when both have things staged.

## How it was detected

Session B's wrap failed its own verification: files it had staged were no longer staged, yet appeared in HEAD — in a commit it didn't make. The forensic trail (commit `13acae22`) was unambiguous because per-session identifiers were already in commit message prefixes.

## Root cause

Git's index is process-shared state with no ownership model, and `git commit` without pathspecs means "commit whatever is in the index" — a correct semantic for one user, a race condition for N. This was the *fifth* distinct mechanism in the same family (task #1316 catalogs them): every git subcommand that implicitly reads "the whole index" or "the whole tree" is a fresh instance of the same bug wearing different clothes.

## Blast radius

16 files misattributed in permanent history; one session's wrap corrupted; and — the strategic cost — the realization that scoping *adds* had fixed nothing about *commits*, sending the team back to enumerate every implicit-breadth git operation.

## The fix

- **Pathspec-required commits:** a PreToolUse guard rejects bare `git commit`, requiring the `git commit -m "..." -- <paths>` form, which commits *only those paths* regardless of what else is staged. The block message teaches the form, so the fix travels with the refusal.
- **Stranger-file detection:** a second guard compares the commit's file set against this session's touched-files journal and refuses to bundle files the session never touched (with a reason-logged bypass for legitimate handoffs — and its own false-positive story, told honestly in [PM-023](023-blocked-from-committing-its-own-file.md)).
- **Wrap serialization:** session wrap-ups acquire a lock and stamp session IDs into commit prefixes, so closing rituals can't interleave invisibly.
- Later hardening moved per-session work onto **per-session index files**, shrinking the shared-state surface itself — which eventually produced its own spectacular near-miss, documented in [PM-004](004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md). Guards all the way down.

## Has the guard fired since?

Weekly. Recent 12-day audit window: pathspec guard **17 blocks**, stranger-file guard **19 blocks + 14 audited bypasses**, its pre-commit backstop **18 more**. Sessions still reach for bare `git commit` constantly — it's muscle memory from every tutorial ever written — and the guard converts each attempt into a correctly-scoped commit.

## Lessons for agent-driven development

1. **`git commit` without pathspecs means "commit everyone's work."** In shared-tree multi-agent setups, the bare form is never safe, even after you've fixed `git add`.
2. **Fixing one member of a bug family fixes one member.** Implicit-breadth operations (`add -A`, bare `commit`, `stash`, `checkout .`) are the same bug; enumerate the family or keep meeting it.
3. **Rituals synchronize; synchronized agents collide.** Wrap-up procedures made all sessions do the same git operations at the same time of day. Any shared ceremony needs a lock.
4. **Teach in the refusal.** A guard that blocks *and shows the correct form* converts an interruption into training; block messages are documentation with perfect timing.
