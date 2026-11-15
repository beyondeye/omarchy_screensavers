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

All documentation is in [`aidocs/`](aidocs/):
- [Onboarding](aidocs/workspace/onboarding.md): set up and start working (collaborators)
- [Contributing with forks](aidocs/workspace/contributing_with_forks.md): the same, through your own forks
- [The dev workspace](aidocs/workspace/dev_workspace.md): layout, the stub effect, submitting upstream
- [Testing](aidocs/testing/manual_testing.md): manual testing, step by step
