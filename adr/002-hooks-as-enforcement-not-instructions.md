# ADR-002: Rules are enforced by hooks, not written as instructions

**Status:** Active · **Date:** 2026-03 onward (the repo's founding thesis) · **Internal refs:** ~100 hooks across 5 months

## Context

Every incident produced a rule. The rules went into CLAUDE.md (Claude Code's project-instructions file), and the agent followed them — usually. "Usually" is the problem. Instruction adherence decays with context length, with session count, and with how far the current task sits from the rule's original context. At 1–2 sessions you can supervise the gap. At 7–12 concurrent sessions running multi-day tasks, "the model usually complies" means a violation somewhere every day, and the violations cluster exactly where they're expensive: destructive git operations, external communications, deploys, data deletion.

## Decision

**Every durable rule gets a mechanism, or it isn't a rule.** The instruction file still exists — it carries context and rationale — but anything that must not happen is enforced by a hook at one of three choke points:

- **PreToolUse gates**: block the tool call before it executes (destructive git commands, writes outside canonical paths, scp to the droplet, file collisions with another session).
- **Stop hooks**: block the *response* from being delivered until it complies (sycophantic phrasing, missing status blocks, banned rationalizations like "good enough for now").
- **Context injectors** (UserPromptSubmit / SessionStart): push current state — task leases, KB corrections, session status — into every turn, so compliance doesn't depend on the model remembering to look.

Escape hatch convention: every guard supports a bypass environment variable of the form `SKIP_<GUARD>="reason:<text>"`. The reason string is logged. This keeps guards from becoming workflow-killers while making every bypass auditable — a silent override is the thing we're trying to eliminate.

## Alternatives considered

- **Bigger, sterner instructions.** Tried for the first weeks. Decays; also competes for context budget with actual work.
- **Human review of everything.** Doesn't scale past ~2 sessions, and the operator's review attention is the scarcest resource in the whole system.
- **Trusting model improvements.** Each model generation followed instructions better, and each still violated the expensive ones occasionally. "Occasionally" times 12 sessions times 5 months is a lot of incidents.

## Consequences

- ~100 hooks (~211 files) is a real maintenance surface with its own failure modes: false positives that block legitimate work, hook latency on every tool call, and hooks that break when the harness changes.
- **The guards themselves become load-bearing infrastructure** — and can cause incidents. [PM-004](../postmortems/004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md) is a safety wrapper nearly leaking a private repo. Who guards the guards is not a rhetorical question; it's a test suite.
- New-rule reflex changed permanently: an incident isn't closed by writing the rule down; it's closed when the hook that makes recurrence impossible is deployed and has a passing self-test.

## What we'd do differently

Adopt a hook registry and per-hook self-tests from the start. The first ~30 hooks were artisanal; retrofitting discipline onto them cost more than building it in would have.
