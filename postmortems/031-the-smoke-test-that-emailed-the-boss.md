# A Test File Shadowed Production Output — and the Wrong Numbers Were Emailed as Real

**Keywords:** test file in production path, mtime latest glob, file discovery bug, synthetic data leaked to production, glob pollution, newest file wins, test isolation

**Incident date:** 2026-05-25 · **Internal refs:** task #1433; glob-pollution guard + filename schema · **Status:** fixed (two independent defenses same day); guard active on production globs

---

## What broke

A daily production job assembles an allocation report and emails it to the operator. It finds its input the way half the world's pipelines do: glob the output directory, take the newest file by modification time.

Earlier that day, a session smoke-testing an integration wrote a synthetic output file — clearly fake to any human reader, prefixed `TESTRUN`, full of placeholder allocations — **into the same directory, matching the same glob.** Being the newest file, it won "latest." The evening pipeline picked it up and emailed the operator a real-looking report built from test fixtures: confident percentages, plausible formatting, fictional content.

No stage failed. Generator: succeeded (it generated a test file, as asked). Discovery: succeeded (newest match, as designed). Email: succeeded (delivered, as scheduled). Every component to spec; the composition, a lie in the operator's inbox.

## How it was detected

The operator read the email and the numbers were wrong in a way he recognized — one allocation was impossible on its face. Human pattern-matching was the *only* detector in the chain; nothing mechanical stood between a `TESTRUN` fixture and an outbound production email.

## Root cause

Surface: a test artifact written to a production-globbed path.

Deeper: **"newest file wins" is an ownership-free trust model.** mtime-based discovery grants production authority to anything that can write a matching filename — tests, partial runs, stray copies. The glob defines a *namespace*, and nothing enforced who may publish into it. The test session wasn't reckless; there was no rule to break, which is the finding.

## Blast radius

One wrong report emailed (caught by eyeball before any decision consumed it); an audit of *every* mtime-latest glob in the pipeline inventory — each one the same incident not yet scheduled; and the day's realization that test/production separation existed as a habit, not a mechanism.

## The fix

Two independent defenses, shipped the same day (deliberately redundant — either alone stops the incident):

- **Filename schema enforcement:** production consumers validate the *name*, not just the glob — a strict pattern (source, date, version) that synthetic files structurally fail. `TESTRUN_*` can sit in the directory forever; it can't parse as a production input.
- **A glob-pollution guard:** a PreToolUse hook that blocks writing files matching registered production globs unless the writer is the registered producer. The registry of production globs — created for this guard — became useful documentation in its own right: nobody had previously known how many mtime-latest patterns production relied on.

Plus the test-hygiene rule that should have existed by policy rather than by incident: synthetic outputs go to scratch directories, never production paths, enforced by the same guard.

## Has the guard fired since?

Yes — 3 blocks in a recent audit window, all sessions attempting to write test artifacts into registered production globs. Each block is this exact incident, cancelled. The filename schema has also rejected malformed real outputs twice — a bonus class of catch (partial runs with mangled names) the defense wasn't even aimed at.

## Lessons for agent-driven development

1. **mtime-latest discovery trusts whoever wrote last.** It's an authorization decision disguised as a convenience; make the authorization explicit or inherit everyone's mistakes.
2. **Agents generate test files constantly — production namespaces need a bouncer.** In agent-driven development the write volume is enormous; habit-based separation fails at that volume.
3. **Validate names as contracts, not patterns as filters.** A schema the producer must satisfy beats a glob the polluter can match.
4. **Every component "working" is compatible with the system lying.** Composition failures need composition-level checks — a plausibility gate before anything outbound (email, orders, publishes) buys the human a mechanical ally.
