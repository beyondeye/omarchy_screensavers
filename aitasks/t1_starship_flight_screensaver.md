---
priority: medium
effort: high
depends: []
issue_type: feature
status: Implementing
labels: [screensaver, effect, tooling]
active_gates: [risk_evaluated]
active_gates_filtered: []
active_gates_profile: fast
active_gates_digest: 4a36c12bb96d.681bafac2cb9.d73bba2fc21f
children_to_implement: [t1_1, t1_2]
assigned_to: dario-e@beyond-eye.com
created_at: 2026-11-15 08:51
updated_at: 2026-11-15 09:58
---

## Goal

A new screensaver effect, **`starship`**, that plays a ~60 s procedural animation of
the full Starship Flight 15 mission, from liftoff to the ship being caught by the
tower. It is inspired by a reference video. The finished effect must be **code that
approximates the animations**: geometry, particles, gradients and camera moves. It must
**not** store the video's frames in any form, including frames converted to text or ANSI.

Reference video (local only, never copy it into the repo; news/webcast footage):
`/home/ddt/Downloads/Starship Flight 15 launch, ship catch _26 CNNs first reactions.mp4`
(854×480, 29.97 fps, 493 s, h264 + audio).

## What is in the video (analysed with the aitask-screen-recording tool)

Only about the first 236 s are useful: an edited SpaceX webcast reel. From about 236 s
it is CNN studio and reporter coverage (ignore it). Times below come from 3 s/10 s
sampling, so cuts are **±3–10 s**. Refine them in phase 1.

| # | video time (approx) | mission time | scene |
|---|---|---|---|
| 1 | 0–15 s | T+0:05 | Liftoff at the pad: tower, rocket, billowing white/orange smoke clouds, flames (two camera angles) |
| 2 | 15–35 s | T+0:15–0:25 | Ascent: wide shot over the coastline, then a small rocket climbing a blue sky with a bright plume |
| 3 | 35–65 s | T+0:35–0:55 | Onboard camera: ship S42 side (hexagonal heat tiles), engine fire, ground/coast far below |
| 4 | 65–75 s | T+1:05 | High altitude: dark sky, glowing pink/white plume |
| 5 | 75–85 s | T+2:28 | Hot staging: burst of orange flames around the ship |
| 6 | 85–125 s | T+2:38–3:08 | Ship coasting: Earth's curved limb, blue atmosphere, sun glare, drifting ice particles |
| 7 | 125–145 s | T+5:27–5:37 | Split screen: booster descending (cloud below) next to the ship |
| 8 | 145–175 s | T+6:16–6:36 | Booster landing burn over green-grey sea, ending in an orange fireball/splash |
| 9 | 175–195 s | T+6:46–6:56 | Ship over Earth, bright sun, black space |
| 10 | 195–220 s | T+8:07–8:32 | Engine cutoff (SECO) in space: plume blooms into a blue-white haze, then clears |
| 11 | 221–236 s | T+22:32:18–31 | Return: ship descends beside the tower (two towers on the coast, overcast sky), engines firing, caught by the tower's arms ("chopsticks"); top-down close-up of the ship held in the arms |

Proposed ~60 s timeline: 8 + 5 + 6 + 3 + 4 + 6 + 7 + 4 + 5 + 10 s, plus 2 s for the
loop transition. Treat it as a starting point and tune it during the storyboard phase.
Not a uniform speed-up: the catch and liftoff deserve more time than the coast.

## Phase 1: reference extraction and a frames→text tool (local references only)

1. Refine the scene cuts and pick representative moments with
   `./.aitask-scripts/aitask_screen_recording.sh` (`bug --range A-B --interval 1`; `anim --window`
   for measurable motions such as the climb, the ship's descent and catch, and the plume growth).
2. Build a tool, e.g. `tools/frames2text/`, that:
   - extracts frames with ffmpeg for a scene list (time ranges plus a per-scene speed factor
     that compresses the timeline to ~60 s);
   - converts each frame to coloured text at the **screensaver's real grid**, by default
     **about 137×33 cells** (1080p at scale 1: `FONT_PX = 24` in `omarchy-screensaver/src/raster.rs`),
     configurable;
   - plays the text frames back in a terminal at the compressed timing, as an "animatic" to
     compare the procedural effect against.
3. **Evaluate existing converters first**, and wrap the best one rather than reinventing it:
   - `chafa` (Arch `extra`, not installed): truecolor, half-block/quadrant/braille symbols. Likely the best.
   - `jp2a` (`extra`, not installed): ASCII, colour.
   - `img2txt` / libcaca (**installed**): `-f ansi|utf8`, colour.
   - `omarchy-transcode-ascii` (part of Omarchy): braille/block, **monochrome threshold**. Useful for
     clean silhouettes (tower, rocket outline), not colour.
   - `ascii-image-converter` (AUR only).
   - There's also a no-dependency fallback: ffmpeg `-f rawvideo -pix_fmt rgb24` piped into
     stdlib Python that emits half-block `▀` cells with truecolor fg/bg. The system Python has
     **no PIL/numpy**. The screensaver draws block elements as exact solid cell fractions
     (omarchy-screensaver PR #6), so half blocks look crisp there.
   Record the comparison briefly in the doc (phase 2).
4. **Storage rule:** all extracted frames and text frames go to a **gitignored** directory
   (add e.g. `/.refs/` to `.gitignore`) or the session scratchpad. The tool must take the
   video path as an argument, never copy the video, and never write into tracked paths. Nothing
   derived from the video's pixels is committed.

## Phase 2: storyboard (committed, but description only)

Write `aidocs/starship/storyboard.md`. For each scene, cover:
- its duration in the 60 s timeline;
- the elements and their shapes, described as parameters (for example rocket proportions,
  tower lattice spacing, the Earth limb's radius and position);
- a palette as hex values sampled from the reference;
- motion: direction, speed and easing, using `anim` fits where they're measurable;
- particle systems: smoke, exhaust, ice flakes, stars, the splash fireball;
- transitions between scenes (cut, fade, wipe).

Numbers and words only; no images or text-art frames.

## Phase 3: the procedural `starship` effect

- Implement it in `ttfx/` as a new effect, using the stub as the template. There are three
  touch points; see `aidocs/workspace/dev_workspace.md`.

### Engine decision (settled 2026-11-15)

**Use ttfx's original engine** (`ttfx/src/engine/`, the `engine::effect::Effect` trait with
`build` / `next_frame -> Option<String>`). Do **not** target the fx engine (`ttfx/src/fx/`),
and add `EffectCommand::Starship(_) => None` in `src/fx/effects/mod.rs` like the stub.

Why:
- **The screensaver only runs the original engine.** `omarchy-screensaver/src/engine.rs`
  builds an `EngineCtx` and calls `command.build_effect()`; nothing there calls `ttfx::fx`.
  An fx-only effect would never play in the screensaver.
- The fx engine is a byte-identical rebuild of the same character/scene model, and only speeds
  up the `ttfx` CLI. A port can come later if CLI performance ever matters.
- The engine's usual model (every input character gets scenes of frames and a path to its
  home position) is built for text effects, and doesn't fit rocket scenes.

**Pattern: draw your own buffer, then copy it onto the fill characters.**
1. Each tick, draw the scene into the effect's own cell buffer (`symbol, fg, bg` per cell).
   Use half-blocks (`▀`) with a separate fg/bg colour for 2 vertical "pixels" per cell.
2. Copy that buffer onto the canvas's fill characters (`CharacterFilter` with
   `inner_fill_chars` + `outer_fill_chars`, which covers the whole canvas) with
   `ch.animation.set_appearance(input_symbol, uses_pre, Some(symbol), Some(ColorPair))`, the
   same call `ttfx/src/effects/matrix.rs` makes. Keep a shadow buffer and touch only cells
   that changed since the last frame. Make the fill characters visible
   (`set_character_visibility`).
3. Return `Some(ctx.frame())`. Let the engine format the frame.

Verified facts this relies on:
- The screensaver's parser (`omarchy-screensaver/src/vt.rs`) handles truecolor fg and bg
  (`38;2` / `48;2`), cursor position and clears. Its `Cell` is `{ch, fg, bg}`, so half-block
  output displays exactly.
- **Don't** have the effect write its own frame string instead of using `ctx.frame()`. The
  screensaver would show it, but the `ttfx` CLI on a tty ignores the frame string and draws
  from the engine's internal grid (`print_differential_frame` in `ttfx/src/engine/terminal.rs`),
  so `make try` would break after the first frame.

Timing: define every duration in **seconds** and convert using the frame rate in the config
(`ctx.terminal.config.frame_rate`). The screensaver runs at 120 (`FRAME_RATE` in
`omarchy-screensaver/src/engine.rs`); the ttfx CLI defaults to 60 (`--frame-rate`). Return
`None` after ~60 s: the screensaver then rebuilds the effect, so looping comes for free.

Reuse the engine's helpers: `utils::easing` for camera moves and motion, `ctx.rng` for
`--seed` determinism, and the input characters' positions/symbols if the branding text is shown.

### Drawing

- Build it from parametric primitives: polygons rasterised to half-blocks (rocket body, fins,
  tower lattice, chopstick arms); particle systems (smoke billows, flames, ice, stars, sparks);
  gradients (sky, Earth limb and atmosphere glow, sun glare, plume bloom); simple camera pans
  and zooms per scene. Use the engine's seeded RNG so `--seed` reproduces runs.
- **Allowed:** small hand-authored shape parameters (vertex lists, proportions, palettes).
  **Not allowed:** embedded bitmaps, frame dumps or big ASCII-art strings taken from the video.
- Decide what happens to the branding text (`screensaver.txt`), for example revealed in the
  clouds or smoke after the catch, or shown at the start. Ask the user during planning.
- Check pacing in both places (see Timing above): ~60 s in the screensaver (`make run`/
  `make headless`, which runs at 120 fps) and in `make try` (60 fps by default).
- Performance: it must keep up at 120 Hz on a large grid. Use `make benchmark` in
  omarchy-screensaver and ttfx's own timing tools.

## Acceptance

- [ ] The frames→text tool exists, has `--help`, and turns a scene list into a playable animatic.
      Its outputs are only in gitignored or scratch paths (`git status` stays clean after a run).
- [ ] `aidocs/starship/storyboard.md` covers all 11 scenes with timings, palette and motion.
- [ ] `ttfx starship` runs about 60 s and loops cleanly in the screensaver, with all scenes
      recognisable next to the animatic.
- [ ] `make check` and `make headless EFFECT=starship` pass (`non_space` > 0), and `--seed` is
      deterministic.
- [ ] No frame-derived data is committed. Grep the diff for large string or array literals before
      committing.
- [ ] A manual-verification follow-up is queued for watching it on real monitors (`make run EFFECT=starship`).

## Notes

- ttfx is a parity port of Python TerminalTextEffects. This effect lives on our fork
  (`beyondeye/ttfx`), not upstream; see the "Submitting upstream" section of
  `aidocs/workspace/dev_workspace.md`.
- This is high effort: split it into child tasks along the three phases during planning.
