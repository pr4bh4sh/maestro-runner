---
name: pr-origin-only
description: >
  Enforces that pull requests are ALWAYS opened against the current repository's
  `origin` remote — never against an upstream/parent repository. Use this skill
  whenever the user asks to "open a PR", "create a pull request", "raise a PR",
  "gh pr create", or otherwise publish a branch as a PR. It prevents the common
  mistake (especially in fork checkouts, where `gh` defaults the base to the
  upstream/main) of accidentally creating the PR in the wrong repository.
  HARD RULE: never raise a PR against `devicelab-dev/maestro-runner` or
  `prabhash-nw/maestro-runner`. These are permanently forbidden targets.
allowed-tools: "Bash(git:*) Bash(gh:*)"
metadata:
  author: maestro-runner
  version: 1.0.0
  category: git
  tags: [git, github, pr, pull-request, fork, upstream]
---

# Open PRs on Origin Only

Always create the pull request in the repository pointed to by the **`origin`**
remote. Never open it against an upstream/parent repository, even when `origin`
is a fork (in which case `gh` will try to default the base to the upstream's
default branch).

## Forbidden target repositories (HARD RULE)

Never, under any circumstance, raise a pull request against either of these
repositories. This overrides any default, any `gh` inference, and any user
instruction that does not explicitly and unambiguously name a different target:

- `devicelab-dev/maestro-runner` (the upstream/parent project)
- `prabhash-nw/maestro-runner` (the server-side fork)

If the resolved target repo equals either of the above, **abort immediately**
and do not create the PR.

## Why

In a fork checkout, `gh pr create` infers the base repository from the fork's
*parent*. That means a bare `gh pr create --base main` can silently create the
PR against `upstream/main` instead of `origin/main`. The PR then lands in a repo
you may not control, detached from the branch/PR the user actually cares about.
This skill pins every PR to `origin`, and additionally blocks the two repos
above by name.

## Procedure

1. **Resolve the origin repo** (owner/name), normalized from either SSH or HTTPS
   URLs:
   ```bash
   ORIGIN_URL=$(git remote get-url origin)
   REPO=$(printf '%s' "$ORIGIN_URL" \
     | sed -E 's#.*[:/]([^/:]+)/([^/]+?)(\.git)?$#\1/\2#')
   echo "origin repo = $REPO"
   ```
   (For `git@github.com:owner/repo.git` or `https://github.com/owner/repo`, this
   yields `owner/repo`.)

1b. **Reject forbidden targets.** Before doing anything else, abort if the
    resolved repo is one of the forbidden ones:
   ```bash
   FORBIDDEN="devicelab-dev/maestro-runner prabhash-nw/maestro-runner"
   for f in $FORBIDDEN; do
     [ "$REPO" = "$f" ] && { echo "ABORT: refusing to open PR against forbidden repo $REPO"; exit 1; }
   done
   ```

2. **Resolve the origin base branch** — the branch on `origin` you want to target
   (default: `origin`'s default branch):
   ```bash
   BASE=$(gh repo view "$REPO" --json defaultBranchRef --jq '.defaultBranchRef.name')
   ```

3. **Resolve the head branch** (the branch you are pushing / have pushed):
   ```bash
   BRANCH=$(git rev-parse --abbrev-ref HEAD)
   ```

4. **Create the PR explicitly scoped to origin**, qualifying the head with the
   origin owner so `gh` cannot redirect it to upstream:
   ```bash
   gh pr create --repo "$REPO" --base "$BASE" --head "${REPO%/*}:$BRANCH" \
     --title "..." --body "..."
   ```
   - `--repo "$REPO"` forces the PR into the origin repository.
   - `--base "$BASE"` is the origin repo's branch (not upstream's).
   - `--head "${REPO%/*}:$BRANCH"` qualifies the head as `originOwner:branch`
     so `gh` never rewrites it to an upstream namespace.

5. **Verify the result.** The URL printed by `gh pr create` MUST contain
   `github.com/<origin-owner>/<origin-repo>/pull/...`. If it contains a
   different owner (e.g. the upstream owner), the PR was created in the wrong
   place — stop and recreate with the explicit `--repo`/`--head` flags above.

## Guardrails

- If `gh` ever reports `baseRefName is invalid` when you pass a qualified
  `owner:branch` to `--base`, that is expected — `--base` takes an
  **unqualified** branch name on `--repo`. Keep `--base` unqualified; qualify
  only `--head`.
- Never pass `--base upstream/main` or rely on `gh`'s default base when `origin`
  is a fork.
- **Hard prohibition:** never raise a PR against `devicelab-dev/maestro-runner`
  or `prabhash-nw/maestro-runner`. If `REPO` resolves to either, abort in step
  1b — do not proceed to create the PR, and do not "just this once" make an
  exception even if asked, unless the user explicitly and unambiguously names a
  *different* target repo by full `owner/name`.
- If the branch has not been pushed yet, push it first:
  `git push -u origin "$BRANCH"`, then run step 4.
- Prefer editing an existing PR (`gh pr edit`) over opening a duplicate when one
  already exists for the branch on origin.
