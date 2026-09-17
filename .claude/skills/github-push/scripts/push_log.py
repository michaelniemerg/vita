#!/usr/bin/env python3
"""
Push observability log for the github-push skill.

The log lives at ops/push-log.jsonl INSIDE the repo and is tracked by git —
this makes it durable and visible on GitHub itself, not just a local file
that disappears when the working directory does. Because of that, logging a
push takes its own small commit (kept separate from the code commit so the
log never shows up as a "file changed" in someone else's diff); both
commits then go out together in a single `git push`.

Usage:
  python push_log.py record [--repo PATH] [--commit HASH]
      Appends an entry for the given commit (default: current HEAD) to
      ops/push-log.jsonl and commits that one file with a small
      "chore(observability)" commit. Does NOT push — run this after
      committing your actual change and before the single `git push`
      that sends both commits.

  python push_log.py show [--repo PATH] [-n N]
      Prints the last N (default 20) recorded pushes as a table. Works
      against any clone of the repo, since the log is tracked in git.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_REL_PATH = Path("ops") / "push-log.jsonl"


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def remote_commit_url(repo, commit_hash):
    try:
        remote_url = run(["git", "remote", "get-url", "origin"], repo)
    except RuntimeError:
        return None
    url = remote_url
    if url.startswith("git@"):
        # git@github.com:owner/repo.git -> https://github.com/owner/repo.git
        url = url.split("git@", 1)[1].replace(":", "/", 1)
        url = "https://" + url
    if url.endswith(".git"):
        url = url[:-4]
    return f"{url}/commit/{commit_hash}"


def record(repo, commit_hash=None):
    repo = Path(repo).resolve()
    commit_hash = commit_hash or run(["git", "rev-parse", "HEAD"], repo)
    commit_hash = run(["git", "rev-parse", commit_hash], repo)  # normalize to full hash
    short_hash = commit_hash[:7]
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    message = run(["git", "log", "-1", "--pretty=%s", commit_hash], repo)
    author = run(["git", "log", "-1", "--pretty=%an <%ae>", commit_hash], repo)
    files_changed_raw = run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash], repo
    )
    files_list = [f for f in files_changed_raw.splitlines() if f]
    url = remote_commit_url(repo, commit_hash)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": branch,
        "commit": commit_hash,
        "commit_short": short_hash,
        "message": message,
        "author": author,
        "files_changed": files_list,
        "files_changed_count": len(files_list),
        "url": url,
    }

    log_path = repo / LOG_REL_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Commit just the log file, as its own small commit. Not pushed here —
    # the caller pushes once, after this and the code commit both exist
    # locally.
    run(["git", "add", str(LOG_REL_PATH)], repo)
    run(["git", "commit", "-m", f"chore(observability): log push {short_hash}"], repo)

    print(f"Logged push: {short_hash} on {branch} ({len(files_list)} file(s) changed)")
    if url:
        print(f"View: {url}")
    print("Log entry committed locally. Run `git push` once to send both commits.")
    return entry


def show(repo, n):
    repo = Path(repo).resolve()
    log_path = repo / LOG_REL_PATH
    if not log_path.exists():
        print("No push history recorded yet.")
        return

    entries = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    entries = entries[-n:]
    if not entries:
        print("No push history recorded yet.")
        return

    print(f"{'Timestamp (UTC)':<20} {'Branch':<15} {'Commit':<9} {'Files':<6} Message")
    print("-" * 90)
    for e in entries:
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        print(
            f"{ts:<20} {e.get('branch', ''):<15} {e.get('commit_short', ''):<9} "
            f"{e.get('files_changed_count', 0):<6} {e.get('message', '')[:40]}"
        )


def main():
    parser = argparse.ArgumentParser(description="Push observability log")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_record = sub.add_parser("record", help="Log the given (or current HEAD) commit as a push event")
    p_record.add_argument("--repo", default=".", help="Path to the git repo (default: current directory)")
    p_record.add_argument("--commit", default=None, help="Commit hash to log (default: HEAD)")

    p_show = sub.add_parser("show", help="Show recorded push history")
    p_show.add_argument("--repo", default=".", help="Path to the git repo (default: current directory)")
    p_show.add_argument("-n", type=int, default=20, help="Number of recent entries to show")

    args = parser.parse_args()

    try:
        if args.cmd == "record":
            record(args.repo, args.commit)
        elif args.cmd == "show":
            show(args.repo, args.n)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
