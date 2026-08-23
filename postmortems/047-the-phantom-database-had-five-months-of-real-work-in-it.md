# The "Stale" Fallback Database Turned Out to Hold Five Months of Real Work — and a Post-Compaction Session Wrote Into It Again the Same Day It Was Diagnosed

**Keywords:** silent fallback database, split brain task store, forked SQLite, append-only merge, id crosswalk, fail-closed client, context compaction regression, relay RPC, idempotent merge, AI agent task tracking

**Incident date:** fork began ~2026-03-09; re-discovered 2026-08-20; merged 2026-08-21 · **Internal refs:** tasks #2133 (the original fix task, still open when this fired), #2214 (merge + fail-closed client) · **Status:** code shipped 2026-08-21 (fail-closed client; merge applied once, script marked do-not-re-run); both tasks still open at time of writing — the connection variable has not yet been persisted in the launch shell, so the refusal currently fires on every session, including the one that wrote this document.

---

## What broke

[PM-027](027-the-database-that-lied-by-being-present.md) documented the mechanism: the task CLI, when its connection variable is unset, silently opens a local SQLite file instead of the canonical store on the always-on droplet. That postmortem called the local file a "stale snapshot" and left the fix open.

Both halves of that were wrong in instructive ways.

**It was not a snapshot. It was a fork.** When the local file was finally diffed against the canonical store, it had 397 rows. 122 shared an id and a normalized title with a canonical row (the merge's "identical" test — title at the same id, nothing stronger; four of them differed in done-state) — and every one of those was created between 03-05 and 03-09. The other 257 existed *only* locally, created from 03-09 through 08-20: 164 in March, 2 in May, 29 in July, 62 in August. Fifty-six of them had been marked done. Sessions on the dev PC had been filing, claiming, and completing real work into a database nothing else read, on and off, for five months — and because both stores kept assigning ids sequentially from the shared starting point, every id issued after the fork named a different task on each machine.

**And the fix was still open four weeks after PM-027.** On 2026-08-20 a session hit the symptom from the other side: `show <id>` returned "Task not found" for every recent id, because it was asking the 384-row fork about ids that only existed in the canonical store (about 2,200 rows that day; 2,242 at merge time). The session diagnosed it, wrote a cleanup document, re-filed six orphaned tasks through the correct path, and filed the merge task.

Then its context was compacted. After compaction, the same session — now working from a summary — went back to the bare CLI command and filed seven more tasks straight into the fork it had spent the morning diagnosing. The knowledge of the correct write path was, in the words of the auditor who later read the raw transcript, "in the dropped tokens." This was not noticed by the session; it was found by an independent model reading the raw transcript for an unrelated efficiency audit ([PM-048](048-the-agent-audited-itself-and-got-the-headline-numbers-wrong.md), Q3).

## How it was detected

Three times, none by the designed path:

1. PM-027's mining run, 07-25 — noticed by a task-count mismatch, fix task filed, fix not shipped.
2. 08-20 — "Task not found for every id" on a session that knew the ids were real.
3. 08-20, post-compaction — the seven mis-filed tasks were caught by an external auditor reading the transcript, not by the CLI, not by the session, and not by any hook. The session then re-filed them (#2236–#2242) and wrote an "operating facts" file whose first line is an instruction to re-read it after any compaction.

## Root cause

Surface: the fallback branch PM-027 already named, left in place because the fix was specified but not shipped.

Deeper, two things:

- **A fallback store that accepts writes is not degraded mode — it is a second system of record.** PM-027 reasoned about the fallback as *stale reads*. The damage was *divergent writes*: every session that launched without the variable did real bookkeeping into the fork, and the fork's only consumer was the next session in the same state. Stale is recoverable by re-reading; forked is recoverable only by merging.
- **A fix that lives in a task is a fix that lives in context.** The correct write path was known on 07-25 and re-learned on 08-20 — and lost again at 17:12 that afternoon when compaction dropped ~984k tokens. Nothing in the environment refused the wrong command. Until the refusal is in the tool, every session (and every post-compaction continuation of a session) rediscovers the bug from scratch.

## Blast radius

- 257 tasks invisible to the canonical store for up to five months, 56 of them "done" in a database no report or briefing read.
- Id collisions: any task number cited in a handoff, commit message, or note from the dev PC during that window may refer to the fork's numbering. Commits and docs had to be re-cited after the merge.
- One session's post-compaction work went into the wrong store within hours of diagnosing the problem.
- The merge itself cost a day: dry-run rehearsal against an exact copy of canonical, a near-match rule (normalized-title similarity ≥ 0.80) because fork rows turned out to be same-day rewordings of canonical rows and a naive merge would have recreated duplicates (11 found at rehearsal, 15 in the shipped run), a WAL-checkpoint bug in the hashing step (the "after" hash was taken before SQLite flushed the write-ahead log — patched and noted in the crosswalk), and a two-reviewer pass on the client.

## The fix

Three layers, append-only throughout:

1. **Merge, never overwrite.** A one-shot merge script: dry-run by default; idempotent via a source-id marker on every inserted row; carries the fork's done-log and remaps blocked-by references; emits a JSON crosswalk (fork id → canonical id, match kind, similarity ratio) as a permanent reference. Result: 257 inserted, 122 skipped as identical, 15 near-matches and 3 title-matches mapped to existing rows; canonical grew from 2,242 to 2,499 rows, md5 before and after recorded. The script's header now says DO NOT RE-RUN, because the second-run idempotence relied on a marker in free-text notes, which a reviewer correctly called non-durable.
2. **Fail closed, in the constructor.** CLI v1.5: with the connection variable unset, the client prints a one-line error naming the variable and exits 3. It no longer opens — and can never *create* — a local store off the canonical host. v1.5.1 moved the check from the CLI layer into the database class's `__init__` after a reviewer pointed out that scripts importing the class directly could re-fork without ever touching the CLI. Canonical-host identity is an explicit marker file on the droplet, not a path string. Local opening requires an explicit opt-in variable, for migration and inspection only.
3. **Remote path that cannot fork.** A relay mode forwards every client method to the droplet as an RPC carrying a request id and caller tag; the server replays cached results on duplicate ids and logs every call, so a retried write cannot double-insert.

The merge was not clean, and this document will not pretend otherwise: the session that found the post-compaction mis-filing had flagged the seven fork rows as duplicates and written "do not migrate them." The near-match rule caught four of the seven; the other three were classified as fork-only and inserted as new canonical rows, where they still sit today duplicating the three tasks that had been correctly re-filed the night before. A written instruction in a cleanup document is not an input the merge script reads.

As of this writing neither task is closed: #2133 (the PM-027 fix task) is still open and untouched since 07-25, and #2214 shipped the code but remains open pending the connection variable being persisted in the launch shell and a review verdict. PM-027's own "about 1,263 live tasks" was also an undercount — by the cleanup document's row counts the canonical store held roughly 2,050 rows in mid-July.

## Has the guard fired since?

The refusal fired on the first command of the weekly writer session that produced this postmortem, two days after the code shipped: the launching shell had not set the variable; the CLI refused with exit 3 and the one-line message; the session re-ran with the relay mode. Two lines of transcript instead of a fourth fork. But read it honestly: the variable has not been persisted anywhere yet, so the refusal is firing on *every* session — that is the unfinished half of the fix showing up as a guard catch, not evidence that the guard distinguishes anything.

## Lessons for agent-driven development

1. **Classify fallbacks by whether they accept writes.** A read-only fallback degrades; a writable fallback forks. The second is a data-recovery incident waiting for its discovery date.
2. **A known bug with an open fix task is an open bug.** Four weeks of "specified, not shipped" produced 62 more orphaned tasks in August alone. The postmortem that names a mechanism does not close it; the tool change does.
3. **Compaction is a fresh session with a worse briefing.** Anything a session learned about *how* to do things correctly — write paths, command forms, which store is real — dies at the summary unless it is either enforced by the environment or written to a file the continuation is told to read first.
4. **Put the refusal in the class, not the command.** Guards at the CLI layer protect the CLI. Other scripts import the class. The reviewer who moved the fail-closed check into `__init__` closed a path the authors had not modeled.
5. **Merges need a rehearsal, a crosswalk, and a do-not-re-run header — and they only honor exclusions that are inputs.** Idempotence that depends on free-text markers is a hope, not a property; so is a "do not migrate these" note the script never reads. Three duplicates went in anyway.
