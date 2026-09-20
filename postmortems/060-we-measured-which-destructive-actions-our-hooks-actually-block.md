# We measured which destructive actions our agent hooks actually block — 20 of 26 probes got through

**Keywords:** PreToolUse hook coverage audit, agent guardrail coverage testing, which tools do Claude Code hooks match, PowerShell bypasses Bash hooks, matcher tool list gap, enforcement self-modification, guard the guards, probe harness for hooks, destructive action classes, measured not assumed safety

**Incident date:** 2026-09-16 · **Internal refs:** #2776, #2786, #2788–#2792, parent #2764 · **Status:** holes partly closed by an additive guard 2026-09-17; the dispatcher's tool list is unchanged as of 2026-09-20

---

## What broke

Nothing broke. That is the point of this entry: a planned change rested on a premise nobody had measured, and the measurement failed.

The change was to let sessions act with less stopping — fewer confirmation prompts on ordinary work. Its stated safety premise was that the *consequential* action classes are gated in code, so acting by default is safe. Five classes carry real consequence here: spending money, sending anything outbound, destroying durable data, creating something that acts on its own schedule, and modifying the enforcement layer itself.

A harness built 26 probes across those five classes and asked, for each, whether any hook refuses it.

**Six were refused. Twenty were not.**

## How it was detected

By building the instrument before the feature, rather than after an incident. The harness does not execute anything:

- For each probe it constructs the tool-call payload the agent harness would send.
- It reads the hook configuration to resolve **which hooks that tool actually routes to** — the matcher is a tool-name list, so this is a lookup, not a guess.
- It pipes the payload to each of those hooks and records whether any refused (a blocking exit status or an explicit deny).
- Every command string is data and every target is a decoy path that does not exist.

Twenty-six probes, 62 seconds. It was run twice — once with a synthetic session identity, once with the real one — and produced **identical results**, so the holes were not an artifact of unknown session state.

## Root cause

Every hole traces to the same structural fact: **a hook's coverage is the list of tool names in its matcher, and nobody had ever diffed those lists against the list of tools the agent can call.** Guards had been added incident by incident, each wired to the tool that caused *that* incident.

The consequences, grouped:

**1. The second shell was almost ungoverned (5 of 5 probes unrefused).** The harness offers two shells. Every guard of consequence had been wired to the first one. The second reached three hooks total, and the guard dispatcher — the hook that fans out to the whole battery — was not wired to it at all. Firing the live trade publisher, sending email, wiping the price cache, registering a scheduled task and blanking the hook configuration all passed. **Anything blocked in one shell was re-runnable in the other.**

**2. Destruction through the shell reached no destructive guard.** The destructive-action guard was registered for the two file-editing tools only, read directly from the dispatcher's registration table. A recursive removal of the price cache and a row-wipe against the knowledge base each passed eighteen hooks without a refusal.

**3. The destructive guard matched destructive *text*, not destructive *effect*.** Covered separately in [PM-061](061-the-guard-read-the-words-not-the-effect.md).

**4. The class that protects the enforcement layer refused 0 of 5.** Editing the dispatcher; blanking the hook configuration file through a write, through a shell redirect, and through the second shell; deleting a guard file outright. Nothing refused any of it. This is the class that makes every other gate conditional — a session that can delete a guard has, in one step, every permission that guard withholds.

**5. Scheduling was covered on exactly one path.** The shell path that edits the system scheduler refused. A scheduled task created through the second shell, a scheduled agent created through the harness's own scheduling tool, a service unit written as a file, and a production service restarted through the relay all passed.

**6. The mail connector send was unrefused.** Outbound sending was defended on the shell path and open on the connector path — two hooks run for connector tools and neither is a send gate.

**7. Self-granting the reduced-stopping mode: all four paths unrefused** — expected, because the grant field did not exist yet. Recorded anyway, so that the grid must show four gated *after* the feature is built, or it ships with a self-service switch.

## Blast radius

No consequential action was taken through any hole, and no log shows one having been taken. The cost was to a belief: for months the answer to "is this safe to automate?" had been "the classes are gated", and the measured answer was **"money and outbound sends are gated, on one of two shells."**

The reduced-stopping feature was held. Its precondition changed from a claim to a green grid.

## The fix

- **An additive guard covering the paths the dispatcher does not reach.** It registers alongside the dispatcher rather than editing it — another session owned that file — and matches the second shell, the connector tools, and the scheduling tools. Classes: outbound send, durable-data destruction, scheduled-task creation, self-granting, and destruction of a guard.
- **Deleting or blanking a guard is refused; ordinary edits to guard files are warned and counted.** Sessions legitimately edit hooks all day, so a hard block would stop the fleet. The sharp line is "you may edit a guard, you may not delete or blank one", and the warn counter exists so the block threshold gets set from data rather than from taste — the same way [PM-021](021-alarm-fatigue-by-the-numbers.md) forced thresholds to be earned.
- **It fails open.** An internal error allows the tool. A guard that breaks must not stop the fleet.
- **The grid is now a repeatable check**, re-run after any guard or configuration change, and required green before the reduced-stopping pilot.
- **One "hole" was not real, and the grid learned from it.** A write probe against a file another session had claimed looked like a missed collision block. Checked directly: that session had already released the claim, so no collision existed and the guard was correct to allow. **A guard whose input is live state can only be probed with that state held** — the next version holds a fixture claim before the probe.

## Has the guard fired since?

The additive guard has recorded **1,019 decisions between 2026-09-17 and 2026-09-20 — 784 refusals and 42 bypasses.** Those numbers must not be read as production catches, and this is worth stating plainly because it is the trap [PM-015](015-eight-thousand-fires-zero-true-blocks.md) and [PM-055](055-the-audit-log-could-not-be-counted.md) were written about: inspecting the records shows the targets are the harness's own decoys, repeated — a decoy address, a decoy guard filename, a decoy state file. **Essentially all of it is the grid and the guard's self-test. Zero production refusals are confirmed.** What the log does prove is that the hook is wired and reachable on every path the grid probes, which is exactly what it failed to be a week earlier.

The structural half of the finding is **still true as of 2026-09-20**, verified by reading the live hook configuration: the dispatcher's matcher remains the four editing tools plus the first shell. The second shell's coverage rests entirely on the additive guard and the capability fence. The dispatcher was never widened; a second guard was placed beside it.

## Lessons for agent-driven development

1. **Coverage is a set intersection, and you must compute it.** A hook protects the tools named in its matcher and nothing else. Diff the matcher lists against the full tool list the agent can call — that diff is your unguarded surface, and it changes every time the harness adds a tool.
2. **Any second path to the same effect is a bypass.** Two shells, a connector, a scheduling tool and a relay are five ways to send an email. Guards keyed to *tools* leak; classify by **effect** and enumerate every tool that can produce it.
3. **Probe the guard system by class, not by incident.** Every hole here was in a class that had never caused an outage yet. Incident-driven guards produce incident-shaped coverage.
4. **The class that protects enforcement is the one to build first.** Every other guarantee is conditional on it, and it was the class with zero coverage.
5. **Build the measurement before the permission.** A coverage grid is a few hours of work and it converted "we believe this is gated" into a number. The premise of the feature was false and cheap to falsify.
6. **A guard that reads live state can only be tested with that state held.** Otherwise a correct allow is indistinguishable from a missed block, and your audit records a false hole.
