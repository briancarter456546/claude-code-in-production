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
