# Pattern: Quoted-Prose Stripping — Content Guards Must Not Judge Mentions as Uses

**Problem:** Content-scanning guards (dangerous-command gates, claim checkers, phrase blockers) regex the raw text of commands and responses. But agents *write about* dangerous things constantly — documentation with `git commit` examples in heredocs, postmortems quoting banned phrases, bug reports quoting a guard's own regex. Judging mentions as uses produces a false-positive family: four false blocks in one session of ours came from exactly this.

**Mechanism:** Before pattern-matching, reduce the text to its **operative surface**: for shell commands, parse with `shlex` and drop quoted arguments/heredoc bodies; for responses, drop code fences, blockquotes, and inline code. Match only what would actually execute or assert.

## Sanitized skeleton

```python
import re, shlex

def strip_heredocs(cmd: str) -> str:
    # remove <<MARKER ... MARKER bodies (documentation payloads, commit messages)
    return re.sub(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n\1\b", " ", cmd, flags=re.S)

def operative_shell(cmd: str) -> str:
    cmd = strip_heredocs(cmd)
    try:
        toks = shlex.split(cmd, posix=True)
    except ValueError:                 # unbalanced quotes: fail toward caution,
        return cmd                     # but LOG that parsing failed
    return " ".join(t for t in toks if not was_quoted(cmd, t))

def operative_prose(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)    # code fences
    text = re.sub(r"`[^`]+`", " ", text)                  # inline code
    text = re.sub(r"^\s*>.*$", " ", text, flags=re.M)     # blockquotes
    return text
```

## Failure modes of this pattern

- **Stripping opens an evasion channel.** If quoting exempts content, wrapping a *real* dangerous command in quotes/heredoc becomes the workaround. Balance: strip for *content* guards (phrases, claims), but for *execution* guards, remember quoted strings can still reach `eval`/`bash -c` — match those invocation shapes explicitly.
- **Partial adoption is the actual failure.** We shipped stripping in three guards and "never generalized" — the false positives just moved to the unpatched ones. Stripping belongs in the shared dispatcher context ([guard-dispatch-consolidation](guard-dispatch-consolidation.md)), written once.
- **A guard that can't survive its own bug report** — blocking any response that quotes its regex — censors discussion of itself and burns operator trust fast ([PM-018](../postmortems/018-the-stop-hook-that-rewarded-hand-waving.md)).
- **Parser failure modes:** `shlex` throws on unbalanced quotes (common in generated text). Decide the failure direction consciously and log it; silent fallback to raw matching resurrects the false positives silently.
- **Block messages that enumerate trigger strings teach evasion** — the complementary leak: describe the rule, don't list the literals ([PM-017](../postmortems/017-the-guard-that-suppressed-itself.md)).

**Where it's enforced in our stack:** the content-scanning guards after tasks #1820/#1839; generalization into the dispatcher's shared context is the tracked completion of the lesson.
