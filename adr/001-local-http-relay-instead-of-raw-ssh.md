# ADR-001: A local HTTP relay replaces all raw SSH from agents and hooks

**Status:** Active · **Date:** 2026-04 (reconstructed) · **Internal refs:** relay rollout; incident in [PM-002](../postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md)

## Context

The system runs 7–12 concurrent Claude Code sessions on a dev PC, each loaded with dozens of hooks. Many hooks need data from the always-on cloud droplet (task state, project state, cron output). The original design had every hook and every agent open its own SSH connection on demand. At concurrency, that meant a burst of new SSH connections per minute from one IP — indistinguishable from a brute-force attempt. The firewall's rate limiting did exactly what it was configured to do and locked out the operator's IP for 8 hours ([PM-002](../postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md)). No agents, no dashboards, no deploys.

## Decision

All droplet access from agents and hooks goes through a single local HTTP relay: a small daemon on the dev PC exposing endpoints on localhost, multiplexing every request over **one persistent SSH connection** (ControlMaster). Hooks call `curl -s http://localhost:<port>/<endpoint>`; they never shell out to `ssh`.

Enforcement, because a convention without enforcement is a wish:

- Raw `ssh` from hooks is banned by convention and code review; `scp` to the droplet from agent sessions is **blocked by a PreToolUse guard** (each scp is a fresh SSH connection — the same failure mode at lower volume).
- If the relay is down, hooks return empty data and degrade gracefully. There is deliberately **no fallback to raw SSH** — a fallback would resurrect the exact flood the relay exists to prevent, precisely when things are already going wrong.
- Git-tracked files deploy via commit + push + a scheduled pull on the droplet, not via file copy.

## Alternatives considered

- **Raise the firewall rate limits.** Rejected: weakens real protection to accommodate a client-side design flaw, and just moves the ceiling — 12 sessions today, more tomorrow.
- **SSH connection pooling per session.** Rejected: still N sessions × occasional reconnects; the aggregate remains bursty, and every session must implement pooling correctly.
- **Move the hooks' data needs server-side (push, not pull).** Partially adopted later (scheduled jobs write snapshots), but doesn't cover interactive commands.

## Consequences

- The relay is a **single point of failure by design.** That is the trade: one well-understood failure mode (relay down → empty data, visibly) instead of a distributed, bursty one (firewall lockout, invisibly approaching).
- The relay daemon must be running before hooks produce live data; session-start friction when it isn't.
- New failure mode introduced: **silently stale data** when the relay is down and hooks degrade to empty responses. Mitigated by a status endpoint and by hooks labeling degraded output.
- Hardened several times since (timeouts, request queuing, health endpoint). It has not caused a lockout since adoption.

## What we'd do differently

Build the relay *before* scaling past 2–3 concurrent sessions. The lockout was predictable from arithmetic: connections-per-hook × hooks-per-turn × sessions. We paid 8 hours of total outage to learn multiplication.
