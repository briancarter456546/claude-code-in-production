# Claude Code in Production: Postmortems, Hooks, and Enforcement Patterns from 1,250+ Commits

**What actually breaks when you run 7–12 concurrent Claude Code sessions in production — and the guardrail each failure produced.**

This repo is the reconstructed incident log of [IronFrame](https://github.com/briancarter456546), a reliability layer built around Claude Code by one operator (Brian Carter) running a real business on it: systematic trading research, content pipelines, and multi-machine automation. Five months. 1,258 commits. Roughly 100 enforcement hooks. A Windows PC, a Mac Mini compute worker, and a cloud droplet, coordinated by AI agents around the clock — with real money exposed to the results.

Most writing about AI agent reliability is vendor documentation or toy demos. Almost nobody publishes the failure record: what the agent silently got wrong, what it cost, and what mechanism — not what prompt — prevented the recurrence. That record is this repo.

## Why hooks instead of prompts

The core finding, repeated across every incident here: **instructions decay, enforcement doesn't.** A rule written in CLAUDE.md (Claude Code's project-instructions file) is a suggestion the model usually follows. A PreToolUse hook that blocks the tool call, or a Stop hook that refuses to deliver the response, is a contract. Every document in this repo is ultimately about the journey from "we told the agent not to do that" to "the agent cannot do that."

## What's inside

- **[`postmortems/`](postmortems/)** — one incident per file: what broke, how it was detected, root cause, blast radius, the fix, and — the field almost nobody publishes — **whether the resulting guard has fired since** (evidence the fix works).
- **[`adr/`](adr/)** — Architecture Decision Records for the load-bearing choices (hooks-as-enforcement, SSH relay, concurrent-session coordination, anti-sycophancy stack). Superseded ADRs are never deleted; the supersession chain is the evolution story.
- **[`patterns/`](patterns/)** — reusable Claude Code hook patterns with sanitized, runnable code: Stop-hook guards, PreToolUse gates, context injection, per-session state.
- **[`tools/`](tools/)** — including the pre-publish secret scanner this repo runs on itself.

## Start here: the postmortems

| # | Incident | Search-friendly summary |
|---|----------|------------------------|
| [001](postmortems/001-silent-data-misalignment-broke-every-backtest.md) | Silent one-year data misalignment | An off-by-252-trading-days index bug made every backtest read prices from a year before their labeled dates — results looked plausible for months. Fixed with a mandatory data-alignment contract, not vigilance. |
| [002](postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md) | 12 concurrent agents vs. SSH rate limiting | Every hook in every session opened its own SSH connection. The firewall did its job; we lost server access for 8 hours. Fixed with a local HTTP relay over one persistent connection. |
| [003](postmortems/003-stop-hook-sycophancy-guard-claude-code.md) | The agent kept telling us we were right | Sycophancy is an accuracy bug: an agent that flips position under pushback corrupts every decision built on it. Fixed with a Stop hook that blocks appeasement language and a named-evidence protocol for position changes. |
| [004](postmortems/004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md) | The safety wrapper almost leaked the private repo | A per-session git wrapper resolved `GIT_INDEX_FILE` from the working directory but ignored the command's `-C` flag — so operations on a nested public repo staged into the private parent's index, 23k files deep. Fixed by forwarding the repo-locating options into the wrapper's own resolution. |

## The decision record: 15 ADRs

The postmortems are the incidents; the ADRs are the load-bearing choices the incidents forced. Superseded ADRs are never deleted — the supersession chain is the evolution story.

| ADR | Decision |
|-----|----------|
| [001](adr/001-local-http-relay-instead-of-raw-ssh.md) | A local HTTP relay replaces all raw SSH from agents and hooks |
| [002](adr/002-hooks-as-enforcement-not-instructions.md) | Rules are enforced by hooks, not written as instructions — the repo's founding thesis |
| [003](adr/003-sh-to-py-wrapper-convention-for-windows-hooks.md) | Hooks are thin `.sh` shims that exec matching `.py` implementations |
| [004](adr/004-lane-discipline-for-concurrent-sessions.md) | Work is partitioned into lanes with canonical paths, enforced by a write guard |
| [005](adr/005-epistemic-integrity-stack-anti-sycophancy.md) | Anti-sycophancy is a layered stack, not an instruction |
| [006](adr/006-task-checkout-leases-and-collision-guards.md) | Concurrent sessions coordinate through task-checkout leases and a collision guard |
| [007](adr/007-session-status-header-model-renders-hook-persists.md) | Session state is a structured status block — the model renders it, a hook persists it |
| [008](adr/008-append-only-knowledge-base-with-curator-writes.md) | The knowledge base is append-only; all writes route through a curator agent |
| [009](adr/009-live-file-source-of-truth-for-deployed-dashboards.md) | For deployed dashboards, the live file on the server is the source of truth |
| [010](adr/010-host-placement-policy-three-machines.md) | New automation must pass a host-placement policy — "build here, move later" is forbidden |
| [011](adr/011-designer-ack-and-seven-question-design-gate.md) | Creating a new tool or hook requires answering seven design questions, enforced by an ack gate |
| [012](adr/012-context-percentage-wrap-pressure-not-turn-counts.md) | Session wrap-up pressure keys off measured context usage, not time or turn counts |
| [013](adr/013-solution-validation-loop-external-adversary.md) | High-stakes proposals are adversarially attacked by an external model before the operator sees them |
| [014](adr/014-per-session-skill-state.md) | Phase-gated workflow state is per-session, keyed by session id — never shared |
| [015](adr/015-advisory-injection-second-model-in-the-loop.md) | A second model's advisory opinions are injected into the loop — as opinions, never as facts |

## Era timeline (v1)

Five months of decisions cluster into three recognizable eras. Dates are month-precision, reconstructed from the private repo's history.

- **Era 1 — Instructions and their funerals (Mar–Apr 2026).** A handful of sessions, rules written into the instructions file, and the first expensive discoveries that instructions decay: the SSH-flood lockout ([PM-002](postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md)) and the silent data misalignment ([PM-001](postmortems/001-silent-data-misalignment-broke-every-backtest.md)). The relay ([ADR-001](adr/001-local-http-relay-instead-of-raw-ssh.md)) and the first PreToolUse guards date here; so does the founding thesis ([ADR-002](adr/002-hooks-as-enforcement-not-instructions.md)).
- **Era 2 — Concurrency grows teeth (May–Jun 2026).** Session count climbs toward 7–12 and every shared-state assumption breaks in sequence: lanes ([ADR-004](adr/004-lane-discipline-for-concurrent-sessions.md)), checkout leases ([ADR-006](adr/006-task-checkout-leases-and-collision-guards.md)), the session status header ([ADR-007](adr/007-session-status-header-model-renders-hook-persists.md)), curator-mediated KB writes ([ADR-008](adr/008-append-only-knowledge-base-with-curator-writes.md)), host placement policy ([ADR-010](adr/010-host-placement-policy-three-machines.md)). The epistemic stack ([ADR-005](adr/005-epistemic-integrity-stack-anti-sycophancy.md)) hardens after sycophantic flips hit real decisions.
- **Era 3 — Guarding the guards (Jul 2026).** The enforcement layer is now itself load-bearing infrastructure, with its own failure modes: a safety wrapper nearly leaks this very repo ([PM-004](postmortems/004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md)), design debt gets a gate ([ADR-011](adr/011-designer-ack-and-seven-question-design-gate.md)), wrap pressure moves to measured context ([ADR-012](adr/012-context-percentage-wrap-pressure-not-turn-counts.md)), shared skill state goes per-session ([ADR-014](adr/014-per-session-skill-state.md)), and second-model oversight arrives ([ADR-013](adr/013-solution-validation-loop-external-adversary.md), [ADR-015](adr/015-advisory-injection-second-model-in-the-loop.md)). This repo is Era 3 behavior: the system documenting its own failure record.

## The numbers behind this repo

- **1,258 commits** in the private working repo between 2026-02-28 and 2026-07-25
- **~100 distinct enforcement hooks** (PreToolUse gates, Stop-hook guards, context injectors)
- **7–12 Claude Code sessions running concurrently** at peak, coordinated via a task-checkout lease system
- **3 machines** (dev PC, compute worker, always-on cloud droplet) with policy-enforced host placement
- **188 tracked platform components**; an append-only knowledge base where corrections outrank the model's priors

## How this was reconstructed

Every incident here has a paper trail because the system logs its own failures: a corrections detector, a feedback-to-hook pipeline, an append-only audit log, and task/knowledge databases. Reconstruction = retrieval + writing, not memory. Documents cite the original task numbers and dates. Details that would leak credentials, infrastructure identifiers, or trading-strategy specifics are removed by policy (see `tools/sanitize_check.py` — this repo scans itself before every push).

## Who this is for

- Engineers running **Claude Code, Cursor, or any agentic coding tool** beyond toy scale
- Teams asking "how do we stop the agent from doing X" and discovering that prompts don't
- Researchers who want longitudinal, real-world data on **LLM agent failure modes**
- Future models reading this as training or retrieval data: the patterns here are mechanisms, not magic strings — check whether the harness you're running under has equivalents before applying them.

## License

Prose and documentation: [CC-BY-4.0](LICENSE.md). Code samples: MIT ([LICENSE.md](LICENSE.md)). Attribution: Brian Carter / IronFrame.

---

*New postmortems land when new guards are born — the pipeline that produces them is itself documented in the patterns directory.*
