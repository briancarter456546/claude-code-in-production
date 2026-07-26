# Exit Code 0, Wrong Results: the Remote Worker's Import Failure Was Caught, Warned, and Ignored

**Keywords:** silent degradation, caught exception wrong results, cross machine dispatch, import error fallback, exit code zero, degraded results clean exit, remote execution integrity

**Incident window:** recurring on the compute-worker dispatch path, 2026-06→07 · **Internal refs:** dispatch design notes (#1484 era); the inflated-handoff variant · **Status:** fixed (degradation is now fatal-by-default on dispatch); results carry integrity manifests

---

## What broke

Heavy backtests dispatch to a compute worker (a Mac mini): push script + inputs, run remotely, pull results. The worker deliberately has **no clone of the repository** — scripts must travel with their dependencies.

A dispatched script imported a repo module. On the worker, the import failed — and the script *caught the ImportError*, logged a warning into a file nobody reads mid-run, substituted a degraded code path, and **completed successfully: exit 0, results file produced, pulled home.** The degraded path had skipped an enrichment step, leaving every instrument unmapped — the results were systematically wrong, in format indistinguishable from right.

The expensive variant surfaced later: a handoff document confidently cited performance numbers (growth, risk ratios) from a results file — and a verification pass found the *named* input file didn't exist; the only matching file, produced on the worker under a silent import failure, contained numbers **less than half** the cited figures on the key metric. The degraded run had produced a *different reality under the same filename*, and downstream prose had built on it.

## How it was detected

The first instance: a reviewer noticed every row of a dimension that should have been mostly-mapped read `UNMAPPED` — visibly absurd *if you looked*, invisible to every automated stage. The variant: a session refused to build further work on numbers it couldn't reproduce, hunted the provenance, and found the divergence between claimed and actual file contents.

## Root cause

Surface: `try/except ImportError` with a warn-and-continue arm — written for local development resilience, lethal on a worker where the import *always* fails.

Deeper: **exception handling encoded the wrong severity policy for the execution context.** On a dev box, "continue without the enrichment" is a convenience; on a no-repo worker, it's a guarantee of silent wrongness. The same code, two contexts, one hardcoded answer. And the transport layer made it worse: dispatch judged success by **exit code**, which measures "did the process end politely" — not "are the results trustworthy."

## Blast radius

At least one contaminated results set consumed by downstream analysis; one handoff document's headline numbers invalidated (caught before further work stacked on them); and a standing doubt tax over every prior dispatch result until spot-audits cleared them.

## The fix

- **Degradation is fatal on dispatch:** dispatched scripts run with a strict flag — any caught-degradation path raises instead of warns when running in worker context. Context, not code, decides severity.
- **Results carry integrity manifests:** the worker emits a manifest alongside results (imports resolved, enrichment stages run, row counts, environment fingerprint); the pull side validates the manifest before results are accepted. Exit code demoted to "process ended," which is all it ever measured.
- **Same-filename-different-content forever banned:** degraded outputs, where they're ever legitimate, must announce themselves *in the filename*.

## Has the guard fired since?

The manifest check has rejected pulls since — including one where the worker environment drifted (a dependency version change broke an import the old way, loudly this time). Each rejection is this postmortem not recurring.

## Lessons for agent-driven development

1. **Exit 0 measures manners, not truth.** A process can fail at its purpose and exit politely; transport layers that trust exit codes inherit every caught exception's optimism.
2. **`except: warn` is a context-dependent decision hardcoded as universal.** Resilience on a dev box is corruption on a worker. Let execution context set severity.
3. **Results need provenance manifests, not just payloads.** "Which imports resolved, which stages ran" travels with the data or the data can't be trusted downstream.
4. **Wrong-but-well-formatted is the most expensive failure class.** Formats invite trust; a degraded run must be *visibly* degraded — in filename, manifest, and metrics — or it will be consumed as real.
