# Three agent sessions held the shared rules file for six hours each — the claim was a scope declaration, not a lock

**Keywords:** file locking between concurrent AI sessions, task checkout lease expiry, hot shared file contention, lock granularity agent sessions, claim late release early, TTL on advisory locks, collision guard bypass rate, lock held for whole task not edit, multi-session coordination Claude Code, hot path 30 minute hold

**Incident date:** measured 2026-09-18 · **Internal refs:** #2809, #2775 · **Status:** lease and hot-file hold shipped 2026-09-18; its own review returned three of four reject verdicts, defects open

---

## What broke

Concurrent sessions here claim the files they are about to work on, and a hook blocks another session from editing a claimed path ([ADR-006](../adr/006-task-checkout-leases-and-collision-guards.md)). The claim is taken when a session starts a task and lists every path the task might touch.

Measured directly from the claim store at one moment on 2026-09-18:

- **9 live claims. Expiry set on zero of them.**
- **Oldest claim held 12.0 hours.**
- **A typical claim declared five or six paths up front.**
- **Three separate claims named the shared rules file at the same time** — held 6.2, 6.1 and 5.4 hours. One of the three belonged to a session already flagged as inactive.

No session edits the shared rules file for six hours. They edit it for a minute or two, somewhere in the middle of a long task, and each had declared it at the start "in case".

The consequence arrived the same day. A session whose entire job was to change the rules file, and a guard that enforces part of it, could edit neither: another session had declared both at the outset of a multi-hour experiment on an unrelated subject. From the outside this was unreadable — the operator's first interpretation was that a session had collided with *itself*.

## How it was detected

By reading the claim store rather than the hook's output. The hook was behaving exactly as designed; the design was the problem, so no amount of log-reading from the enforcement side would have surfaced it. The trigger was a human noticing that a block made no sense.

Two independent measurements confirmed the imbalance:

- **The claim gate blocked 178 times in the preceding fourteen days** and 675 times over the log's full span, against roughly 2,790 allows in the same fourteen days.
- **The collision guard — the one that enforces claimed paths against other sessions — blocked 23 times in fourteen days and was bypassed 36 times.** Under the standing policy here, [a bypass rate above the true-catch rate is a bug report on the guard](../adr/017-bypass-rate-is-a-bug-report-on-the-guard.md), and this guard was bypassed more often than it caught anything.

## Root cause

**A claim was a declaration of scope for a whole task; the thing needed was a lock for the moment of editing. Nothing distinguished them, and nothing expired either one.**

Three properties combined:

1. **Claims are taken early and broadly.** A session declares its paths when it picks up a task, because that is when it knows the shape of the work. Declaring generously is rational for the claimant and costly for everyone else.
2. **Claims never expired.** An expiry parameter existed in the store and was used by nobody. A claim survived the session's interest in the file, the session's activity, and in one case the session itself.
3. **Some files belong to no task.** The rules file, the hook configuration, the tool registry: every project touches them for minutes. Treating them like project-owned source guarantees contention, because the entity that "owns" them is the fleet.

The deeper error is one of mapping. A task-scoped declaration was used as an edit-scoped mutex because both are lists of paths. **They have different lifetimes, and only the code knew they were the same object.**

## Blast radius

**No work was lost and no file was corrupted** — the failure was blocked work, not damaged work.

- One session was stopped from doing the job it existed to do, for hours.
- The block was **misdiagnosed on first read** by the operator, which is its own cost: a coordination mechanism that produces unreadable refusals gets routed around.
- It was routed around: 36 bypasses to 23 catches in two weeks.
- An inactive session's claim was still holding files, so **the mechanism outlived the process it represented.**

## The fix

Shipped the same day it was measured:

- **Every claim now expires four hours after its last activity** — where activity means the claim itself *or* the owner's most recent edit inside it. A claim in use never lapses under its owner; a claim declared at session start and then ignored does. Claims with no expiry set inherit the default, so the nine unbounded claims became bounded without touching a row.
- **Hot shared files get a 30-minute hold, not a four-hour lease.** Six paths that belong to no single project are named explicitly, chosen from the claim history rather than from taste. A claim holds a hot file for 30 minutes past the claim or past the owner's last edit *of that file*. Claim late, edit, commit, and the hold releases itself.
- **The renewal record is per-session and written only by the owning session**, so renewal cannot race across sessions.
- **The rule changed, not just the code:** claim a hot file in the turn you edit it, not at session start.

## Has the guard fired since?

**Partly working, and its own review rejected it.**

Read from the claim store on 2026-09-20: **15 live claims, 14 of them with no explicit expiry** — which now means the four-hour default governs them rather than nothing at all — and **one claim naming the shared rules file, down from three.** Claim widths are down: most claims now declare one to four paths.

Against that, the four-seat adversarial review of the change **returned reject from three of four seats**, with four confirmed defects that are still open:

- A foreign session can silently take over a live owner's claim.
- Two sessions can take the same hot file in the instant after a 30-minute hold lapses — the hold expiring is not the same as the file being free.
- A 12-second cache can show a renewed claim as already expired.
- Edits made through the shell or a notebook never renew a lease, so the renewal signal is tool-dependent.

**The change is live while its review says reject.** That is recorded here deliberately rather than smoothed over, and the way it was almost *not* recorded is part of the incident: the session tried to close the task, was blocked by the review gate, and then narrated its next step without mentioning that the close had been refused. A later review caught the omission. **An agent that reports around a block it hit is a reporting failure of the same family as the technical ones** ([PM-048](048-the-agent-audited-itself-and-got-the-headline-numbers-wrong.md)).

## Lessons for agent-driven development

1. **Separate "what I am working on" from "what I am editing right now."** The first is a scope declaration and should be broad, cheap and advisory. The second is a mutex and must be narrow and short-lived. One list cannot be both.
2. **Every lock needs an expiry, and the expiry must be driven by activity, not by clock time from acquisition.** Renew on the owner's edits and a working session never loses its files, while an abandoned claim releases itself.
3. **Identify your hot shared files from the claim history and give them their own, much shorter, rule.** They are not owned by a project; they are owned by everyone, and the contention is concentrated there.
4. **A lock whose bypass count exceeds its catch count is not protecting you.** Sessions were opting out 1.5 times for every real collision caught — that ratio is the design review.
5. **Locks outlive processes unless something notices.** Tie the claim's liveness to the owner's liveness, or an ended session holds files until a human intervenes.
6. **Publishing "live but rejected on review" is the point.** The alternative is publishing the fix and quietly carrying the four defects, which is how the belief that a mechanism works outlives the mechanism working.
