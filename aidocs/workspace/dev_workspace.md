# omarchy_screensavers

A workspace for writing new Omarchy screensaver effects.

```
omarchy_screensavers/
├── .cargo/config.toml     # [patch]: builds here use ./ttfx instead of the GitHub tag
├── Makefile               # try / run / headless / check / status
├── aidocs/                # these docs
├── ttfx/                  # clone of omacom/ttfx: the effects (branch feat/stub-effect)
└── omarchy-screensaver/   # clone of omacom/omarchy-screensaver: the Wayland overlay
```

Both clones are their own git repositories and are ignored by this one.
`make setup` recreates them.

## The loop

```bash
make try                    # fastest: play the effect in this terminal
make try EFFECT=wipe        # compare with an existing effect
make headless               # render through the real screensaver, no display
make run                    # the real overlay on every monitor; any input dismisses it
make check                  # tests in both repos
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

## Submitting

- **The effect:** ttfx is a byte-exact port of
  [TerminalTextEffects](https://github.com/ChrisBuilds/terminaltexteffects) and asks
  for effect ideas to go upstream first. Open an issue there, land the Python
  effect, then PR the Rust port to `omacom/ttfx`. A new ttfx tag then has to be
  pulled into `omarchy-screensaver/Cargo.toml`.
- **Screensaver behaviour:** PR to `omacom/omarchy-screensaver`.
- Fork first and add your fork as a remote (`gh repo fork --remote` inside a clone).
- Don't commit `omarchy-screensaver/Cargo.lock` changes: they come from the local
  `[patch]`. Run `git -C omarchy-screensaver checkout Cargo.lock` before committing there.
