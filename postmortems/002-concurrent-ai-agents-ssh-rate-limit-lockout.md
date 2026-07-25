# 12 Concurrent AI Agents Locked Us Out of Our Own Server for 8 Hours

**Keywords:** Claude Code concurrent sessions, SSH rate limiting, UFW, AI agent infrastructure, connection pooling, ControlMaster, agent swarm, DevOps for AI agents, relay pattern

**Incident date:** 2026-03-20 · **Internal refs:** tasks #2012, #2025, #2086, #2087 · **Status:** fixed; pattern has been hardened four times since

---

## What broke

Every Claude Code session in this setup runs lifecycle hooks — on session start, on every prompt, on tool calls — and many of those hooks need something from the production droplet: task state, knowledge-base context, project status. The original implementation did the obvious thing: each hook ran `ssh droplet "command"`.

The obvious thing multiplied badly. One session spawned **15+ independent SSH connections per session**, and at peak there were **7–12 sessions running concurrently**. The droplet's firewall (UFW with SSH rate limiting) saw a burst of connection attempts from one IP and did exactly what it is configured to do: classified it as an SSH brute-force attempt and dropped the source.

Result: **8 hours locked out of our own production server**, with scheduled trading-pipeline jobs running unsupervised on it the whole time.

## How it was detected

SSH began timing out from every terminal, not just from agent sessions. The droplet was fine — dashboards served, crons ran — it just would not talk to us. That asymmetry (services up, admin path down) is the fingerprint of a network-layer block rather than a server failure, and console access via the cloud provider confirmed the firewall state.

## Root cause

Three compounding design errors, all boring, all common:

1. **No connection reuse.** Each hook invocation opened a fresh TCP + SSH handshake. Nothing shared anything.
2. **Fan-out nobody sized.** Hooks were written one at a time, each individually innocent. Nobody multiplied hooks × prompts × sessions. The system's aggregate SSH rate was an emergent property nobody had ever computed.
3. **The agent multiplies your mistakes.** A human runs `ssh` a few times a minute at worst. An agent harness runs it on every lifecycle event of every parallel session. Any per-call cost or risk you would tolerate manually becomes a flood at agent scale.

Note what the root cause is *not*: the firewall. The rate limit was correct. Building around it (raising limits, whitelisting) would have hidden the design flaw, not fixed it.

## The fix: one door, one connection

A **local HTTP relay** — a small Flask process on the dev machine (`localhost:5050`) that owns exactly **one persistent SSH connection** (OpenSSH `ControlMaster` multiplexing) to the droplet. Every hook and agent now calls:

```bash
curl -s -X POST http://localhost:5050/run --data-urlencode 'cmd=...'
```

instead of `ssh`. From the droplet's perspective, twelve chattering agent sessions collapse into a single long-lived connection.

Design decisions that mattered:

- **Fail-soft, never fall back.** If the relay is down, hooks return empty context gracefully. They do *not* fall back to raw SSH — a fallback would silently recreate the flood exactly when the system is already degraded.
- **Enforcement, not convention.** "Use the relay" as a written rule lasted until the first agent forgot it. It became a PreToolUse hook that blocks raw `ssh` from agent sessions outright.

## Evolution since (the part that usually goes unwritten)

The relay pattern was not born finished. Four hardenings, each from a real failure:

1. **`scp` banned too** (internal #2012). File copies were originally exempt ("single connection, it's fine"). At 12 concurrent sessions, aggregate `scp` calls re-created the same rate-limit exposure. A new hook blocks all `scp` from agent sessions; files now travel via git or run remotely via the relay.
2. **Stale-mux detection** (#2025). The persistent connection could die silently, leaving a dead socket the relay kept trying to use. Added liveness checks + auto-reconnect.
3. **CLI ergonomics were a footgun** (#2086). Running the relay script with `--help` or `--status` *killed the live tunnel* (the new process claimed the control socket). Fixed so diagnostics never touch the running instance.
4. **Self-healing watchdog** (#2087). A supervisor now restarts the relay when it dies, because the relay had become the single point every session depends on — creating a chokepoint means owning its availability.

That last point is the honest cost of the pattern: you trade "everyone floods the server" for "everything depends on the relay." The watchdog line-item is the price of admission, not an optional extra.

## Has the guard fired since?

Continuously. The raw-`ssh` and `scp` blocks fire whenever a fresh session or newly written script reaches for the direct path — which new code reliably does, because the direct path is the obvious one. Zero firewall lockouts since 2026-03-20.

## Lessons for agent-driven development

1. **Compute aggregate rates, not per-call costs.** Agent systems turn every per-invocation decision into a multiplication problem: calls × hooks × sessions. Size the product, not the term.
2. **Chokepoints beat discipline.** One process owning the scarce resource (connections, API budgets, write access) is enforceable; N well-behaved callers is a hope.
3. **No silent fallbacks to the dangerous path.** A degraded mode that quietly resumes the original failure behavior is worse than a hard failure — it fires precisely when you're least watching.
4. **When you build a chokepoint, build its babysitter.** Single points of failure are fine if something owns restarting them.
