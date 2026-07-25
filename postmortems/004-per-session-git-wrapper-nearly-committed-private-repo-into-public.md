# The Reliability Wrapper Almost Committed Our Private Repo Into a Public One

**Keywords:** git internals, GIT_INDEX_FILE, git staging area, per-session index, `git -C`, git wrapper script, nested git repository, monorepo, AI agent git safety, concurrent sessions, data exfiltration risk

**Incident date:** 2026-07-25 · **Internal refs:** tasks #1779 (wrapper), #2118 (fix) · **Status:** fixed the same day; the fix is new, so the evidence is a regression test, not history — see below

---

## What broke

To publish this very repository, we created it as a small standalone git repo *nested inside* the large private one it documents — a clean-room directory with its own remote, excluded from the parent by `.gitignore`. Ordinary setup.

Every git command run against that nested repo silently used the **wrong staging area**. Specifically, it used a staging area (git index) pre-loaded with the **23,569 tracked files of the private parent repo**. A freshly-`git init`'d, supposedly empty repo reported **23,580 files staged for commit**. When we staged the 11 real files of the public repo, they were added *into the parent's index at bogus top-level paths* — leaving the private repo's entire file list sitting in the staging area, one `git commit` away from being written into a commit on the **public** repo's branch.

The reliability layer built to make agent git operations *safer* was the thing that nearly caused the leak.

## How it was detected

Not by any guard. By an impossible number.

`git status` on a brand-new repo containing 11 files reported ~23,580 staged. An empty repo cannot have 23,580 of anything. That single implausible count — the kind of thing you notice only if you actually read tool output instead of skimming for "success" — was the entire detection. Read the wrapper source, and the mechanism fell out in one line.

## Root cause

The private repo uses a per-session git wrapper (`.claude/bin/git`, from an earlier reliability effort). Its job: give each concurrent agent session its own private staging area, so twelve sessions staging files at once don't stomp each other's in-flight work in the single shared `.git/index`. It does this by setting `GIT_INDEX_FILE` to a session-scoped index file inside the resolved repo, initialized from that repo's `HEAD`.

To find "the resolved repo," it ran:

```bash
gitdir="$(git rev-parse --git-dir)"     # no arguments forwarded
```

That call **ignores the command's own `-C` / `--git-dir` flags.** So `git -C ./public-repo add .` resolved `gitdir` from the *current directory* — the parent repo — set `GIT_INDEX_FILE` to the parent's session index seeded from the parent's 23,569-file `HEAD`, and only then handed control to the real git, which dutifully changed into `./public-repo` and staged files **into the parent's index**. The same blind spot poisoned the index-initialization step, which ran `read-tree HEAD` against the parent too.

The deeper cause is the one worth keeping: **an abstraction that silently rewrites a global (`GIT_INDEX_FILE`) is only safe if it resolves that global against the *exact same target* the wrapped command will use.** The wrapper resolved the target one way (from CWD) and the real command resolved it another (from `-C`). Any divergence between "what the wrapper thinks you're operating on" and "what you're actually operating on" becomes a silent cross-wiring. Here the two targets were two different repositories, and one was private.

## Blast radius

Zero leaked — contained before any commit. What it cost was the containment itself: the poisoned session index had to be reset (`GIT_INDEX_FILE=<file> git read-tree HEAD`), and the public repo rebuilt from scratch with an explicit `GIT_INDEX_FILE` override forced onto **every** command, with the commit's file list manually verified to be exactly 11 before anything reached the remote.

The trust cost is larger than the time cost. Every prior cross-repo git operation any session had ever run through this wrapper is now suspect — not necessarily wrong, but no longer assumed right. And there was a coda: when the incident was later written into our knowledge base, the write tool passed the backticked command names in the description *through a shell that executed them* — a second, unrelated tooling failure stacked on the first. Two separate infrastructure layers mis-handling the same incident, in the same hour, is the whole thesis of this repo in miniature: **the failures cluster in the machinery around the agent, not in the agent's reasoning.**

## The fix

Both layers, one change to `.claude/bin/git`:

1. **Repair the class, not the symptom.** Before resolving the git directory, parse the leading global options the real command will use — `-C`, `--git-dir`, `--work-tree`, `--namespace`, `--bare`, `-c` — and forward them to the internal resolution, so the wrapper resolves the *same* repository git will operate on:

   ```bash
   gitdir="$(git "${lead[@]}" rev-parse --absolute-git-dir)"   # forwards -C et al.
   ```

   `--absolute-git-dir` (git >= 2.13) also returns an absolute path directly, retiring a hand-rolled `pwd`-prefixing block that would itself have mis-resolved under `-C`. The index-initialization `read-tree` now forwards the same options, so a nested repo's session index is seeded from the *nested* repo's HEAD.

2. **The operational guard that actually caught it** already exists and stays: a hard rule that any git command targeting a repo other than the primary one must set `GIT_INDEX_FILE` explicitly. That rule is what made the safe rebuild possible while the wrapper was still broken; the code fix is what removes the need to remember it.

## Has the guard fired since?

Honestly: the fix is hours old, so there is no "since" yet — an untested fix is a hypothesis, and this repo's rule is to say so. What exists is a **regression test** run against the patched wrapper:

- `git -C <nested-repo> status` now reports a **clean** nested tree, not 23,580 phantom parent files.
- The nested repo's session index is seeded from the **nested** HEAD (11 files), verified by counting it.
- No session-index file is created on the parent side by a `-C <nested>` command.
- The ordinary no-`-C` path, subdirectory invocations, `-c` config options, and outside-any-repo calls all still resolve correctly.

That is the bar this fix has cleared. Whether it holds under the next unanticipated invocation is what "has the guard fired since" will answer in a future revision of this file — which is exactly why the field exists.

## Lessons for agent-driven development

1. **An abstraction over a global must resolve that global against the command's real target.** The wrapper set `GIT_INDEX_FILE` from CWD while the command it wrapped honored `-C`. Whenever a shim rewrites environment or arguments, it must compute its rewrite from the *same* inputs the wrapped tool will see — or it silently cross-wires them.
2. **Implausible output is a first-class detector — if something reads it.** No guard fired here. A count that couldn't be true did the work. Agents that pattern-match tool output for "success" and move on will sail straight past exactly this class of catch; reading the numbers is not optional.
3. **Your safety layer is attack surface.** Code written to make operations *safer* (per-session isolation) created a novel, higher-consequence failure (cross-repo staging) that the plain tool never had. Every reliability mechanism you add is also a new thing that can be wrong — and it tends to be wrong in ways more surprising than the problem it solved.
4. **When the target is sensitive, verify the artifact, not the exit code.** "The commit succeeded" says nothing about *what* it committed. The only thing that made the rebuild trustworthy was manually confirming the commit held exactly the 11 intended files. For anything touching a trust boundary — public vs. private, prod vs. dev — check the contents, every time.
