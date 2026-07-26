# An API Key Leaked Through a Write Path No Hook Can Observe: the Harness Editing Its Own Settings

**Keywords:** API key leak, Claude Code settings.local.json, harness self-mutation, secret scanning pre-commit, hook blind spot, permission allowlist, secrets in config, defense in depth

**Incident date:** 2026-06 (task #1592) · **Internal refs:** #1592; pre-commit secret scanner; unified pattern library · **Status:** fixed at the durable boundary; scanner runs on every commit

---

## What broke

An API key appeared in a git-committed file. The stack had guards against exactly this: a PreToolUse hook scanning Write/Edit calls for key-shaped strings. The guards never fired — because **no tool call ever wrote the key.**

The write path: when the operator approves a Bash command in Claude Code, the harness can record that approval as an allowlist entry in `settings.local.json`. The approved command line *contained the key inline* (an env-var-prefixed invocation), so the harness — helpfully, autonomously, outside any tool call — wrote the literal key into a settings file. That file was untracked-but-committable, and a later broad staging swept it toward the repo.

The enforcement lesson in one line: **the hook layer governs the agent's tool calls; it does not govern the harness's own file writes.** Same architectural floor as the autocomplete leak ([PM-024](024-ghost-text-from-another-session.md)) — this time with a credential on it.

## How it was detected

The commit-layer scan caught the key-shaped string on its way into history — the last line of defense doing its job. Forensics then traced the surprising author: not a Write call, not a redirect, but the harness's approval-recording behavior.

## Root cause

Surface: a key passed inline on a command line, memorialized by an approval-recording feature that faithfully stored what it saw.

Deeper: **the guard architecture had an unexamined assumption — "all file writes we care about pass through tool calls."** False. The harness writes settings, history, caches, and approval records on its own authority. Any of those can capture sensitive content that transited a command line or prompt. Related aggravator found in the same incident: two separate secret-pattern implementations (the Write-time guard and the commit-time scanner) had *drifted apart*, so even the observable layer had inconsistent coverage.

## Blast radius

One key rotated (assume-compromised policy on any key that touched a committable file); an audit of settings/history files for other captured secrets; and a permanent demotion of the Write-time guard from "the defense" to "a convenience layer" in the team's threat model.

## The fix

- **The durable boundary got the real gate:** a native git **pre-commit secret scanner** — running in git itself, not in the hook layer — blocks key-shaped content in any staged file regardless of who wrote it: agent, harness, human, or cron. Commit is the last chokepoint where every author converges; that's where fail-closed lives.
- **One pattern library:** the Write-time guard and the commit scanner now import the same pattern set — drift between scan layers ended structurally.
- **Inline secrets banned at the source:** keys reach processes via the environment or env-files the shell resolves (never pasted into command lines or chat), per standing key-hygiene policy — removing the material the harness could capture.

## Has the guard fired since?

The commit scanner runs on every commit in the repo and has blocked key-shaped strings since (including test fixtures and — recursively — early drafts of sanitization tooling whose example patterns looked too real). This public repo's own pre-push scanner is a descendant of the same lesson.

## Lessons for agent-driven development

1. **Map the writers your guards can't see.** The harness itself writes files — settings, approvals, history. If your enforcement only watches tool calls, those paths are unguarded by construction.
2. **Gate at the boundary where all authors converge.** Per-writer guards are convenience; the commit (or push, or publish) is where fail-closed belongs, because it doesn't care who wrote the bytes.
3. **A secret on a command line is already leaked** to every recorder of command lines — shells, harnesses, logs. Environment resolution isn't paranoia; it's scoping.
4. **Duplicate scan implementations will drift.** One pattern library, many enforcement points — never parallel regex sets maintained by hope.
