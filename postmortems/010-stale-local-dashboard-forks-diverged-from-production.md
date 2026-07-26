# Local Copies of Production Dashboards Silently Diverged — So We Banned Local Copies

**Keywords:** stale fork, source of truth, dashboard deployment, AI agent deploys, lost update problem, production drift, git for deployed files, ops dashboards

**Incident window:** repeated through 2026-04→07; policy inverted 2026-07 · **Internal refs:** source-of-truth gate; git-stage guard (#1589); scp-staleness guard; 2026-05-28 clobber incident · **Status:** fixed by policy inversion + 3 guards; guards fire regularly

---

## What broke

Ops dashboards are HTML files served from the always-on droplet. The natural workflow — keep the file in git, edit locally, deploy a copy — produced **stale forks**: the local "canonical" copy and the live file drifted apart, because reality kept editing the live file without telling git. Hotfixes happened server-side. Scheduled jobs regenerated sections in place. And with many concurrent sessions, *several* local copies existed at once, each believing itself current.

Two recurring damage patterns:

- **Regression-by-deploy:** a session edits its (stale) local copy and pushes, silently reverting live fixes it never knew about.
- **The lost update (2026-05-28):** two sessions pulled the same dashboard, edited independently; the second push erased the first session's work with no conflict, no warning — file copy has no merge semantics.

The failure repeated because the workflow *felt* correct. It's the standard workflow. Two separate sessions independently proposed "let's git-track the dashboard HTML" as the fix — the exact mechanism that creates stale forks — which is why one of the guards below exists specifically to block that "fix."

## How it was detected

Each incident individually: a live feature Brian used was suddenly gone after an unrelated deploy; diffs between a local copy and the live file showing changes nobody in the current session made. The pattern-level diagnosis — that *copies are the disease* — took several incidents to crystallize.

## Root cause

**Two writable homes for one artifact.** Git assumed it was the source of truth; production behaved like the source of truth; both were right often enough to stay plausible. Any system where a file can be modified in two places without a merge step will diverge, and the divergence will be discovered by the person who least expects it.

## Blast radius

Multiple reverted live fixes; one full lost-update clobber; hours of "which version is real?" archaeology per incident; and — the lasting cost — zero trust in any local dashboard copy, which is what finally made the policy inversion acceptable.

## The fix

Invert the rule: **the live file on the server is canonical.** Dashboards are explicitly *not* git-tracked. Workflow: pull the live file, edit, push back, verify at the live URL. "Done" means verified live.

Three guards, one per failure path:

- An **Edit/Write gate** blocks creating dashboard HTML in local scratch directories (kills the fork at birth).
- A **git-stage guard** blocks `git add`/`cp`/`mv` that would put dashboard HTML under version control (kills the well-intentioned "fix" that recreates the disease).
- A **staleness guard** records the SHA at pull time and blocks a push if the live file changed since (kills the lost update — the 2026-05-28 mechanism, specifically).

The honest cost: weaker version history for dashboards (server-side backups instead of git log) and no offline editing. Paid deliberately — editing a fiction is worse than a server round-trip.

## Has the guard fired since?

Regularly. The git-stage guard alone logged 12 blocks in a recent 12-day audit window — sessions still instinctively reach for `git add index.html`, and the guard still says no. The staleness guard's blocks are rarer but each one is a prevented lost-update. The instinct this postmortem documents has not gone away; it's just fenced.

## Lessons for agent-driven development

1. **Every artifact gets exactly one writable home.** The moment a second home exists, divergence is a scheduling question, not a risk.
2. **When production mutates files, git is not your source of truth — admit it.** Half-tracked state is worse than untracked state, because it carries false authority.
3. **File copy has no merge step.** Concurrent editors of a copied artifact will destroy each other's work politely and silently.
4. **Guard against the intuitive fix, not just the failure.** Two sessions independently proposed the fork-creating "solution." The guard that blocks the *plausible wrong fix* is the one that ends the recurrence loop.
