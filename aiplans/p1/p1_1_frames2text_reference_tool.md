---
Task: t1_1_frames2text_reference_tool.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
plan_verified:
  - claudecode/opus5_5 @ 2026-11-15 12:08
---

# p1_1 — frames→text reference tool + scene-cut refinement

## Context

Child 1 of t1 (the `starship` screensaver effect). It builds the reference tooling that later
children (t1_2 storyboard, t1_3–t1_5 effect) compare against: a stdlib-Python tool that turns the
local reference video into a coloured-text "animatic" at the screensaver's real grid (137×33), and
it refines the scene cut times. Nothing derived from the video's pixels may ever be committed.
Full spec: `aitasks/t1/t1_1_frames2text_reference_tool.md`; settled decisions: parent plan
`aiplans/p1_starship_flight_screensaver.md`. Workspace repo only, no submodule changes.

## Verification notes (2026-11-15, verify pass)

Checked against the tree; the plan holds, with these corrections folded into the steps below:
- `tools/` and `aidocs/starship/` do not exist yet (new). `.gitignore` has no `/.refs/` entry yet.
- `FONT_PX = 24.0` confirmed at `omarchy-screensaver/src/raster.rs:8`.
- chafa 1.18.3 at `/usr/bin/chafa`: `-f/--format`, `-c/--colors`, `-s/--size`, `--stretch`,
  `--symbols`, `--animate` all exist. `img2txt` has `-W`, `-H`, `-f utf8`. ffmpeg/ffprobe present.
- **Correction:** `/usr/bin/python3` (3.14.10) *does* have PIL 13.0.0 (no numpy), and `python3` on
  PATH resolves to the aitask venv (`~/.aitask/bin/python3`). Stay **stdlib-only** anyway (portable
  across both); shebang `#!/usr/bin/env python3`; `tomllib` is available.
- **Correction:** use `-ss S -t (E-S)` before `-i` (fast input seek, explicit duration) instead of
  `-to E`, whose meaning shifts between input/output position.
- `tempfile.gettempdir()` is `/tmp`; the session scratchpad (`/tmp/claude-1000/…`) is under it, so
  the "outside any repo, under temp root" rule accepts it.
- The screen-recording tool defaults `--out` to `$TMPDIR/video-prep/…` (outside the repo); pass
  `--out <scratchpad>/video-prep/…` explicitly anyway.
- The reference video exists at the stated path (20 MB).
- **Correction (review, confirmed by test):** chafa 1.18.3 **cannot read PPM**: a valid synthetic P6
  gives exit 2, "Unknown file format"; its loaders are AVIF GIF HEIF JPEG JXL PNG QOI SVG TIFF WebP
  XWD. chafa reads an equivalent stdlib-encoded PNG (exit 0), and so does img2txt. → The
  intermediate format is **PNG**, encoded with stdlib `zlib` + `struct` (filter type 0, RGB8). PPM is dropped.
- **Correction (review, confirmed by test):** chafa's output is `\e[?25l` + 33 rows of 137 cells,
  each ending `\e[0m\n`, then `\e[?25h`. The last newline scrolls a 137×33 terminal. img2txt also ends
  with a newline. → `convert` normalises every converter's output to exactly ROWS rows with no
  newline at the end and no cursor-visibility escapes. `play` never writes a newline.

## Steps

1. `.gitignore`: append a `# Reference frames derived from local videos (never commit)` comment and
   `/.refs/`.
2. `tools/frames2text/frames2text.py` (stdlib only, `#!/usr/bin/env python3`, `chmod +x`):
   - `argparse` subcommands `extract`, `convert`, `play`, `all`; shared `--cols 137 --rows 33
     --out .refs/starship` (default resolved against the repo root found via
     `git rev-parse --show-toplevel` from the script's directory).
   - `extract <video> <scenes.toml> [--target-fps 10]`: load scenes with `tomllib`
     (`[[scene]]` tables: `name`, `start`, `end`, `speed`; validate `end > start`, `speed > 0`).
     Per scene run
     `ffmpeg -v error -ss S -t (E-S) -i VIDEO -vf fps=F/speed,scale=COLS:ROWS*2:flags=area -f rawvideo -pix_fmt rgb24 -`,
     split stdout into frames of `COLS*ROWS*2*3` bytes, write `<scene>/NNNNN.rgb` (raw, for
     halfblock) and `<scene>/NNNNN.png` (for chafa/img2txt). The PNG comes from a small stdlib
     encoder `encode_png(w, h, rgb)`: signature, IHDR (8-bit, colour type 2), one zlib-compressed
     IDAT with filter byte 0 per scanline, IEND, CRCs via `zlib.crc32`. Playback duration per frame = `1/target_fps`
     (so the scene plays `(E-S)/speed` seconds). Write `manifest.json` (cols, rows, scenes →
     frame stems, seconds per frame, total seconds). Print the total compressed duration.
   - `convert [--converter auto|chafa|halfblock|img2txt]`: `auto` = chafa if `shutil.which("chafa")`
     else halfblock; print the chosen one. chafa:
     `chafa -f symbols -c full -s COLSxROWS --stretch --symbols block+half --animate off <png>`;
     img2txt: `img2txt -W COLS -H ROWS -f utf8 <png>`; halfblock: per cell `▀`, fg = top pixel,
     bg = bottom pixel, SGR `38;2`/`48;2` emitted only on change, `\e[0m` at each line end.
     **Normalise** every converter's output with `normalize_frame(text, rows)`: remove `\e[?25l` and
     `\e[?25h`, drop `\r`, split on `\n`, drop trailing empty rows, append `\e[0m` to each row, then
     require exactly `rows` rows, each `cols` cells wide once SGR is stripped (`visible_width`). A
     mismatch is an error naming the converter and frame. Store the rows joined by `\n`, with no
     newline at the end. Writes `NNNNN.ans` next to the frame and records the converter in the manifest.
     The first frame of each converter is checked for the correct size, so a converter whose output
     format drifts fails at once instead of producing a broken animatic.
   - `play [--fps N] [--loop]` (no cropped mode. Review found that with autowrap off, extra characters
     **overwrite the last column** instead of being dropped: a tmux pane 5 wide given `ABCDEFGHIJ` shows
     `ABCDJ`. Cropped playback wasn't requested, so it is left out):
     - **Size check.** Read `shutil.get_terminal_size()` before entering the alternate screen and
       again before every frame. If the terminal is smaller than the manifest's cols×rows, restore the
       terminal and exit 2 with
       `terminal is WxH, the animatic needs COLSxROWS: enlarge it or re-run extract/convert with --cols/--rows`.
       A larger terminal is fine: the frame sits top-left and the rest stays blank.
     - **Framing without scrolling.** Enter the alternate screen (`\e[?1049h`), hide the cursor
       (`\e[?25l`) and clear (`\e[2J`). Autowrap stays at the terminal's default: rows are exactly COLS
       cells wide and the size check guarantees they fit. Draw each row r with
       `\e[{r};1H` + row. **No `\n` or `\r` is ever written**, so the screen cannot scroll, even at
       exactly COLS×ROWS. Each frame is one buffered `sys.stdout.write` + `flush`.
     - Timing: sleep to the manifest schedule (drift-corrected with `time.monotonic`); `--fps`
       overrides it. The `try/finally` (also on Ctrl-C) restores `\e[0m`, `\e[?25h` and `\e[?1049l`.
     - `--once-frames N` (hidden test aid): play only the first N frames, then hold the last one
       until a 2 s timeout, so a tmux capture can grab it.
   - `all <video> <scenes.toml>` = extract → convert → play.
   - The video path is only read (ffmpeg input); never copied or linked.
3. Storage guard `check_dest(path, temp_root=None)`, called for `--out` and before **every** file
   write (via one `write_bytes/write_text` helper):
   - `realpath` (follows symlinks); find the nearest existing parent; `git -C parent rev-parse
     --show-toplevel`.
   - Inside a work tree: require `git check-ignore -q <path>` to succeed and
     `git ls-files -- <path>` to be empty.
   - Outside any work tree: require the path under `realpath(temp_root or tempfile.gettempdir())`.
   - Refuse to replace an existing symlink (`os.path.islink` on the unresolved path).
   - Anything else → `SystemExit` with a clear message before anything is written. No override flag.
4. `tools/frames2text/test_frames2text.py` (stdlib `unittest`, temp git repos): refuses a tracked dir,
   accepts an ignored dir, refuses a symlink from an ignored dir into a tracked dir, accepts a temp
   dir outside any repo, refuses an outside-repo non-temp dir (injectable `temp_root` pointing at a
   second temp dir), refuses overwriting an existing symlink. Plus:
   - halfblock conversion on a synthetic 2×2 frame; scenes-TOML validation;
   - `encode_png` round-trip sanity (signature, IHDR fields, IDAT decompresses to the filtered scanlines);
   - **real chafa run** (skipped if chafa is missing): synthetic 137×66 RGB → `encode_png` → the
     exact chafa command → `normalize_frame` gives 33 rows, each 137 cells wide, no newline at the end;
   - the same for img2txt (skipped if missing);
   - `play` writer: the byte stream for one frame contains no `\n`/`\r` and addresses rows 1..ROWS
     only through CUP;
   - **exact-size playback** (skipped if tmux is missing): in a detached `tmux new-session -x 137 -y 33`,
     run `play --once-frames 1` on a 1-frame manifest whose rows carry distinct markers;
     `tmux capture-pane -p` must show marker row 1 on screen line 1 and row 33 on line 33 (no scroll),
     and the **rightmost cell** (column 137) of each row must hold that row's own end marker.
     A second session at `-x 100 -y 20` must exit 2 with the size message and draw nothing.
5. Scene refinement: run `./.aitask-scripts/aitask_screen_recording.sh bug --range A-B --interval 1
   --out <scratchpad>/video-prep/…` over 0–125 s and 175–236 s, view the contact sheets, and
   `anim --window` for the climb, plume growth, ship descent and catch. Fill in
   `tools/frames2text/scenes/starship_flight15.toml` (9 scenes: 1–6, 9, 10, 11; timestamps and
   speeds only) with speeds totalling ~60 s, more time to liftoff and the catch, less to the coast.
   Record the measured motion numbers in a `## Notes for t1_2` section of this plan.
6. `aidocs/starship/reference_tooling.md` (usage, storage rule, short chafa vs halfblock vs img2txt
   comparison on 2–3 representative frames: silhouette legibility, colour fidelity, speed) plus a
   row in the CLAUDE.md "Read these instead of scanning the repo" table.

### Post-phase (risk mitigations)
1. [frame_data_guard] Before the commit, run
   `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review it by hand (no hex dumps,
   ANSI frames or pixel arrays staged). Check with `git status --ignored` that `.refs/` is ignored and
   untracked.

## Verification

- `tools/frames2text/frames2text.py --help` and each subcommand's `--help` work.
- `python3 -I -m unittest tools/frames2text/test_frames2text.py` passes.
- **Real extract → chafa conversion**: `frames2text.py extract "<video>" tools/frames2text/scenes/starship_flight15.toml`
  then `convert` (auto → chafa, which must be printed). Every `.ans` frame passes `normalize_frame`
  (33 rows × 137 cells), and the manifest total is ~60 s.
- **Real playback at the exact target size**: in `tmux new-session -d -x 137 -y 33`, run `play` on the
  real animatic for a few seconds. `tmux capture-pane -p -e` shows the frame aligned to the top-left,
  with no blank or shifted first line (no scroll) and an intact right edge. In a 100×20 session the
  size error appears and exit status is 2. The full ~60 s animatic plays in a normal terminal of at least 137×33.
- `--out aidocs/` is refused, and so is a symlink into a tracked dir.
- `git status` is clean apart from the intended files; `.refs/` is ignored.
- Commit in this repo: `feature: Add the frames2text reference tool (t1_1)`.

Step 9 (Post-Implementation): archive this child via the task workflow.

## Risk

### Code-health risk: low
- Purely additive: a new `tools/frames2text/` dir, one `.gitignore` line, a new doc and one
  CLAUDE.md table row. No existing code or submodule is touched. · severity: low · → mitigation: none needed

### Goal-achievement risk: medium
- Frame-derived data leaks into the repo, either through a guard gap (symlink, tracked path under an
  ignored pattern) or through a careless commit. · severity: medium · → mitigation: inline post-phase frame_data_guard, plus the mandatory `check_dest` rule and its tests (step 4)
- A converter's input format or output framing doesn't match what the tool assumes (as found in review:
  chafa has no PPM loader, chafa/img2txt end with a newline that scrolls the screen, and with autowrap
  off extra characters overwrite the last column). · severity: low (residual) ·
  → mitigation: none needed (PNG intermediate, `normalize_frame` size check, no cropped mode,
  real-chafa and tmux exact-size tests including the rightmost cell)
- chafa's stretched symbol output may not look like the screensaver's crisp half-block rendering,
  so the animatic misleads the later comparison. · severity: low · → mitigation: none needed (halfblock converter and the doc's comparison cover it)
- Cut times refined from 1 s sampling may still be off by ~1 s. · severity: low · → mitigation: none needed (the storyboard tunes timing again)

### Planned mitigations
- timing: post-phase | name: frame_data_guard | type: test | priority: high | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into commits | desc: grep the staged diff for large string/array literals and confirm .refs/ is ignored and untracked before committing
