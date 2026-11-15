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

The `starship` tests (`ttfx/tests/starship.rs`) also check the storyboard's
per-scene colour signatures, the cuts and cross-fades, the loop, and the timing
options. `ttfx/tests/starship_pool_ceiling.rs` runs in its own process and
measures the effect's memory ceiling (see "Performance" below). The whole set
takes a few seconds in release mode. Some dev aids are `#[ignore]`d and run only
on request:

```bash
cd ttfx
cargo test --release --test starship palette_preview -- --ignored --nocapture      # ramps vs. palette, in colour
cargo test --release --test starship calibrate_distances -- --ignored --nocapture  # per-tick distances at boundaries
STARSHIP_DUMP=/tmp/<scratch> STARSHIP_DUMP_T=3,8,19 \
  cargo test --release --test starship dump_frames -- --ignored                    # raw RGB frames (add STARSHIP_DUMP_4K=1)
```

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

A full-screen effect such as `starship` needs the whole terminal as its canvas.
The ttfx CLI defaults to the size of the text, so pass the canvas size and, to
match the screensaver's pace, a frame rate:

```bash
make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"
make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60" \
         EFFECT_ARGS="--start-at 16"          # jump to a storyboard time (scene 3)
```

`starship` options:
- `--start-at <s>`: start at that storyboard time, in seconds. It must be in [0, 64).
  The animation is simulated up to that point, so the frame is the same as an
  uninterrupted run's.
- `--duration-scale <x>`: play slower (>1) or faster (<1), in [0.25, 4]. Only the
  pacing changes, not the content.
- `--stress` (or `TTFX_STARSHIP_STRESS=1`): a CPU stress mode where every cell
  changes on every tick (see "Performance").

Values outside these ranges, `nan` or `inf` are rejected with an error.

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
`non_space` greater than 0 means characters were drawn. It counts characters on
the last frame only, so it is a smoke test, not evidence that any scene looks
right. `FRAMES`, `COLS` and `ROWS` set the run. For `starship`, run the whole 64 s
timeline (at 120 fps) plus the rebuild: `make headless EFFECT=starship FRAMES=7800`.

Also check the random pick and custom input:

```bash
S=omarchy-screensaver/build/rust/release/omarchy-launch-screensaver
$S --headless --include-effects stub,wipe --seed 3 --frames 5     # random pick includes it
echo "Hello" > /tmp/hello.txt && $S --headless --input /tmp/hello.txt --effect stub --frames 60
```

## Performance: `make perf`

```bash
make perf EFFECT=starship RES=1080p             # or RES=4k; PERF_SECONDS=65 by default
TTFX_STARSHIP_STRESS=1 make perf EFFECT=starship RES=4k
make perf EFFECT=starship RES=4k PERF_SEED=entropy PERF_SECONDS=321   # 5 loops, a new seed each
```

`omarchy-screensaver/benches/timeline.rs` plays the effect the way the overlay does.
Each 1/120 s tick runs one step, the VT parse and the raster, and the bench times
each phase. When the effect ends, the overlay's rebuild is measured too. It prints
one summary line, the 10 slowest ticks and a 10 s series. How to read it:

- `total_ms(p99, max)`: the budget at 120 Hz is a p99 under 8.3 ms and a max under
  16 ms. `over_8.3ms` and `longest_over_run` show stutter: a run of slow ticks is a
  visible hitch.
- `changed_frac(min)`: the share of cells that changed per tick. In stress mode it
  must be `1.000`, which shows that the worst case really ran.
- `retained_mb`, `peak_mb`, `appearances` and the `series`: supporting figures only.
  `starship`'s memory bound does not come from a run. Every colour it emits is an
  entry of a fixed palette P, so at most |P|² cell appearances can ever exist.
  `ttfx/tests/starship_pool_ceiling.rs` creates all of them, then replays the
  screensaver's rebuild (the next instance is built before the ended one is
  dropped; the ended one has already released its own buffers), and checks the
  peak heap (≤ 64 MB).

`render_delta` redraws only the cells that changed (it still reports their
bounding box as the damage), so a scene that changes a few scattered cells costs
little to raster. The forced stress mode, where every cell changes on every tick,
still exceeds the p99 budget at 4K. That is the raster's floor, not the effect's
cost (see the archived t1_3 plan, "Perf notes"). The bench measures wall time, so
other load on the machine inflates it. On a hybrid CPU, pin it to a performance
core (`taskset -c 0 make perf ...`) and compare runs taken under the same
conditions.

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
