# -*- coding: utf-8 -*-
"""
sanitize_check.py -- pre-publish secret/PII scanner for this repository.

This repo is public documentation distilled from a private production
system. Before every push, this scanner walks every file that would be
published and fails the build if it finds:

  1. Generic secret shapes: IPv4 addresses, email addresses, private-key
     headers, long hex/base64 token literals, cloud key prefixes.
  2. Local-environment leakage: Windows user-profile paths, home dirs.
  3. Operator-defined redline terms loaded from tools/redlines.local.txt
     (gitignored) -- usernames, hostnames, internal system codenames.
     The terms live OUTSIDE the public tree so the scanner itself cannot
     leak what it protects against. If the file is absent the scanner
     still runs the generic checks and warns loudly.

Usage:
    python tools/sanitize_check.py            # scan repo root
    python tools/sanitize_check.py --strict   # missing redlines file = failure

Exit codes: 0 clean, 1 findings (or missing redlines under --strict).
ASCII-only output by design.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REDLINES_PATH = Path(__file__).resolve().parent / "redlines.local.txt"

SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SKIP_FILES = {"redlines.local.txt"}
TEXT_EXTS = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".toml", ".sh", ".cfg", ".ini"}

# (label, regex, allowlist-of-substrings-that-are-fine)
GENERIC_PATTERNS = [
    ("ipv4_address",
     re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
     {"0.0.0.0", "127.0.0.1", "1.0.0.0", "255.255.255.255"}),
    ("email_address",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
     set()),
    ("private_key_header",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
     set()),
    ("aws_access_key",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     set()),
    ("github_token",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
     set()),
    ("generic_api_key_assign",
     re.compile(r"(?i)\b(api[_-]?key|secret|token|passwd|password)\s*[=:]\s*['\"][A-Za-z0-9+/_\-]{16,}['\"]"),
     set()),
    ("long_hex_literal",
     re.compile(r"\b[0-9a-fA-F]{40,}\b"),
     set()),
    ("windows_user_path",
     re.compile(r"(?i)[A-Z]:\\\\?Users\\\\?[A-Za-z0-9_.-]+"),
     set()),
    ("unix_home_path",
     re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
     set()),
]


def load_redlines():
    """One term per line; blank lines and # comments ignored. Case-insensitive."""
    if not REDLINES_PATH.exists():
        return None
    terms = []
    for line in REDLINES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def iter_files(root):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix.lower() not in TEXT_EXTS and path.name != "llms.txt":
            continue
        yield path


def scan_file(path, redline_terms):
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [(path, 0, "unreadable", str(exc))]
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for label, rx, allow in GENERIC_PATTERNS:
            for m in rx.finditer(line):
                if m.group(0) in allow:
                    continue
                findings.append((path, lineno, label, m.group(0)[:60]))
        if redline_terms:
            low = line.lower()
            for term in redline_terms:
                if term.lower() in low:
                    findings.append((path, lineno, "redline_term", term))
    return findings


def main():
    ap = argparse.ArgumentParser(description="Pre-publish secret/PII scanner")
    ap.add_argument("--strict", action="store_true",
                    help="treat a missing redlines.local.txt as failure")
    args = ap.parse_args()

    redline_terms = load_redlines()
    if redline_terms is None:
        print("[WARN] tools/redlines.local.txt not found -- generic checks only")
        if args.strict:
            print("[FAIL] --strict requires the redlines file")
            return 1
    else:
        print("[OK] loaded %d redline terms (contents not shown)" % len(redline_terms))

    all_findings = []
    n_files = 0
    for path in iter_files(REPO_ROOT):
        n_files += 1
        all_findings.extend(scan_file(path, redline_terms))

    if all_findings:
        print("[FAIL] %d finding(s) across %d scanned file(s):" % (len(all_findings), n_files))
        for path, lineno, label, detail in all_findings:
            rel = path.relative_to(REPO_ROOT)
            shown = detail if label != "redline_term" else "(redline term matched -- not echoed)"
            print("  %s:%d  [%s]  %s" % (rel, lineno, label, shown))
        return 1

    print("[OK] clean -- %d files scanned, 0 findings" % n_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
