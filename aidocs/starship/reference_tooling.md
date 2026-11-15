# Reference tooling for the `starship` effect

`tools/frames2text/frames2text.py` turns the local reference video into a
coloured-text **animatic** at the screensaver's real grid. Use it to compare the
procedural `starship` effect against the footage, scene by scene. It's stdlib
Python 3.11+ and needs `ffmpeg`. `chafa` is used when it's installed; `img2txt`
is optional.

The animatic is a **local reference only**. Nothing derived from the video's
pixels is ever committed, and the effect itself must be procedural code (see the
parent task t1).

## Commands

```bash
V="$HOME/Downloads/Starship Flight 15 launch, ship catch _26 CNNs first reactions.mp4"
S=tools/frames2text/scenes/starship_flight15.toml

tools/frames2text/frames2text.py all "$V" $S      # extract + convert + play (~60 s)
tools/frames2text/frames2text.py extract "$V" $S  # frames -> .refs/starship/NN_scene/NNNNN.{rgb,png}
tools/frames2text/frames2text.py convert          # -> NNNNN.ans (exactly 137x33 cells each)
tools/frames2text/frames2text.py play [--loop]    # needs a terminal of at least 137x33
python3 -I tools/frames2text/test_frames2text.py  # tests (chafa/img2txt/tmux ones skip if missing)
```

- `--cols/--rows` (default 137x33) is the grid. 137x33 is 1080p at scale 1
  (`FONT_PX = 24` in `omarchy-screensaver/src/raster.rs`). Each frame is scaled to
  cols x rows*2 pixels, so a half-block cell holds two vertical pixels.
- `--target-fps` (default 10) is the animatic's frame rate. A scene with speed `s`
  samples the video at `target_fps/s`, so it plays `(end-start)/s` seconds.
- `--converter auto|chafa|halfblock|img2txt` (default `auto`: chafa if installed,
  else halfblock). `convert` prints which one ran.
- `--out DIR` (default `<repo>/.refs/starship`) is used by every subcommand.
- `play --fps N` overrides the manifest rate. It must be a finite number > 0;
  bad values are rejected (exit 2) before the screen is touched.

`play` draws in the alternate screen. It places every row with a cursor move and
never writes a newline, so the picture can't scroll even in a terminal of exactly
137x33. If the terminal is smaller, it exits 2 with a message, before drawing or
in mid-play. There's no cropping mode: with autowrap off, a terminal overwrites
its last column instead of dropping extra characters. Frames that fall behind
schedule are dropped, so the timing holds. Ctrl-C restores the terminal.

## Storage rule (enforced, no override)

Before anything is written, `--out` and every file are resolved to their real
path (symlinks followed). The write is allowed only if one of these holds:

- the path is inside a git work tree, `git check-ignore` reports it as ignored,
  and `git ls-files` lists nothing tracked under it (`/.refs/` is in
  `.gitignore`); or
- the path is outside every git work tree and under the temp directory
  (`tempfile.gettempdir()`, e.g. a session scratchpad under `/tmp`).

Anything else is refused: a tracked or un-ignored directory, a symlink into one,
a git directory, or a non-temp directory outside a repo. The check runs again
**before every single file write, replace or removal**. Nothing is cached, so a
file force-added to git or a `.gitignore` edit mid-run is caught on the next
write. (One `git check-ignore` per file, since it only reports a path as ignored
when it's untracked too: about 7 s for a full extract.) Files are opened with
`O_NOFOLLOW`, so an existing symlink is never replaced or written through. The
video is only read by ffmpeg, never copied or linked. `git status` stays clean
after a run, and `.refs/` shows up only under `git status --ignored`.

Failures leave a consistent state. `extract` writes into a staging directory
(`.staging-<pid>/`) and replaces the previous output only after every scene has
succeeded. A bad video, an ffmpeg error or a scene past the end of the video
leaves the old frames and manifest untouched. `convert` marks the manifest as
unconverted while it replaces `.ans` files, so `play` refuses a half-converted
set instead of mixing old and new frames.

## Scene list

`tools/frames2text/scenes/starship_flight15.toml` holds timestamps and speeds
only. The cut times come from ffmpeg scene detection
(`select='gt(scene,0.10)'`), checked with 1 s frame grabs where a shot changes
without a hard cut. Hard cuts in 0-244 s: 11.01, 37.47, 67.30, 77.58, 124.36,
144.01, 153.62, 179.11, 183.25, 188.12, 191.69, 219.95, 220.09, 223.72, 231.53,
236.47, 244.04. **The SpaceX footage ends at 244.04 s, not ~236 s**: 236.47-244.04
is the wide shot of the caught ship, and CNN coverage follows.

| # | scene | video (s) | speed | plays (s) | notes |
|---|---|---|---|---|---|
| 1 | liftoff | 0.0-18.0 | 1.8 | 10.0 | pad wide shot, then the aerial camera from 11.01; it tilts up to the coast by ~18 s |
| 2 | ascent | 18.0-37.4 | 3.2 | 6.1 | coastline, then a small rocket with a pink plume in a blue sky |
| 3 | onboard | 37.5-67.25 | 5.0 | 6.0 | S42 hull, hex tiles, engine fire, coast below |
| 4 | high_altitude | 67.35-77.5 | 3.4 | 3.0 | dark sky, glowing pink/white plume |
| 5 | hot_staging | 77.6-85.0 | 1.5 | 4.9 | same onboard shot as 6: flash ~79 s, flames peak ~80 s, booster falls away by ~85 s |
| 6 | coast | 85.0-124.3 | 6.5 | 6.0 | Earth limb, blue atmosphere, sun glare, ice particles |
| 9 | ship_over_earth | 179.15-183.2 | 1.0 | 4.1 | also shown at 188.12-191.69, on the other side of the booster splash |
| 10 | seco | 191.75-219.9 | 4.0 | 7.0 | plume blooms into a blue-white haze, then clears |
| 11 | catch | 220.15-244.0 | 1.8 | 13.3 | towers wide, descent beside the tower (223.72), top-down in the arms (231.53), caught-ship wide (236.47) |

Total: 60.4 s (604 frames at 10 fps). Scenes 7 (split-screen booster) and 8
(booster landing burn and splash) are dropped. The webcast's HUD (timer, speed
and altitude gauges) is part of the footage, so it's in the animatic too. Ignore
it when comparing.

## Converter comparison

Measured on the full 604-frame set at 137x33 on this machine (parallel
conversion). Legibility was judged by rendering frames from liftoff, coast and
catch back to images, side by side with the 137x66 source.

| converter | ms/frame | KB/frame | silhouettes (tower, rocket, ship) | colour |
|---|---|---|---|---|
| **chafa** (default) | 4.2 | 133 | best: quadrant and eighth blocks sharpen the tower lattice, rocket outline and hull edge | truecolor, close to the source |
| halfblock (built-in) | 5.6 | 129 | good: exactly the 137x66 downscale, slightly softer edges | truecolor, pixel-exact to the downscale |
| img2txt (libcaca) | 2.0 | 48 | only high-contrast shapes survive | 16-colour ASCII dithering; sky and smoke break into noise |

Use **chafa** for the animatic. Use **halfblock** to see exactly what a
half-block renderer (like the `starship` effect) can show at this grid, since
that's the effect's own output model. img2txt isn't useful as a reference.
