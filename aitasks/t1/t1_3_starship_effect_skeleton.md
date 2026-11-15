---
priority: high
effort: high
depends: [t1_2]
issue_type: feature
status: Ready
labels: [effect, screensaver, tooling]
gates: [risk_evaluated]
anchor: 1
created_at: 2026-11-15 09:59
updated_at: 2026-11-15 09:59
---

## Context

Child 3 of t1 (the `starship` screensaver effect: a ~60 s procedural animation of the Starship
Flight 15 mission). Parent plan: `aiplans/p1_starship_flight_screensaver.md`; read it first,
especially its "Facts verified during exploration". Also read the archived t1_1 and t1_2 plans and
`aidocs/starship/storyboard.md` (the spec) and `aidocs/starship/reference_tooling.md`.

This child builds the effect's foundation in `ttfx/`:
- the renderer pipeline and its stress spike;
- the primitives, particles and timeline;
- a whole-timeline perf bench in `omarchy-screensaver/`;
- the automated scene-progression test harness;
- scenes 1–3.

The later scenes are placeholders until t1_4/t1_5.

Settled decisions: 9 scenes (1–6, 9, 10, 11; no booster landing). The branding text is revealed
after the catch (t1_5). Use the **original ttfx engine** (`engine::effect::Effect`, `build` /
`next_frame -> Option<String>`), not the fx engine. Durations are in seconds, converted with
`ctx.terminal.config.frame_rate` (the screensaver runs at 120, the ttfx CLI defaults to 60).
Return `None` after ~60 s. No embedded bitmaps, frame dumps or big ASCII-art strings; small
hand-authored shape parameters and palettes are fine.

Verified facts (from parent planning):
- The screensaver canvas is the full grid (`omarchy-screensaver/src/engine.rs` `terminal_config`,
  `ignore_terminal_dimensions: true`, anchor C). With no `--effect` it picks randomly from all
  effects, so `starship` joins the rotation. On `None` it rebuilds the effect with the same seed.
- The overlay loop (`omarchy-screensaver/src/wayland.rs:231-265`): one `advance_deferred()` per
  1/120 s tick, catching up with up to 8 steps when late; `rasterize_pending()` (VT parse) and
  `render_delta` per present. A slow tick therefore shows up as a stutter burst.
- `benches/render.rs` runs only 512 steps (~4.3 s) of `decrypt` and reports an average.
  `make headless` counts `ch != ' '` on the final grid only (a black `▀` counts), so it is **not**
  scene evidence. `Animation::next_frame` (`engine.rs:87`) is private.
- The ttfx CLI `--canvas-width/--canvas-height` default to -1 (= text size); a full-screen effect
  needs `0`. Without stdin the CLI prints `NO INPUT.`, so `make try` pipes the branding text in.
- Full-canvas characters: `CharacterFilter { input_chars: true, inner_fill_chars: true,
  outer_fill_chars: true, added_chars: false }` (`ttfx/src/effects/matrix.rs:513`). Draw with
  `ch.animation.set_appearance(&ch.input_symbol, uses_pre, Some(symbol), Some(ColorPair::new(Some(fg), Some(bg))))`
  (`matrix.rs:99`, `ttfx/src/engine/animation.rs:677`). `ColorPair` is in
  `ttfx/src/utils/graphics.rs:243`. Easing: `ttfx/src/utils/easing.rs` (`Easing`, `ease(p)`).
  Use the seeded RNG `ctx.rng`.
- The screensaver's VT parser (`omarchy-screensaver/src/vt.rs`) handles `38;2`/`48;2` truecolor;
  its `Cell` is `{ch, fg, bg}`. Block elements are drawn as exact solid fractions, so `▀` is crisp.
- Don't write your own frame string: return `ctx.frame()`. The ttfx CLI on a tty draws from the
  engine grid (`print_differential_frame` in `ttfx/src/engine/terminal.rs`).

## Key Files to Modify / Create

- `ttfx/src/effects/starship.rs`, or `ttfx/src/effects/starship/{mod.rs,raster.rs,particles.rs,timeline.rs,scenes/*.rs}`
  once it grows past ~800 lines.
- `ttfx/src/effects/mod.rs`: `pub mod starship;`, `EffectCommand::Starship(starship::StarshipConfig)`
  with a doc comment (it is the `--help` line), the `build_effect()` arm and the `name()` arm. All
  alphabetical; copy the `Stub` lines at 109/160/203.
- `ttfx/src/fx/effects/mod.rs`: `EffectCommand::Starship(_) => None` (next to Stub, line 121).
- `ttfx/tests/starship.rs` (new).
- `omarchy-screensaver/benches/timeline.rs` (new) and `omarchy-screensaver/Cargo.toml`
  (`[[bench]] name = "timeline", harness = false`, like `render`).
- Workspace `Makefile` and `aidocs/testing/manual_testing.md`.

## Reference Files for Patterns

- `ttfx/src/effects/stub.rs`: the template (config struct, `EffectHooks`, `Effect` impl).
- `ttfx/src/effects/matrix.rs`: fill-char selection and `set_appearance` usage.
- `omarchy-screensaver/benches/render.rs`: bench structure, counting allocator, `Rasterizer`,
  `render_delta`.
- `aidocs/workspace/dev_workspace.md`: the three touch points and the commit rules.

## Implementation Plan

### Pre-phase (risk mitigation `renderer_spike`) — do this FIRST
1. Write a minimal `starship` with two layers:
   - an **animated** full-screen plasma/hue field whose colours change in **every cell on every
     tick** (the worst case for dirty cells);
   - a stress layer of ~5 000 alpha-blended particles.

   Pipeline: `Pixbuf` (W×2H RGB) → `▀` cells (fg = top pixel, bg = bottom pixel) → a shadow
   buffer of the previous cells → `set_appearance` only on changed cells → `Some(ctx.frame())`.
   Visibility is set once in `build`. No per-tick allocations.
2. Write the timeline bench (below) and run it at **1080p (1920×1080×1) and 4K (3840×2160×1)**.
   The gate: **p99 tick < 8.3 ms and max < 16 ms at 4K**, step + VT parse + raster combined.
   If it fails, restructure first: only dirty cells, reuse the buffers, and a cheaper frame-string
   path (profile with `perf record`). Record the numbers in this child's plan notes.
3. Check in a real terminal:
   `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
   keeps drawing correctly past frame 1.

### Timeline bench (`omarchy-screensaver/benches/timeline.rs`)
- Configured by env vars:
  - `SSAVER_BENCH_EFFECT` (default `decrypt`);
  - `SSAVER_BENCH_WIDTH`, `SSAVER_BENCH_HEIGHT`, `SSAVER_BENCH_SCALE` (default 1920×1080×1);
  - `SSAVER_BENCH_SECONDS` (an **explicit duration**, default 10 s);
  - `SSAVER_BENCH_SEED`.

  Do not detect the end of the effect, and leave the production API (`engine.rs`) unchanged.
- Per 1/120 s tick: `animation.advance_deferred()`, `rasterize_pending()`, then `render_delta`
  (full `render` the first time). The grid comes from `Rasterizer::grid_size`. Time each phase
  with `Instant`.
- Print one summary line: p50/p95/p99/max for each phase (step, parse, raster) and for the total,
  the number of ticks over 8.3 ms, the longest run of consecutive ticks over 8.3 ms, and
  allocations. Then print the 10 slowest ticks with their timeline second (tick / 120).
- Generic, with no starship knowledge, so it is upstreamable, and it works when ttfx lacks
  `starship`.

### Effect
4. `StarshipConfig` (clap):
   - `--start-at <seconds>` (default 0; a dev aid to jump to a time on the timeline);
   - `--duration-scale <f64>` (default 1.0).
5. Primitives (`raster.rs`):
   - filled-polygon scanline rasteriser (even-odd), lines, discs;
   - linear and radial gradients, alpha blending;
   - a 2-D camera (pan/zoom/shake) mapping world coordinates to pixels.

   All of it is allocation-free per tick.
6. Particles (`particles.rs`): a pooled `ParticleSystem` (pos, vel, life, size, colour ramp,
   drag, buoyancy, emitter rate), deterministic via `ctx.rng`.
7. Timeline (`timeline.rs`):
   - the scene table in seconds, from the storyboard;
   - `pub fn scene_at(t) -> SceneId` and the table itself, as test hooks;
   - cut and cross-fade transitions with a `blend_weight(t)` function (monotonic 0→1, easing
     from the storyboard);
   - `render_scene_only(scene, t)` (test hook: one scene with no blending);
   - returns `None` after the total.
8. Scenes 1–3 from the storyboard:
   - pad liftoff: tower lattice, rocket, smoke billows, flames, two camera angles;
   - ascent: coast wide shot → small rocket with a bright plume in a blue sky;
   - onboard camera: hex tile pattern on the ship's side, engine fire, coast below.

   Scenes 4–6, 9, 10, 11 and the branding hold are **placeholders**: flat fields in one reserved
   placeholder colour (e.g. `#ff00ff`), so the loop is already 60 s.
9. Registration in the two `mod.rs` files (above).

### Tests (`ttfx/tests/starship.rs`)
10. Build an `EngineCtx` like the screensaver does: full canvas, a seed, `frame_rate` 60 and 120,
    with the branding text as input. Read each canvas character's current visual (symbol, fg, bg)
    from the `ctx.terminal` arena after `next_frame`: the same data `ctx.frame()` formats.
    - Determinism: the same seed gives identical frame strings for 600 ticks.
    - Length: the total ticks are 60 s × frame_rate (±1).
    - **Position-sensitive** distance between frames: the mean per-cell RGB distance over fg and
      bg, plus the fraction of cells that changed by more than ΔE ≈ 30. Histograms are only for
      the signature fractions.
    - Signatures at mid-scene for the **implemented** scenes (1–3), from the storyboard: the
      dominant-colour fractions are within tolerance, there are no placeholder-colour cells, and
      the **scene-specific** darkness/variety limits hold.
    - Cuts: the distance between the last tick of A and the first tick of B is above the cut threshold.
    - Fades:
      - every consecutive tick pair is under a per-tick step limit;
      - the endpoints match `render_scene_only` of A and of B within tolerance;
      - `blend_weight` is monotonic.

      Do **not** require the sum of the steps to equal the endpoint distance.
    - Motion: frames 0.5 s apart differ, so no scene is frozen.
    - Loop: run until `None`, then rebuild with the same seed. The first frame equals the first
      run's first frame cell for cell. The last frame → first frame distance is under the
      per-tick step limit. (For now the outro is the placeholder; t1_5 makes it pass for real. Mark
      that assertion `#[ignore]` with a note until t1_5, or assert it against the placeholder fade.)
    - Placeholder scenes are allowed to fail the "no placeholder colour" check only on the
      not-yet-implemented scenes. Keep a list in the test that t1_4/t1_5 shrink to empty.

### Workspace Makefile
11. Add:
    - `TTFX_ARGS ?=` and `EFFECT_ARGS ?=`; `try` runs `$(TTFX) $(TTFX_ARGS) $(EFFECT) $(EFFECT_ARGS) < $(TEXT)`;
    - `FRAMES ?= 120`, `COLS ?= 120`, `ROWS ?= 40` for `headless` (defaults unchanged);
    - `perf`: `RES ?= 1080p` (1080p → 1920×1080, 4k → 3840×2160, scale 1) and `PERF_SECONDS ?= 61`,
      i.e. 7320 ticks. That is the whole 7200-tick timeline, **plus** the rebuild tick after `None`,
      plus ~1 s of the restarted scene 1; the rebuild tick is in the stats. It runs
      `cd omarchy-screensaver && SSAVER_BENCH_EFFECT=$(EFFECT) SSAVER_BENCH_SECONDS=$(PERF_SECONDS) ... cargo bench --bench timeline`.

    Update the Makefile's comment header and `aidocs/testing/manual_testing.md`.

## Verification Steps

- `make check` passes, including `ttfx/tests/starship.rs`.
- `make perf EFFECT=starship RES=1080p` and `RES=4k` meet the budget (record the numbers).
- `make headless EFFECT=starship FRAMES=7320` runs. It is a smoke test only, not scene evidence.
- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
  shows scenes 1–3, then placeholders, for about 60 s.
- CLI determinism: run
  `ttfx/target/release/ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt > <scratch>/a.out`
  twice, then `cmp` the outputs.
- **frame_data_guard** before **each** commit (ttfx, screensaver, workspace): run
  `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'`, review by hand, and check that
  `git status --ignored` shows `.refs/` ignored.
- Commits, per repo:
  1. ttfx: `Add the starship effect skeleton and launch scenes`, then push.
  2. omarchy-screensaver: run `git -C omarchy-screensaver checkout Cargo.lock` **first**, then
     `Add a whole-timeline benchmark`, then push.
  3. workspace: `feature: Add the starship effect skeleton (t1_3)` (Makefile, docs,
     `git add ttfx omarchy-screensaver`).

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_1** id=2026-11-15T10:59:05Z.8fc474a4acd13a0169ebd54c from=t1_1 at=2026-11-15T10:59:05Z base=572ad6a5a5f04a6bfb7e0dd03f26560242fa0428 base_branch=main dirty=yes host=omg16
>
> | Advisory: the user said the starship loop may run a few seconds past 60 s if needed (expect roughly
> | 63-65 s: 60.4 s of scene footage from the t1_1 animatic plus the ~3 s branding hold and outro). This
> | task hardcodes exactly 60 s in several places: "Return None after ~60 s", the length test "60 s x
> | frame_rate (+-1)", the placeholder loop "already 60 s", and the Makefile perf defaults
> | PERF_SECONDS ?= 61 / 7320 ticks / "7200-tick timeline" and FRAMES=7320. Take the total from the
> | storyboard's timeline table (t1_2) instead: one TOTAL_SECONDS constant in the timeline, with the test
> | and PERF_SECONDS/FRAMES derived from it (total + 1 s for the rebuild tick).

> **✉ note:t1_2** id=2026-11-15T15:48:55Z.6195dd2fab63d02735f7a2af from=t1_2 from_verified=yes at=2026-11-15T15:48:55Z base=0a42c015f1bee2afddc3320cad0ebd28c541fb0e base_branch=main dirty=no host=omg16
>
> | Advisory, from t1_2 (starship storyboard), as of commit 0a42c01. The spec is now
> | aidocs/starship/storyboard.md. It fixes these numbers and rules:
> | 
> | - Total length 64.0 s (58.0 s scenes + 6.0 s branding: form 58.0-59.5, hold 59.5-62.5,
> |   loop fade 62.5-64.0). 7680 ticks @120 fps, 3840 @60 fps. PERF_SECONDS = 65 and
> |   FRAMES = 7800 (total + 1 s). Anything hard-coding 60 s / 7200 / 7320 should take these from
> |   one TOTAL_SECONDS constant instead.
> | - Transitions (1.5):
> |   - a cross-fade of length d occupies the FIRST d s of the incoming scene, and the outgoing scene
> |     keeps its own clock; w = InOutSine. Fades: 1->2 0.5 s, 5->6 1.0 s;
> |   - 2a->2b and 11d->B are continuous (no blend, no pool clear); every other boundary is a hard cut.
> | - Signatures are measured ONLY inside the normalised region u in [0,1), v in [0,0.82)
> |   (pixel centre inside; denominator = pixels in the region), over half-block pixels (fg = top,
> |   bg = bottom). near = RGB distance <= 48; near-black = luma < 0.08; bright = luma > 0.70
> |   (Rec.709). Section 4 lists every signature with its test time; all pass against the reference.
> | - Particles (1.7): one pool of fixed capacity 5 000, allocated in build, with overflow spawns
> |   dropped deterministically. At a cross-fade the outgoing emitters stop at end_A and their particles
> |   are killed at the end of the fade. A hard cut clears the pool. Scene 1 at t = 0 has no particles
> |   (it is the loop fade's target). Every system states rate, life, velocity, size, ramp, drag,
> |   buoyancy and peak; shared defaults are in 1.7.
> | - Comparisons with the animatic use the reference time mapping (1.8: linear per sub-shot, valid
> |   frames only), never global time.
> | - Branding (3): reveal starts in [58.0, 59.25] (0.25 s fades), and the text cells' bg gets a luma
> |   cap of 0.50, so fg #f3efe6 has contrast >= 0.438.

> **👁 note:read** id=2026-11-15T15:53:25Z.95aec08d952a0c2151272d3c by=t1_3 at=2026-11-15T15:53:25Z mode=explicit ids=2026-11-15T10:59:05Z.8fc474a4acd13a0169ebd54c,2026-11-15T15:48:55Z.6195dd2fab63d02735f7a2af
