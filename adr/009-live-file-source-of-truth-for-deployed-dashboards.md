# ADR-009: For deployed dashboards, the live file on the server is the source of truth

**Status:** Active · **Date:** 2026-07 (after repeated stale-fork incidents) · **Internal refs:** source-of-truth gate, git-stage guard, staleness guard

## Context

Ops dashboards are served from the always-on droplet. The intuitive workflow — keep the dashboard's HTML in the git repo, edit locally, deploy a copy — created **stale forks**: the local "canonical" copy and the live file diverged silently, because hotfixes happened on the server, cron jobs regenerated sections in place, and multiple sessions each held their own local copy. Sessions then confidently edited a local file that no longer resembled production and deployed regressions over live fixes. The same lost-update pattern hit in both directions.

## Decision

Inversion of the usual rule: **the live file on the server is canonical.** Dashboards are explicitly *not* git-tracked — a tracked copy is a fork waiting to go stale. The workflow is: pull the live file down, edit, push back, verify at the live URL. "Done" means verified live, never "works locally."

Three guards enforce it (one per failure path):

- An **Edit/Write gate** blocks creating or editing dashboard HTML in the legacy local scratch directories.
- A **git-stage guard** blocks `git add`/`cp`/`mv` that would re-introduce a dashboard file into version control.
- A **staleness guard** compares timestamps/hashes before an upload to catch the lost-update case — pushing over a live file that changed since you pulled it.

## Alternatives considered

- **Git as source of truth with disciplined deploys.** The original design. Fails because *discipline is the thing that doesn't scale* across 12 sessions and server-side mutation (crons rewriting live files).
- **Making live files immutable (all changes via git deploy).** Rejected: several dashboards are partially regenerated in place by scheduled jobs; freezing them means rearchitecting working production for the benefit of the workflow.
- **Two-way sync automation.** Rejected: automated bidirectional sync of divergent files is conflict resolution without a human, i.e., data loss with extra steps.

## Consequences

- Editing requires a server round-trip; no offline dashboard work.
- Version history for dashboards is weaker (server-side backups instead of git log) — a real loss, accepted in trade for never editing a fiction.
- The rule is counterintuitive enough ("*don't* put it in git?") that the guards do regular work blocking well-meaning sessions; this is the guard system functioning, not failing.

## What we'd do differently

Recognize the pattern category sooner: this is the third subsystem where "a copy of the truth" caused incidents (dashboards, price data, instructions duplicated into docs). The general rule — every datum gets exactly one canonical home, and copies are either regenerated or forbidden — should have been an ADR before any of its instances.
