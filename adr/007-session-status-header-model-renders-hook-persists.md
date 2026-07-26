# ADR-007: Session state is a structured status block — the model renders it, a hook persists it

**Status:** Active · **Date:** 2026-06, revised (see [ADR-012](012-context-percentage-wrap-pressure.md)) · **Internal refs:** session-status persist hook

## Context

The operator runs up to a dozen sessions and switches between them all day. The cost isn't inside any one session — it's the *re-entry* cost: opening a window cold and spending two minutes reconstructing what this session is doing, how far along it is, and whether it's drifting. Scrollback is not a status report. Multi-day sessions made this worse: the context that would explain the session's state had often already been compacted away.

## Decision

Every response opens and closes with a **structured session-status block**: eight fixed fields covering the session goal, the active work thread, progress, problems, what's next, and a drift flag (is this session still doing what it was opened to do?).

The load-bearing design choice is the **split of responsibilities**:

- **The model renders the block** — it's the only party that knows what happened this turn.
- **A Stop hook parses the rendered block and persists it** to a per-session state file. The model is prohibited from writing the state file directly.

Why the split matters: letting the model write its own state file invites silent corruption (wrong file, stale merge, invented fields) — the same class of failure as self-grading. The hook validates the schema on the way through; a malformed block fails loudly at persist time instead of poisoning the next session's warm start. The persisted state is then re-injected at the start of the next turn, closing the loop: render → persist → inject.

There is a session-level toggle to disable the blocks entirely (some work styles don't want the overhead).

## Alternatives considered

- **Free-form "summary at the end" instructions.** Decayed into vibes within days; unparseable, so nothing downstream could consume it.
- **Model writes the state file directly.** Rejected for the corruption reasons above — and because it makes the state file's integrity depend on instruction-following, which is the exact dependency this whole system exists to remove ([ADR-002](002-hooks-as-enforcement-not-instructions.md)).
- **Deriving status automatically from tool logs.** Attractive, but tool logs record *actions*, not *intent*; the drift flag in particular requires the model's own judgment about goal alignment.

## Consequences

- Token overhead every turn — two rendered blocks plus the injected prior state. Accepted as the price of cold-readability.
- The schema is a contract: changing a field name means updating the renderer instructions, the parser, and the injector together.
- The drift flag turned out to be the most valuable field for the operator — a one-glance answer to "has this window gone sideways?"

## What we'd do differently

Version the schema from day one. Field changes were initially made informally and broke the parser twice before the schema got a version number and a self-test.
