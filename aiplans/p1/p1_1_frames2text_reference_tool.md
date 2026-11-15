---
Task: t1_1_frames2text_reference_tool.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
---

# p1_1 — frames→text reference tool + scene-cut refinement

Context: see the task file `aitasks/t1/t1_1_frames2text_reference_tool.md` (full spec) and the
parent plan `aiplans/p1_starship_flight_screensaver.md`. Workspace repo only, no submodule changes.

## Steps

1. `.gitignore`: append `/.refs/`.
2. `tools/frames2text/frames2text.py` (stdlib only, `#!/usr/bin/env python3`, `chmod +x`):
   - `argparse` subcommands `extract`, `convert`, `play`, `all`, plus shared
     `--cols 137 --rows 33 --out .refs/starship`.
   - `extract`: for each scene in the TOML (`tomllib`), run
     `ffmpeg -v error -ss S -to E -i VIDEO -vf fps=F/speed,scale=COLS:ROWS*2:flags=area -f rawvideo -pix_fmt rgb24 -`.
     Split the stdout into frames of `COLS*ROWS*2*3` bytes and write `NNNNN.rgb` and `NNNNN.ppm`
     (a P6 header plus the same bytes). Write `manifest.json` (scenes → frames, seconds per frame).
   - `convert`: `auto|chafa|halfblock|img2txt`. `auto` uses chafa when `shutil.which` finds it.
     Print the chosen converter. Use the chafa flags from the task. halfblock emits
     `\e[38;2;r;g;bm\e[48;2;r;g;bm▀`, only when the colours change, with `\e[0m` at the end of
     each line. Write `NNNNN.ans` next to the frame.
   - `play`: alternate screen and hidden cursor; per frame, `\e[H` + the frame, then sleep to the
     manifest timing (drift-corrected with `time.monotonic`). `--loop`. A `try/finally` restores
     the terminal.
   - `all`: extract → convert → play.
3. Storage guard `check_dest(path, temp_root=None)`, called for `--out` and before every file
   write:
   - take the `realpath`, find the nearest existing parent, and run
     `git -C parent rev-parse --show-toplevel`;
   - inside a work tree: require `git check-ignore -q`, and that `git ls-files -- path` is empty;
   - outside a work tree: require the path to be under `realpath(temp_root or tempfile.gettempdir())`;
   - refuse to replace an existing symlink;
   - anything else exits non-zero before writing.
4. `tools/frames2text/test_frames2text.py`: covers the 5 destination cases from the task, with
   temp repos.
5. Scene refinement: run
   `./.aitask-scripts/aitask_screen_recording.sh bug --range A-B --interval 1` over 0–125 s and
   175–236 s, and `anim --window` for the climb, plume growth, ship descent and catch. Fill in
   `tools/frames2text/scenes/starship_flight15.toml` (9 scenes: 1–6, 9, 10, 11) with speeds that
   total ~60 s. Record the measured motion numbers in a `## Notes for t1_2` section of this plan.
6. `aidocs/starship/reference_tooling.md` plus a row in the CLAUDE.md table.

### Post-phase (risk mitigations)
1. [frame_data_guard] Before the commit, run
   `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review it by hand. Check with
   `git status --ignored` that `.refs/` is ignored and untracked.

## Verification

- `tools/frames2text/frames2text.py --help` and each subcommand's `--help` work.
- `python3 -I -m unittest tools/frames2text/test_frames2text.py` passes.
- `frames2text.py all "<video>" tools/frames2text/scenes/starship_flight15.toml` plays an animatic
  of about 60 s, with chafa chosen automatically.
- `--out aidocs/` is refused, and so is a symlink into a tracked dir.
- `git status` is clean apart from the intended files; `.refs/` is ignored.

Step 9 (Post-Implementation): archive this child via the task workflow.
