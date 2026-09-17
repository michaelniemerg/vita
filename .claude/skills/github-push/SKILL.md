---
name: github-push
description: Stage, run pre-commit checks, commit, and push local code changes to a GitHub repository for the Vita project, with observability built in. Runs a secret/key scan and the relevant pytest suite before every commit, drafts a Conventional Commits-style message, and requires explicit sign-off separately before the commit and before the push. Also logs every push to a durable, git-tracked ops/push-log.jsonl. Always use this skill whenever the user asks to commit, push, commit and push, ship, sync, or publish changes to GitHub, or asks to see recent push/commit history for a repo.
---

# GitHub Push (with pre-commit checks and observability)

Stages a working directory's changes, runs two automatic checks, commits
with a Conventional Commits message, logs the push, and pushes to GitHub —
with an explicit human sign-off at two separate points (before the commit,
and again before the push), not one sign-off covering both.

## Before doing anything

1. **Confirm credentials are already set up. Never ask the user to paste a
   token or password into chat, and never store one yourself.** Check for
   one of:
   - An SSH key already loaded (`ssh -T git@github.com` succeeds), or
   - The `gh` CLI already authenticated (`gh auth status`), or
   - A `GITHUB_TOKEN` / `GH_TOKEN` environment variable already set.

   If none of these are present, tell the user exactly that and stop. Don't
   improvise a workaround that involves typing a secret into the
   conversation.

2. **Confirm the repo and branch.** If the working directory isn't yet a
   clone of the target repo and the user has given a remote URL, clone it
   first (`git clone <url>`). Otherwise confirm which local repo and branch
   are in play if it isn't obvious from context.

3. **Never push without showing the user what's about to go out and getting
   an explicit go-ahead first.** A push is a real, external, only
   partially-undoable action — treat it the same as any other
   explicit-permission action, not a routine step. This is separate from
   the commit-time sign-off in step 4 below; neither one substitutes for
   the other.

## Workflow

1. **Check repo state.** `git status`, current branch, `git remote -v`, and
   whether the local branch is ahead/behind its upstream.

2. **Stage and review.** Stage the files the user has actually been working
   on — don't blindly `git add -A` if the working tree has unrelated
   untracked files. Then show a diff summary (`git diff --cached --stat`)
   so the user can see what's about to be committed.

3. **Run pre-commit checks, in this order. Both must pass or be explicitly
   overridden by the user before continuing to step 4.**

   a. **Secret scan.**
      ```
      python3 scripts/scan_secrets.py --repo <path-to-repo>
      ```
      This is a pattern match against the staged diff (AWS keys, GitHub/
      Slack tokens, private key headers, `SOMETHING_PASSWORD = "..."`-style
      assignments), not a guarantee. If it exits 1, show the flagged lines
      to the user directly and stop. Do not commit until they've either
      removed the line or explicitly confirmed it's not a real secret (a
      test fixture, a placeholder). Never silently strip a flagged line and
      never commit past a flag without the user's explicit word.

   b. **Test suite.** Run pytest scoped to whichever module the staged
      files fall under (`modules/mortality/`, `modules/propensity/`,
      `modules/persistency/`, `modules/pricing-engine/`,
      `modules/quote-intel/`, `mcp-server/`, `ui/`). If the
      change spans more than one module, or doesn't clearly map to one, run
      the full suite instead. If any test fails, show the failure output
      and stop. Do not commit until the user explicitly says to proceed
      anyway, or the failure is fixed and the suite is re-run clean.

4. **Draft a Conventional Commits message and get sign-off on it
   specifically, before committing.** Format: `<type>(<scope>): <summary>`.
   - `<type>` — one of `feat`, `fix`, `chore`, `docs`, `test`, `refactor`,
     inferred from the diff. Don't ask unless it's genuinely ambiguous.
   - `<scope>` — the module folder touched (e.g. `pricing-engine`,
     `mortality`). Omit it if the change spans more than one module or
     isn't module-specific (a repo-root doc change, for instance).
   - Show the drafted message and wait for explicit confirmation or a
     correction. This sign-off covers the commit only — it is not the same
     approval as the push go-ahead in step 6, even if the user answers both
     in one message.

5. **Commit the code change** with the confirmed message.

6. **Log the push.** Run:
   ```
   python3 scripts/push_log.py record --repo <path-to-repo>
   ```
   This appends an entry to `ops/push-log.jsonl` (commit hash, branch,
   author, timestamp, files changed, a constructed link to the commit) and
   commits *just that one file* as its own small
   `chore(observability): log push <hash>` commit. It does not push.
   Keeping this as a separate commit means the log entry never shows up as
   a "file changed" in someone else's diff of the actual change.

7. **Confirm and push.** State the branch, remote, and both pending commits
   (the code change and the log entry), and ask for an explicit go-ahead —
   distinct from the step-4 sign-off. On confirmation, run `git push` once;
   it sends both commits together.

8. **Report back.** Relay the branch, short commit hash, files-changed
   count, and the commit link. If the push fails (e.g. the remote has
   diverged), report the exact error — don't force-push unless the user
   explicitly asks for that.

## Showing push history

If the user asks to see recent push activity or "observability" for a repo,
run:
```
python3 scripts/push_log.py show --repo <path-to-repo> -n 20
```
This reads `ops/push-log.jsonl` directly, so it works on any clone of the
repo — including one this session hasn't pushed from itself.

## Environment note

Credential persistence depends on what's running this skill, not on the
skill itself:
- **Claude Code or Claude Desktop**, running locally: an SSH key or `gh
  auth login` set up on that machine persists across sessions the normal
  way.
- **A connected local-shell tool inside a claude.ai chat** (e.g. a
  Windows-command connector): whether credentials persist depends on that
  connector and the underlying machine, not on this skill — check step 1
  fresh each session rather than assuming a prior session's check still
  holds.
- **An ephemeral sandbox with no persistent filesystem**: nothing survives
  between sessions, including a cloned repo — it needs re-cloning, and
  credentials need to already be available in that fresh session. The
  durable part is whatever's already on GitHub, including
  `ops/push-log.jsonl` once it's been pushed at least once.
