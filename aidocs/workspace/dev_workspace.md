# The dev workspace

A workspace for writing new Omarchy screensaver effects. New here? Start with
[onboarding.md](onboarding.md).

```
omarchy_screensavers/
├── .cargo/config.toml     # [patch]: builds here use ./ttfx instead of the GitHub tag
├── Makefile               # setup / try / run / headless / check / status
├── aidocs/                # these docs
├── ttfx/                  # submodule: beyondeye/ttfx, branch feat/stub-effect (the effects)
└── omarchy-screensaver/   # submodule: beyondeye/omarchy-screensaver, branch main (the Wayland overlay)
```

Both submodules are forks of `omacom/...`. Each has `origin` (the fork, where you
push) and `upstream` (omacom, where PRs go). `make setup` adds the `upstream` remotes.
Working through your own forks instead? `make use-forks` re-points `origin` at them; see
[contributing_with_forks.md](contributing_with_forks.md).

## The loop

```bash
make try                    # fastest: play the effect in this terminal
make try EFFECT=wipe        # compare with an existing effect
make headless               # render through the real screensaver, no display
make run                    # the real overlay on every monitor; any input dismisses it
make check                  # tests in both repos
make status                 # branch and changes in both submodules
```

For step-by-step testing, with checklists, see [../testing/manual_testing.md](../testing/manual_testing.md).

Effect options go to ttfx directly, e.g.
`ttfx/target/release/ttfx stub --reveal-direction center_to_outside < ~/.config/omarchy/branding/screensaver.txt`.

## Where the stub effect lives

| File | What |
|---|---|
| `ttfx/src/effects/stub.rs` | CLI options (`StubConfig`) and the animation (`build` / `next_frame`) |
| `ttfx/src/effects/mod.rs` | `pub mod stub;`, the `EffectCommand::Stub` variant (its doc comment is the `--help` line), `build_effect()` and `name()` arms |
| `ttfx/src/fx/effects/mod.rs` | `EffectCommand::Stub(_) => None`: not ported to the faster fx engine, so it runs on the original one |

To rename it: rename the file, then replace `stub`/`Stub`/`StubConfig` in those three
files. Keep the lists alphabetical.

## Known quirk: omarchy-screensaver's Cargo.lock

The `[patch]` in `.cargo/config.toml` swaps the GitHub ttfx for `./ttfx`, so the first build
rewrites `omarchy-screensaver/Cargo.lock`. That change is local only and should never be
committed. `.gitmodules` sets `ignore = dirty` for that submodule, so the workspace's
`git status` doesn't flag it. Before committing *inside* `omarchy-screensaver`, run
`git -C omarchy-screensaver checkout Cargo.lock`.

## Submitting upstream

- **The effect:** ttfx is a byte-exact port of
  [TerminalTextEffects](https://github.com/ChrisBuilds/terminaltexteffects) and asks
  for effect ideas to go upstream first. Open an issue there, land the Python
  effect, then PR the Rust port from `beyondeye/ttfx` to `omacom/ttfx`. A new ttfx tag
  then has to be pulled into `omarchy-screensaver/Cargo.toml`.
- **Screensaver behaviour:** branch in `omarchy-screensaver/`, push to the fork, and PR to
  `omacom/omarchy-screensaver`.
- Open PRs with `gh pr create --repo omacom/<repo>` from inside the submodule.
