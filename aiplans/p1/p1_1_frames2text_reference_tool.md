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

## Implementation status (2026-11-15)

Steps 1–6 done; post-phase frame_data_guard runs at commit time (Step 8).

Deviations from the plan:
- **Test command**: `python3 -I -m unittest tools/frames2text/test_frames2text.py` cannot import a
  path-style module under `-I` (cwd not on `sys.path`). The test file adds its own dir to `sys.path`
  and calls `unittest.main()`, so the command is `python3 -I tools/frames2text/test_frames2text.py`
  (`python3 -I -m unittest discover -s tools/frames2text` also works).
- **Storage guard, directories**: `git check-ignore` does not match a dir-only pattern (`/.refs/`)
  against a directory that does not exist yet unless the path ends in `/`. `check_dest` therefore
  checks directories with a trailing slash. Writes go through `SafeWriter`: it verifies each file's
  real parent directory once (ignored + nothing tracked under it, cached) and opens files with
  `O_NOFOLLOW`. A path inside a `.git` directory is refused too.
- **chafa optimisation**: kept chafa's default `-O 5`. On flat and striped test images it emitted no
  REP/cursor CSI. `normalize_frame` rejects every CSI except SGR (after removing `?25h/l`), so a
  future chafa that emits REP fails loudly instead of miscounting cells.
- **Extra tests**: an ignored dir holding a force-added tracked file is refused; `.git/` is refused;
  the CLI refuses a tracked `--out`; the committed scene list loads and totals 55–65 s.
- **Docs**: besides the CLAUDE.md row, the same row went into AGENTS.md (mirrored table) and a pointer
  line into README.md.
- **Scene refinement**: the SpaceX footage ends at **244.04 s**, not ~236 s (236.47–244.04 is the
  wide shot of the caught ship). Scene 11 runs to 244.0.

Verification results:
- 22 tests pass (chafa, img2txt and tmux tests ran, not skipped).
- Real `extract` → `convert` (auto → chafa): 604 frames, 60.4 s, every frame normalised to 33×137.
- Real `play` in a detached tmux pane of exactly 137×33: all 33 captured rows are 137 cells and row 1
  starts with colour (no scroll); playback ran 60.46 s wall time with exit 0. In a 100×20 pane:
  exit 2, the size message, nothing drawn.
- Converters (604 frames, parallel): chafa 4.2 ms/frame, 133 KB; halfblock 5.6 ms, 129 KB;
  img2txt 2.0 ms, 48 KB (16-colour ASCII, poor fidelity).

## Notes for t1_2

Cut times (ffmpeg `select='gt(scene,0.10)'`, 0–244 s): 11.01, 37.47, 67.30, 77.58, 124.36, 144.01,
153.62, 179.11, 183.25, 188.12, 191.69, 219.95, 220.09, 223.72, 231.53, 236.47, 244.04 (CNN starts).
Kept-scene ranges and speeds are in `tools/frames2text/scenes/starship_flight15.toml` (total 60.4 s:
10.0 / 6.1 / 6.0 / 3.0 / 4.9 / 6.0 / 4.1 / 7.0 / 13.3 s).

Shot contents (from 1 s frame grabs):
- 1 liftoff: 0–11.01 pad wide shot (tower left of the rocket, white/orange billows spread both sides
  of the pad, T+1–T+6). 11.01–18 a high aerial angle, top-down-ish over the coast: one big smoke
  column leans up-left from the pad while the rocket climbs straight up with a short orange flame. The
  camera tilts up to the coastline by ~18 s.
- 2 ascent: rocket mid-frame with a long pink plume against blue sky and horizon (T+17), then a small
  rocket moving up-right across a blue gradient, shrinking (T+25–31).
- 3 onboard: a fixed camera along the S42 hull. The hull fills the left ~half diagonally (dark tiles,
  hex pattern, "S42" marking), the engine end points lower-right, the coast/sea is visible far below.
- 4 high altitude: near-black navy sky, a bright white engine point with a pink/magenta plume trailing
  downward, centred.
- 5 hot staging: same onboard framing. ~79 s first flash; ~80 s orange flames engulf the right half;
  ~81–84 s the booster separates and falls away down the frame, engines glowing.
- 6 coast: same framing, sky deep blue; Earth limb arc lower-right; sun glare lower-right; drifting
  white ice flakes over the upper right.
- 9 ship over Earth: camera from the other side. The hull fills the left; Earth fills the right
  half as a big disc; a bright sun with flare at upper right; black space.
- 10 seco: starts black space with the hull; the plume blooms into a blue-white haze that fills the
  right of the frame (~200–212 s), then fades.
- 11 catch: 220.1 wide, two towers on a flat brown coast under an overcast grey sky, the ship as a
  small dark streak falling (upper middle). 223.7 the camera follows the ship down beside the tower
  (engines firing, a short orange/pink flame). 231.5 top-down close-up of the steel ship held between
  the arms. 236.5 wide: the ship hangs on the tower.

Motion measurements (`aitask_screen_recording.sh anim --window`, full-frame signal; camera shake and
compression make these indicative only):
- liftoff smoke growth (0–11 s): decelerating, best fit `cubic-bezier(0.325, 0.912, 0, 0.7)` over
  ~6.1 s (M3 standard `cubic-bezier(0.2,0,0,1)` 6.2 s, nearly as good). The billows expand fast,
  then slow.
- ascent (22–37 s): no usable curve. The fit degenerates (`cubic-bezier(0.006, 1.409, …)`): the
  rocket is a small object on a near-uniform sky. By eye it moves up-right ~0.04 frame-heights/s and
  shrinks steadily: treat it as linear.
- SECO bloom (192–219.9 s): decelerating over ~21.6 s, `cubic-bezier(0.05, 0.831, 0.113, 0.925)`
  (M3 emphasized decelerate `cubic-bezier(0.05,0.7,0.1,1)` is within 0.003 rmse).
- catch descent (223.8–231.5 s): the camera tracks the ship, so it stays upper-middle while the tower
  rises into view. It decelerates to rest by ~229.5 s and settles: spring fit dampingRatio ≈ 0.8,
  stiffness ≈ 24 (settles ~1.3 s), or `cubic-bezier(0.3, 0.866, 0, 1.078)` over ~2.3 s (slight
  overshoot).

## Post-Review Changes

### Change Request 1 (2026-11-15 13:40)
- **Requested by user:** four review findings, all verified as valid:
  1. (high) `SafeWriter` cached each parent dir's eligibility, so a file force-added to git after the
     first write was overwritten by a reused writer.
  2. (low) `play --fps` accepted negative values (frames dropped, exit 0) and `0` (fell back to the
     manifest rate).
  3. (medium) `extract` deleted the previous frames before ffmpeg had succeeded, leaving a manifest
     that pointed at missing frames.
  4. (low) `convert` kept every completed future, and with it every frame's text (~147 MiB for 604
     frames), until the pool finished.
- **Changes made:**
  1. Removed the cache: every write, replace and removal re-runs `check_dest` on that file. Files use
     a one-call fast path (`git check-ignore -q` exits 0 only for an ignored, untracked path in a work
     tree; 1 → refused; 128 → the full check: temp root / `.git` refusal). Real extract: 7.2 s (was
     1.5 s cached; 16.6 s with the full three-call check per file).
  2. argparse types: `--fps`/`--target-fps` must be finite > 0, `--cols/--rows/--jobs/--once-frames`
     ≥ 1, `--hold` finite ≥ 0; rejected with exit 2 before anything is drawn. `play()` validates too
     (and treats `fps=0` as an error, not as "unset").
  3. `extract` writes into `<out>/.staging-<pid>/`; on any failure (ffmpeg error, a scene with no
     frames, Ctrl-C) the staging dir is removed and the previous output is untouched. On success
     `_swap_in` removes the old manifest first, clears old frame files, moves the staged files in
     (both ends checked), and writes the new manifest last. `convert` writes the manifest with
     `converter: null` before replacing `.ans` files and sets it only on success, so `play` refuses a
     half-converted set. A missing/short `.rgb` or missing `.png` is now a clean error, not a traceback.
  4. `as_completed` loop pops each future from the dict once its result is written; pending futures
     are cancelled on error.
  - Tests: 22 → 31 (reused-writer force-add and `.gitignore`-edit regressions, end-to-end
    extract/convert on a synthetic ffmpeg `testsrc` video, failed re-extract keeps old output
    (bad video, and a scene past the end), re-extract replaces old scenes, failed convert leaves the
    manifest unconverted and `play` refuses it, CLI/`play()` fps and grid-arg validation).
  - Doc: storage-rule paragraph (per-write check, failure consistency), `--fps` note.
- **Files affected:** `tools/frames2text/frames2text.py`, `tools/frames2text/test_frames2text.py`,
  `aidocs/starship/reference_tooling.md`

## Final Implementation Notes
- **Actual work done:** `tools/frames2text/frames2text.py` (stdlib-only CLI: `extract` / `convert` /
  `play` / `all`), `tools/frames2text/test_frames2text.py` (31 tests), the scene list
  `tools/frames2text/scenes/starship_flight15.toml` (9 scenes, 60.4 s), `aidocs/starship/reference_tooling.md`,
  `/.refs/` in `.gitignore`, and a doc pointer in CLAUDE.md, AGENTS.md and README.md. Code commit
  `572ad6a` (`feature: Add the frames2text reference tool (t1_1)`).
- **Deviations from plan:** see "Implementation status" and "Post-Review Changes" above. In short:
  the test command is `python3 -I tools/frames2text/test_frames2text.py`; directories are checked with a
  trailing `/` for git's dir-only patterns; eligibility is re-checked on every write with a one-call
  `git check-ignore` fast path (no caching); `extract` stages then swaps; `convert` marks the manifest
  unconverted while it runs; the CLI validates numeric args; the SpaceX footage ends at 244.04 s (not
  ~236 s).
- **Issues encountered:** (review, before implementation) chafa 1.18.3 has no PPM loader → PNG
  intermediate; chafa/img2txt end with a newline that scrolls a 137×33 terminal → `normalize_frame` and
  newline-free CUP playback; autowrap-off overwrites the last column → no cropping mode. (Review, after
  implementation) a cached eligibility verdict, unvalidated `--fps`, destructive re-extract and retained
  futures → fixed in Change Request 1. With the guard committed, README.md in the working tree also
  held a "Development workflow" section written by someone else during this session; only this task's
  one README line was staged and committed (via `git update-index --cacheinfo`). The other section was
  left uncommitted in the working tree.
- **Key decisions:** chafa is the default converter (`auto`), halfblock is the built-in fallback and the
  "what the effect can show" view, img2txt is a forced option only. Scene 9 uses its first stretch
  (179.15–183.2) because the shot is split by the booster splash. Every per-frame write is
  re-validated; full extract ~7 s.
- **Upstream defects identified:** None
- **Notes for sibling tasks:**
  - Make the animatic with `tools/frames2text/frames2text.py all "<video>" tools/frames2text/scenes/starship_flight15.toml`
    (outputs in `.refs/starship/`, gitignored). `play` needs a terminal of at least 137×33. For a
    pixel-exact half-block view (what the `starship` effect can actually draw), run
    `convert --converter halfblock`.
  - Scene timings for the effect's 60 s timeline: 10.0 / 6.1 / 6.0 / 3.0 / 4.9 / 6.0 / 4.1 / 7.0 / 13.3 s
    (liftoff, ascent, onboard, high_altitude, hot_staging, coast, ship_over_earth, seco, catch). Shot
    contents, cut times and motion fits are in "Notes for t1_2" above. The `anim` full-frame fits are
    indicative only; the descent/catch settle (spring, damping ≈ 0.8) and the decelerating bloom/smoke
    curves are the usable ones.
  - The webcast HUD (timer, gauges) is in the footage; ignore it when comparing.
  - Exact-size terminal checks without a display: run inside `tmux -L <sock> -f <conf with "set -g
    status off">` with `new-session -d -x 137 -y 33`, then `capture-pane -p [-e]`. This works for
    checking the effect's `make try` output as well.
  - The storage-guard pattern (`check_dest` + `SafeWriter`) can be reused for any future tool that
    writes video-derived data.
