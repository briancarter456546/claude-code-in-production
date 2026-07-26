# The Deploy Was Hash-Verified Correct — a Cron Reverted It 30 Minutes Later

**Keywords:** deploy reverted by sync, git sync cron overwrite, deployment verification window, scp deploy vs git pull, production running old code, deploy pipeline conflict

**Incident date:** 2026-04-10 · **Internal refs:** sync-guard hook; the version-bump variant (same week) · **Status:** fixed (deploy paths unified through git); advisory guard fires on the conflicting pattern

---

## What broke

A production allocator script was deployed to the droplet by direct file copy, and the deploy was *verified*: hash of the deployed file matched the intended version. Green checkmark, session moved on.

Thirty minutes later the droplet's scheduled git-sync pulled the repository — which still contained the *old* version of the file, because the deploy had gone machine-to-machine, not through git. The pull "restored" the old code over the verified new code. Production ran the previous version that night with no indication anywhere: the deploy log said success (true, at the time), the sync log said routine pull (true), and the two truths composed into a lie.

Same week, the sibling failure: a script was version-bumped (`v1_0` → `v2_1` naming convention) but the scheduler entry still invoked the old filename — the old version ran nightly *forever*, while the new one sat deployed and never called. Two shapes, one lesson: **deploy state has more than one writer, and verification checked only one of them.**

## How it was detected

Wrong numbers in the next morning's output, traced backward: production behavior matched the old logic; the file on disk *was* the old file; the deploy log swore otherwise. The sync timestamps between deploy and execution closed the case.

## Root cause

Two deployment channels with different sources of truth: direct copy (truth = what was pushed) and git-sync (truth = what's in the repo), both writing the same path on a schedule that guaranteed the later one wins. The verification was *point-in-time* against a target that had a **standing appointment to be overwritten**. Verification that expires before the next scheduled writer isn't verification — it's a snapshot.

## Blast radius

One production night on stale logic (caught before it compounded); the version-bump variant ran undetected longer; and the broader realization that *every* file on the droplet had to be classified: is git or direct-copy its owner? Files with two owners were incidents waiting for a schedule.

## The fix

- **One writer per path:** git-tracked files deploy *only* via commit+push+sync — direct copy to git-owned paths is blocked by an advisory guard that names the sync cron in its warning. Non-git files (generated artifacts, dashboards per [PM-010](010-stale-local-dashboard-forks-diverged-from-production.md)) are owned by their generators, and git never touches them.
- **Version bumps update the caller in the same change:** the scheduler-entry check became part of the version-bump procedure after the sibling incident — renaming a file without re-pointing its cron is now a checklist collision, not a discovery.
- **Post-deploy verification moved past the next writer's slot** where it matters: verify after the sync has run, or verify the *repo* state (the thing the sync will enforce), not just the disk state.

## Has the guard fired since?

The sync-conflict advisory fires when sessions reach for direct copy onto git-owned paths — the instinct persists, the guard redirects it. No verified-then-reverted recurrence since path ownership was made exclusive.

## Lessons for agent-driven development

1. **Enumerate every writer of a path before trusting any verification of it.** A green hash check is a statement about *now*; scheduled writers make "now" a very short time.
2. **Two deployment channels to one target is an incident with a timer.** Pick one owner per path and block the other, mechanically.
3. **Renames must chase their callers.** A version-bumped file that nothing invokes is indistinguishable from a successful deploy in every log except the output.
4. **Verify after the last writer, or verify the source of truth the writers enforce.** Timing is part of the verification's semantics, not an implementation detail.
