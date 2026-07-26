# $75 a Day for an LLM to Decide, Every 30 Minutes, That Nothing Needed Doing

**Keywords:** LLM in cron loop, agent cost control, LLM control plane, scheduled agent spawning, token cost runaway, deterministic vs LLM orchestration, autonomous agent economics

**Incident window:** ~2026-05, several days before accounting caught it · **Internal refs:** the orchestration-comparison era; cost-policy notes · **Status:** fixed (architecture, not budget); the placement rule became doctrine

---

## What broke

An automation experiment wired a scheduled job to spawn a **full frontier-model agent session every 30 minutes** to serve as a "heartbeat": wake up, load context, evaluate whether anything across the pipeline needed attention, act if so.

Almost every wake-up concluded — correctly! — that nothing needed doing. The conclusion cost the same as thinking hard: a large-model session with loaded context, ~48 times a day. The bill ran to roughly **$75/day for approximately zero useful output** — a heater that emitted "all clear" in prose.

The failure isn't the bill; it's the *architecture the bill was measuring*: an LLM had been placed at the **control plane** — the layer that decides *when* and *whether* — where the questions ("did a file change? is a queue non-empty? did a job fail?") are deterministic, cheap, and answerable in microseconds by code. The model's actual comparative advantage — judgment on ambiguous content — was needed in roughly none of the 48 daily invocations, and when it was, the heartbeat's fixed cadence was the wrong trigger anyway.

## How it was detected

The API bill. Cost accounting attributed the spend to the schedule in minutes; the mechanism was obvious the moment anyone looked at what the sessions had concluded — days of transcripts saying variations of "no action required."

## Root cause

Surface: an always-on cadence attached to an expensive evaluator.

Deeper: **"agent" had become the default unit of automation.** In an agent-heavy stack, every new automation reached for the most capable tool by reflex — the same misplacement instinct as building on whatever machine you're standing on ([ADR-010](../adr/010-host-placement-policy-three-machines.md)), but in the compute-cost dimension. The correct decomposition was sitting in plain sight: *detection* is deterministic (watch for the triggering condition in code, for free), *judgment* is the LLM's job (invoke one only when a detected condition needs interpreting). The heartbeat had bought judgment 48 times a day to perform detection.

## Blast radius

A few hundred dollars — trivially bounded, and honestly the cheapest tuition in this repo. The real value was doctrinal: this incident named a placement error that later audits found in smaller forms elsewhere (LLM calls summarizing logs nobody read; a model invoked to produce a constant).

## The fix

- The heartbeat was replaced by **deterministic watchers**: cheap scheduled checks (file mtimes, queue depths, exit codes, freshness assertions) that cost effectively nothing per tick — and **escalate to an LLM session only on a triggering condition**, with the condition's specifics in the prompt. Cost collapsed to ~zero on quiet days, which is most days; response *quality* on loud days improved, because the invoked model got a concrete trigger instead of an open-ended "anything up?"
- The placement rule entered policy: **control in deterministic code; LLMs at the insight layer, invoked by conditions, never polling.** New scheduled automations answer "why is this not a plain script?" at design time (the [ADR-011](../adr/011-designer-ack-and-seven-question-design-gate.md) checklist covers scheduled processes).
- Cost attribution by automation became a standing report, so the next misplacement announces itself in dollars within a day, not days.

## Has the guard fired since?

The design-gate question has redirected several proposed "agent checks X periodically" automations into watcher-plus-escalation shapes at zero incremental cost. The cost report has flagged one smaller recurrence (an over-eager summarization call), caught in two days. The watchers themselves fire constantly — that's their job, at a price of approximately nothing.

## Lessons for agent-driven development

1. **LLMs at the control plane is the wrong abstraction.** *When/whether* questions are deterministic; spend code on them. Spend models on *what does this mean* — and only when a condition triggers.
2. **Fixed-cadence polling with an expensive evaluator is a subscription to redundant conclusions.** Event-driven escalation gets better answers and a ~zero idle cost.
3. **In agent-first stacks, "spawn an agent" becomes the hammer for every nail.** Make "why not a plain script?" a mandatory design question, or the reflex wins by default.
4. **Cost is telemetry.** Per-automation spend attribution catches architecture errors that code review misses — the bill knew before anyone did.
