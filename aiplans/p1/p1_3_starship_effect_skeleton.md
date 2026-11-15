---
Task: t1_3_starship_effect_skeleton.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
plan_verified:
  - claudecode/opus5_5 @ 2026-11-15 18:18
---

# p1_3: effect skeleton, bounded renderer, perf/memory harness, test harness, scenes 1–3

## Context

This is child 3 of t1 (the `starship` screensaver effect). It builds the foundation in `ttfx/`:

- the renderer;
- the particles;
- the timeline;
- the test harness;
- scenes 1–3.

It also adds a generic whole-timeline benchmark in `omarchy-screensaver/`. The full spec, with
file/line references, is `aitasks/t1/t1_3_starship_effect_skeleton.md`. The numeric spec is
`aidocs/starship/storyboard.md`; read its §1 (Global) first.

**Verified 2026-11-15 (verify pass).** All line and API references in the task still hold:

- the stub registration is at `src/effects/mod.rs` lines 34/109/160/203 and `src/fx/effects/mod.rs:121`;
- `matrix.rs:99` and `:513`;
- `animation.rs:677` `set_appearance`;
- `graphics.rs:243` `ColorPair`;
- `engine.rs` `advance_deferred`/`rasterize_pending` and `Rasterizer::grid_size`/`render_delta`;
- the CLI flags `--canvas-width/-height/--frame-rate/--seed/--ignore-terminal-dimensions`;
- headless `--frames/--cols/--rows`.

Other things that matter:

- `Color::from_rgb(r,g,b)` is `pub(crate)` and allocation-free.
- `ttfx::cli::Cli` is `pub` and derives `Parser`, so tests can call `try_parse_from`.
- The screensaver's `effect_by_name` parses **only the effect name**
  (`Cli::try_parse_from(["ttfx", name])`, `omarchy-screensaver/src/engine.rs:146`). It can't pass
  effect args, so the bench can't pass them either.
- `common.rs` `parse_positive_float` accepts `inf`.

### Changes from the earlier plan

1. **Total length 64.0 s, not 60.**
   - The storyboard (§1.4) gives 7680 ticks at 120 fps and 3840 at 60; `PERF_SECONDS = 65` and
     `FRAMES = 7800`.
   - One `TOTAL_SECONDS` constant in `timeline.rs` drives the `None` tick, the length tests, the
     docs and the Makefile defaults.
   - This addresses both inbox notes, from t1_1 and t1_2.
2. **Timeline semantics from the storyboard §1.5/§1.7.**
   - Scenes are 1 (1a/1b), 2 (2a/2b), 3, 4, 5, 6, 9, 10, 11 (11a–d) and B.
   - Cross-fades occupy the **first d s of the incoming scene**: 1→2 lasts 0.5 s and 5→6 lasts
     1.0 s. `w = InOutSine`, and the outgoing scene keeps its own clock.
   - 2a→2b and 11d→B are **continuous**: no blend and no pool clear. Every other boundary is a
     hard cut, which clears the pool.
   - The loop fade (62.5–64.0) goes to scene 1 at t = 0, which has **no particles**.
3. **The loop fade is implemented generically now**, in the timeline. So the loop test runs for
   real and is not `#[ignore]`d. t1_5 replaces B's placeholder content only.
4. **Signatures are measured exactly as in the storyboard §1.3/§1.6:**
   - over half-block pixels (fg = top, bg = bottom), inside `u∈[0,1), v∈[0,0.82)` (by pixel centre);
   - near = RGB distance ≤ 48;
   - near-black = luma < 0.08;
   - bright = luma > 0.70 (Rec.709).
5. **NEW: an enforced bound on retained cell appearances**, found in this verify pass, then
   reviewed and reshaped.
   - ttfx keeps every distinct `(symbol, colours)` visual forever (`CharacterVisual::interned`
     `Box::leak`s into a thread-local `VISUAL_POOL`, `ttfx/src/engine/animation.rs:228`).
   - Without `--seed` the screensaver re-seeds every loop (`engine.rs` `build_effect`).
   - RGB555 alone allows 32768² ≈ 1.07·10⁹ appearances, so finite-run measurements can't prove a
     bound.
   - **Approach:** a **fixed, seed-independent palette** P with `|P| ≤ P_CAP`. Every emitted fg
     and bg is a palette entry, chosen through a static RGB555→index lookup table.
   - So the reachable set is **by construction** at most `|symbols| · |P|²`. In t1_3 the only
     symbol is `▀`, giving `|P|²`, whatever the seed or the number of loops.
   - Measurements are only supporting evidence.
   - If the palette can't meet the visual budget within the memory cap, **stop before the scene
     work** and revisit the rendering path. The engine-side follow-up task is queued (see Risk).
6. **NEW: the stress run really changes every cell.**
   - The CPU stress mode forces each cell's emitted palette pair to change on every tick, after
     quantisation.
   - The effect and the bench both count the changed cells, and representative timeline runs are
     measured separately.
7. **NEW: validated timing controls.**
   - `--duration-scale` and `--start-at` have finite ranges, enforced by the parser.
   - The simulation always advances in **storyboard-time** increments, and a seek is
     simulation-exact.
   - Tests compare a non-default scale and a seek against an uninterrupted run, and check that
     invalid values are rejected.

### Pre-phase (risk mitigations)

1. **[renderer_spike] The bounded pipeline, its stress test and the gate.** Do this before any
   scene.
   1. **Palette, `palette.rs`.**
      - `P` is built deterministically and seed-free, once per process (`OnceLock`). It contains:
        - every hex colour in the storyboard (≈100 entries, hand-authored and one per line, so
          `frame_data_guard` doesn't flag it as a single huge literal);
        - the declared gradient ramps (each scene lists `(a, b, steps ≤ 16)` for its sky/sea/haze
          gradients; t1_3 declares scenes 1–3, and t1_4/t1_5 add theirs);
        - a 16-step grey ramp;
        - a 6×6×6 coverage cube, for blends that aren't on a ramp.
      - Duplicates are removed and the list is sorted. `const P_CAP: usize = 448`, and a test
        asserts `P.len() <= P_CAP`.
      - `LUT: [u16; 32768]` maps RGB555 → nearest-palette index (RGB distance). It is built once
        (32768 × |P| distance checks, about 15 ms) and shared across rebuilds.
      - `ColorTable: [Color; |P|]` is built once (with `Color::from_rgb`). Emission takes
        `PalIdx(u16)` only, so the effect has **no** code path that emits a colour outside P. That
        is type-level enforcement.
      - Optional, decided at the gate by the visual check: a 2×2 ordered dither between the nearest
        and second-nearest entries. It stays inside P, so the bound is unaffected.
   2. **Pipeline.**
      - `Pixbuf` (W×2H, RGB f32) → `PalIdx` per pixel via LUT and dither → cell key
        `(fg_idx << 16) | bg_idx` (u32) → a shadow buffer of the previous keys (with a `u32::MAX`
        sentinel) → for each changed key,
        `set_appearance(&input_symbol, uses_pre, Some("▀"), Some(ColorPair::new(Some(table[fg]), Some(table[bg]))))`
        → `Some(ctx.frame())`.
      - The effect makes no allocations per tick. It keeps `changed_cells` for the last tick
        (`pub`, a test hook).
   3. **Stress mode.** It is selected by `--stress` (ttfx CLI) **or** the env var
      `TTFX_STARSHIP_STRESS=1`, read once in `build`. The env var is the only way to select it
      under the screensaver or the bench, because those can't pass effect args. It is a permanent
      dev mode, kept for the t1_4/t1_5 perf re-checks.
      - The scene is an animated full-screen plasma plus 5 000 alpha-blended particles: a full
        pool, drawn as discs.
      - **Forced change:** the emitted index is `(LUT(pixel) mod H) + (tick & 1)·H`, with
        `H = |P|/2`. Consecutive ticks therefore use disjoint palette halves, so **every cell's
        key changes every tick**, while the value still depends on the composited pixel
        (particles included). It stays inside P.
   4. **The timeline bench** (step 1 below), with the changed-cell, retained-memory and
      distinct-appearance counters.
   5. **The byte ceiling, measured exhaustively, not estimated.** This is a new test binary,
      `ttfx/tests/starship_pool_ceiling.rs`.
      - Add `[[test]] name = "starship_pool_ceiling", harness = false` to `ttfx/Cargo.toml`. That
        gives it its own process and a single-threaded `main`, so there is no libtest-harness
        thread noise. The per-thread `VISUAL_POOL` and `APPEARANCE_MEMO` then start empty, as they
        do in a fresh screensaver process.
      - A counting `#[global_allocator]` tracks live bytes (alloc − dealloc, with realloc handled
        as a delta) and the **peak** live bytes.
      - **Baseline:** live bytes at the top of `main`, before any ttfx code runs: no `EngineCtx`, no
        palette `OnceLock`, no pool.
      - **Procedure:**
        - build an `EngineCtx` at the 4K grid (274×67) with the screensaver's config, and build
          `Starship` (this allocates the LUT, the colour table, the pixbufs, the shadow keys and the
          particle pool);
        - then, through `starship::emit_appearance(ctx, id, fg: PalIdx, bg: PalIdx)` (the
          **same** `pub` function `next_frame` uses to call `set_appearance`), emit **every
          pair in P×P**, all |P|² of them, cross-half pairs included, on one character;
        - then call `ctx.frame()` once.
      - **Report and assert:**
        - the distinct `current_character_visual` pointers seen equal |P|², so every pair was new
          and was interned;
        - `ceiling_mb = (peak live − baseline)`, covering the representation, the HashSet at its
          final capacity, the resize transients (old and new tables coexisting), the memo, the LUT
          and table, the effect buffers and the frame string;
        - `final_mb = (live at end − baseline)`.
        - **Gate: `ceiling_mb ≤ 64`.** If it is over, lower `P_CAP` and re-check the visual budget.
      - Because P×P is the complete reachable set for starship (by construction, step 1), this
        **is** the maximum retained storage the effect can cause. Another effect in the rotation
        adds its own bounded set; that is outside this gate.
      - It also prints a **conservative analytic cross-check**:
        `|P|² · (size_of::<CharacterVisual>() + symbol heap block (≥ 16 B) + Box/allocator
        overhead (16 B)) + HashSet capacity (next_pow2(|P|²·8/7) slots · (8 + 1) B, doubled for
        the resize transient) + LUT 64 KiB + table`. The test asserts the measured ceiling is
        ≤ this estimate × 1.25, which catches a hidden cost the model misses.
   6. **Measure** and record the results under `## Perf notes`:
      - **CPU (stress):** run `TTFX_STARSHIP_STRESS=1 make perf EFFECT=starship` at `RES=1080p` and
        `RES=4k`.
        - The gate is p99 tick < 8.3 ms and max < 16 ms at 4K (step + parse + raster).
        - It also requires `changed_frac_min = 1.0` on every tick after the first. A ttfx test
          asserts the same thing (step 4, `stress_changes_every_cell`).
      - **Supporting evidence** (not proof): `PERF_SEED=entropy PERF_SECONDS=321` (5 loops,
        5 seeds) gives the appearance series and `retained_mb`. Both must stay ≤ |P|² appearances
        and ≤ `ceiling_mb`. Run it on stress, and on the real timeline after step 3. The stress
        mapping only exercises same-half pairs, so it is a CPU workload, not a memory proof; the
        saturation test is the memory proof.
      - **Visual budget, measured before the scenes:**
        - a `palette_error` test renders synthetic content for scenes 1–3: each declared gradient
          ramp across the full screen, plus smoke-colour particles alpha-blended (0.2–0.8) over
          each sky ramp;
        - it measures the palette-mapping error (unquantised vs emitted RGB distance), with an
          initial budget of mean ≤ 6 and p99 ≤ 20;
        - plus your visual check of the stress/ramp output in `make try`.
   7. **Gate outcome.**
      - All pass → record the results and continue to the scenes.
      - CPU fails → restructure (profile with `perf record`; cheaper LUT/dither; check raster-side
        cost).
      - Visual budget can't be met with `|P| ≤ P_CAP` (with or without dither) within the memory
        bound → **stop and ask you**, and revisit the rendering path. Don't start the scenes.
   8. Check in a real terminal that
      `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
      draws correctly past frame 1. Use the tmux exact-size capture trick from the archived p1_1
      notes, then ask you to look.

## Steps

### 1. Timeline bench: `omarchy-screensaver/benches/timeline.rs`

Add a `[[bench]] name = "timeline", harness = false` entry to its `Cargo.toml`. Copy the counting
allocator from `benches/render.rs` and add:

- a `DEALLOCATED_BYTES` counter;
- an `AtomicBool` "don't count" flag around the bench's own bookkeeping.

Configuration comes from env vars:

| Var | Default |
|---|---|
| `SSAVER_BENCH_EFFECT` | `decrypt` |
| `SSAVER_BENCH_WIDTH` | 1920 |
| `SSAVER_BENCH_HEIGHT` | 1080 |
| `SSAVER_BENCH_SCALE` | 1 |
| `SSAVER_BENCH_SECONDS` | 10 |
| `SSAVER_BENCH_SEED` | `1` (`entropy` → `None`, as in production) |
| `SSAVER_BENCH_WINDOW_SECONDS` | 64 |

Effect-specific modes go through the effect's own env var, e.g. `TTFX_STARSHIP_STRESS`, because
there's no engine API change.

- Each 1/120 s tick runs `advance_deferred()` → `rasterize_pending()` → `render_delta` (a full
  `render` the first time). The grid comes from `Rasterizer::grid_size`. Each phase is timed with
  `Instant`.
- **Changed cells:** for each tick, count the cells whose `(ch, fg, bg)` differs from the previous
  tick. The `previous_cells` used for `render_delta` already exists.
- **Distinct appearances:** a `HashSet<(char, fg, bg)>` over `cells()` after each parse, with the
  count flag off. It is sampled every second.
- Output:
  - one summary line: p50/p95/p99/max for step, parse, raster and total; ticks over 8.3 ms; the
    longest run over 8.3 ms; allocations; `changed_frac` p50 and min (excluding the first tick);
    `retained_mb` (alloc − dealloc bytes); `peak_mb`; `appearances`; and
    `appearances_window_growth_pct`. These are supporting figures only; the memory ceiling comes
    from `starship_pool_ceiling`;
  - the 10 slowest ticks with their second (tick / 120);
  - one `series` line of (second, appearances, retained_mb) every 10 s.
- It is generic (no starship knowledge) and doesn't detect the effect's end. An unknown effect
  gives a clean error.

### 2. Effect module: `ttfx/src/effects/starship/`

- **`mod.rs`**: `StarshipConfig` (clap) and the `Starship` struct, with `EffectHooks` and `Effect`.
- **Timing controls**, validated in the parser with custom functions, not `parse_positive_float`
  (which accepts `inf`):
  - `--duration-scale <f64>`, default 1.0. It must be finite and in **[0.25, 4.0]**; anything else
    (0, negative, NaN, `inf`, out of range) is rejected with a clear message.
  - `--start-at <seconds>`, default 0, in storyboard seconds. It must be finite, ≥ 0 and
    **< `TOTAL_SECONDS`**; anything else (negative, NaN, `inf`, ≥ 64) is rejected. A seek can
    never make the effect return `None` immediately.
  - `--stress`, a bool (see the pre-phase).
- **Clock semantics.**
  - `fps = ctx.terminal.config.frame_rate`, with 0 (the CLI's "unlimited") treated as 60.
  - Each tick advances **storyboard time** by `dt_sb = 1 / (fps · scale)`.
  - The particles, the emitters and every scene `step` take `dt_sb` and `t_sb = tick_sb · dt_sb`,
    so the scale changes pacing only, never what the storyboard does.
  - `total_ticks = max(1, round(TOTAL_SECONDS · fps · scale))`, so it is ≥ 1 for any valid input,
    even with `--frame-rate 1`.
  - `start_tick = min(round(start_at · fps · scale), total_ticks − 1)`. The clamp stops rounding
    near the end from producing an empty run. In `build` the effect runs `start_tick`
    simulation steps (step only; no compose, quantise or emit), which is exactly the state an
    uninterrupted run has at that tick.
  - Frames are then emitted for ticks `start_tick … total_ticks−1`, and `None` comes at
    `total_ticks`. A screensaver rebuild doesn't pass args, so it always uses the defaults.
- `build`:
  - select every character
    (`CharacterFilter{input_chars, inner_fill_chars, outer_fill_chars: true, added_chars: false}`);
  - map each one by `motion.current_coord` to the top-down row-major index
    `idx = (rows − row)·cols + (col − 1)` (row 1 is the **bottom** row). Debug-assert that every
    cell is covered exactly once;
  - `set_character_visibility(id, true)` once;
  - allocate the pixbufs (main plus a second one for cross-fades), the shadow keys and the pool.
- `next_frame`: step, compose, quantise, diff, emit; then `Some(ctx.frame())`. No `ctx.update`
  is needed: there are no active characters.
- Test hooks, all `pub`:
  - `pixels()`, the emitted RGB pixbuf;
  - `unquantised()`, for the palette-error test;
  - `changed_cells()`;
  - `live_particles()`;
  - `render_only(&mut self, scene) -> &Pixbuf`, the task's `render_scene_only`: the current tick's
    state, composed with one scene's layer only and no mix.
- **`palette.rs`**: see the pre-phase.
- **`raster.rs`**:
  - `Pixbuf`;
  - an even-odd scanline polygon fill with reused edge scratch;
  - lines and discs;
  - linear and radial gradients;
  - an alpha blend;
  - `Camera {pan, zoom, pivot, shake}`, mapping H-units to pixels in one place (storyboard §1.1:
    `px_x = x·rows·32/14`, `px_y = y·2·rows`, `A = cols·14/(rows·32)`). Shake is two sines per
    axis (f, 1.7f) with phases seeded from `ctx.rng`.

  Nothing in it allocates per tick.
- **`particles.rs`**: a pool with fixed capacity 5 000, allocated in `build`.
  - Fields: pos, vel, age, life, size0/1, a colour ramp (≤ 3 stops), drag, buoyancy, and an owner
    tag.
  - Emitters use fractional accumulators in storyboard time.
  - §1.7 defaults: spawn jitter ±0.01 H, life/speed ±20 %, direction ±15°, alpha `OutQuad` 1→0,
    1 px or a disc for size ≥ 2.
  - When the pool is full the spawn is dropped, but the RNG is still advanced.
  - API: `kill_owner` and `clear`.
- **`timeline.rs`**:
  - `pub const TOTAL_SECONDS: f64 = 64.0`;
  - `pub enum SceneId {S1, S2, S3, S4, S5, S6, S9, S10, S11, B}`;
  - `pub const SCENES` (id, start, dur, `into_next: Cut | CrossFade(d) | Continuous | Loop`), from
    §1.4;
  - sub-shot tables (1a/1b, 2a/2b, 11a–d);
  - `pub fn scene_at(t)`, which reports B inside a fade into B;
  - `pub fn blend_weight(t) -> Option<(from, to, w)>` with `w = InOutSine`, also covering the loop
    fade 62.5–64.0 (B → scene 1 at t = 0);
  - pool rules: at a cut, `clear`; at a fade start, stop A's emitters; at the fade end,
    `kill_owner(A)`; at a continuous boundary, nothing.
- **`scenes/{pad, ascent, onboard, placeholder}.rs`**. Each has `step(world, dt_sb, t_sb)` and
  `draw(world, t_sb, &mut Pixbuf)`, plus a declared ramp list for the palette.
  - Scene 1 at t = 0 has a stateless draw (sky, tower, stack; no particles), which is the loop
    fade's target.
  - The placeholder fills `#ff00ff` (which is in P) and covers S4–S11 and B's form/hold. B's loop
    fade still mixes to scene 1's first frame.

### 3. Scenes 1–3, per the storyboard §2.1–2.3

- **Pad/liftoff (0–10 s).**
  - 1a pad wide:
    - stack, tower lattice, chopsticks, ground band;
    - the stack rises 0.08 H with `InQuad`;
    - shake 0.004→0.008 H at 7 Hz;
    - smoke as billow discs, growing with `CubicBezier(0.325, 0.912, 0, 0.7)` over 3.3 s, plus
      particles: smoke 0→900/s, flames 400/s.
  - A hard cut at 6.0.
  - 1b aerial: marsh, coastline arc, the rocket climbing at 0.08 H/s, the smoke column (700/s plus
    billow discs).
  - A 0.5 s fade into 2.
- **Ascent (10–16 s).**
  - One rocket model, `B = 0.55 H·z·s`, plume `0.67·B`, trail `0.5·B`.
  - The §2.2 schedule: tilt −0.75 H `InOutSine` over 10.0–11.6; zoom 1.0→0.29 about (0.50, 0.77)
    over 11.95–13.3; the climb with `CubicBezier(0.25, 0.65, 1, 1)` over 13.4–16.0; s 1→0.375;
    tilt 10°→20°.
  - Plume 300/s. Smoke edge detail in 2a only, stopping at 12.5. 2a→2b is continuous.
  - A cut to 3.
- **Onboard (16–22 s).**
  - The hull polygon; hex tiles 0.03 H with 1 px seams; the stainless band; the fire puff
    ±20 % at 3 Hz; the coast boundary curve; the first 0.5 s darker.
  - Shake 0.003 H at 11 Hz; the ground drifts 0.01 H/s.
  - Exhaust 1 200/s and debris 60/s.
  - A cut to 4.
- Tune against the signatures (step 4) and the animatic (`tools/frames2text`; `.refs/` only,
  never committed). Afterwards:
  - re-run `palette_error` on the **real** scene frames at the signature times;
  - re-run the supporting `PERF_SEED=entropy` measurement on the real timeline;
  - update `## Perf notes`.

### 4. Tests: `ttfx/tests/starship.rs`

Use a helper that builds an `EngineCtx` like the screensaver does:

- the full canvas, `ignore_terminal_dimensions: true`, anchor C;
- `Rng::seeded(seed)`, `Clock::virtual_with_frame_rate(fps)`;
- the input `omarchy-screensaver/assets/screensaver.txt`, copied into `tests/fixtures/`.

It reads the cells `(symbol, fg, bg)` from `arena[..].animation.current_character_visual`, mapped
by `current_coord`. Grids are 137×33 at 60 fps unless stated otherwise.

- **Bound enforcement:**
  - `palette_cap`: `P.len() <= P_CAP`, and the palette is identical across processes (a checksum of
    P is computed twice from scratch).
  - `emitted_colours_in_palette`: full runs with seeds 1, 2, 3, plus stress mode. Every emitted fg
    and bg is a member of P, and every symbol is `▀`.
  - `appearance_bound`: over those runs, the distinct `(symbol, fg, bg)` triples are
    ≤ `|P|²`, a check that holds by construction. The observed counts are printed as evidence.
  - `emission_path_shared`: `next_frame` emits only through `emit_appearance`. Check it with a
    grep-style source test (no other `set_appearance` call in `src/effects/starship/`), so the
    saturation test measures the real path.
  - The `starship_pool_ceiling` binary (pre-phase step 5) runs under `make check`, because
    `cargo test` runs every test target.
- `palette_error`: the synthetic ramp and alpha-mix content (pre-phase) within the visual budget,
  and later the real scene frames.
- `stress_changes_every_cell`: in stress mode at 137×33, for 120 ticks, `changed_cells() == cols·rows`
  on every tick after the first, and the frame strings differ on every row.
- `determinism`: the same seed gives identical frame strings for 600 ticks.
- `length`: `TOTAL_SECONDS·fps` frames before `None`, at 60 (3840) and 120 (7680).
- **Timing controls:**
  - `duration_scale_length`: scale 0.5 at 60 fps gives 1920 frames; scale 2.0 gives 7680.
  - `duration_scale_storyboard_time`: at scale 2.0, `scene_at` and the emitted frame at
    storyboard 19.0 s fall in scene 3 (tick = 19.0·60·2), and the scene-3 signature passes there.
    That shows pacing changes without changing content.
  - `seek_matches_uninterrupted`: at scales 1.0 and 2.0, a build with `--start-at 11.5` (and with
    a value off the tick grid, e.g. 11.503) emits as its **first** frame exactly the frame string
    of an uninterrupted run at `round(11.5·fps·scale)`. The next 60 frames are identical too.
  - `seek_length`: with `--start-at 63.9` the effect still emits ≥ 1 frame before `None`.
  - `invalid_timing_args_rejected`: `Cli::try_parse_from(["ttfx","starship", …])` is an error for
    `--duration-scale` 0, −1, `nan`, `inf`, 0.2 and 4.5, and for `--start-at` −1, `nan`, `inf`, 64
    and 100. The boundaries 0.25, 4.0 and `--start-at 0` are accepted.
- **Signatures** (storyboard §4): 1a at 3.0, 1b at 8.0, 2a at 11.5, 2b at 14.2 and 3 at 19.0, with
  the listed tolerances and limits. They must have zero pixels near the placeholder colour. 1a and
  3 are also checked at 274×67.
- `placeholders`: `const PLACEHOLDER_SCENES = [S4, S5, S6, S9, S10, S11, B]`. Each listed scene is
  ≥ 99 % placeholder at its mid-point (which keeps the list honest; t1_4/t1_5 shrink it). The
  unlisted scenes have 0 %.
- `cuts`: at 1a→1b, 2→3 and 3→4, the distance between the last tick of A and the first tick of B
  is above the cut threshold (initially a mean of 25, tuned and documented).
- `fades`, for 1→2 (and 5→6):
  - each consecutive pair is under the per-tick step limit;
  - the first and last fade ticks match `render_only(A)` and `render_only(B)` within tolerance;
  - `blend_weight` is monotonic.

  There is no sum check.
- `continuous_2a_2b`: `live_particles()` doesn't drop to 0 at 12.5, and the step across it is under
  the per-tick limit.
- `motion`: for each implemented sub-shot, frames 0.5 s apart differ.
- `scene1_t0_no_particles`.
- `loop`, at 60 and 120:
  - run to `None` and rebuild with the same seed: the first frames are identical;
  - the last frame → the first frame of the rebuild is under the per-tick limit.
- Runtime: `make check` uses `--release`. Slow tests stay normal if each takes under ~20 s;
  otherwise they get `#[ignore]` plus a `make check-slow`. Decide after measuring, and document it.

### 5. Registration (alphabetical, copying the `Stub` lines)

- `ttfx/src/effects/mod.rs`:
  - `pub mod starship;`;
  - `/// Starship Flight 15: a 64 s procedural launch-to-catch animation (full screen).`
    `Starship(starship::StarshipConfig)`;
  - the `build_effect` arm;
  - the `name` arm `"starship"`.
- `ttfx/src/fx/effects/mod.rs`: `EffectCommand::Starship(_) => None`.

### 6. Workspace Makefile and docs

- `TTFX_ARGS ?=` and `EFFECT_ARGS ?=`; `try` runs `$(TTFX) $(TTFX_ARGS) $(EFFECT) $(EFFECT_ARGS) < $(TEXT)`.
- `FRAMES ?= 120`, `COLS ?= 120`, `ROWS ?= 40` for `headless` (the defaults are unchanged).
- `perf`:
  - `RES ?= 1080p` (1080p → 1920×1080, 4k → 3840×2160, scale 1);
  - `PERF_SECONDS ?= 65` (starship's `TOTAL_SECONDS` + 1; a comment says to keep it in sync);
  - `PERF_SEED ?= 1`;
  - it runs `cd omarchy-screensaver && SSAVER_BENCH_EFFECT=$(EFFECT) SSAVER_BENCH_WIDTH=… SSAVER_BENCH_HEIGHT=… SSAVER_BENCH_SCALE=1 SSAVER_BENCH_SECONDS=$(PERF_SECONDS) SSAVER_BENCH_SEED=$(PERF_SEED) cargo bench --bench timeline`.
    Env vars such as `TTFX_STARSHIP_STRESS` are inherited.
- Update the Makefile's comment header, and update `aidocs/testing/manual_testing.md`:
  - the `try` args for full-screen effects;
  - `headless FRAMES=7800` (a smoke test only);
  - `make perf` and its budget lines;
  - `TTFX_STARSHIP_STRESS=1`;
  - the supporting `PERF_SEED=entropy PERF_SECONDS=321` run, and that the memory bound comes from
    the palette (`|P|²`), not from the run;
  - `--duration-scale`/`--start-at` and their ranges;
  - the slow tests, if any.

### Post-phase (risk mitigations)

1. **[frame_data_guard]** Before **each** of the three commits:
   - run `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review the result by hand;
   - check that `git status --ignored` shows `.refs/` ignored.

## Verification

- `make check` passes, including `ttfx/tests/starship.rs`.
- `TTFX_STARSHIP_STRESS=1 make perf EFFECT=starship` at `RES=1080p` and `RES=4k` meets the CPU
  gate with `changed_frac_min = 1.0`. `make perf EFFECT=starship` (the real timeline) is recorded
  too.
- The bound: `starship_pool_ceiling` saturates all of P×P through the real engine path in its own
  process, with `ceiling_mb` (peak live − pre-ttfx baseline) ≤ 64 and within 1.25× the analytic
  estimate. The supporting `PERF_SEED=entropy PERF_SECONDS=321` runs (stress and timeline) stay
  below it. All of this goes in `## Perf notes`.
- `make headless EFFECT=starship FRAMES=7800` runs (a smoke test).
- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"` shows
  scenes 1–3, then the placeholders, then the loop fade, in about 64 s.
- CLI determinism:
  `ttfx/target/release/ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt`,
  run twice into the scratchpad, then `cmp`.
- Commits, one per repo, each preceded by `frame_data_guard`:
  1. ttfx (branch `feat/stub-effect`): `Add the starship effect skeleton and launch scenes`, then push.
  2. omarchy-screensaver: first `git -C omarchy-screensaver checkout Cargo.lock`, then
     `Add a whole-timeline benchmark`, then push.
  3. Workspace: `feature: Add the starship effect skeleton (t1_3)` (Makefile and docs, with
     `git add ttfx omarchy-screensaver`).
- Step 9 (Post-Implementation): archive via the workflow. In the Final Implementation Notes for
  t1_4/t1_5, include:
  - declare each scene's ramps in the palette and keep `|P| ≤ P_CAP`;
  - the branding text (t1_5) adds symbols, so its fg must come from a bounded ramp, which keeps
    the bound at `|text symbols| · |ramp| · |P|`, and that has to be re-checked against the
    64 MB budget;
  - shrink `PLACEHOLDER_SCENES`;
  - the loop fade stays in `timeline.rs`;
  - re-run the stress and timeline perf runs.

## Perf notes

Pre-phase gate, measured 2026-11-15 on omg16 (release builds).

- **Palette:** |P| = 345 (cap 448), so the bound is 119 025 `▀` appearances.
- **`starship_pool_ceiling`** (4K grid, all of P×P through `emit_appearance`, isolated process):
  - distinct_visuals = 119 025, and re-emitting P×P regrew the heap by 0 bytes;
  - build 11.94 MB (mostly the engine's 274×67 character arena);
  - pairs 36.98 MB (≈ 326 B per appearance: a 208 B visual chunk, the symbol, and two colour-code
    `String`s);
  - **ceiling 51.78 MB ≤ 64**; model 49.83 MB, ratio 1.039.
  - The first model missed the two `ColorCode::Rgb(String)` allocations per visual (ratio 1.217);
    they are now in the model.
- **`palette_error` (synthetic):** n = 3563, mean 4.52, p99 16.73, max 23.43. Within the budget
  (6 / 20).
- **CPU stress** (`TTFX_STARSHIP_STRESS=1`, 10 s, `changed_frac` min = 1.000 at both sizes):
  - 1080p (137×33): total p50 3.39, p99 4.80, max 7.44 ms; step p99 1.52; 0 ticks over 8.3 ms.
    **Pass.**
  - 4K (274×67): step p50 1.62, p99 2.39; parse p99 1.09; **raster p50 6.81, p99 8.91**;
    total p99 11.93, max 13.90; 941/1200 ticks over 8.3 ms. **Fail**, dominated by the
    screensaver raster: about 20.7M pixel writes per tick (a black clear of the damage box, then
    a bg fill and a `▀` top-half fill per cell).
  - Before the per-pair visual cache: 4K step p50 3.17 ms and about 8 000 allocations per tick,
    because the engine's 4096-slot appearance memo thrashes. With the cache: about 200 per tick.
- **Terminal:** stress mode in a 137×33 tmux pane draws all 4521 cells as `▀` and keeps changing
  between captures.
- **Gate verdict (the user, 2026-11-15):**
  - Continue to the scenes. The 4K stress failure is a screensaver-raster limit, not the
    effect's. Queue a follow-up task to cut the redundant raster writes in omarchy-screensaver,
    and re-measure the real timeline at 4K after the scenes.
  - The palette banding is acceptable (seen via `palette_preview`), so there is no dither.

After scenes 1–3:

- **Palette:** |P| = 380, so the bound is 144 400.
  - `starship_pool_ceiling`: ceiling **59.33 MB ≤ 64**; model 57.38, ratio 1.034; re-emitting all
    pairs regrew the heap by 0 bytes.
  - `P_CAP` was lowered from 448 to 400. At about 322 B per pair plus about 12 MB of arena, 448
    would be about 77 MB, over the gate. The ceiling test with the real |P| is the authority.
- **`palette_error`:** synthetic mean 4.34, p99 15.07; real scene frames (the signature times)
  mean 2.42, p99 10.20.
- **Signatures** (1080p; 4K for 1a and 3):

  | Shot | Measured | Want |
  |---|---|---|
  | 1a | 49.4 / 19.8 % | 45±15 / 15±12 |
  | 1b | 67.6 / 67.6 / 6.0 % | 65±12 / 60±12 / 11±10 |
  | 2a | 58.0 % | 55±20 |
  | 2b | 99.6 % | 90±10 |
  | 3 | 50.6 / 45.1 / 2.8 %, bright 3.0 % | 47±12 / 50±12 / 4±10 |

  4K gives the same within 1.5 points. Particle sizes and hex-seam widths are defined at the
  137×66 reference and scale with the grid.
- **Real timeline, CPU** (`make perf EFFECT=starship`, seed 1, 65 s, on a quiet machine):
  - 1080p: total p99 4.50, max 5.80 ms, 0 over 8.3 ms;
  - 4K: total p99 5.69, max 7.51 ms, 0 over 8.3 ms. **Pass.**
  - Re-run later under heavy unrelated load (load average about 4.4: browser and other agent
    sessions), the same seed-1 4K run gave p99 14.9 ms with 1423 ticks over. The bench measures
    wall time, so re-check CPU on an idle machine.
- **Supporting multi-seed runs, 4K** (`PERF_SEED=entropy PERF_SECONDS=321`, 5 loops):
  - timeline: 11 034 appearances (bound 144 400); window growth 2.32 %; retained 47.24 MB,
    including the bench's own 33 MB framebuffer;
  - stress: 72 110 appearances, window growth 0.01 %.
- **CLI determinism:** two `--seed 1` runs, 757 710 834 bytes each, have identical SHA-256.
- **Terminal:** `make try` at 137×33 draws scenes 1–3 at the signature times (4521 `▀`, no
  magenta), then the placeholders, and exits after about 64 s.
- `make headless EFFECT=starship FRAMES=7800`: `non_space=4800`, `empty_rows=0`.
- **Review round 1 (the user's concerns, all confirmed and fixed):**
  1. *Rebuild overlap.* The screensaver builds the replacement before dropping the ended
     instance (`omarchy-screensaver/src/engine.rs` `next_frame`). The ceiling test now replays
     that lifecycle: the old instance saturates P×P and plays to `None`; then a new ctx and
     effect are built and played while the old one is alive. A diagnostic of the same overlap
     at |P| = 380 reached 69.70 MB.
     - Fixes: the effect releases its own buffers when it returns `None` (asserted with
       `holds_buffers()`), and the coverage cube went from 5×5×5 to 4×4×4, so |P| = 317 and
       `P_CAP` is 340.
     - Result: **ceiling 55.71 MB ≤ 64** (overlap 54.02); model 54.34, ratio 1.025. Palette
       error is unchanged (synthetic mean 4.37 / p99 15.30; real frames 2.42 / 10.20).
  2. *Plume direction.* `plume_spec` used π/2 − tilt, giving +vx against the drawn axis
     (−sin, cos). It is now π/2 + tilt. The new test `ascent_plume_leaves_along_the_body`
     checks at 14.2 s that the mean vx is < 0 and the direction is within about 18° of the axis.
  3. *Gradients.* Added `Pixbuf::radial` (elliptical, colour and alpha from the centre to the
     rim) and `polygon_linear` (any direction, clipped to a polygon), both on a generic
     allocation-free `polygon_with`. They are used for the fire puff, the pad glows and the
     stainless sheen. Tested by `gradient_primitives`.
  4. *Boundary test gap.* `continuous_2a_2b_keeps_the_world` now requires particles older than
     one tick to survive 12.5 s, including the edge detail. The new `hard_cuts_clear_the_pool`
     checks the opposite at 6, 16 and 22 s.
  5. *`EmitSpec.rate`* was unused, so it is removed; the rate is `World::spawn`'s argument,
     documented there.
  - The motion test now counts changed pixels (≥ 20) instead of a frame-wide mean, which is
    meaningless for a small rocket on a clear sky.
  - A 4K timeline re-run under load (load average 3.7) gave p99 9.66 ms (321 over) with raster
    p99 7.2 ms; raster code was not changed. Re-check on an idle machine.
- **Review round 2: 4K timeline sign-off (the user chose per-cell raster damage in t1_3).**
  - **Diagnosis.**
    - An A/B over 1a, alternating the pre-review and current render code under the same load,
      measured the same (total p99 about 9 ms both), so the review fixes caused no regression.
    - 1a was raster-bound: about 10 % of cells change per tick, but they are scattered across
      the screen, and `render_delta` redrew their whole bounding box.
    - The CPU is a hybrid (P-cores 0–7, E-cores 8–23, powersave governor), so runs vary with
      load. Measure pinned with `taskset -c <P-core>`.
  - **Change** (`omarchy-screensaver/src/raster.rs`):
    - `render_delta` redraws only the changed cells, with cell clipping kept. It still reports
      the changed-cell bounding box as the `Damage`.
    - A cell is cleared to black only when its new bg is black, since a non-black bg is an
      opaque fill of the whole cell.
    - The per-cell drawing moved into `draw_cell`, which `draw_region` (the full render) also
      uses.
  - **Tests:**
    - `delta_matches_full_render_for_each_transition` covers text → block, block on a bg → text
      on black, text/block → blank (black and coloured bg), NUL, shade, an unchanged frame, and
      everything going black. It runs at scales 1 and 2 on a surface with margins.
    - `delta_matches_full_render_for_random_frames`: 200 seeded frames with 0/1/3/24 changes
      each.
    - Both compare every frame with a fresh full render and check the damage rectangle (or
      `None`). Removing the black clear makes both fail.
    - `render.rs`'s own full-frame oracle assert passes.
  - **Re-measured** under the same load (load average about 4.4):

    | Run | total p99 | max | ticks over 8.3 ms |
    |---|---|---|---|
    | 4K timeline, pinned P-core, ×3 | 3.83–4.31 ms | 8.70–9.27 ms | 1 of 7800 |
    | 4K timeline, unpinned | 2.37 ms | 6.57 ms | 0 |
    | 1080p timeline, unpinned | 0.62 ms | 2.23 ms | 0 |

    **The 4K timeline passes** (it was p99 about 9–17 ms under the same load). Raster p99 went
    from about 6.4 to 1.5 ms.
  - **Forced stress, reported separately** (unpinned, 10 s, `changed_frac` min 1.000):
    - 4K: total p99 10.56, max 13.84 ms, 353/1200 over; raster p50 5.05 ms (it was 6.81). It
      still misses p99, so **the stress exception is kept**: the raster's floor when every cell
      changes.
    - 1080p: p99 3.03, max 4.98 ms, 0 over.
- **Tests:** the tests in `tests/starship.rs` (27 after review) take about 3–5 s in release mode, so none are
  `#[ignore]`d and no `make check-slow` is needed. The 3 ignored ones are dev aids
  (`palette_preview`, `calibrate_distances`, `dump_frames`).

## Risk

### Code-health risk: medium
- ttfx's visual pool never frees appearances, and the screensaver re-seeds every loop, so an unconstrained continuous-colour effect grows memory without bound. · severity: high (residual low: the fixed palette bounds the reachable set at |P|² by construction, and an isolated-process saturation of all of P×P measures the byte ceiling) · → mitigation: inline pre-phase renderer_spike; visual_pool_engine_fix
- A slow tick at 120 Hz causes catch-up stutter whenever `starship` is picked from the random rotation. · severity: medium · → mitigation: inline pre-phase renderer_spike (forced every-cell-changes stress run at 4K)
- Invalid timing args (scale 0/NaN/inf, a seek past the end) could cause a division by zero, bad tick maths, or an immediate `None`. · severity: medium (residual low: parser ranges + seek/scale tests) · → mitigation: none (designed into steps 2 and 4)
- Signature and threshold tests can be brittle (hand-tuned tolerances across grid sizes). · severity: low · → mitigation: none (the thresholds come from the reference-checked storyboard; tuned values are documented)
- The blast radius is small: a new module, three registry lines, a generic bench, Makefile variables. · severity: low · → mitigation: none needed

### Goal-achievement risk: medium
- A fixed palette with ≤ 448 entries may band visibly or miss blended colours, failing the visual budget, which would block this rendering path. · severity: medium · → mitigation: inline pre-phase renderer_spike (palette_error budget + your visual check before the scenes; stop and revisit if it fails)
- Procedural scenes 1–3 may need many tuning iterations to land inside the signature tolerances. · severity: medium · → mitigation: none (iterate against the signatures and the animatic)
- Frame-derived data could leak into commits during the tuning against the animatic. · severity: medium · → mitigation: inline post-phase frame_data_guard

### Planned mitigations
- timing: pre-phase | name: renderer_spike | type: test | priority: high | effort: medium | inline_risk: low | added_complexity: low | addresses: unbounded visual-pool growth; 120 Hz stutter; palette banding | desc: build the fixed-palette bounded pipeline (reachable appearances ≤ |P|² by construction), stress it with a forced every-cell-changes plasma + 5k particles at 1080p/4K, measure the byte ceiling by saturating all of P×P through the real engine path in an isolated process (≤ 64 MB), and measure the palette error, with finite-run measurements as supporting evidence; stop and revisit the rendering path if the visual or memory budget fails
- timing: post-phase | name: frame_data_guard | type: chore | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into commits | desc: grep the staged diff for large literals and confirm .refs/ is ignored before each of the three commits
- timing: after | name: visual_pool_engine_fix | type: performance | priority: medium | effort: high | inline_risk: high | added_complexity: high | addresses: unbounded visual-pool growth (root cause) | desc: design an engine-side bounded/evictable visual path in the ttfx fork for buffer-drawing effects (render_visuals/emitted_visuals compare raw pointers, so freeing needs care)

## Final Implementation Notes
- **Actual work done:**
  - `ttfx/src/effects/starship/`:
    - `mod.rs`: config, clock, build/next_frame, the single emission path `emit_appearance`,
      a per-pair visual cache, buffer release on `None`, test hooks;
    - `palette.rs`: the fixed seed-free palette, the RGB555 LUT, `Color` table, `P_CAP`;
    - `raster.rs`: pixbuf, scanline polygon (`polygon_with` / `polygon_linear`), radial
      gradient, ellipse, line, rect, vgradient, camera, shake, hash noise;
    - `particles.rs`: the 5 000 pool, emit specs, deterministic spawn;
    - `timeline.rs`: the scene table, sub-shots, `scene_at`, `blend_weight` (fades and loop),
      pool events;
    - `scenes/{mod,pad,ascent,onboard}.rs`: world, stress mode, placeholder, billows,
      gradients, scenes 1–3.
  - Registration in `src/effects/mod.rs` and `src/fx/effects/mod.rs`.
  - Tests:
    - `tests/starship.rs`: 27 tests, plus 3 ignored dev aids;
    - `tests/starship_pool_ceiling.rs`: harness-free, its own process;
    - `[[test]]` in `Cargo.toml`; the `tests/fixtures/starship_input.txt` fixture.
  - omarchy-screensaver:
    - `benches/timeline.rs` and its `[[bench]]` entry;
    - `src/raster.rs`: `render_delta` redraws only the changed cells (`draw_cell` is shared
      with the full render), plus two oracle tests.
  - Workspace: the `Makefile` (`TTFX_ARGS`/`EFFECT_ARGS`, `FRAMES`/`COLS`/`ROWS`,
    `perf`/`RES`/`PERF_SECONDS`=65/`PERF_SEED`) and `aidocs/testing/manual_testing.md`.
- **Deviations from plan:**
  - The memory bound is a fixed palette (decided at verify), not free RGB.
  - The visual cache was added, because without it the engine's 4096-slot appearance memo
    thrashes at about 8k allocations per tick.
  - Stress is selected by `--stress` or `TTFX_STARSHIP_STRESS=1`, since the screensaver parses
    effect names only. So the bench has no `SSAVER_BENCH_EFFECT_ARGS`.
  - `P_CAP` is 340 (planned 448). The ceiling test now covers the rebuild overlap.
  - `render_delta` changed in the screensaver: the user's choice at the 4K sign-off, in place
    of the queued raster follow-up.
  - The loop fade is generic now, not `#[ignore]`d.
  - Particle sizes and hex-seam widths scale with the grid (they are defined at 137×66).
  - Scene 3's hull is lit `#5d6570` with a dark band, and its sea is `#3b70a7`/`#44709b`. That
    matches the reference frame and the signature, while the storyboard text says "hull
    `#454448`".
- **Issues encountered:**
  - The model missed the two colour-code `String`s per visual (ratio 1.217 → 1.034).
  - Review round 1 found five issues: the rebuild overlap pushed the ceiling to 69.7 MB, the
    plume direction sign was wrong, the linear and radial gradients were missing, the 2a→2b
    test had a gap, and `EmitSpec.rate` was dead. All are fixed.
  - Bench numbers swing with machine load on this hybrid CPU. Use `taskset` and compare runs
    taken under the same conditions.
  - Review round 2: scene 1a at 4K was raster-bound by the bounding-box redraw. Per-cell damage
    fixed it.
- **Key decisions:**
  - every colour is in P, and P×P is measured exhaustively in-process, including the
    rebuild overlap;
  - one emission path;
  - storyboard-time stepping, with a seek that simulates without drawing;
  - parsers reject non-finite and out-of-range timing values;
  - the forced-stress 4K exception is kept: when every cell changes on every tick, the raster's
    floor is above the budget.
- **Upstream defects identified:**
  - `ttfx/src/engine/animation.rs:228` — `CharacterVisual::interned` `Box::leak`s every
    distinct appearance into a process-lifetime `VISUAL_POOL` that is never freed. Any
    continuous-colour effect grows memory without bound under the screensaver's re-seeding
    (tracked as the planned after-mitigation `visual_pool_engine_fix`).
- **Notes for sibling tasks (t1_4, t1_5):**
  - **Palette:** add each scene's gradients to `palette.rs` (`RAMPS_*` plus `ALL_RAMPS`) and
    keep `|P| ≤ P_CAP = 340`. `|P|` is 317 now, so there is room for only about 23 more entries:
    prune the 4×4×4 cube or reuse storyboard colours first.
  - **Re-run** `cargo test --release --test starship_pool_ceiling` (≤ 64 MB, rebuild overlap
    included) and `palette_error_*` after every palette change.
  - **Branding (t1_5):** text cells add symbols. Their fg must come from a bounded ramp, so the
    bound becomes `|text symbols| · |ramp| · |P|` plus `|P|²`, and the ceiling test must be
    extended to saturate those too. Use `emit_appearance` or a sibling that also takes only
    `PalIdx`, and keep `emission_path_shared` true.
  - **Scenes:** each implements `step(world, rng, t, dt)` and `draw(world, t, buf)` in
    `scenes/<name>.rs`, dispatched in `scenes/mod.rs`. Emitters go through `World::spawn` with
    a `Slot` (add slots for new systems).
  - **Lengths:** particle sizes and 1 px details are defined at 137×66 and must scale with
    `buf.h / 66`, so the signatures match on every grid. Check 4K too (`signatures_4k`).
  - **Tests:** remove scenes from `PLACEHOLDER_SCENES` and add their rows to `SIGS`. The loop
    fade stays in `timeline.rs`. B's content replaces the placeholder only.
  - **Tools:** `dump_frames` plus a scratch reference-map script (block-wise nearest-signature
    colour) were the fastest way to match layouts. `.refs/` holds the animatic frames as raw
    137×66 RGB.
  - **Perf:** re-run `make perf EFFECT=starship RES=4k` (pinned with `taskset -c 0-7` on this
    machine) and `TTFX_STARSHIP_STRESS=1 make perf …`. Raster now costs in proportion to the
    changed cells.
