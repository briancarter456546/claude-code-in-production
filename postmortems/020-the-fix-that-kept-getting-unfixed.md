# The Guard Fix That Concurrent Sessions Kept Silently Reverting

**Keywords:** concurrent sessions reverting fixes, fix ordering, guard dependencies, multi-agent code conflicts, deploy gate false positives, stuck commits, fix durability

**Incident window:** 2026-05-26/27 (two stuck-commit incidents) through cycle_003 · **Internal refs:** tasks #1342, #1473; builder-deploy-gate v1.1→v1.3 · **Status:** fixed durably — after the third attempt, in the right order

---

## What broke

A deploy gate protected an autonomous build pipeline: while a build cycle was in its BUILD phase, pushes were held so half-finished artifacts couldn't ship. Version 1.0 had a scoping bug — `find_active_cycle()` returned *any* open cycle, so the gate blocked **unrelated pushes from unrelated sessions**. A trading session's `git push` was blocked because a completely different lane had a workshop-content build open. Worse, the gate's `exit 2` killed the whole chained command — `git add && commit && push` — leaving changes unstaged and the commit lost.

Then it got interesting, three failures deep:

1. **v1.1 fixed the scoping** (gate keys on the owning session's signature). Shortly after, the fix *stopped being in the file*. **Another concurrent session had reverted it** — not maliciously; it had a stale copy or resolved a conflict the wrong way. This was before the cross-session git guards existed ([PM-008](008-broad-git-add-swept-another-sessions-files.md), [PM-011](011-bare-commit-swept-the-shared-index.md)); nothing prevented one session from clobbering another's uncommitted or just-committed hook changes.
2. **The gate then tripped on its own bookkeeping:** its audit-trail appends (`events.jsonl`) registered as changes-during-BUILD, so the gate blocked commits *caused by the gate recording that it had blocked commits*. Two stuck-commit incidents in two days, across two sessions.
3. The team faced a choice documented at the time: re-land session signatures "that keep getting reverted," or change the trigger to diff-intersection (block only pushes whose diff actually touches the active cycle's artifacts). They chose diff-intersection — **the design that stays correct even if a concurrent session mangles it**, because it derives scope from the push itself rather than from maintained state.

## How it was detected

Each layer loudly: lost commits and unstaged changes are hard to miss. The *revert* was the subtle one — diagnosed only when the "fixed" failure recurred and `git log`/file inspection showed the fix absent, with no record of anyone deciding to remove it.

## Root cause

Surface: scoping bug, then self-triggering bookkeeping.

Deeper: **fix durability depends on the surrounding system's ability to protect a fix.** In a multi-session environment without commit-attribution guards, any uncoordinated change — including a fix — can be silently undone by a sibling session. The fix wasn't wrong; it was *undefended*. The durable resolution combined a defended environment (the git guard family arrived) with a design less dependent on defense (derive-don't-maintain).

## Blast radius

Two days of stuck commits across two sessions; one lost commit's worth of rework; and the enduring ordering lesson: several other planned guard improvements were resequenced to land *after* the git-attribution guards, once it was clear fixes couldn't survive without them.

## The fix

- v1.3: **diff-intersection trigger** (block only when the push's diff intersects the active cycle's paths) + bookkeeping paths exempted from the gate's own scan + gate exit behavior changed to fail the push cleanly without nuking the staged state.
- Environmental: the cross-session git guard family, which makes silent fix-reverts detectable and mostly impossible.

## Has the guard fired since?

Yes, correctly scoped: it blocks builder-artifact pushes during BUILD (7 blocks in a recent 12-day window, all legitimate) and no longer touches unrelated lanes. No revert of the fix since the attribution guards shipped — which is the real test it kept failing before.

## Lessons for agent-driven development

1. **A fix in a concurrently-edited system is not durable until the system can detect its removal.** Order your work: attribution/protection guards *first*, then the fixes they defend.
2. **Guards must exempt their own bookkeeping.** Any gate that writes logs inside the area it monitors will eventually block itself.
3. **Prefer derived scope over maintained state.** State can be clobbered by a sibling; a scope computed from the artifact under review (the diff) survives everyone's edits.
4. **Blocking exits must not destroy work in flight.** `exit 2` in the middle of a chained git command cost a commit; a gate's failure path is part of its design.
