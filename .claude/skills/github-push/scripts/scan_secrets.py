#!/usr/bin/env python3
"""
Secret/key scanner for the github-push skill.

Scans the currently staged diff (git diff --cached) for patterns that look
like credentials, API keys, or private keys. Only looks at ADDED lines
(lines starting with a single '+', not the '+++' file header), so it won't
flag pre-existing context lines that happen to be shown in the diff.

Usage:
  python scan_secrets.py [--repo PATH]
      Scans the staged diff (git diff --cached). This is the mode the
      github-push skill uses locally before a commit.

  python scan_secrets.py [--repo PATH] --diff-against <ref-or-sha>
      Scans the diff between <ref-or-sha> and HEAD instead of the staged
      diff. This is the mode a CI workflow uses, since there's no staging
      area in a checked-out PR -- pass the PR's base commit SHA.

Exit code 0: nothing suspicious found.
Exit code 1: one or more suspicious lines found (printed to stdout).

This is a pattern-based check, not a guarantee. It catches common,
recognizable secret shapes (AWS keys, GitHub/Slack tokens, private key
headers, obvious "PASSWORD = ..." assignments). It will not catch every
possible secret, and it can false-positive on things that merely look like
one (e.g. a test fixture). A hit means "stop and look", not "this is
definitely a leak" — the skill should show the flagged lines to the user
and wait for them to confirm before committing. Never auto-commit past a
flag and never auto-strip the line either.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("AWS Access Key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Access Key (assignment)",
     re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{30,}['\"]")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key header",
     re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |)PRIVATE KEY-----")),
    # Note: no \b before the keyword -- \b treats underscore as a word
    # character, so DB_PASSWORD or API_KEY would never match a leading \b.
    # Matching the keyword as a substring of the identifier instead.
    ("Generic secret assignment",
     re.compile(r"(?i)[A-Za-z0-9_]*(secret|api[_-]?key|token|password|passwd)"
                r"[A-Za-z0-9_]*\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout


def scan(repo, diff_against=None):
    repo = Path(repo).resolve()
    if diff_against:
        diff = run(["git", "diff", f"{diff_against}...HEAD", "-U0"], repo)
    else:
        diff = run(["git", "diff", "--cached", "-U0"], repo)

    findings = []
    current_file = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current_file = line[4:]
            if current_file.startswith("b/"):
                current_file = current_file[2:]
            continue
        if line.startswith("---"):
            continue
        if not line.startswith("+"):
            continue
        content = line[1:]
        for name, pattern in PATTERNS:
            if pattern.search(content):
                findings.append((current_file or "?", name, content.strip()[:120]))

    if not findings:
        print("No obvious secrets found in the staged diff.")
        return 0

    print(f"Found {len(findings)} line(s) that look like they might contain a secret:\n")
    for file, name, content in findings:
        print(f"  {file}: {name}")
        print(f"    {content}")
    print("\nThis is a pattern match, not a certainty. Confirm with the user before")
    print("committing -- either the line comes out, or they explicitly confirm it's")
    print("a false positive (e.g. a test fixture).")
    return 1


def main():
    parser = argparse.ArgumentParser(description="Scan staged diff for likely secrets")
    parser.add_argument("--repo", default=".", help="Path to the git repo (default: current directory)")
    parser.add_argument("--diff-against", default=None,
                         help="Compare against this ref/SHA instead of the staged diff (CI usage)")
    args = parser.parse_args()
    sys.exit(scan(args.repo, args.diff_against))


if __name__ == "__main__":
    main()
