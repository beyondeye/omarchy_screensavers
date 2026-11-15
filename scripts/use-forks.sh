#!/usr/bin/env bash
# use-forks.sh — point this checkout's submodules at YOUR forks.
#
# For developers who work through their own GitHub forks instead of pushing to
# the team forks. For each submodule (ttfx, omarchy-screensaver) it:
#   1. forks the team fork (the URL in .gitmodules) to your account with gh,
#      unless --no-fork (or the fork already exists: gh then reuses it)
#   2. sets the submodule URL in .git/config only (.gitmodules stays shared)
#   3. sets remotes: origin = your fork, team = the team fork, upstream = omacom
#   4. makes the tracked branch follow origin, pushing it there if your fork lacks it
#
# Usage: scripts/use-forks.sh [--user LOGIN] [--no-fork]
#   --user LOGIN   GitHub account that owns your forks (default: the gh login)
#   --no-fork      don't call `gh repo fork`; the forks must already exist
# Safe to re-run. Run it after `make setup`.

set -euo pipefail
cd "$(dirname "$0")/.."

user="" fork=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) user="${2:?--user needs a login}"; shift 2 ;;
    --no-fork) fork=0; shift ;;
    -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
done
[[ -n "$user" ]] || user=$(gh api user -q .login)

set_remote() { # repo name url
  if git -C "$1" remote get-url "$2" >/dev/null 2>&1; then
    git -C "$1" remote set-url "$2" "$3"
  else
    git -C "$1" remote add "$2" "$3"
  fi
}

for sub in ttfx omarchy-screensaver; do
  [[ -e "$sub/.git" ]] || { echo "$sub: not initialized — run 'make setup' first" >&2; exit 1; }
  team_url=$(git config -f .gitmodules "submodule.$sub.url")
  upstream_url=$(git config -f .gitmodules "submodule.$sub.upstream")
  branch=$(git config -f .gitmodules "submodule.$sub.branch")
  team_slug=$(sed -E 's#^https://github.com/##; s#\.git$##' <<<"$team_url")   # owner/repo
  repo=${team_slug#*/}
  fork_url="https://github.com/$user/$repo.git"

  if [[ "${team_slug%%/*}" == "$user" ]]; then
    echo "$sub: $user owns the team fork already; nothing to change"
    continue
  fi
  if (( fork )); then
    gh repo fork "$team_slug" --clone=false >/dev/null 2>&1 || true
    gh repo view "$user/$repo" >/dev/null 2>&1 || {
      echo "$sub: no fork at $user/$repo. If yours has another name, rename it to '$repo' on GitHub." >&2
      exit 1
    }
  fi

  # check before changing anything, so a missing fork leaves the checkout as it was
  if ! git ls-remote -q "$fork_url" >/dev/null 2>&1; then
    echo "$sub: can't reach $fork_url — create the fork (drop --no-fork) and re-run; nothing changed" >&2
    exit 1
  fi

  git config "submodule.$sub.url" "$fork_url"
  set_remote "$sub" origin "$fork_url"
  set_remote "$sub" team "$team_url"
  set_remote "$sub" upstream "$upstream_url"
  # --prune: drop origin/* refs left over from when origin was the team fork,
  # so the branch check below sees what your fork really has
  git -C "$sub" fetch -q --prune origin
  git -C "$sub" fetch -q team
  if ! git -C "$sub" rev-parse -q --verify "refs/remotes/origin/$branch" >/dev/null; then
    # e.g. an older fork of omacom/... that predates the team branch
    git -C "$sub" push -q origin "refs/remotes/team/$branch:refs/heads/$branch"
    git -C "$sub" fetch -q origin
  fi
  git -C "$sub" switch -q "$branch" 2>/dev/null || git -C "$sub" switch -q -c "$branch" --track "origin/$branch"
  git -C "$sub" branch -q -u "origin/$branch" "$branch"
  echo "$sub: origin=$fork_url team=$team_url upstream=$upstream_url (on $branch)"
done
