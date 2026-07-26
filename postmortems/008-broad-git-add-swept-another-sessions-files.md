# `git add -A` With Concurrent AI Agents: One Session Committed Another Session's Work

**Keywords:** git add -A dangers, concurrent AI agents git, shared git index, Claude Code multiple sessions, commit hygiene automation, git staging collisions, agent version control

**Incident window:** 2026-05-12 first confirmed; recurrence same day the "fix" was declared done (2026-05-22) · **Internal refs:** tasks #1128, #1377; commit 3a5b6517 · **Status:** mitigated by a guard family; still fires weekly (evidence below)

---

## What broke

Multiple Claude Code sessions share one repository working tree and therefore one git index. A session finishing a trading-systems audit ran a broad `git add` and committed. The commit — labeled as the audit — also contained a *tax document rollup* that a completely different session had generated and not yet committed.

The immediate damage is misattribution: files land under a commit message that has nothing to do with them, signed by a session that never touched them. The compounding damage is archaeological: months later, `git log -- <that-file>` returns a lie. Every future investigation that trusts commit provenance inherits the corruption.

The kicker: the first guard shipped on the morning of 2026-05-22, the task was marked done — and **the same class of sweep recurred that afternoon** through a path the first guard didn't cover. "Explicit paths" turned out to be insufficient scoping too, because the danger lives in the *staging area's shared state*, not just in the `add` command's breadth (see [PM-011](011-bare-commit-swept-the-shared-index.md) for the second half of this story).

## How it was detected

A later session investigating the tax files found them buried in commit `3a5b6517` under the message "37-systems C2 audit" — a commit whose author-session verifiably never worked on taxes. The paper trail itself raised the alarm; nothing at commit time did.

## Root cause

`git add -A` / `git add .` answer the question "what changed in this tree?" — but with N concurrent sessions, "what changed" includes *everyone's* uncommitted work. The command has no concept of authorship. The deeper cause: **git's staging model assumes one human per working tree**, and every agent-automation pattern built on "add everything, commit, move on" imports that assumption silently.

## Blast radius

Corrupted commit provenance on affected paths (permanent — history rewrites on a shared branch were judged worse than the disease); one confirmed recurrence after the first fix; a lasting rule change in how every session stages work.

## The fix

A layered guard family, built incident by incident:

- **`git add` breadth guard (PreToolUse):** blocks `-A`, `.`, and glob adds that would recurse into paths the session hasn't touched. Additions must be scoped.
- **Per-session touched-files journal:** hooks record which files *this* session actually modified, giving later guards an authorship oracle (imperfect — see [PM-023](023-blocked-from-committing-its-own-file.md) for its own failure mode).
- Downstream layers for the staging half: pathspec-required commits and stranger-file detection ([PM-011](011-bare-commit-swept-the-shared-index.md)).

## Has the guard fired since?

Continuously — this family does more live blocking than almost anything else in the stack. In one recent 12-day audit window: broad-add guard **5 blocks**, pathspec-commit guard **17 blocks**, stranger-file guard **19 blocks + 14 reason-logged bypasses**. Cross-session staging attempts are still a weekly event; they just stop at the gate now. (Fire counts are from the append-only audit log; the window is bounded by log rotation and labeled accordingly.)

## Lessons for agent-driven development

1. **`git add -A` is a single-player command.** The moment two agents share a working tree, breadth becomes theft — of attribution, at minimum.
2. **"Done" on a race-condition fix means "survived the next race,"** not "shipped this morning." Ours recurred within hours, through the adjacent gap.
3. **Provenance corruption outlives the incident.** The expensive cost wasn't the day of confusion; it's that `git log` lies about those paths forever.
4. **Authorship needs its own record.** Git doesn't know which session touched a file; if your guards need that fact, you must journal it yourself — and then treat the journal as a component with its own failure modes.
