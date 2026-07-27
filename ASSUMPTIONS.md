# 103 Things You'd Assume an AI Coding Agent Can Do (Until Production Teaches You Otherwise)

Every line below is an assumption a reasonable person makes on day one of running Claude Code — and every one of them failed in our production record and now has a hook, gate, contract, or protocol behind it. The point isn't that the model is bad; it's that "usually right," multiplied by 7–12 concurrent sessions running for months, means each of these breaks somewhere, expensively. This list is why 148 enforcement hooks exist.

Where an assumption has its own documented funeral, the link points to it. Unlinked lines are covered across the [chronicle](chronicle/00-origins.md) and the guard fleet generally.

## Following instructions

1. If a rule is written in CLAUDE.md, the agent will follow it. *([ADR-002](adr/002-hooks-as-enforcement-not-instructions.md))*
2. If the agent followed a rule for the last twenty turns, it will follow it on turn twenty-one.
3. A rule that survived one session transfers automatically to the next session.
4. Making the instruction louder (bold, caps, "NEVER") makes it stick.
5. The agent will remember to check the reference file you told it to always check first.
6. Telling the agent "don't be sycophantic" stops it from being sycophantic. *([PM-003](postmortems/003-stop-hook-sycophancy-guard-claude-code.md))*
7. Telling the agent to estimate runtime before executing means it will actually do the arithmetic. *([PM-042](postmortems/042-fifteen-hours-and-eighty-four-minutes.md))*
8. A rule with an obvious reason behind it doesn't need enforcement.
9. If the agent acknowledges a correction, the behavior is corrected.
10. Instructions compete fairly for attention no matter how long the session gets.

## Memory, context, and long sessions

11. The agent knows how full its own context window is. *([PM-006](postmortems/006-agent-misread-its-own-context-window-usage.md))*
12. The agent will warn you before it runs out of room — and won't nag you to stop when it has plenty. *([PM-007](postmortems/007-wrap-nudge-overfiring-below-half-context.md))*
13. Context compaction preserves the important parts. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
14. If the agent doubted a result earlier, it still doubts it after compaction. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
15. A session that has run for three days is the same reasoner it was on day one.
16. The agent's stated session goal is still the actual session goal.
17. What the agent remembers about the codebase matches what's currently in the codebase.
18. If the agent said a number four turns ago and refuted it two turns ago, it won't reuse the refuted number. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
19. Writing something important in conversation is as durable as writing it to disk.
20. The agent will notice when its own working notes have been deleted out from under it. *([PM-026](postmortems/026-the-files-deleted-at-midnight.md))*

## Git and version control

21. `git add -A` stages *your* work. *([PM-008](postmortems/008-broad-git-add-swept-another-sessions-files.md))*
22. `git commit` commits *your* work. *([PM-011](postmortems/011-bare-commit-swept-the-shared-index.md))*
23. A commit's message describes the files inside it. *([PM-008](postmortems/008-broad-git-add-swept-another-sessions-files.md))*
24. `git log -- <file>` tells you who authored the change. *([PM-008](postmortems/008-broad-git-add-swept-another-sessions-files.md))*
25. "Remote SHA verified" means the push reached the remote. *([PM-028](postmortems/028-the-push-that-lied.md))*
26. A safety wrapper around git makes git operations safer in all cases. *([PM-004](postmortems/004-per-session-git-wrapper-nearly-committed-private-repo-into-public.md))*
27. The agent won't commit another session's staged files under its own message. *([PM-011](postmortems/011-bare-commit-swept-the-shared-index.md))*
28. File permissions committed on Windows behave the same after a Linux pull. *([PM-034](postmortems/034-windows-kills-guards-quietly.md))*
29. `git log --all` finds every file that ever existed in the repo. *(see [META](META.md) on `--full-history`)*
30. If the push says "everything up-to-date," everything is up to date in the way you think. *([PM-028](postmortems/028-the-push-that-lied.md))*

## Running more than one session

31. Two Claude Code sessions in one repo will stay out of each other's way. *([ADR-006](adr/006-task-checkout-leases-and-collision-guards.md))*
32. Each session knows which files it touched. *([PM-023](postmortems/023-blocked-from-committing-its-own-file.md))*
33. Each session knows which session it is. *([PM-022](postmortems/022-two-sessions-one-identity.md))*
34. Session state files belong to the session that reads them. *([ADR-014](adr/014-per-session-skill-state.md))*
35. Two sessions editing settings.json will merge their changes. *([PM-025](postmortems/025-sessions-erased-each-others-hook-registrations.md))*
36. A fix you shipped stays shipped while other sessions are running. *([PM-020](postmortems/020-the-fix-that-kept-getting-unfixed.md))*
37. Tab-autocomplete suggests things from *your* session. *([PM-024](postmortems/024-ghost-text-from-another-session.md))*
38. The working directory you left is the working directory you'll come back to. *([PM-034](postmortems/034-windows-kills-guards-quietly.md))*
39. A dozen sessions each being individually gentle with a server is collectively gentle with the server. *([PM-002](postmortems/002-concurrent-ai-agents-ssh-rate-limit-lockout.md))*
40. When something is deleted, some session's log will say which session deleted it. *([PM-026](postmortems/026-the-files-deleted-at-midnight.md), [PM-037](postmortems/037-the-investigator-was-the-culprit.md))*

## Code, data, and correctness

41. Code that runs without error is code that worked. *([PM-032](postmortems/032-exit-zero-wrong-answer.md))*
42. Exit code 0 means the results are right. *([PM-032](postmortems/032-exit-zero-wrong-answer.md))*
43. A caught exception is a handled exception. *([PM-032](postmortems/032-exit-zero-wrong-answer.md))*
44. NaN in the data will cause a visible failure rather than a silent one. *([PM-009](postmortems/009-nan-prices-created-immortal-zombie-positions.md))*
45. The agent reasons about how long its code will take, not just whether it's correct. *([PM-042](postmortems/042-fifteen-hours-and-eighty-four-minutes.md))*
46. A backtest producing plausible numbers is reading the right dates. *([PM-001](postmortems/001-silent-data-misalignment-broke-every-backtest.md))*
47. The newest file matching the glob is the production output. *([PM-031](postmortems/031-the-smoke-test-that-emailed-the-boss.md))*
48. Test artifacts and production artifacts won't end up in the same place. *([PM-031](postmortems/031-the-smoke-test-that-emailed-the-boss.md))*
49. Dividend adjustment is a detail that won't flip a system from fail to pass. *([PM-043](postmortems/043-overfitting-anxiety-nearly-killed-real-edges.md))*
50. If a guard exists in one pipeline, the agent will carry it into the sibling pipeline. *([PM-039](postmortems/039-the-guard-that-existed-but-was-never-ported.md))*
51. Two implementations of the same spec produce the same numbers. *([PM-039](postmortems/039-the-guard-that-existed-but-was-never-ported.md))*
52. The agent writing an assertion means the assertion has been executed at least once. *([PM-038](postmortems/038-the-validation-that-never-happened.md))*
53. `.dropna()`, default encodings, and library defaults will do what you'd expect on your platform. *([ADR-003](adr/003-sh-to-py-wrapper-convention-for-windows-hooks.md))*
54. A 20x runtime misestimate would surely get noticed before you act on it. *([PM-042](postmortems/042-fifteen-hours-and-eighty-four-minutes.md))*

## Honesty, verification, and self-knowledge

55. When the agent says it ran the tool, it ran the tool. *([tool-registry](patterns/tool-registry.md))*
56. When the agent says the test passed, the test both exists and passed. *([PM-038](postmortems/038-the-validation-that-never-happened.md))*
57. A "walk-forward validated" claim implies a walk-forward actually occurred. *([PM-038](postmortems/038-the-validation-that-never-happened.md))*
58. Confidence scores assigned by the claimant mean something. *([PM-038](postmortems/038-the-validation-that-never-happened.md))*
59. The agent will hold its position under pushback when it's right. *([PM-003](postmortems/003-stop-hook-sycophancy-guard-claude-code.md))*
60. The agent will change its position when you present evidence it's wrong — and only then. *([PM-003](postmortems/003-stop-hook-sycophancy-guard-claude-code.md))*
61. If you're right and the agent is wrong, the disagreement resolves in your favor. *([PM-035](postmortems/035-the-model-talked-us-out-of-being-right.md))*
62. An agent investigating an incident will consider itself as a possible cause. *([PM-037](postmortems/037-the-investigator-was-the-culprit.md))*
63. The agent's summary of what happened this session matches what happened this session. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
64. Numbers in the agent's prose trace back to a source you could check. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
65. An agent asked to critique its own work supplies the adversarial pressure a real critic would. *([ADR-013](adr/013-solution-validation-loop-external-adversary.md), [PM-013](postmortems/013-integrity-ledger-certified-fabricated-results.md))*
66. The agent knows what it doesn't know. *([PM-006](postmortems/006-agent-misread-its-own-context-window-usage.md))*

## Bias and calibration

67. The agent's skepticism is calibrated — it doubts wrong things and trusts right things. *([PM-043](postmortems/043-overfitting-anxiety-nearly-killed-real-edges.md))*
68. Being trained to avoid overconfidence means it won't manufacture false prudence instead. *([PM-043](postmortems/043-overfitting-anxiety-nearly-killed-real-edges.md))*
69. Statistical corrections applied by the agent are sized to the actual search, not stacked until nothing survives. *([PM-043](postmortems/043-overfitting-anxiety-nearly-killed-real-edges.md))*
70. "This result seems too good to be true" will still be believed by the same agent tomorrow. *([PM-036](postmortems/036-compaction-ate-the-doubt.md))*
71. The agent treats your correct hunch as a reason to check, not a claim to debate. *([PM-035](postmortems/035-the-model-talked-us-out-of-being-right.md))*
72. Agreement from a second model run the same way is independent confirmation. *([ADR-013](adr/013-solution-validation-loop-external-adversary.md))*

## The environment and the harness

73. Hooks see everything that writes files. *([PM-030](postmortems/030-the-secret-the-hooks-could-not-see.md))*
74. The harness itself won't write your API key into a config file. *([PM-030](postmortems/030-the-secret-the-hooks-could-not-see.md))*
75. Environment variables you set inline reach the processes that need them. *([PM-014](postmortems/014-the-escape-hatches-that-never-existed.md))*
76. The prompt arrives to hooks the way the hook author assumed it does. *([PM-016](postmortems/016-the-classifier-that-never-ran.md))*
77. A hook that has been registered stays registered. *([PM-025](postmortems/025-sessions-erased-each-others-hook-registrations.md))*
78. A hook that runs is a hook that works. *([PM-016](postmortems/016-the-classifier-that-never-ran.md))*
79. The documented bypass mechanism for a guard actually functions. *([PM-014](postmortems/014-the-escape-hatches-that-never-existed.md))*
80. Session history is scoped to the session. *([PM-024](postmortems/024-ghost-text-from-another-session.md))*
81. Crashed sessions release everything they were holding. *([PM-034](postmortems/034-windows-kills-guards-quietly.md))*
82. The scheduler runs your jobs in the order they depend on each other. *([PM-033](postmortems/033-production-degraded-politely.md))*
83. A cron that is installed is a cron that has ever succeeded. *([PM-033](postmortems/033-production-degraded-politely.md))*
84. Warnings in logs get read. *([PM-033](postmortems/033-production-degraded-politely.md))*

## The guards themselves (the meta-layer)

85. A guard born from a real incident catches real incidents. *([PM-015](postmortems/015-eight-thousand-fires-zero-true-blocks.md))*
86. A guard that fires often is a guard that's working. *([PM-015](postmortems/015-eight-thousand-fires-zero-true-blocks.md))*
87. A guard that never fires means the bad behavior stopped. *([ADR-016](adr/016-guards-are-audited-against-their-own-fire-logs.md))*
88. The exemption list and the trigger list of a detection rule don't overlap. *([PM-017](postmortems/017-the-guard-that-suppressed-itself.md))*
89. Guard block-messages don't teach the agent how to evade the guard. *([PM-017](postmortems/017-the-guard-that-suppressed-itself.md))*
90. Adding another guard is free. *([PM-019](postmortems/019-when-the-safety-layer-became-the-outage.md), [PM-021](postmortems/021-alarm-fatigue-by-the-numbers.md))*
91. Approval gates get more scrutiny with each repeated approval, not less. *([PM-021](postmortems/021-alarm-fatigue-by-the-numbers.md))*
92. The agent can't approve its own permission slip. *([PM-012](postmortems/012-agent-forged-its-own-approval-marker.md))*
93. The enforcement layer can't itself take down every tool call. *([PM-019](postmortems/019-when-the-safety-layer-became-the-outage.md))*
94. Green smoke tests on the integrity system mean the integrity system has integrity. *([PM-013](postmortems/013-integrity-ledger-certified-fabricated-results.md))*
95. An anti-fabrication gate rejects claims that are partially fabricated, not just fully fabricated. *([PM-013](postmortems/013-integrity-ledger-certified-fabricated-results.md))*

## Money, scale, and production

96. An LLM checking "does anything need doing?" every 30 minutes is a cheap way to stay safe. *([PM-041](postmortems/041-seventy-five-dollars-a-day-of-heartbeat.md))*
97. Verifying a deploy once means it stays deployed. *([PM-029](postmortems/029-deploy-verified-then-reverted-thirty-minutes-later.md))*
98. The database that answers your query is the database you meant to ask. *([PM-027](postmortems/027-the-database-that-lied-by-being-present.md))*
99. A dashboard that renders is a dashboard showing current data. *([PM-010](postmortems/010-stale-local-dashboard-forks-diverged-from-production.md), [PM-035](postmortems/035-the-model-talked-us-out-of-being-right.md))*
100. Nothing outbound (emails, orders, publishes) will fire on synthetic inputs. *([PM-031](postmortems/031-the-smoke-test-that-emailed-the-boss.md))*
101. The agent deletes only what stopped mattering. *([PM-040](postmortems/040-the-irreversible-ab-test.md), [PM-037](postmortems/037-the-investigator-was-the-culprit.md))*
102. The comparison data behind a shipped decision will still exist when you want to re-check the decision. *([PM-040](postmortems/040-the-irreversible-ab-test.md))*
103. Doing all of the above carefully yourself, once, means it stays done across a fleet of agents working around the clock. *([ADR-002](adr/002-hooks-as-enforcement-not-instructions.md))*

---

**The scale point, in one paragraph:** each line above looks paranoid in isolation, and none of them survived contact with production. The structure that replaced assumption with enforcement — 148 hooks, checkout leases, append-only audit logs, curator-mediated memory, adversarial breaks pointed in both directions, and audits of the guards themselves — wasn't designed; it accreted, one postmortem at a time. That accretion is documented with receipts across this repo, and the honest summary of the whole record is: **the agent is a superb worker and an unreliable witness, and every unverified assumption on this list eventually sent a bill.**
