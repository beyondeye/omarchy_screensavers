---
Task: t1_3_starship_effect_skeleton.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
---

# p1_3 — effect skeleton, renderer, perf harness, test harness, scenes 1–3

Context: `aitasks/t1/t1_3_starship_effect_skeleton.md` is the full spec, with the verified engine
facts and the file/line references. Also the parent plan, the storyboard, and the archived p1_1/p1_2.

### Pre-phase (risk mitigations)
1. [renderer_spike] Build a minimal `starship`: an animated full-screen plasma (every cell changes
   every tick) plus ~5 000 alpha-blended particles. It runs Pixbuf → `▀` cells → shadow-buffer
   diff → `set_appearance` on the changed cells → `ctx.frame()`.
   - Register it (step 5) and write the timeline bench (step 1), so it can be measured.
   - Gate: at 4K (3840×2160×1), p99 tick < 8.3 ms and max < 16 ms, for step + VT parse + raster.
     Also check 1080p.
   - Check `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
     in a real terminal.
   - Record the numbers under `## Perf notes` in this plan. If the gate fails, restructure before
     step 2.

## Steps

1. `omarchy-screensaver/benches/timeline.rs` plus a `[[bench]]` entry in its Cargo.toml.
   - Env vars: `SSAVER_BENCH_EFFECT` (default `decrypt`), `SSAVER_BENCH_WIDTH/HEIGHT/SCALE`
     (default 1920×1080×1), `SSAVER_BENCH_SECONDS` (default 10), `SSAVER_BENCH_SEED`.
   - Per tick: `advance_deferred` → `rasterize_pending` → `render_delta`, with each phase timed.
   - Output: the p50/p95/p99/max summary, the number of ticks over 8.3 ms, the longest run over
     8.3 ms, allocations, and the 10 slowest ticks with their seconds.
   - No `engine.rs` API changes.
2. `ttfx/src/effects/starship/`:
   - `mod.rs`: `StarshipConfig` (`--start-at`, `--duration-scale`) and the Effect impl.
   - `raster.rs`: Pixbuf, polygon/line/disc, gradients, blend, camera.
   - `particles.rs`: a pooled system using `ctx.rng`.
   - `timeline.rs`: the scene table, `scene_at`, `blend_weight`, `render_scene_only`.
   - `scenes/{pad,ascent,onboard}.rs`.

   Placeholder scenes are flat `#ff00ff`.
3. Scenes 1–3 per the storyboard.
4. `ttfx/tests/starship.rs`: determinism, length at 60/120 fps, the position-sensitive distance,
   signatures for scenes 1–3, cut/fade checks (consecutive-tick limits plus endpoints;
   `blend_weight` monotonic; no sum check), motion, loop (the outro assertion is `#[ignore]` until
   t1_5), and the placeholder list.
5. Registration:
   - `ttfx/src/effects/mod.rs`: `pub mod starship;`, the `Starship` variant with a doc comment,
     the `build_effect` and `name` arms (alphabetical);
   - `ttfx/src/fx/effects/mod.rs`: `Starship(_) => None`.
6. Workspace `Makefile`: `TTFX_ARGS`/`EFFECT_ARGS` for `try`; `FRAMES/COLS/ROWS` for `headless`;
   `perf` with `RES` (1080p|4k) and `PERF_SECONDS ?= 61`. Update the header comment and
   `aidocs/testing/manual_testing.md`.

### Post-phase (risk mitigations)
1. [frame_data_guard] Before each of the three commits, run the staged-diff grep, review it by
   hand, and check that `.refs/` stays ignored.

## Verification

- `make check`.
- `make perf EFFECT=starship RES=1080p` and `RES=4k` are within budget.
- `make headless EFFECT=starship FRAMES=7320` runs (smoke test only).
- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"` runs
  about 60 s.
- CLI determinism: two runs of `ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt`
  give identical output under `cmp`.
- Commits:
  1. ttfx `Add the starship effect skeleton and launch scenes`, then push.
  2. screensaver: run `git -C omarchy-screensaver checkout Cargo.lock` first, then
     `Add a whole-timeline benchmark`, then push.
  3. workspace `feature: Add the starship effect skeleton (t1_3)`.

Step 9 (Post-Implementation): archive via the workflow.
