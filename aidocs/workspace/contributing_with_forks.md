# Contributing through your own forks

Use this procedure if you **don't** have push access to the team repos, or prefer to work
through your own forks. Collaborators with push access follow [onboarding.md](onboarding.md)
instead. Everything else (building, testing, the stub effect) is the same.

## The repos

| Repo | Team copy (PR target) | Your fork | Its upstream |
|---|---|---|---|
| The workspace | `beyondeye/omarchy_screensavers` | `<you>/omarchy_screensavers` | (none) |
| `ttfx/` submodule | `beyondeye/ttfx` | `<you>/ttfx` | `omacom/ttfx` |
| `omarchy-screensaver/` submodule | `beyondeye/omarchy-screensaver` | `<you>/omarchy-screensaver` | `omacom/omarchy-screensaver` |

Remote names inside each submodule after setup:
- `origin`: your fork, where you push
- `team`: the beyondeye fork, where PRs go
- `upstream`: omacom

`.gitmodules` keeps pointing at the team forks, so your PRs never change it.
`make use-forks` changes the submodule URLs in your `.git/config` only.

## 1. Fork and clone the workspace

```bash
gh repo fork beyondeye/omarchy_screensavers --clone   # origin = your fork, upstream = beyondeye
cd omarchy_screensavers
make setup        # fetches the submodules (from the team forks) and puts them on their branches
./ait setup       # aitasks dependencies and the task-data worktree
```

`gh repo fork` copies every branch, including the `aitask-data` branch that holds the task files.

## 2. Point the submodules at your forks

```bash
make use-forks
```

This forks `beyondeye/ttfx` and `beyondeye/omarchy-screensaver` to your account, using
your `gh` login. If you already have a fork from the same family, such as an older fork of
`omacom/ttfx`, GitHub reuses it, and the script pushes the team branch (`feat/stub-effect`)
into it. Then it sets the three remotes and makes each tracked branch follow `origin`.

Options: `make use-forks ARGS="--user <login>"` names a different account, and `ARGS="--no-fork"`
skips the `gh repo fork` call when your forks already exist. Your forks must be named `ttfx` and
`omarchy-screensaver`. The script is safe to re-run, and `make status` shows where you are.

Then `make check` and `make try`, as in [onboarding.md](onboarding.md#3-check-it-works).

## 3. Change an effect (a submodule)

```bash
cd ttfx
git switch -c feat/my-effect feat/stub-effect
# ... edit, make try, make check ...
git commit -am "Add the my-effect effect"
git push -u origin feat/my-effect
gh pr create --repo beyondeye/ttfx --base feat/stub-effect
```

Use the same pattern in `omarchy-screensaver/`, targeting `--base main`. Before committing
there, run `git checkout Cargo.lock`; see [dev_workspace.md](dev_workspace.md#known-quirk-omarchy-screensavers-cargolock).

## 4. Change the workspace (Makefile, docs, submodule pointers)

```bash
git switch -c docs/my-change
# ... edit ...
git commit -am "docs: ..."
git push -u origin docs/my-change
gh pr create --repo beyondeye/omarchy_screensavers
```

**Merge order for submodule pointers.** A workspace commit that moves `ttfx` or
`omarchy-screensaver` to a new commit only works for others once that commit exists in the
**team** fork. If the pin points at a commit that exists only in your fork, everyone else's
`make sync` fails. So:
1. Get the submodule PR merged into `beyondeye/ttfx` (or `beyondeye/omarchy-screensaver`) first.
2. Then `cd ttfx && git fetch team && git switch --detach team/<branch>`, go back up, and run
   `git add ttfx`. That pins the commit as it was merged: a squash merge gives it a different
   hash from yours.
3. Open the workspace PR with that pointer.

## 5. Staying current

```bash
git pull upstream main     # the workspace from beyondeye (your origin is your fork)
make sync                  # fetch every submodule remote, check out the pins, back onto branches
git push origin main       # optional: keep your fork's main current
```

`make sync` fetches from `team` as well as your fork, so it finds pins that only the team
fork has.

## Task data (aitasks) in a fork

Your fork has its own copy of the `aitask-data`, `aitask-ids` and `aitask-locks` branches.
`ait` claims new task numbers from `aitask-ids` on `origin`, which is your fork, so
those numbers don't come from the team's counter and can clash with real task numbers.
Don't open workspace PRs that add task files. Propose work as an issue on
`beyondeye/omarchy_screensavers`, for example with the `aitask-contribute` skill. The
task files you see are your fork's copy as of when you forked; they don't follow the
team's task list.
