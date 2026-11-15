---
priority: medium
effort: medium
depends: []
issue_type: feature
status: Implementing
labels: [tooling, screensaver]
gates: [risk_evaluated]
assigned_to: dario-e@beyond-eye.com
anchor: 1
created_at: 2026-11-15 09:57
updated_at: 2026-11-15 11:16
---

## Context

Child 1 of t1 (the `starship` screensaver effect: a ~60 s procedural animation of the Starship
Flight 15 mission). The parent plan is `aiplans/p1_starship_flight_screensaver.md`; read it first,
for the settled decisions and the verified facts.

This child builds the **reference tooling**: a frames→text tool that turns the reference video into
a coloured-text "animatic" at the screensaver's real grid. Later children use it to compare the
procedural effect against. The child also refines the scene cuts. Nothing derived from the video's
pixels may ever be committed.

Decisions already settled (do not re-ask):
- **9 scenes are kept: 1–6, 9, 10, 11.** Scenes 7 (split-screen booster descent, ~125–145 s) and
  8 (booster landing burn → splash, ~145–175 s) are dropped by the user.
- **chafa takes precedence when installed** (chafa 1.18.3 is installed at `/usr/bin/chafa`).
  `--converter auto` (default) = chafa if it is on PATH, else the built-in stdlib-Python
  half-block converter. `img2txt` (libcaca, installed) is a third forced option.
- The system Python (3.14) has **no PIL/numpy**: use the stdlib only.

Reference video (local only, **never copy it into the repo**):
`/home/ddt/Downloads/Starship Flight 15 launch, ship catch _26 CNNs first reactions.mp4`
(854×480, 29.97 fps, 493 s, h264). Only 0–236 s are useful; from ~236 s on it is CNN studio
footage. Approximate scenes kept (±3–10 s, refine them here):

| # | video time | scene |
|---|---|---|
| 1 | 0–15 s | Liftoff at the pad: tower, rocket, smoke billows, flames (two angles) |
| 2 | 15–35 s | Ascent: coastline wide shot → small rocket and bright plume in a blue sky |
| 3 | 35–65 s | Onboard camera: ship side (hex heat tiles), engine fire, coast below |
| 4 | 65–75 s | High altitude: dark sky, pink/white plume |
| 5 | 75–85 s | Hot staging: burst of orange flame around the ship |
| 6 | 85–125 s | Ship coast: Earth's curved limb, blue atmosphere, sun glare, ice particles |
| 9 | 175–195 s | Ship over Earth, bright sun, black space |
| 10 | 195–220 s | SECO: plume blooms into blue-white haze, then clears |
| 11 | 221–236 s | Return: ship descends beside the tower, caught by the chopstick arms; top-down close-up |

Target grid: **137×33 cells** (1080p at scale 1; `FONT_PX = 24` in
`omarchy-screensaver/src/raster.rs`), configurable. Half-blocks give 137×66 "pixels".

## Key Files to Modify / Create (workspace repo, not a submodule)

- `.gitignore`: add `/.refs/`.
- `tools/frames2text/frames2text.py` (new, executable, stdlib Python 3, `--help`).
- `tools/frames2text/scenes/starship_flight15.toml` (new): the 9 kept scenes as `name`, `start`,
  `end` and `speed`. **Timestamps only.** Python's `tomllib` reads it.
- `tools/frames2text/test_frames2text.py` (new, stdlib `unittest`): tests for the storage rule.
- `aidocs/starship/reference_tooling.md` (new): usage, the storage rule, and a converter comparison.
- `CLAUDE.md`: add a row to the "Read these instead of scanning the repo" table for the new doc.

## Reference Files for Patterns

- `./.aitask-scripts/aitask_screen_recording.sh` (`info|bug|anim|frames|sheet|pick`): use it to
  refine the scene cuts (`bug --range A-B --interval 1`) and to measure motion
  (`anim --window` for the climb, plume growth, ship descent and catch).
- `Makefile` header style; `aidocs/workspace/dev_workspace.md` for the doc style (plain, short).

## Implementation Plan

1. `.gitignore` += `/.refs/`.
2. `frames2text.py` subcommands:
   - `extract <video> <scenes.toml> [--out DIR] [--cols 137 --rows 33] [--target-fps 10]`: for each
     scene, run ffmpeg with `-ss start -to end`, `fps=target_fps/speed`, and
     `scale=cols:(rows*2):flags=area`. Write raw `rgb24` frames (for halfblock) and binary PPM
     (P6, header written by the stdlib) for chafa. Also write a `manifest.json` (scene name, frame
     files, playback duration per frame) in the output dir.
   - `convert [--converter auto|chafa|halfblock|img2txt]`: writes `.ans` text frames.
     - `auto` = chafa when `shutil.which("chafa")` finds it, else halfblock. Print which one ran.
     - chafa: `chafa --format symbols --colors full --size 137x33 --stretch --symbols block+half
       --animate off <frame.ppm>` (flags checked against chafa 1.18.3).
     - halfblock: each cell `▀` with fg = top pixel and bg = bottom pixel, as `38;2`/`48;2`
       truecolor SGR. Emit SGR only when the colour changes, to keep the frames small.
     - img2txt: `img2txt -W 137 -H 33 -f utf8` (check the flags with `img2txt --help`).
   - `play [--fps N] [--loop]`: alternate screen (`\e[?1049h`), hide the cursor, then per frame
     cursor home + the frame, timed from the manifest so the compressed timeline totals ~60 s.
     Restore the terminal on exit and on Ctrl-C (try/finally).
   - `all <video> <scenes.toml>` = extract + convert + play.
3. **Output storage rule (mandatory, no override flag):**
   - The default output is `<repo>/.refs/starship/`. For `--out` and for **every file written**,
     resolve the real path (`os.path.realpath`, which follows symlinks) **before** checking it.
   - Accept the destination only if one of these holds:
     - (a) it is inside a git work tree, `git -C <nearest existing parent> check-ignore -q <path>`
       succeeds (git never reports tracked paths as ignored), and `git ls-files` lists nothing
       under it;
     - (b) it is outside every git work tree and under `realpath(tempfile.gettempdir())` (the
       session scratchpad lives there).
   - Anything else is an error raised before anything is written. Refuse to replace an existing
     symlink. Never copy or link the video.
4. `test_frames2text.py`: build a temp git repo and test that the rule refuses a tracked dir,
   accepts an ignored dir, refuses a symlink from an ignored dir into a tracked dir, accepts a temp
   dir outside any repo, and refuses an outside-repo non-temp dir. Point an injectable temp-root
   parameter at a second temp dir so the last case works.
5. Refine the cut times with the screen-recording tool (0–125 s and 175–236 s), then fill in the
   TOML. Choose `speed` per scene so the compressed timeline totals ~60 s. Starting allocation from
   the parent (re-tune it): more time to liftoff (1) and the catch (11), less to the coast (6).
   Record the measured `anim` motion numbers (durations, easing fits) in this child's plan file
   notes, for t1_2.
6. Write `aidocs/starship/reference_tooling.md`: commands, the storage rule, and a short
   comparison of chafa, halfblock and img2txt on 2–3 representative frames (legibility of the
   tower/rocket silhouette, colour fidelity, speed). Add the CLAUDE.md table row.

## Verification Steps

- `tools/frames2text/frames2text.py --help` (and each subcommand's `--help`).
- `python3 -I -m unittest tools/frames2text/test_frames2text.py` passes.
- `tools/frames2text/frames2text.py all "<video>" tools/frames2text/scenes/starship_flight15.toml`
  plays an animatic of about 60 s in the terminal, with chafa chosen automatically.
- `--out aidocs/` is refused, and `--out` pointing at a symlink into a tracked dir is refused.
- `git status` shows only the intended files, and `git status --ignored` shows `.refs/` as ignored.
- **frame_data_guard** (parent post-phase): before committing, run
  `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and check by hand that no hex
  dumps, ANSI frames or pixel arrays are staged.
- Commit in this repo: `feature: Add the frames2text reference tool (t1_1)`.
