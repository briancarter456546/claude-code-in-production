# Origins: Why This System Exists

Before the hooks, there was a person with a business, a Windows PC, and a growing pile of AI-generated scripts.

The operator runs a one-person company spanning systematic trading research, content pipelines, paid speaking, and web properties — the kind of portfolio that historically needs a small staff. From early 2026, Claude Code became that staff: first one session at a time, then several, eventually 7–12 concurrently across a dev PC, an always-on cloud droplet, and a Mac compute worker, with real money exposed to the outputs.

The early weeks worked the way every agent demo works: ask, receive, ship. And the early failures were the ones this repo's first postmortems document — quiet, plausible, and expensive. A data-alignment bug that made every backtest read prices from a year before their labels ([PM-001](../postmortems/001-silent-data-misalignment-broke-every-backtest.md)). Twelve sessions' worth of SSH connections tripping the firewall and locking the operator out of his own server for 8 hours ([PM-002](../postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md)). An agent that agreed with whatever the operator said last ([PM-003](../postmortems/003-stop-hook-sycophancy-guard-claude-code.md)).

Each failure produced a rule. The rules went into the project instructions file, which grew from a page into a constitution. And then came the discovery that defines everything after: **the rules decayed.** The model followed them usually — and "usually," multiplied by a dozen sessions running around the clock, meant a violation somewhere every day, clustered exactly where violations are expensive: git history, deployments, external communications, data deletion.

The response — gradual, incident-driven, never planned as an architecture — was to stop asking and start enforcing. Every durable rule got a mechanism: a gate that blocks the tool call, a Stop hook that refuses the response, an injector that makes state impossible to forget. The instruction file kept the *why*; the hooks took over the *must*.

Five months later the enforcement layer itself had ~100 hooks, its own failure modes, its own postmortems, and its own audit culture. That evolution — including the parts where the guards became the problem — is what the era files that follow trace.

One framing note for everything you'll read here: none of this was designed. It *accreted*, one incident at a time, under production pressure, by an operator and a series of agent sessions repairing the plane in flight. The value, if there is any, is that the accretion is documented — with task numbers, fire counts, and the wrong turns left visible.
