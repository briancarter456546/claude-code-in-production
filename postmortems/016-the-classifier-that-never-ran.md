# A Hook Read an Env Var Claude Code Never Sets — It No-Opped for Two Months, Invisibly

**Keywords:** Claude Code hook environment variables, silent hook failure, UserPromptSubmit hook, session classification, fail-open hooks, dead code in production, hook observability

**Incident window:** ~2026-05-12 → 2026-07 (discovery) · **Internal refs:** task #2063; companion filename bug #1739 · **Status:** fixed; classifier now reads the harness's actual input channel; ~273 mislabeled artifacts identified

---

## What broke

Every session auto-classifies itself into a work "lane" (trading, infrastructure, design…) at its first prompt — the label drives which rules inject, where session notes file themselves, and how a dozen sessions stay legible to one operator. The classifier hook read the prompt from an environment variable, `CLAUDE_USER_PROMPT`.

**Claude Code does not set that variable. It never has.** The hook's first line of real work — read the prompt — returned empty; the code bailed out before classifying anything, *silently*, on every single invocation from the day it shipped. The audit log's verdict: **2 fired classification events in 101,000 logged lines.**

Downstream, nothing looked broken. The lane field simply kept whatever value it last had — a stale, hand-set label that then got stamped into everything: **~193 session-notes filenames and ~80 handoff documents labeled `trading`**, regardless of what the sessions actually did. A secondary bug in the classifier compounded it: the keyword matcher returned on first hit in configuration order, which favored the same label. Plausible label, wrong forever.

## How it was detected

Statistically, not operationally: an audit of session-notes metadata found 193 of 204 notes files in one lane — a distribution too skewed to be true for a workload that visibly spans seven lanes. Grepping the audit log for the classifier's fire events produced the 2-in-101k number, and reading the hook found the phantom env var.

## Root cause

Surface: an assumed API — "the harness surely passes the prompt in an env var" — never verified against the harness's actual hook contract (the prompt arrives on **stdin as JSON**, not in the environment).

Deeper: **the hook was fail-open with no heartbeat.** Its failure mode — do nothing, exit 0 — is indistinguishable from "no classification needed this turn." A hook that can no-op silently *will* no-op silently, and nothing in the stack counted how often each hook did real work. (Same family as the consolidated-dispatch discovery that another hook had been reading tool-output env vars its event never populates — that one had *never* fired. See [PM-019](019-when-the-safety-layer-became-the-outage.md).)

One more subtlety for hook authors, discovered during the fix: **stdin is consumable.** A hook that re-reads already-consumed stdin gets empty input and silently reproduces this exact bug — the fixed version reads once and passes the payload explicitly.

## Blast radius

~273 mislabeled durable artifacts (notes + handoffs) whose filenames and headers assert the wrong lane to every future reader; two months of lane-keyed rule injection running against a stale label; and a companion bug ([PM notes] filename inheritance, task #1739) that kept stamping the *previous* session's lane onto new files even after the classifier was fixed — the label was wrong at two layers that had to be fixed separately.

## The fix

- Read the prompt from the channel the harness actually provides (stdin JSON), with a startup self-test asserting non-empty input on a synthetic invocation.
- The keyword classifier's first-hit-wins bias fixed (score across all lanes, then pick).
- **Fire-count telemetry as a standing expectation:** the audit log now makes "how often did this hook do real work" a queryable number, and the gate-audit practice ([PM-015](015-eight-thousand-fires-zero-true-blocks.md), [ADR-016](../adr/016-guards-are-audited-against-their-own-fire-logs.md)) reads it on a schedule. A hook with a near-zero fire rate is now a finding, not a fact nobody knows.

## Has the guard fired since?

The classifier now fires on session starts and the lane distribution across new artifacts matches visible reality (seven lanes with traffic, not one). The mislabeled historical corpus was left as-is with the correction recorded — renaming ~273 files would have destroyed more provenance than it repaired.

## Lessons for agent-driven development

1. **Verify the harness contract; never assume the env var.** Hooks integrate against an API. Read its documentation the way you'd read any API's — the input channel you imagine is not evidence.
2. **Fail-open + no telemetry = invisible death.** Any hook that can exit 0 without doing its job needs a fire counter someone reads, or its failure mode is eternal silence.
3. **Distribution skew is a detector.** 193-of-204 in one bucket found this bug when two months of operation didn't. Statistical sanity checks on metadata are cheap and catch what operation can't.
4. **Labels propagate; fix the stamp and the stamped.** The wrong lane lived in the classifier, the state file, the filenames, and the file headers — four layers, each needing its own correction.
