# The Autonomous Publisher Submitted the Same Orders Twice Because Its Drift Check Could Not See Pending Orders — and the Journal That Would Have Shown It Was Being Wiped Every 30 Minutes

**Keywords:** duplicate order submission, idempotency missing, drift check positions only, overnight queued market orders, cancel-and-replace, autonomous trading cron, audit journal wiped by git sync, hard-reset deploy, paper trading platform, six safety layers wrong threat

**Incident date:** observed 2026-07-30; fixed 2026-08-08; journal repaired 2026-08-15 · **Internal refs:** task #2460 (publisher v1.1 cancel-and-replace + cron leg removal + journal untrack) · **Status:** fixed; one week of post-fix runs verified clean on 2026-08-15; the cancel step is fail-closed and has aborted nothing yet because nothing has been stuck.

---

## What broke

A publisher script mirrors a paper-trading strategy's target portfolio to a third-party platform: it reads the latest allocation, diffs it against the platform's reported positions, and submits the minimum order set. It runs from cron several times a day with no human in the loop — the propose → ack → live safety chain exists in the code, but the cron auto-acks it.

Two of those runs were after the close (18:10) and before the open (08:10). Market orders submitted while the market is closed sit in a *Working* state on the platform until 09:30. The publisher's drift check — the layer that decides whether anything needs doing — compared **positions only**. Working orders were invisible to it. So at 08:10 the next morning the script saw the same positions, computed the same plan, and submitted it again. At the open, both copies executed. The second set of closes tried to sell shares the strategy no longer held, and the platform answered with "cannot sell, not owned" notices.

Observed 2026-07-30: the same four-order batch submitted in consecutive runs.

Nobody saw it in the order journal, because there was no order journal to see — see below.

## How it was detected

By the platform's rejection notices, read by a human. The publisher had six documented safety layers (dry-run default, sha-bound ack with TTL, an external-comms hook, a HALT sentinel, a dead-systems blocklist, and the drift re-check). All six guard against *submitting the wrong plan*. None guards against *submitting the right plan twice*. The threat model was "agent does something unapproved"; the failure was "agent does the approved thing again."

## Root cause

Surface: the drift check read a subset of the platform's state. Positions are what the strategy holds; Working orders are what it is about to hold. A check that diffs only the first will re-issue the second on every closed-market cycle until something fills.

Deeper:

- **No idempotency anywhere in the chain.** The platform's API has no client-side idempotency key (a known gap, listed as a risk in this repo's source ledger weeks before it fired). The publisher did not generate one either. With neither, "did I already submit this?" had to be answered by inspecting state — and the state inspected was incomplete.
- **A post-close submission leg that could never fill before the next leg ran.** The 18:10 run could only ever create overnight Working orders; by design it guaranteed the double-queue whenever the 08:10 run followed.
- **The audit trail was git-tracked on a host whose deploy mechanism is a hard reset.** The order journal (append-only JSONL of every submission) was committed to the repo. The droplet syncs by `git reset --hard` every 30 minutes ([PM-029](029-deploy-verified-then-reverted-thirty-minutes-later.md) documents the same mechanism reverting a deploy). Every sync restored the journal to its last committed state — which was 2026-06-02. For two months the strategy fired daily and the journal on the production host never advanced past June 2. The one artifact that would have shown "same batch, twice, consecutive runs" was being erased by the machinery that delivers code.

## Blast radius

Paper capital only — by policy this strategy never trades live money, and the duplicate closes failed rather than over-selling a real account. Real costs: an unknown number of duplicate submissions between the journal's June 2 freeze and July 30 (not enumerable — the evidence was wiped); the "not owned" notices visible to anyone following the public strategy; and a two-month hole in the audit record that cannot be backfilled.

## The fix

Four parts, all Brian-approved on 2026-08-08 and 08-15:

1. **Cancel-and-replace on closed-market live runs.** Before submitting, the 08:10 run cancels *all* Working signals on the platform, then submits the fresh plan. Fail-closed: any error in the cancel step aborts the run before anything is submitted. Because the propose step recomputes from absolute platform state, a skipped run self-heals at the next cycle instead of accumulating. Tested on a five-case offline harness (happy path, cancel failure, fetch failure, in-session run, email) before deploy.
2. **The 18:10 auto-live leg was removed** from the cron. The 18:05 *propose* is retained so the plan is visible; nothing is submitted after the close. The new 8/11/15 schedule was registered in the scheduled-jobs inventory with the stale "propose-only" comment corrected — the code comment had described a human-in-the-loop that the cron had long since automated away.
3. **Journal untracked from git.** `git rm --cached`, gitignored on both hosts, file stays on disk; a pre-migration backup was kept on the droplet to restore after the first post-change sync. The audit trail now survives the deploy. Entries wiped before the untrack are gone — the journal on the production host jumps from 06-02 to 08-17.
4. **Every cancel-and-replace is journaled and emailed**, so the next duplicate — if the cancel ever fails to clear one — announces itself.

## Has the guard fired since?

- One week of post-fix runs was verified clean on 08-15. In the journal that survives (08-17 onward, read on 08-23): every plan was submitted exactly once — a 1-order plan on 08-19, a 3-order plan on 08-21 — and no next-morning run re-submitted a prior day's batch. The cancel sweep writes no journal record when there is nothing to cancel, so "nothing was stuck" is inferred from the absence of duplicates, not observed directly. The fail-closed abort path has not been exercised in production; it passed the offline harness.
- The journal has advanced on every trading day since 08-17. Before the untrack, its last entry on the production host was dated 06-02 — 74 days without a record while the strategy fired daily.
- The operator-facing rules file had carried the same "propose-only, human ack required" description until 08-04 and the old schedule until 08-15; both corrected. Code comment, cron, and rules file had each been describing a safety property that no longer existed.

## Lessons for agent-driven development

1. **Idempotency is a property of the whole chain, not of any one layer.** Six layers that each answer "is this plan approved?" do not, together, answer "has this plan already been sent?" If the upstream API lacks an idempotency key, you must mint one or inspect *complete* state — and state includes what is pending, not just what is settled.
2. **A scheduled step that cannot succeed before the next step runs is a duplicate generator.** Check every cron leg against the question: can its effect be observed by the next leg? If not, the next leg will redo it.
3. **Audit logs must live outside the deploy mechanism's blast radius.** A hard-reset sync treats every tracked file as code. Anything that accumulates at runtime — journals, ledgers, state — is destroyed by the same step that ships the fix for destroying it.
4. **Safety-layer comments rot in the direction of more safety than exists.** The header said propose-only with human ack; the cron had been auto-acking for weeks. Documentation of a guard that has been removed is worse than no documentation: it forecloses the question.
5. **"Paper" is where you find this; the fix is the same as for real money.** The platform rejected the duplicate sells because the paper account had nothing left to sell. A margin account would have filled them.
