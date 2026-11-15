# Testing an effect yourself

Run everything from the workspace root (`omarchy_screensavers/`). The examples use
`stub`; pass `EFFECT=<name>` to the make targets for your own effect. There are four
levels, fastest first. Most iteration happens at level 1.

## 0. Build and run the automated tests

```bash
make check
```

This runs `cargo test` in `ttfx/` and `make check` in `omarchy-screensaver/`.
Every test should report `ok`. These tests catch broken code, not ugly
animations, so the levels below are still needed.

## 1. In a terminal (seconds per iteration)

```bash
make try                          # your branding text, animated by the stub
make try EFFECT=wipe              # an existing effect, for comparison
```

`make try` rebuilds ttfx when a source file has changed and plays the effect once in the
current terminal. Try the options and other inputs directly:

```bash
T=ttfx/target/release/ttfx
echo "Hello Omarchy" | $T stub                                   # short text
$T stub --reveal-direction center_to_outside  < omarchy-screensaver/assets/screensaver.txt
$T stub --reveal-delay 0 --final-gradient-frames 8 < omarchy-screensaver/assets/screensaver.txt
$T stub --final-gradient-stops ff0000 00ff00 0000ff --final-gradient-direction radial \
        < omarchy-screensaver/assets/screensaver.txt
$T stub --help                                                    # every option
```

Accepted values:
- `--reveal-direction`: `row_top_to_bottom`, `row_bottom_to_top`, `column_left_to_right`,
  `column_right_to_left`, the four `diagonal_*` corners (for example
  `diagonal_top_left_to_bottom_right`), `center_to_outside`, `outside_to_center`
- `--final-gradient-direction`: `horizontal`, `vertical`, `diagonal`, `radial`

What to look for:
- [ ] The animation starts at once and ends on its own, and the prompt comes back with the cursor visible.
- [ ] The final frame shows the complete text in the gradient colors, with nothing missing or misplaced.
- [ ] Resizing the terminal mid-run restarts the animation cleanly.
- [ ] Ctrl+C stops it cleanly, and the cursor comes back.
- [ ] A bad option value (for example `--reveal-direction sideways`) prints a clear error.

## 2. Through the screensaver, without a display

```bash
make headless
```

This should print one line like
`frames=120 cells=120x40 non_space=401 empty_rows=30 effect=stub backend=rust`.
`non_space` greater than 0 means characters were drawn. Also check the random pick and
custom input:

```bash
S=omarchy-screensaver/build/rust/release/omarchy-launch-screensaver
$S --headless --include-effects stub,wipe --seed 3 --frames 5     # random pick includes it
echo "Hello" > /tmp/hello.txt && $S --headless --input /tmp/hello.txt --effect stub --frames 60
```

## 3. The real overlay

```bash
make run
```

This covers every monitor with your local build. A key press, click, scroll or
mouse movement dismisses it, so take your hands off the keyboard and mouse after
pressing Enter. The screensaver repeats its effect until dismissed.

- [ ] It covers every monitor, and the cursor is hidden.
- [ ] Characters look crisp, in the right font, with no gaps between block characters.
- [ ] It loops smoothly with no stutter.
- [ ] Any input dismisses it at once, and the cursor comes back.
- [ ] It works with other text too. Pass extra flags through the screensaver's own Makefile:
      `make -C omarchy-screensaver run RUNFLAGS="--effect stub --input /tmp/hello.txt"`.

If it ever refuses to close, switch to another TTY (for example Ctrl+Alt+F2) or SSH in,
and run `pkill -f omarchy-launch-screensaver`.

## 4. Optional: through Omarchy's own idle trigger

Omarchy's idle service runs `omarchy-launch-screensaver`, which always `exec`s the
**packaged** binary at `/usr/lib/omarchy-screensaver/omarchy-screensaver`. Neither
`make run` nor `make install PREFIX=~/.local` changes what idle starts:
`/usr/share/omarchy/bin` comes before `~/.local/bin` in `PATH`. To see your
build start on idle, swap the packaged binary temporarily:

```bash
sudo cp /usr/lib/omarchy-screensaver/omarchy-screensaver{,.orig}
sudo install -m755 omarchy-screensaver/build/rust/release/omarchy-launch-screensaver \
     /usr/lib/omarchy-screensaver/omarchy-screensaver
omarchy-launch-screensaver force --effect stub    # or wait idle.screensaver seconds (see ~/.config/omarchy/shell.json)
# restore the packaged version:
sudo mv /usr/lib/omarchy-screensaver/omarchy-screensaver{.orig,}   # or: sudo pacman -S omarchy-screensaver
```

Undo the swap when you're done. A system update to the `omarchy-screensaver` package
also overwrites it.

## Before a PR: what to record

Both upstream repos ask for evidence, not "tests pass":
- the output of `make check`
- which of the checklist items above you ran, and what you saw
- a short screen recording of `make run` (motion is the change). For example, use
  `omarchy-capture-screenrecording`, or the screen recording option in the Omarchy menu.
  Start the recording first, then `make run` from a terminal.
