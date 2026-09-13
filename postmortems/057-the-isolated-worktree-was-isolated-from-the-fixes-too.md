# Moving an agent session into a git worktree isolated it from the fixes too: an empty phantom database, pre-fix hooks, and two staging areas

**Keywords:** git worktree per agent session, linked worktree stale branch, sqlite connect creates empty database, gitignored data store __file__ parent, worktree falls behind main, unattended git merge race, per-session git index wrapper, GIT_INDEX_FILE worktree, Claude Code concurrent sessions isolation

**Incident dates:** 2026-09-08 to 2026-09-12, all during the first real worktree session of a staged migration · **Internal refs:** #2631, #2685 · **Status:** three defects fixed, one mitigated by a report-only schedule; six call sites of the first defect still open

---

## What broke

[PM-053](053-the-approval-landed-in-a-copy-the-guard-never-read.md) described the dry run of a migration that gives each concurrent session its own **git worktree** instead of one shared checkout. That dry run found one defect. The first *real* session moved into a worktree — a single long-running session, observed on purpose — found three more within four days, each a different way isolation cut the session off from something it needed:

1. **The first knowledge-base command opened an empty database and reported it as normal.** The store reported `next node id: 1` against a real store of 1,969 nodes. No error.
2. **Two days later the worktree was 32 commits behind main** and was running every fix landed in that time as its pre-fix code — including its own pre-commit hooks.
3. **The per-session git wrapper split the session across two staging areas**, one of which the isolation probe could not see.

## How it was detected

Each by a scheduled observation of the pilot, not by a guard:

- (1) on the very first command of the pilot, because the output said `store: UNNAMED` where every other session sees a named store.
- (2) by re-running the worktree's 8-check isolation probe, which had passed 8 of 8 at creation and now passed 6 of 8. Observation had been promised daily and had not happened for two days.
- (3) by an external code review of the migration tool, then verified in place by comparing file sizes and timestamps of the two index files in the worktree's git directory.

## Root cause

**(1) Gitignored data stores resolved from the script's own directory, and sqlite creates on read.** The knowledge base is deliberately not in git, so a new worktree has no copy. The CLI located the store relative to its own file — which, run from a worktree, is the worktree. `sqlite3.connect()` does not fail on a missing file; it creates one. So a read silently produced a new empty store, and a write would have put a finding into a file nothing else ever reads. This is the same class as the ack store in PM-053, now on record in four places (session state, approval markers, a price cache, the knowledge base).

**(2) A worktree branch never moves on its own.** In a shared checkout, a fix committed by any session is live for all sessions the moment it lands on disk. A worktree pins its branch where it was created. The pilot's branch fell 32 commits behind in two days; five hook and settings files differed from main by 393 lines, and one hook added on main did not exist in the worktree at all. The consequence had already started: the pre-fix copy of the review-ledger code had created a **private ledger inside the worktree**. It held zero reviews, so nothing was lost — but a review run there would have been invisible to the budget and escalation logic that reads the real one.

**(3) The wrapper did not know worktrees exist.** This system routes git through a wrapper that gives each session its own index file ([PM-011](011-bare-commit-swept-the-shared-index.md)). A linked worktree already has a private index natively. The wrapper built a session index inside the worktree's git directory anyway, so two indexes existed and diverged — by 10 entries when measured. The isolation probe strips git environment variables before checking, so it saw the native index and passed while ordinary commands used the other one.

**The deeper cause, common to all three:** a shared checkout gave these components *three kinds of sharing for free* — shared data files, shared current code, shared git plumbing — and nothing in any of them declared that it depended on that. Isolation removed all three at once.

## Blast radius

Small, because the migration moved one session and watched it:

- **No data lost.** The phantom knowledge base (about 110 KB) was removed before any write; the private ledger had zero reviews; the worktree's private audit log held 32 rows, all test fixtures.
- **Two days of fixes did not apply** to one session's code path, including hook changes.
- **The counterfactual** is what the observation schedule existed for: every one of these would have hit every migrated session at once, silently, and the knowledge-base one loses data on the first write.

A related measurement from the same week shows why the wrapper still matters: a commit issued through a shell that bypasses the wrapper used the shared index and **tried to bundle files owned by 30 different sessions**. A separate pre-commit backstop refused it. The wrapper protects only commands routed through it; the backstop protects regardless.

## The fix

- **(1)** The knowledge-base CLI resolves the store from an explicit override, then the *primary* checkout (found by reading the worktree's `.git` pointer file and its `commondir` — two file reads, no subprocess), then its own directory; and it prints a loud warning whenever the resolved store is absent, so a wrong path can never again look like an empty-but-fine store. The resolver is deliberately copied rather than imported: a stale worktree carries a stale shared library, and a resolver that falls back silently inside it reproduces the bug. Six other call sites of the same shape remain open under a tracking task — one of them a citation-checking guard that returns "nothing to verify" when the store file is absent, which is fail-open.
- **(2)** A keep-current job merges main into lagging worktrees. It was first built to merge unattended; an external review **rejected** that, because the only signal that a session is idle is a heartbeat written on prompts and edits, not during long reasoning or long commands — a hint, not a lock — and git cannot protect a file being written concurrently. No lock exists that sessions honor, so this is not fixable inside the script. The scheduled run is now **report-only**: probe, record, alert a human; merging stays a deliberate manual command. A manual merge restored the pilot to 8 of 8 after four stray files created by pre-fix code were moved to quarantine, not deleted.
- **(3)** The wrapper now detects a linked worktree (its git directory contains a `commondir` file; the primary's does not) and steps aside, running real git with no session index. Self-test 30 of 30, with a negative control: in a fresh temp repo and worktree, the old version created two session indexes and the staged file did not land in the native index; the new one created none and it did.

## Has the guard fired since?

The report-only keep-current job is registered and running daily as of this week. Two days after the manual merge, a probe run measured the pilot worktree **48 commits behind main again** (2026-09-12). The drift has not stopped; what changed is that it is now measured on a schedule instead of discovered by accident. The wrapper's worktree step-aside has its test matrix but only one real worktree to run in. The migration remains gated.

## Lessons for agent-driven development

1. **Isolation removes every implicit share at once.** Before moving agents into worktrees, containers, or sandboxes, list what they were sharing *by accident* — data files, current code, tool plumbing — because nothing declares those dependencies.
2. **Never let "open" create.** A store opened by a library that creates missing files will report an empty-but-valid result for any wrong path. Check existence and fail loudly before connecting.
3. **A worktree is a fork of your guardrails, not just your code.** Hooks and pre-commit checks inside it are the versions from its branch point; every safety fix since then does not exist there.
4. **A heartbeat is not a lock.** Liveness written on some events cannot make an unattended mutation of a live session's files safe. When no real lock exists, schedule the detection and leave the mutation to a human.
5. **Probes that sanitize their environment test a different world.** The isolation probe stripped the very variables that caused the defect, and passed.

Related: [PM-053](053-the-approval-landed-in-a-copy-the-guard-never-read.md) (the dry-run instance of the same class), [PM-011](011-bare-commit-swept-the-shared-index.md) and [PM-004](004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md) (why the wrapper exists and how it failed before), [PM-027](027-the-database-that-lied-by-being-present.md) (a database that lied by being present — this one lied by being created).
