# ADR-019: Publication from a shared checkout goes through a scoped publisher, and the old commit-then-push workflow is refused, not discouraged

**Status:** Active · **Date:** 2026-10-04 (tool), 2026-10-05 (rule), 2026-10-10 (refusal layer ratified) · **Internal refs:** #3059, #3068, #3080, #3063, #3069

## Context

Every Claude Code session on the primary machine works in **one checkout**. That means one index, one `HEAD` and one working tree, shared by 7–12 concurrent sessions. The staging area was a shared surface long before this decision. [PM-008](../postmortems/008-broad-git-add-swept-another-sessions-files.md) and [PM-011](../postmortems/011-bare-commit-swept-the-shared-index.md) show broad adds and bare commits sweeping a sibling's files, and [PM-062](../postmortems/062-the-staging-area-reported-live-files-as-deleted.md) shows the index listing live files as deleted. Each incident got its own guard. The workflow underneath stayed the same: stage, commit, push.

Two measurements in early October made the workflow itself the problem.

**The race was structural.** In the 35.1 hours before the publisher landed, `main` took **79 commits**, with a **median gap of 5.9 minutes** between them. (Re-measured for this ADR. The tool's own commit message reported 64 commits with the same median; the difference is the window's end point.) Any candidate that pins a parent and then does something slow loses that race. Sessions paid for it quietly with rejected pushes and hand-made merge commits.

**The staging area could change under a verified commit.** One session verified a seven-file staged set and then committed it. Between the scoped-diff check and `write-tree`, a per-session wrapper's automatic index re-seed replaced the staged set. The resulting commit's message describes seven files, with a blob-continuity table for all seven. **The commit contains one file, and it is none of the seven.** It belongs to an unrelated lane. The commit never reached a remote, and it is still in the object store as evidence. The same day, a different session found an uncommitted edit to a shared hook file reverted off disk. The file carried a timestamp *older* than the edit, so it was not a fresh overwrite (#3063). Our nightly cross-session review joined it with three similar reports from the same window. No root cause has been assigned.

## Decision

**A session in the shared checkout does not stage, commit, push, merge, rebase, reset, stash, restore, check out or switch as a way to publish or recover.** It publishes a scoped change through one tool. Read-only git (`status`, `diff`, `log`, `show`, `rev-parse`, `ls-remote`, `fetch`) stays unrestricted, so the rule cannot be misread as "stop using git."

The tool has five properties. Each one answers a failure we had seen:

1. **An explicit manifest of path plus blob id.** The committed content is the verified content **by construction**. Nothing ambient can be swept in, and that is what keeps other sessions' files out.
2. **A private temporary index, never the shared one.** Every git call names the real binary by absolute path, because the per-session wrapper is a shell function that intercepts a bare `git` from any directory.
3. **The base is read at the last moment** and the commit is parented there. No parent is pinned, so no parent can go stale.
4. **Fast-forward only, with an expected-old-value lease.**
5. **Abort with a stated reason rather than improvise.** An abort changes no ref.

The tool never merges, rebases, touches the shared index or working tree, removes untracked files, or force-pushes. Dry run is the default and `--apply` is required. **Every run writes a receipt** with the manifest, base, candidate, final SHA and push outcome.

**It scans its own blobs for secrets.** Plumbing (`update-index --cacheinfo`, `commit-tree`) does not fire pre-commit hooks, so a tool built this way would silently skip the secret scanner. That is exactly how the earlier hand-built plumbing commits bypassed it. The tool therefore scans every manifest blob **by object id** before it pushes. Object id rather than `git show :path` was chosen for a measured reason: git launched from a Python subprocess did not inherit the per-session index variable, so `:path` read the shared index and returned stale bytes. A blob id is a content hash, so it cannot return the wrong bytes.

### Rule first, enforcement second

The tool shipped on 2026-10-04. The standing rule still said, in so many words, that plain commit-then-push was pre-authorized and that sessions should **not** ask first.

The fleet was not drifting from the rule. It was obeying it. In the 48 hours to the end of 4 October (UTC), `origin/main` took **106 commits, and 22 carried a publisher receipt.**

The operator's ruling was that enforcement could not ship ahead of the rule: *"Otherwise the guard would refuse the workflow the standing rules still explicitly authorize, and active sessions would reasonably treat the refusal as a conflict to route around."* So the first change was **documentation only**. The rule line was rewritten in place to call the old workflow *prohibited*, not merely discouraged. Its heading changed because the old title had become false.

### Then the refusal layer, with no bypass

The command-string refusal in the shared `PreToolUse` dispatcher has **no bypass at all**:

- no environment variable
- no caller-supplied label
- no writable config value
- no path allowlist
- no "this is the publisher" exemption

That last one was considered and rejected as caller-supplied and forgeable. The publisher needs no exemption because it never issues porcelain. Ten of the eleven refused verbs never appear in its subprocess calls.

The detector under the refusal was measured and widened first. As built, it was blindest on commands that carried a guard bypass ([PM-073](../postmortems/073-the-git-detector-was-blindest-where-sessions-were-bypassing-guards.md)).

The operator's bar was stated plainly: legacy publication should be **impossible by normal habit, visible and costly when deliberate, and never silently re-enabled. Not cryptographically impossible.**

## Alternatives considered

- **Keep commit-then-push and add more guards on the index.** Rejected because that was the existing trajectory and it had stopped converging. Each guard closed one sweep shape. The index re-seed case defeats any check that runs *before* `write-tree`, because the index changed *after* the check.
- **Per-session worktrees for everyone.** This remains the long-run direction, but it is not ready. It needs a single-writer merge process, and the shared state sessions depend on (the knowledge base among it) still resolves inside the primary checkout ([PM-057](../postmortems/057-the-isolated-worktree-was-isolated-from-the-fixes-too.md)).
- **An operator-run release window.** One protected 10-minute window landed one verified deployment cleanly. The operator rejected turning that into a standing manual release service, and that ruling is what triggered packaging the pattern as a tool.
- **A publisher exemption signal on the refusal.** Rejected because the signal is caller-supplied and therefore forgeable.
- **Install the pre-commit refusal now.** Built and tested, and deliberately **not installed** in the live chain. `--no-verify` skips it entirely, so it would only ever detect. It also has to permit no-session host automation in v1, and it audits that on every pass instead of hiding it.

## Consequences

**The rule held, measured.** From the rule commit (2026-10-05) to 2026-10-11, `origin/main` took **30 commits. All 30 match a publisher receipt's final SHA.** None arrived any other way. Over its first week the tool wrote 56 published receipts, 50 dry runs, 6 aborts and 1 secret-scan refusal.

**Enforcement went live on save, not on review.** In a shared checkout, a hook is live in every session the moment its file is written. The refusal logged its first production refusal on **2026-10-05**. Its code was committed on **2026-10-09**, and the operator ratified it as policy on **2026-10-10**. For four days an unreviewed, uncommitted guard was enforcing across the whole fleet. Our nightly cross-session review flagged it as "went live on save, undisclosed." This is not a property of this guard. It is a property of developing hooks in the checkout they guard, and this ADR inherits it.

**No-session automation was left on the old workflow, and it is now stranded.** Scheduled host jobs that commit-then-push were carved out of the rule on purpose, so the change would not silently stop them. The publisher does not move local `HEAD` (by design: it never touches the shared checkout). So local `main` stopped advancing while `origin/main` moved on, and every nightly push since has been rejected non-fast-forward. As of 2026-10-11: **19 commits exist only on local `main`.** Fourteen are nightly-job outputs, and each job's log shows seven rejected pushes. The carve-out kept the jobs *running*. It did not keep them *publishing*. This is tracked as its own task (#3069) and is not resolved by this ADR.

**A published path still looks unpublished locally.** After `--apply`, `git status` usually still shows the file as untracked or modified, because the shared index and `HEAD` were deliberately not touched. The tool's help says so in plain words, because the natural reflex — "it didn't take, add and commit it again" — is the exact workflow being retired.

**What got easier:** a session can publish from a dirty shared tree without reconciling anyone else's state. "Who published this, and was it what they verified?" now has a receipt-backed answer for every commit.

**What got harder:** recovery. A staged change or local-only commit is now *reported*, not merged or reset, and it waits for instructions. That is slower on purpose.

## What we'd do differently

Ship the rule change, the tool and the automation migration as **one** change. Splitting them let the rule and the tool contradict each other for a day. It also left the nightly jobs on a path whose remote kept moving away from them, and nothing said so for a week except the jobs' own logs.
