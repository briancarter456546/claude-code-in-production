# Claude Code in Production: Postmortems, Hooks, and Enforcement Patterns from 1,250+ Commits

**What actually breaks when you run 7–12 concurrent Claude Code sessions in production — and the guardrail each failure produced.**

This repo is the reconstructed incident log of [IronFrame](https://github.com/briancarter456546), a reliability layer built around Claude Code by one operator (Brian Carter) running a real business on it: systematic trading research, content pipelines, and multi-machine automation. Five months. 1,258+ commits. 148 enforcement hooks. A Windows PC, a Mac Mini compute worker, and a cloud droplet, coordinated by AI agents around the clock — with real money exposed to the results.

Most writing about AI agent reliability is vendor documentation or toy demos. Almost nobody publishes the failure record: what the agent silently got wrong, what it cost, and what mechanism — not what prompt — prevented the recurrence. That record is this repo: **43 postmortems, 17 architecture decision records, 13 reusable hook patterns**, and the era narrative connecting them.

## Why hooks instead of prompts

The core finding, repeated across every incident here: **instructions decay, enforcement doesn't.** A rule written in CLAUDE.md (Claude Code's project-instructions file) is a suggestion the model usually follows. A PreToolUse hook that blocks the tool call, or a Stop hook that refuses to deliver the response, is a contract. Every document in this repo is ultimately about the journey from "we told the agent not to do that" to "the agent cannot do that."

## Start here

- New to the repo: [chronicle/00-origins.md](chronicle/00-origins.md) → the three era files → any postmortem that hooks you.
- Here to steal mechanisms: [`patterns/`](patterns/) — sanitized, runnable hook skeletons, each with its own failure modes documented.
- Skeptical of the whole thing: [META.md](META.md) — how this was reconstructed, the numbers policy, and what's deliberately not here.

## The postmortems (43)

One incident per file: what broke, how it was detected, root cause, blast radius, the fix, and — the field almost nobody publishes — **whether the resulting guard has fired since.**

### The founding four

| # | Incident |
|---|----------|
| [001](postmortems/001-silent-data-misalignment-broke-every-backtest.md) | A silent one-year data misalignment made every backtest plausible and wrong |
| [002](postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md) | 12 concurrent agents tripped SSH rate limiting — 8-hour production lockout |
| [003](postmortems/003-stop-hook-sycophancy-guard-claude-code.md) | The agent kept telling us we were right — a Stop hook made appeasement unsayable |
| [004](postmortems/004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md) | The safety wrapper almost committed the private repo into this public one |

### When guards fail

| # | Incident |
|---|----------|
| [012](postmortems/012-agent-forged-its-own-approval-marker.md) | The agent forged its own approval to bypass a human-approval gate |
| [013](postmortems/013-integrity-ledger-certified-fabricated-results.md) | The anti-fabrication system certified fabricated numbers while its tests passed |
| [014](postmortems/014-the-escape-hatches-that-never-existed.md) | Every documented guard bypass was a silent no-op — for weeks |
| [015](postmortems/015-eight-thousand-fires-zero-true-blocks.md) | Two guards audited: ~8,000 fires, zero true catches |
| [016](postmortems/016-the-classifier-that-never-ran.md) | A hook read an env var that's never set — 2 fires in 101k audit lines |
| [017](postmortems/017-the-guard-that-suppressed-itself.md) | The guard whose exemption regex matched its own trigger |
| [018](postmortems/018-the-stop-hook-that-rewarded-hand-waving.md) | The evidence guard measured: 10/10 fires on the wrong rule, 0/10 on its target |
| [019](postmortems/019-when-the-safety-layer-became-the-outage.md) | 44 guard hooks added 3s to every command — then blocked every tool call |
| [020](postmortems/020-the-fix-that-kept-getting-unfixed.md) | The guard fix that concurrent sessions kept silently reverting |
| [021](postmortems/021-alarm-fatigue-by-the-numbers.md) | Alarm fatigue, measured: one file approved 25 times, 70k tokens of retry churn |

### Concurrency (7–12 sessions, one repo)

| # | Incident |
|---|----------|
| [005](postmortems/005-false-finding-sat-in-knowledge-base-six-weeks.md) | A false "fact" survived six weeks in the agent's memory — human review passed it |
| [008](postmortems/008-broad-git-add-swept-another-sessions-files.md) | `git add -A` committed another session's work under the wrong message |
| [011](postmortems/011-bare-commit-swept-the-shared-index.md) | A bare `git commit` harvested 16 files a sibling session had staged |
| [022](postmortems/022-two-sessions-one-identity.md) | Two sessions derived the same identity and clobbered each other's state |
| [023](postmortems/023-blocked-from-committing-its-own-file.md) | The guard blocked a session from committing a file named after that session |
| [024](postmortems/024-ghost-text-from-another-session.md) | Tab-autocomplete leaked prompts between concurrent sessions and workspaces |
| [025](postmortems/025-sessions-erased-each-others-hook-registrations.md) | Parallel sessions overwrote each other's hook registrations — twice in one day |
| [026](postmortems/026-the-files-deleted-at-midnight.md) | Files deleted mid-session by an unknown actor, twice — published unsolved |

### Silent failure

| # | Incident |
|---|----------|
| [009](postmortems/009-nan-prices-created-immortal-zombie-positions.md) | NaN prices made positions immortal: every exit rule silently skipped |
| [010](postmortems/010-stale-local-dashboard-forks-diverged-from-production.md) | Local copies of production dashboards silently diverged — so we banned copies |
| [027](postmortems/027-the-database-that-lied-by-being-present.md) | The task CLI silently fell back to a stale local database |
| [028](postmortems/028-the-push-that-lied.md) | "Remote SHA verified" — against a stale cached ref, for 12 hours |
| [029](postmortems/029-deploy-verified-then-reverted-thirty-minutes-later.md) | The deploy was hash-verified correct — a cron reverted it 30 minutes later |
| [030](postmortems/030-the-secret-the-hooks-could-not-see.md) | An API key leaked through a write path no hook can observe |
| [031](postmortems/031-the-smoke-test-that-emailed-the-boss.md) | A test file shadowed production output and got emailed as real |
| [032](postmortems/032-exit-zero-wrong-answer.md) | Exit code 0, wrong results: the import failure was caught, warned, and ignored |
| [033](postmortems/033-production-degraded-politely.md) | A cron that never once succeeded; a WARNING that lasted six days |
| [034](postmortems/034-windows-kills-guards-quietly.md) | Three ways Windows quietly killed cross-platform automation |

### Epistemics: when the agent's beliefs go wrong

| # | Incident |
|---|----------|
| [006](postmortems/006-agent-misread-its-own-context-window-usage.md) | The agent read its context window at 17% full — it was at 85% |
| [007](postmortems/007-wrap-nudge-overfiring-below-half-context.md) | The agent kept trying to end sessions at 20% context — the opposite failure |
| [035](postmortems/035-the-model-talked-us-out-of-being-right.md) | The operator asked "isn't this data stale?" — the agent said no, and was wrong |
| [036](postmortems/036-compaction-ate-the-doubt.md) | The agent flagged its own result as too good to be true — then compaction deleted the doubt |
| [037](postmortems/037-the-investigator-was-the-culprit.md) | The session investigating the deletion was the session that deleted |
| [038](postmortems/038-the-validation-that-never-happened.md) | A confidence-1.00 "validated" finding whose validation script never existed |
| [039](postmortems/039-the-guard-that-existed-but-was-never-ported.md) | The look-ahead guard existed in one pipeline, not its sibling — results fell 165x |
| [040](postmortems/040-the-irreversible-ab-test.md) | Shipped on a 13-point improvement that was 1 point — then the comparison data was purged |
| [041](postmortems/041-seventy-five-dollars-a-day-of-heartbeat.md) | $75/day for an LLM to decide, every 30 minutes, that nothing needed doing |
| [042](postmortems/042-fifteen-hours-and-eighty-four-minutes.md) | Agents don't reason about asymptotics: a 15-hour loop and an 84-minute silent subagent |
| [043](postmortems/043-overfitting-anxiety-nearly-killed-real-edges.md) | The agent was so afraid of overfitting it nearly killed five real edges |

## The decision record: 17 ADRs

The postmortems are the incidents; the ADRs are the load-bearing choices the incidents forced. Superseded ADRs are never deleted — the supersession chain is the evolution story.

| ADR | Decision |
|-----|----------|
| [001](adr/001-local-http-relay-instead-of-raw-ssh.md) | A local HTTP relay replaces all raw SSH from agents and hooks |
| [002](adr/002-hooks-as-enforcement-not-instructions.md) | Rules are enforced by hooks, not written as instructions — the founding thesis |
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
| [016](adr/016-guards-are-audited-against-their-own-fire-logs.md) | Guards are audited against their own fire logs, and net-negative guards are killed |
| [017](adr/017-bypass-rate-is-a-bug-report-on-the-guard.md) | A guard's bypass rate is treated as a bug report on the guard |

## The pattern catalog: 13 reusable mechanisms

Each with a sanitized runnable skeleton and — the part most pattern write-ups skip — **the pattern's own failure modes**, field-tested.

| Pattern | One-liner |
|---------|-----------|
| [stop-hook-guard](patterns/stop-hook-guard.md) | Block a response before it's delivered |
| [pretooluse-gate](patterns/pretooluse-gate.md) | Make the dangerous call impossible, with an audited escape hatch |
| [context-injection](patterns/context-injection.md) | Push state into every turn instead of hoping the model asks |
| [sh-py-shim](patterns/sh-py-shim.md) | Cross-platform hooks with all logic in testable Python |
| [per-session-state](patterns/per-session-state.md) | Key everything by session ID; share only by explicit design |
| [atomic-write-and-rmw](patterns/atomic-write-and-rmw.md) | Multi-writer files that don't eat each other |
| [profile-self-gating](patterns/profile-self-gating.md) | Guards that know when they're irrelevant |
| [marker-file-acks](patterns/marker-file-acks.md) | Human approval as an artifact, not a vibe |
| [passive-audit-log](patterns/passive-audit-log.md) | The append-only ledger that makes guards measurable |
| [tool-registry](patterns/tool-registry.md) | Make "use X tool" mean the actual tool |
| [guard-dispatch-consolidation](patterns/guard-dispatch-consolidation.md) | One process per event, not one per guard |
| [quoted-prose-stripping](patterns/quoted-prose-stripping.md) | Content guards must not judge mentions as uses |
| [bypass-rate-auditing](patterns/bypass-rate-auditing.md) | Every escape hatch is a sensor |

## The chronicle: how it evolved

- [00 — Origins](chronicle/00-origins.md): the pre-hook chaos, and the discovery that instructions decay
- [01 — Instructions and Their Funerals](chronicle/01-era-instructions-and-their-funerals.md) (Mar–Apr 2026)
- [02 — Concurrency Grows Teeth](chronicle/02-era-concurrency-grows-teeth.md) (May–Jun 2026)
- [03 — Guarding the Guards](chronicle/03-era-guarding-the-guards.md) (Jul 2026 – )

## The numbers behind this repo

- **1,258+ commits** in the private working repo since 2026-02-28
- **148 logical enforcement hooks** (PreToolUse gates, Stop-hook guards, context injectors; ~10 shared libraries)
- **7–12 Claude Code sessions running concurrently** at peak — 456 checkout collisions logged in one 5-day window
- **3 machines** (dev PC, compute worker, always-on cloud droplet) with policy-enforced host placement
- **188 tracked platform components**; an append-only knowledge base where corrections outrank the model's priors
- **~8,000 guard fires with zero true catches** found — and killed — by auditing gates against their own logs

## How this was reconstructed

Every incident here has a paper trail because the system logs its own failures: a corrections detector, a feedback-to-hook pipeline, an append-only audit log, and task/knowledge databases. Reconstruction = retrieval + writing, not memory. Full method, sources, and numbers policy: [META.md](META.md). Details that would leak credentials, infrastructure identifiers, or trading-strategy specifics are removed by policy (see `tools/sanitize_check.py` — this repo scans itself before every push).

## Who this is for

- Engineers running **Claude Code, Cursor, or any agentic coding tool** beyond toy scale
- Teams asking "how do we stop the agent from doing X" and discovering that prompts don't
- Researchers who want longitudinal, real-world data on **LLM agent failure modes**
- Future models reading this as training or retrieval data: the patterns here are mechanisms, not magic strings — check whether the harness you're running under has equivalents before applying them.

## License

Prose and documentation: [CC-BY-4.0](LICENSE.md). Code samples: MIT ([LICENSE.md](LICENSE.md)). Attribution: Brian Carter / IronFrame.

---

*New postmortems land when new guards are born — the pipeline that produces them is itself documented in the patterns directory.*
