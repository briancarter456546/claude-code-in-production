# The guard kept blocking and told the agent to run the approval it had just run — into a copy nothing reads

**Keywords:** git worktree isolation, hook path resolution, __file__ parent repo root, marker file ack, gitignored state directory, Claude Code hooks absolute path, CLAUDE_PROJECT_DIR, guard block loop, primary checkout vs linked worktree

**Incident date:** 2026-09-05 · **Internal refs:** #2631, #2648 · **Status:** fixed before rollout (root resolution replaced); found in a dry run, never hit a working session

---

## What broke

Several guards in this system are unblocked by a **marker file**: to create a new tool, or to run a destructive operation, the agent writes a small JSON ack — lane, reason, expiry — with a helper script, and the guard reads it and allows the call. Marker files exist here precisely *because* environment-variable bypasses do not reach hook processes ([PM-014](014-the-escape-hatches-that-never-existed.md)).

While piloting a migration that gives each concurrent session its own **git worktree** instead of a shared checkout, the pilot session hit a guard, wrote the ack, and was blocked again. And again. The guard's message told it to write the ack. The ack existed. The guard could not see it.

## How it was detected

In the Phase 0 dry run, before any working session was moved — the migration's rollout plan required running each guard end to end from inside a worktree. Measured, in order:

1. Ack issued with the working directory inside the worktree - the marker landed **in the worktree's** store.
2. The guard's own dry-run mode, invoked from the worktree, **ALLOWED** — it found the local marker.
3. The actual tool call, targeting a file in the primary checkout, was still **BLOCKED**.
4. Re-issuing the identical ack from the primary root unblocked it immediately.

Step 2 is the reason this would have been miserable to debug in a real session: the guard's own diagnostic agreed with the agent, and disagreed with the guard.

## Root cause

Two path-resolution rules that disagree, in code nobody thought of as related.

**The writer resolves from its own file.** The ack helper set its repository root to the directory of the script itself. A session whose working directory is a worktree invokes the helper *by bare name*, so the interpreter resolves the **worktree's** copy of the script, whose parent is the worktree — and the marker is written there.

**The readers resolve from an absolute path fixed at registration.** Claude Code launches hooks by the command string in its settings file. Verified: **56 hook command entries, every one an absolute path into the primary checkout**, and the variable the harness offers for project-relative invocation appears **zero times**. So inside a worktree session, every hook that fires is the *primary's* file, and any root it derives from its own location is the primary — while the working directory, and every path in the tool input, belongs to the worktree.

Writer resolves relative to the caller. Reader resolves relative to the primary. In a shared checkout those are the same directory, so the defect is invisible until the day isolation is introduced.

**Compounding it:** the ack directory is gitignored, deliberately — approvals are local, per-machine, and must never travel in a commit. So a freshly created worktree starts with an **empty** ack store while the primary holds hundreds of markers. Every previously granted approval appears revoked, all at once, for reasons the block message does not mention.

## Blast radius

Zero in production: caught in the dry run that existed to catch it. The counterfactual is the interesting part — this would have fired **on day one for every session moved into a worktree**, on four separate guards the helper serves, in the form hardest for an agent to escape: a block whose remedy is the thing the agent already did. That is the [PM-021](021-alarm-fatigue-by-the-numbers.md) failure mode with an infinite retry loop attached, and the likely session behavior is not "debug the path resolution" but "disable the guard."

It is also the **third instance of one class in three weeks**: shared coordination state resolving to a private copy inside a worktree. The other two were the cross-session session-state directory and a data cache. Same shape, same fix, found separately each time.

## The fix

- **The helper resolves the primary repository root explicitly** instead of using its own file's parent, so an ack issued from anywhere lands in the one store the guards read.
- **The primary root is resolved without spawning a subprocess**, because hooks run under a seconds-level budget: in a linked worktree the repository pointer is a *file* whose contents name the git directory, and that directory's common-dir pointer resolves to the primary. Two file reads, no process spawn, stable across a decade of git versions. The fallbacks where that layout does not hold are declared unsupported rather than silently guessed.
- **The rule was generalized and written down:** coordination state is shared across worktrees **by path resolution in code, never by a filesystem link inside the worktree.** An earlier design placed a Windows junction inside each worktree instead; it was rejected after a six-way delete test showed several routine tools delete *through* a junction — including one traversal not documented anywhere upstream.
- **The remaining guards that normalize tool-input paths were put on the Phase 0 checklist**, since a worktree session hands them paths with an unfamiliar prefix. One such guard blocked a legitimate write during the review, which is how that item got on the list.

## Has the guard fired since?

The repaired helper resolves to the primary root in the current source, and the end-to-end sequence above now allows at step 3. What has *not* happened is a full rollout: the migration is still gated, and until several sessions run for days inside worktrees, "no path-resolution defects remain" is a claim supported by three found instances and one checklist, not by uptime.

## Lessons for agent-driven development

1. **Writers and readers of shared state must resolve their root the same way, and it should be one function.** Two independently reasonable conventions — "relative to my file" and "absolute at registration" — are identical until the day you introduce isolation, then they are silently opposite.
2. **Know how your harness launches hooks.** Absolute paths captured at registration mean hooks are *not* relative to the working directory; anything that assumes otherwise breaks the moment the working directory moves.
3. **A block whose remedy the agent has already performed is worse than a false positive.** It is unfalsifiable from inside the session and trains the agent to disable the guard. Guards that gate on a marker should say *which store* they read.
4. **Gitignored approval state does not survive a fresh checkout — that is the feature and the trap.** Any migration that creates a new working copy must decide what happens to local approvals *before* day one, not discover it.
5. **Dry-run the guard fleet from the new topology before moving any real work.** All three instances of this class were found by running each hook end to end from the new location; none would have been found by reading code.

Related: [ADR-014](../adr/014-per-session-skill-state.md) and the [per-session-state](../patterns/per-session-state.md) pattern are the "key by session, share only by design" rule this violated in the other direction; [marker-file-acks](../patterns/marker-file-acks.md) is the mechanism itself; [PM-023](023-blocked-from-committing-its-own-file.md) is the other guard that blocked an agent from doing the correct thing for a reason invisible inside the session.
