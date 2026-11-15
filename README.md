# omarchy_screensavers

A workspace for developing new [Omarchy](https://omarchy.org) screensaver effects. It bundles
[ttfx](https://github.com/omacom/ttfx), where the effects live, and
[omarchy-screensaver](https://github.com/omacom/omarchy-screensaver), the Wayland overlay,
as submodules, and wires them together for local builds.

```bash
git clone --recurse-submodules https://github.com/beyondeye/omarchy_screensavers.git
cd omarchy_screensavers && make setup && ./ait setup
make try
```

That's for collaborators with push access. To work through your own forks instead, see
[Contributing with forks](aidocs/workspace/contributing_with_forks.md).

## Development workflow

Development here is managed with the [aitasks](https://github.com/beyondeye/aitasks) framework:
work is tracked as markdown task files in git (`aitasks/`, with implementation plans in `aiplans/`),
and AI coding agents pick up, plan and implement tasks through its skills. The `./ait` command is
its entry point (`./ait setup` installs it, `./ait board` opens the task board). `./ait ide`
starts the tmux session and launches `ait monitor`, the one-command way to run and watch agents.

All documentation is in [`aidocs/`](aidocs/):
- [Onboarding](aidocs/workspace/onboarding.md): set up and start working (collaborators)
- [Contributing with forks](aidocs/workspace/contributing_with_forks.md): the same, through your own forks
- [The dev workspace](aidocs/workspace/dev_workspace.md): layout, the stub effect, submitting upstream
- [Testing](aidocs/testing/manual_testing.md): manual testing, step by step
- [Starship reference tooling](aidocs/starship/reference_tooling.md): the frames2text animatic tool and scene cuts
