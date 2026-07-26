# ADR-012: Session wrap-up pressure keys off measured context usage, not time or turn counts

**Status:** Active (v1.1 of the session-header scheme) · **Date:** 2026-07 · **Internal refs:** wrap-suggestion guard; context misdetection incident

## Context

Long-running sessions need to wrap cleanly — commit, hand off, persist state — *before* the context window degrades the work. The first heuristics were proxies: session age, turn count, a vague "this feels long." Both proxies failed in both directions. Multi-day, 50+ turn sessions are **normal** here and often sit at low context usage; meanwhile a single turn that ingests large files can burn half the window in minutes. Two concrete failures forced the redesign: sessions estimated their own context usage narratively and were wildly wrong (a session at ~85% actual usage read itself as ~17%, sailing past every danger zone); and the opposite — agents *over-suggesting* wrap-up, nudging toward session closure at 20% usage because "we've done a lot," burning operator attention on ceremony.

## Decision

Wrap pressure is a function of **one measured number**: context-used percentage, computed by the harness/hooks (not self-estimated by the model) and injected into the session-status loop ([ADR-007](007-session-status-header-model-renders-hook-persists.md)). Fixed zones with defined obligations:

- **< 50% — green:** work normally. Wrap-up may not even be *suggested*.
- **50–70% — yellow:** draft the handoff alongside ongoing work.
- **70–85% — red:** wrap and commit.
- **> 85% — critical:** stop; handoff only.

Enforcement on both failure directions: the injected number kills self-estimation, and a **Stop hook blocks wrap-nudges below 50%** — an agent may not suggest wrapping, committing-as-closeout, or handoff-writing in the green zone unless the operator raises it.

## Alternatives considered

- **Turn-count / wall-clock thresholds.** The original. Rejected: both are uncorrelated with the actual resource being consumed.
- **Model self-assessment of context pressure.** Rejected by direct evidence (the 85%-reads-as-17% incident). The model cannot see its own window occupancy; asking it to is asking for confident fiction.
- **Auto-compaction as the whole answer.** Compaction extends runway but silently loses working detail; wrapping is about *choosing* what survives. The zones schedule that choice while good context still exists.

## Consequences

- Requires an accurate denominator: when the measured ceiling changed with a model upgrade, the percentage was briefly wrong at the source — the single number is a single point of failure for the whole scheme.
- The below-50% nudge ban occasionally suppresses a genuinely reasonable early wrap; the operator can always invoke it manually.
- Session hygiene became legible: the operator can glance at any window's zone instead of guessing which sessions are near the edge.

## What we'd do differently

Distrust model self-reports about *any* harness-level quantity from day one — context usage was just the first one we caught. If the harness can measure it, inject the measurement; never ask the model to introspect it.
