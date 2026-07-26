# Tab-Autocomplete Leaked Prompts Between Concurrent Claude Code Sessions

**Keywords:** Claude Code autocomplete leak, cross-session prompt leakage, history.jsonl, ghost text, multi-session isolation, harness-level bug, prompt confidentiality, workspace isolation

**Incident date:** ~2026-05-24 (documented); still open upstream at time of writing · **Internal refs:** task #1328; collision taxonomy class 3 · **Status:** mitigated by operator practice; not fixable at the hook layer — documented as the boundary case

---

## What broke

An operator running many Claude Code windows pressed Tab in one session and was offered **a prompt from a different session** — ghost text originating in another window's work, in one observed case traceable to another *workspace* entirely.

The mechanism, from inspection of the harness's files: the CLI's prompt autocomplete reads a **global history file** (`~/.claude/history.jsonl`) that at the time contained ~8,085 entries spanning 12 distinct session IDs — with entries carrying a `project` field and session attribution *that the autocomplete lookup didn't filter on*. Suggestion candidates came from everyone's history: other sessions, other projects. Pasted content associated with prompts lives in the same file, widening what could surface.

Accepted ghost text is worse than a confidentiality oddity: a plausible-looking suggestion from a *different task's* context, accepted by reflex in the wrong window, becomes an instruction the wrong agent executes.

## How it was detected

The operator recognized text he'd typed *elsewhere* appearing as a suggestion. The write-up that followed (schema inspection, entry counts, session-ID census of the history file) turned an anecdote into a reproducible report with a proposed one-line-shaped fix: filter candidates on the current `project` / exclude foreign live session IDs — the data needed for the filter is already in every entry.

## Root cause

The autocomplete feature predates the many-concurrent-sessions usage pattern: a global history is the *right* UX for one user, one session at a time. Under 7–12 concurrent sessions across multiple workspaces, "your history" became "everyone's history." Classic assumption rot — the feature didn't change; the deployment pattern did.

Structurally, this is **collision class 3 in our taxonomy: harness-level ghost text** — the class that lives *below* the hook layer. PreToolUse/Stop hooks see tool calls and responses; they cannot see or filter the CLI's own UI suggestions. Our entire enforcement architecture has a floor, and this bug lives under it.

## Blast radius

Confidentiality: prompts (and potentially pasted content) from one workspace visible in another. Integrity: the accepted-wrong-suggestion path. Practical damage in our single-operator case was contained — same human on both sides of the leak — but the mechanism generalizes to any multi-tenant or multi-project use of the same machine account.

## The fix

What's actually available at each layer:

- **Upstream (the real fix):** filter autocomplete candidates by project/workspace and exclude live foreign sessions — filed as an issue draft with the schema evidence; tracked open.
- **Operator practice (the mitigation):** treat Tab-completion as untrusted in multi-session use; the taxonomy entry trains sessions and operator alike to *classify* the symptom instantly instead of re-diagnosing "impossible" text.
- **Hook layer:** nothing. Stated plainly because it's the honest architecture note: enforcement layered on tool calls cannot reach the harness's input UI.

## Has the guard fired since?

No guard *can* — that's this postmortem's contribution. What fires instead is the collision-context injector: any session whose prompt mentions ghost-text symptoms gets the taxonomy injected, which is how recurrence gets identified in minutes rather than hours. The upstream issue remains the fix of record.

## Lessons for agent-driven development

1. **Your enforcement architecture has a floor.** Hooks govern tool calls and responses; the harness's own UI, files, and self-mutations (see also [PM-030](030-the-secret-the-hooks-could-not-see.md)) live beneath it. Map the floor; don't pretend it isn't there.
2. **Global-by-default features rot under multi-session use.** History, caches, settings: each is a leak channel the moment sessions multiply. Audit every `~/.tool/` file for cross-session reads.
3. **Ghost text is an integrity threat, not just a privacy one.** The dangerous outcome isn't seeing another session's prompt — it's *executing* it in the wrong context by reflexive Tab.
4. **Report upstream with schema receipts.** "Autocomplete showed weird text" gets triaged as vibes; entry counts, field names, and a proposed filter get fixed.
