# META: How This Repo Was Reconstructed

Credibility in a failure record comes from method. This page is the method.

## Sources

Everything here was reconstructed from the private working repository's own records — none of it from memory:

- **The hook fleet itself:** ~148 logical hooks whose header comments conventionally document their origin incident, task numbers, and version history. A full-header sweep of every hook produced the largest single share of incident candidates.
- **The task database:** ~2,100+ tracked tasks; incident-shaped entries carry the forensics (what broke, what was tried, what shipped).
- **The append-only knowledge base:** validated findings, and — more useful here — its *corrections* layer: 90+ recorded instances of "the agent's belief was wrong," each with what replaced it.
- **The audit ledger:** an append-only JSONL of guard decisions (blocks, bypasses with reasons, policy violations). Every "has the guard fired since" figure cites it, with the evidence window stated (the raw log rotates; ~12 days at current volume — older claims cite weekly digests or task records instead).
- **Session handoffs and notes:** 1,300+ files ever created in the working repo's inbox/notes directories — including ~900 deleted ones, recovered from git history (`--full-history`; the naive form silently drops them, a lesson that is itself in a postmortem).
- **Degraded-window reviews:** systematic turn-by-turn re-reads of sessions from known-bad periods, diffing sessions against their own later statements.

## Method

For each document: pull the task entries and KB nodes → walk `git log` for the commit sequence → read the guard's source and header → read the period's handoffs → draft against the templates → sanitize → publish. The system logs its own failures (a corrections detector, a feedback-to-hook pipeline, the audit ledger), so reconstruction is retrieval plus writing, not archaeology.

**Numbers policy:** quantitative claims (fire counts, latencies, before/after metrics) come from the primary records above. Where a figure could not be re-verified against its source at writing time, it is hedged or omitted; evidence windows are labeled. One postmortem ([PM-026](postmortems/026-the-files-deleted-at-midnight.md)) is published explicitly *unsolved*, and one ([PM-013](postmortems/013-integrity-ledger-certified-fabricated-results.md)) documents a fix in progress — the policy is to say so rather than backdate tidy endings.

## Sanitization

A pre-publish scanner (`tools/sanitize_check.py`) runs against every push, checking for credentials, IPs, hostnames, private paths, personal identifiers, and an operator-maintained redline list (which includes all trading-strategy identifiers). By policy this repo never contains: server addresses, API key material, trading system names/parameters/results, or client names. Machine roles appear generically (the dev PC, the droplet, the compute worker). Task numbers and dates are kept — they're the citation trail.

The scanner itself is a descendant of a leak postmortem ([PM-030](postmortems/030-the-secret-the-hooks-could-not-see.md)), and its redline list is deliberately *not* published: a scanner containing the literal secret terms would itself be the leak.

## What this repo is not

Not a framework, not a benchmark, not advice. It's one operator's longitudinal failure record with the mechanisms that stopped each failure from recurring. Harness-specific details will rot; the patterns directory labels them as versioned. Check whether the harness you're running has equivalents before applying anything here.
