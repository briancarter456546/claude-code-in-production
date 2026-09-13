# Windows Task Scheduler refused 11 enabled nightly agent jobs and recorded zero missed runs: the backup, the review, and this writer

**Keywords:** Windows Task Scheduler missed run, 0x800710E0 operator or administrator has refused the request, StartWhenAvailable, WakeToRun, DisallowStartIfOnBatteries, NumberOfMissedRuns 0, scheduled task silently skipped, laptop sleep scheduled job, nightly backup did not run, success marker freshness monitor

**Incident date:** first noticed 2026-09-10 (one job's log stopped after 2026-09-08); fleet audited and fixed the same day · **Internal refs:** #2604, #2714, #2631 · **Status:** fixed on every enabled task; post-fix audit 2026-09-13 below

---

## What broke

The development PC runs a few dozen Windows scheduled tasks for the agent system: a nightly knowledge-base backup, a nightly review that reads every session's transcript, a derived file index, weekly audit emails, and the scheduled Claude Code session that writes this repository.

A nightly index job logged clean runs three nights in a row and then simply stopped. No failure in its log, because it never started. Windows reported its last result as `0x800710E0` — *"the operator or administrator has refused the request"* — and, in the same query, **`NumberOfMissedRuns: 0`**.

A fleet audit the same day found it was not one job:

- **28** scheduled tasks run something inside the repository.
- **25** lacked one or more of the four settings that let a missed start recover; **19** of those were enabled.
- **11 enabled tasks** had last ended with that same refusal — including the knowledge-base backup, the nightly transcript review *and its fallback*, the weekly guard-audit review, a git-index sweeper, a metrics ingest, and **the weekly chronicle writer that produces this repository**.

Windows counted none of them as missed. Nothing alerted.

## How it was detected

By a human-noticeable symptom, not a monitor: a downstream file index was two days stale. Following that to its job led to the scheduler's own task info — result code refused, missed runs zero — and the settings explained why. The fleet audit came next because the settings on one task were obviously copied from a template.

## Root cause

**The registration settings made a missed start permanent.** The tasks were registered with the defaults a laptop-oriented scheduler gives you:

- run only when the user is logged on interactively,
- do not start on battery, and stop if the machine goes on battery,
- **no "run as soon as possible after a scheduled start is missed,"**
- no wake-to-run.

A job scheduled for 02:30 on a machine that is asleep, on battery, or logged off at 02:30 is refused. Without the catch-up setting it is never retried; the next attempt is the next scheduled slot, which fails the same way if the machine keeps the same habits. And because a refused start is not, to Windows, a *missed* run, the counter that looks like it should catch this stays at zero.

**The deeper cause: every one of these jobs defined success as "the scheduler shows it."** Several wrote logs; none wrote a success marker that something else checked for freshness. A job that never starts writes nothing, and nothing is exactly what a healthy job with no news also writes.

**A second, independent trap found in the same pass:** the PC's clock is set to US Central time, while schedules across the system were labelled and reasoned about in Eastern. Every "ET" time on this machine was off by an hour.

## Blast radius

- The backup of the knowledge base — the system's primary memory — was among the silently refused jobs. Its data was intact; its safety net was not running.
- The nightly review, which exists to catch what sessions miss, missed itself, and so did its fallback, which ran under the same settings.
- Downstream staleness is known for one job (a derived index, two days stale). For the others the exact number of lost runs is **not recoverable**: Windows kept no count, and the jobs kept no marker.
- An honesty note on the numbers: an earlier read-only pass the same day counted 26 of 28 tasks missing settings and "at least 9" refused; the fixer's own audit, run later against the live scheduler, counted 25 and 11. The figures above are the fixer's.

## The fix

- **One settings fixer instead of per-task re-registration.** It audits read-only by default, dry-runs by default, and on apply sets exactly: catch-up on, start and keep running on battery, and wake-to-run **only on tasks without a repetition interval** — waking the machine for a job that repeats every few minutes would stop it from ever sleeping. It never changes a task's action, trigger, or account, never deletes, and skips disabled tasks, because someone switched those off on purpose.
- **The operator ran the apply, not the agent.** The session's permission layer refuses a Claude Code session changing system scheduled tasks; the fixer was written for a human to run. That refusal was correct and was left in place.
- **The general rule was written into the knowledge base:** register with catch-up, wake, and battery settings, and have each job write a success marker only on completion. The job registry already supports a freshness expectation (a completion file plus a maximum age); jobs added since, such as the worktree keep-current job, declare one. Retrofitting markers onto every older job is not done.

## Has the guard fired since?

Post-fix audit, run read-only while writing this document (2026-09-13): **29** repo tasks; **0 enabled tasks** missing any of the settings (the 6 still missing are all disabled); **1** enabled task whose last result is still a refusal — a check job whose last run was in May, which the settings change cannot retroactively re-run and which is now a visible item rather than a silent one. The index job that started this has run on schedule since, and so has the chronicle writer: this document exists.

What the audit also shows, and what the fix does *not* address: several enabled tasks now end with non-zero application exit codes. Those are ordinary job failures — a different class, and one that is at least visible once the jobs actually start.

## Lessons for agent-driven development

1. **"Refused" is not "missed" to the Windows scheduler.** Do not use its missed-run counter as a liveness signal; it can read zero for a job that has not started in days.
2. **Register every unattended job with catch-up enabled**, and decide wake and battery behavior per job — a repeating job with wake-to-run keeps the machine awake forever.
3. **A job's success must be an artifact something else checks.** If "it ran" is only visible in the scheduler's UI, a job that never starts and a job with nothing to report are indistinguishable.
4. **Audit scheduling as a fleet, not a task.** The broken settings came from a copied template, so the defect was in every job registered the same way — including the fallback built to cover the primary.
5. **Check the machine's clock zone before trusting any schedule label.** A timezone written in a comment is a claim, not a setting.

Related: [PM-033](033-production-degraded-politely.md) (a cron that never once succeeded while warnings stayed polite), [PM-034](034-windows-kills-guards-quietly.md) (other ways Windows quietly killed automation), [PM-054](054-nothing-checked-whether-the-controls-were-still-alive.md) (controls nobody checked were still alive).
