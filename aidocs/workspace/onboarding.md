# Onboarding: from clone to a running effect

## 1. Prerequisites

- An Omarchy machine (Hyprland). `make try` works in any terminal, but `make run` needs a
  compositor with `wlr-layer-shell`.
- Rust (stable), `pkg-config` and libxkbcommon. On Omarchy/Arch: `sudo pacman -S --needed rust pkgconf libxkbcommon`
- `gh` (GitHub CLI), logged in, if you will push or open PRs
- Push access to `beyondeye/omarchy_screensavers`, `beyondeye/ttfx` and
  `beyondeye/omarchy-screensaver`. Ask the owner to add you as a collaborator on all three.

## 2. Clone

```bash
git clone --recurse-submodules https://github.com/beyondeye/omarchy_screensavers.git
cd omarchy_screensavers
make setup        # puts the submodules on their branches and adds the upstream remotes
./ait setup       # aitasks: installs its dependencies and sets up the task-data worktree
```

Already cloned without `--recurse-submodules`? `make setup` fetches the submodules too.

Task data (`aitasks/`, `aiplans/`) lives on the `aitask-data` branch and is mounted at
`.aitask-data/` by `./ait setup`. Always commit it with `./ait git`, never plain `git`
(see `CLAUDE.md`).

## 3. Check it works

```bash
make check        # tests in both submodules
make try          # the stub effect animates your branding text in this terminal
make run          # the real screensaver with the stub; any input dismisses it
```

The first build takes a minute or two. See [../testing/manual_testing.md](../testing/manual_testing.md)
for what to look for.

## 4. Working in a submodule

Each submodule is a full git repo. `origin` is our fork, and `upstream` is omacom.

```bash
cd ttfx
git switch -c feat/my-effect          # branch from feat/stub-effect (or upstream/master)
# ... edit, make try, make check ...
git add -A && git commit -m "Add the my-effect effect"
git push -u origin feat/my-effect
```

The workspace pins each submodule to an exact commit. When your submodule work should
become what everyone gets, commit the new pointer in the workspace:

```bash
cd ..                                  # back to omarchy_screensavers
git add ttfx && git commit -m "chore: Point ttfx at feat/my-effect"
git push
```

(If you also want `make setup` to check out your branch, change `branch =` for that
submodule in `.gitmodules`.)

## 5. Pulling in other people's work

```bash
git pull                     # the workspace, including new submodule pointers
git submodule update         # check out the pinned submodule commits (detached HEAD)
make setup                   # back onto the tracked branches
git -C ttfx pull             # newest commits on that branch, if past the pin
```

Keeping the forks current with omacom:
`git -C ttfx fetch upstream && git -C ttfx merge upstream/master`. omarchy-screensaver's
branch is `upstream/main`.

## Where to go next

- [dev_workspace.md](dev_workspace.md): the layout, the stub effect's files, and how to submit upstream
- [../testing/manual_testing.md](../testing/manual_testing.md): testing, step by step
