# "Remote SHA Verified" — Against a Stale Cached Ref: 12 Hours of Pushes That Never Happened

**Keywords:** git push verification, stale origin ref, oversized commit blocked push, false success verification, remote tracking branch, wrap verification, git push silently failing chain

**Incident date:** 2026-06 · **Internal refs:** wrap verification procedure; six-cause chain in the incident record · **Status:** fixed (verification fetches before comparing); recovery side-effect documented

---

## What broke

Session wrap-up includes a verification step: after `git push`, confirm the remote actually has the commit — compare local HEAD against the remote branch SHA. Belt and suspenders. The suspenders were painted on.

The chain, six causes deep:

1. A session produced an **oversized commit (>100MB payload)** that the remote rejected on push.
2. Every *subsequent* session's push then failed too — their commits sat behind the oversized one in history; the chain grew.
3. Local commits kept succeeding, so each session's own work "completed."
4. The wrap verification compared local HEAD against **`origin/main` — the local remote-tracking ref — without fetching first.** That ref is a cache of the last successful remote contact. Since pushes were failing, it was stale — but the *local commit graph* had advanced on top of it in a way that made the comparison logic pass.
5. Result: **~12 hours of sessions wrapping with "remote SHA verified ✓"** while nothing had reached the remote at all; the unpushed chain quietly grew across sessions.
6. The finale: the droplet's scheduled auto-sync eventually pulled — from a remote that didn't have the work — and the eventual untangling *recovered* the situation in a way that left no alarm anywhere. The failure healed itself into invisibility; it was found in forensics, not in the moment.

## How it was detected

After the fact, from the seam: droplet state didn't reflect work that session records claimed was pushed and verified. Reconstructing the push-failure window from git reflogs and the oversized-commit rejection produced the chain above.

## Root cause

Surface: verification read a cache and called it the remote. `origin/main` without `git fetch` is a *memory* of the remote, exactly as fresh as the last successful contact — which is precisely the thing in question when pushes are failing.

Deeper: **the verification shared fate with the operation it verified.** Both the push and the check depended on the same assumption (remote contact works); when the assumption broke, they failed *in agreement*. A check that can't fail independently of its subject is decoration. Compare [PM-013](013-integrity-ledger-certified-fabricated-results.md) — same law at a different layer.

## Blast radius

12 hours of falsely-verified wraps across multiple sessions; a growing unpushed chain that risked exactly the divergence the 30-minute sync architecture exists to prevent; and — the quiet cost — a verification step whose green checkmark had to be retroactively distrusted for its whole prior history.

## The fix

- Verification **fetches first**, then compares against the freshly-updated remote ref — the check now contacts the actual remote or fails saying it couldn't.
- Push failures became loud in wrap: a failed push aborts the wrap ritual instead of proceeding to a "verification" step.
- The oversized-commit class got its own gate (size check pre-commit), removing the original trigger.
- Silent-recovery paths in the sync were given logging — recovery is fine; *unrecorded* recovery is how failures escape their postmortems.

## Has the guard fired since?

The fetch-first verification has caught real push failures since (non-fast-forward rejections from concurrent-session races — a known, separate friction), each one stopping a wrap that would previously have lied. The >100MB class hasn't recurred past its gate.

## Lessons for agent-driven development

1. **Verify against the source, not a cache of the source.** `origin/main` without a fetch is your last impression of the remote, and last impressions are what verification exists to distrust.
2. **A check must be able to fail when its subject fails — independently.** Shared-fate verification always agrees with the operation, which is another way of saying it verifies nothing.
3. **Chains of local successes can hide one remote failure.** Commit-succeeded is not pushed; pushed is not on-the-remote; each seam needs its own truth.
4. **Silent recovery erases evidence.** Systems that self-heal without logging convert incidents into permanent unknowns — log the heal, or the postmortem never happens.
