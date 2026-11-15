---
Task: t1_starship_flight_screensaver.md
Branch: main
Base branch: main
Output branch: main
plan_verified: []
---

# t1 — `starship` screensaver effect: decomposition plan

## Context

t1 asks for a new ttfx effect, `starship`: a ~60 s procedural animation of the Starship Flight 15
mission (liftoff → hot staging → coast → SECO → tower catch; the booster landing is dropped). It
must be **code** (geometry, particles, gradients, camera moves) and must never store or commit
frames derived from the reference video. The task is high effort and asks to be split along its
three phases. This plan splits it into **5 children** (user's choice) and queues a standalone
manual-verification follow-up. It also records the design decisions settled during planning.

Decisions settled during planning (2026-11-15):
- **Scenes:** the task's scenes 7 (split-screen booster descent) and 8 (booster landing burn →
  fireball/splash) are **dropped**. The effect has **9 scenes**: 1–6, 9, 10, 11. Their ~11 s goes
  to the liftoff (scene 1) and the catch (scene 11). After hot staging, the booster falls away out
  of frame.
- **Branding text:** revealed **after the catch**: `screensaver.txt` forms out of the smoke/clouds,
  holds ~3 s, and fades into scene 1's opening colours. Then the effect returns `None` and the
  screensaver rebuilds it, so it loops.
- **frames→text converter:** **chafa takes precedence when it is installed** (it is: 1.18.3).
  `--converter auto` (default) uses chafa if it is on `PATH`, else the built-in stdlib-Python
  half-block converter (ffmpeg `rgb24` → `▀` cells with truecolor fg/bg; no PIL/numpy).
  `--converter chafa|halfblock|img2txt` forces one. The comparison goes in the docs.
- **Engine:** the original ttfx engine (`engine::effect::Effect`), using the task's pattern: draw
  into the effect's own buffer, then copy it onto the fill characters.
  `EffectCommand::Starship(_) => None` in `src/fx/effects/mod.rs`.

Facts verified during exploration (relevant to every child):
- The screensaver (`omarchy-screensaver/src/engine.rs` `terminal_config`) sets the canvas to the
  full grid (`ignore_terminal_dimensions: true`, anchor C) and steps at `FRAME_RATE` = 120. When
  `next_frame` returns `None` it rebuilds the effect, re-seeding with the same `--seed` if one is
  set. With no `--effect` it picks **randomly from all ttfx effects**, so `starship` joins the
  random rotation.
- **The overlay's real loop** (`omarchy-screensaver/src/wayland.rs:231-265`): one
  `advance_deferred()` per 1/120 s engine tick (ttfx step + `ctx.frame()` string; only the latest
  string is kept), **catching up with up to 8 steps** when late. Then, per present,
  `rasterize_pending()` (VT parse into `Cell {ch, fg, bg}`) and `Rasterizer::render_delta` per
  surface. A slow tick therefore shows up as a catch-up burst, not as a lower average.
- **The existing bench** (`omarchy-screensaver/benches/render.rs`): 2560×1440 at scale 2, effect
  hard-coded to `decrypt`. It runs 8 warmup presents plus 120 measured presents, at 4 engine
  steps each: 512 steps ≈ 4.3 s of timeline. It prints only the average ms per frame. It cannot
  see the later scenes of a 60 s effect.
- **`make headless`** (`omarchy-screensaver/src/main.rs:64-89`) counts cells with `ch != ' '` in
  the **final** grid only. A black `▀` counts as occupied, so `non_space > 0` proves nothing about
  what a scene looks like. `SSAVER_DUMP=1` prints the characters only, without colours.
- The **ttfx CLI** defaults `--canvas-width/--canvas-height` to `-1` (= text size, TTE
  semantics); a full-screen effect needs `0` (= terminal size). `make try` passes no options yet.
- Full-canvas character set: `CharacterFilter { input_chars, inner_fill_chars, outer_fill_chars: true }`
  (`ttfx/src/effects/matrix.rs:513`). Each cell is drawn with `ch.animation.set_appearance(...)`
  (`matrix.rs:99`, `engine/animation.rs:677`). `ColorPair { fg_color, bg_color }`
  (`utils/graphics.rs:243`). Easing: `utils::easing::Easing::ease(p)` (`utils/easing.rs:12,88`).
- Reference video: `/home/ddt/Downloads/Starship Flight 15 launch, ship catch _26 CNNs first reactions.mp4`
  (854×480, 29.97 fps, 493 s; only 0–236 s useful). `aitask_screen_recording.sh` offers
  `info|bug|anim|frames|sheet|pick`. chafa 1.18.3 flags checked: `--format symbols`,
  `--colors full`, `--size WxH`, `--stretch`, `--symbols block+half`, `--animate off`.

### Pre-phase (risk mitigations)
1. [renderer_spike] In t1_3, before writing any scene, build the bare pipeline and **stress** it.
   The temporary `starship` draws two layers into its buffer:
   - a full-screen **animated** plasma/hue field whose colours change in **every cell on every
     tick**, the worst case for the dirty-cell shadow buffer;
   - a particle stress layer of about 5 000 particles with alpha blending, the expected upper bound
     for the smoke and plume scenes.

   Each tick it turns the buffer into `▀` cells, copies the changed ones onto every canvas
   character with `set_appearance`, and returns `ctx.frame()`.

   Measure it with the new timeline bench (t1_3, below) at **1080p and 4K, scale 1**. The bench
   mirrors the overlay loop: per tick, `advance_deferred` + `rasterize_pending` (VT parse) +
   `render_delta` (pixel raster). It reports p50/p95/p99/max per tick and the 10 slowest ticks,
   each with its timeline second.

   Go on only when the **p99 tick is < 8.3 ms and the max is < 16 ms** at 4K. Otherwise
   restructure first: only dirty cells, no per-tick allocations, a cheaper frame-string path. Also
   check that `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
   keeps drawing correctly past frame 1 in a real terminal. `make try` pipes the branding text in;
   the ttfx CLI prints `NO INPUT.` without stdin. Record the numbers in t1_3's plan notes.

## Child tasks

Children auto-depend on earlier siblings. Each child task file gets the full context (why, files,
reference patterns, steps, verification) so it can run in a fresh session.

### t1_1 — frames→text reference tool + scene-cut refinement (workspace repo)
- `.gitignore`: add `/.refs/`.
- `tools/frames2text/frames2text.py` (stdlib Python 3, executable, `--help`). Subcommands:
  - `extract <video> <scenes.toml> [--out DIR]`: per scene, ffmpeg-extracts frames at
    `fps = target_fps / speed` over `[start, end]`, scaled to `cols×(rows*2)`, as raw `rgb24`
    (for halfblock) and PPM (for chafa, written by the stdlib).
  - `convert [--converter auto|chafa|halfblock|img2txt] [--cols 137 --rows 33]`: writes ANSI
    text frames (`.ans`). `auto` picks chafa when `shutil.which("chafa")` finds it, else
    halfblock, and prints which one ran. chafa: `chafa --format symbols --colors full --size 137x33
    --stretch --symbols block+half --animate off`. halfblock: `▀`, fg = top pixel,
    bg = bottom pixel, truecolor.
  - `play [--fps N] [--loop]`: plays the text frames at the compressed timing (alternate screen,
    cursor home + frame; restores the terminal on Ctrl-C).
  - `all` = extract + convert + play.
- **Output storage rule (mandatory, no override flag):** the default output is `<repo>/.refs/starship/`.
  For any `--out` and for every file it writes, the tool first resolves the real path with
  `os.path.realpath`, so symlinks are followed before the check. It then accepts the destination
  only if one of these holds:
  - (a) it is inside a git work tree and `git -C <nearest existing parent> check-ignore -q <path>`
    reports it ignored. Tracked paths are never reported as ignored. It also refuses if
    `git ls-files` lists anything under it;
  - (b) it is outside every git work tree and under the system temp dir
    (`realpath(tempfile.gettempdir())`, which holds the session scratchpad).

  Anything else is an error, raised before anything is written. The tool refuses to replace an
  existing symlink and never copies the video. A small self-test (`frames2text.py selftest`, or
  `tools/frames2text/test_frames2text.py` with stdlib `unittest`) covers these destinations:
  tracked dir, ignored dir, symlink from ignored to tracked, temp dir, and an outside-repo
  non-temp dir.
- `tools/frames2text/scenes/starship_flight15.toml`: the 9 kept scenes (1–6, 9, 10, 11; the
  booster-return clips at ~125–175 s are left out), each with name, `start`, `end` and `speed`.
  Timestamps only, committed (no pixel data).
- Refine the scene cuts with `./.aitask-scripts/aitask_screen_recording.sh bug --range A-B --interval 1`
  over 0–125 s and 175–236 s. Use `anim --window` for the climb, plume growth, ship descent and
  catch. Record the measured motion numbers in the child's plan notes for t1_2.
- Doc: `aidocs/starship/reference_tooling.md` (usage, storage rule, comparison of chafa,
  halfblock and img2txt at 137×33). Add a row to the `CLAUDE.md` docs table.
- Commit in this repo: `feature: Add the frames2text reference tool (t1_1)`.
- Verify:
  - `--help` works and the self-test passes;
  - `all` on the video produces a playable animatic of about 60 s;
  - `git status` is clean apart from the intended files, and nothing under `.refs/` is tracked;
  - `--out docs/` and `--out` pointing at a symlink into a tracked dir are both refused;
  - the post-phase `frame_data_guard` check.

### t1_2 — storyboard (docs only)
- `aidocs/starship/storyboard.md`, global section: grid 137×33 → 137×66 half-block pixels,
  coordinate system, and a seconds-based timeline totalling 60 s. The timeline includes the ~3 s
  branding reveal and the loop transition into scene 1.
- Then **all 9 kept scenes** (1–6, 9, 10, 11; scenes 7 and 8, the booster return, are dropped by
  the user's decision). Each scene gives:
  - its duration;
  - its elements, as parameters: rocket proportions (booster 71 m + ship 52 m, 9 m diameter →
    ratios), tower lattice spacing, chopstick arm geometry, Earth limb radius and centre, sun position;
  - a palette as hex values sampled from the reference with ffmpeg plus the converter's raw output
    (hex values only);
  - motion: direction, speed and easing, using t1_1's `anim` fits;
  - particle systems;
  - transitions;
  - a **"signature" line**: the dominant colours and their expected screen fraction (e.g.
    "scene 6: ≥40 % of cells near #0a0f2a space black, ≥15 % near #3a7bd5 limb blue"). t1_3–t1_5
    turn these into automated checks.
- A branding-reveal section (text forming in the post-catch smoke, and the fade into scene 1).
- Numbers and words only; no images or text-art. Add to the `CLAUDE.md` docs table.
- Commit: `documentation: Add the starship storyboard (t1_2)`.

### t1_3 — effect skeleton, renderer, primitives, perf harness, scenes 1–3 (ttfx + screensaver + Makefile)
- **Pre-phase `renderer_spike`** (above) comes first.
- **Timeline perf harness** in `omarchy-screensaver/benches/timeline.rs` (new `[[bench]]` in its
  `Cargo.toml`, `harness = false`, like `render.rs`). Arguments come from env vars:
  `SSAVER_BENCH_EFFECT` (default `decrypt`), `SSAVER_BENCH_WIDTH/HEIGHT/SCALE` (default
  1920×1080×1), `SSAVER_BENCH_SECONDS` (an **explicit duration**, default 10 s) and `SSAVER_BENCH_SEED`.
  It does not try to detect the end of the effect: `Animation::next_frame` (`engine.rs:87`) is
  private and rebuilds the effect silently, and the production API stays unchanged. The workspace
  `make perf` passes `SSAVER_BENCH_SECONDS=$(PERF_SECONDS)` with `PERF_SECONDS ?= 61`, i.e. 7320
  ticks. A starship run therefore covers the whole 7200-tick timeline, **plus** the tick after the
  final frame, where `next_frame` returns `None` and `Animation` rebuilds the effect, plus about 1 s
  of the restarted scene 1. That rebuild tick is in the per-tick statistics, and the slowest-ticks
  list labels it by its timeline second (≈ 60.0 s).
  - It mirrors the overlay loop: per 1/120 s tick, `advance_deferred` + `rasterize_pending` +
    `render_delta`, with the grid from `Rasterizer::grid_size`.
  - Each phase is timed with `Instant` per tick (step, parse, raster). It prints a summary line
    (p50/p95/p99/max per phase and total, the number of ticks over 8.3 ms, allocations) and the
    10 slowest ticks with their timeline second.
  - It works for any effect (generic, no starship knowledge), so it can be upstreamed. It is
    committed to the screensaver fork as a plain imperative commit (`Add a whole-timeline
    benchmark`). It keeps working when upstream ttfx lacks `starship`: the default effect is `decrypt`.
- `ttfx/src/effects/starship.rs`, or `starship/` with `mod.rs`, `raster.rs`, `particles.rs` and
  `scenes/*.rs` once it grows past ~800 lines:
  - `StarshipConfig` (clap): `--start-at <seconds>` (dev aid: jump to a time on the timeline) and
    `--duration-scale <f64>` (default 1.0).
  - `Pixbuf`: W×2H RGB plus layers, with `to_cells()` → `(▀, fg, bg)`. A shadow buffer of the
    last cells means only changed cells go through `set_appearance`. The targets are every canvas
    character (all three filters, as in matrix.rs), made visible once in `build`. No per-tick
    allocations.
  - Primitives: a filled-polygon scanline rasteriser, lines, discs, linear and radial gradients,
    alpha blending, and a simple 2-D camera (pan/zoom/shake) applied to world coordinates.
  - Particles: a pooled `ParticleSystem` (pos, vel, life, size, colour ramp, drag, buoyancy)
    driven by `ctx.rng`, so `--seed` stays deterministic.
  - Timeline: a scene table in seconds (from the storyboard), converted with
    `ctx.terminal.config.frame_rate`; cut and cross-fade transitions; returns `None` after the total.
  - A test hook: `pub fn scene_at(t) -> SceneId` and the timeline table, so tests can find the
    scene boundaries.
  - Scenes 1–3: pad liftoff (tower lattice, rocket, smoke billows, flames, two angles), ascent
    (coast wide shot → small rocket with a bright plume in a blue sky), onboard camera (hex tile
    pattern on the ship's side, engine fire, coast below).
  - Later scenes are placeholders until t1_4/t1_5, so the loop stays 60 s from day one. Each
    placeholder is a **flat field in a colour reserved for placeholders**, so the tests below can
    flag any that are left over.
- Registration: in `ttfx/src/effects/mod.rs`, `pub mod starship;`, `EffectCommand::Starship` with
  a doc comment, `build_effect()` and `name()`, all alphabetical. In `ttfx/src/fx/effects/mod.rs`,
  `EffectCommand::Starship(_) => None`.
- **Automated scene-progression tests** in `ttfx/tests/starship.rs`. They read the engine's own
  per-character visuals (`ctx.terminal` arena: symbol plus fg/bg of each canvas character after
  `next_frame`, the same data `ctx.frame()` formats), never the headless `non_space` count.
  - Determinism: the same seed gives identical frame strings for 600 ticks.
  - Length: the total tick count is 60 s × frame_rate (±1 tick) at 60 fps and at 120 fps.
  - Comparisons are **position-sensitive**. The distance between two frames is the mean per-cell
    RGB distance over the fg and bg of the same cell, plus the fraction of cells whose colour moved
    by more than ΔE ≈ 30. Histograms are used only for the signature fractions below, never to
    show continuity or a change.
  - Per-scene signature at mid-scene (implemented scenes only), from the storyboard's signature
    lines:
    - the dominant-colour fractions fall within tolerance;
    - no placeholder-colour cells remain;
    - **scene-specific** limits for darkness and variety, taken from the storyboard (e.g. scene
      10's starfield may be ≥ 95 % near-black but needs ≥ N bright star cells; the pad scene must
      have < 30 % near-black). There is no universal near-black cap.
  - Cuts: the position-sensitive distance between the last tick of scene A and the first tick of
    scene B is above the cut threshold.
  - Fades: **every pair of consecutive ticks** through the transition stays under a per-tick step
    limit, so nothing jumps abruptly. The fade's endpoints and progression are checked separately:
    - **endpoints**: the first fade tick is within tolerance of scene A rendered alone at that
      time, and the last is within tolerance of scene B rendered alone (test hook:
      `render_scene_only(scene, t)`);
    - **blend progression**: a unit test on the timeline's blend-weight function shows it runs
      monotonically from 0 to 1 over the fade with the intended easing.

    There is no sum-equals-endpoint check: smoke, particles and camera motion make the
    intermediate changes legitimately exceed the net A→B difference.
  - Motion: within a scene, frames 0.5 s apart differ (position-sensitive), so no scene is frozen.
  - Loop (end to start): run until `None`, then rebuild the effect with the same seed, as the
    screensaver does. The rebuilt first frame must equal the first run's first frame cell for cell.
    The **position-sensitive** distance between the last frame before `None` and that first frame
    stays under the per-tick fade step limit, so there is no flash. The last 0.5 s of the outro are
    checked tick by tick like any fade.
  - Each child extends these tests for the scenes it implements.
- Workspace `Makefile`:
  - `TTFX_ARGS ?=` / `EFFECT_ARGS ?=` for `try` (`$(TTFX) $(TTFX_ARGS) $(EFFECT) $(EFFECT_ARGS)`);
  - `FRAMES/COLS/ROWS` variables for `headless`, with the defaults unchanged;
  - a `perf` target (`make perf EFFECT=starship RES=1080p|4k [PERF_SECONDS=61]`) that runs the
    timeline bench with an explicit duration.

  Document them in `aidocs/testing/manual_testing.md`.
- Commits:
  - ttfx: `Add the starship effect skeleton and launch scenes`, pushed;
  - screensaver: `Add a whole-timeline benchmark`, run `git -C omarchy-screensaver checkout Cargo.lock` first, then push;
  - this repo: `feature: Add the starship effect skeleton (t1_3)` (Makefile, docs, `git add ttfx omarchy-screensaver`).

  Run the `frame_data_guard` check before each commit.

### t1_4 — space scenes 4, 5, 6, 9, 10 (ttfx)
- Scene 4, high altitude: dark sky, glowing pink/white plume.
- Scene 5, hot staging: a ring-shaped burst of orange flame; the booster falls away.
- Scene 6, ship coast: the Earth limb as a large-radius disc with an atmosphere glow gradient,
  sun glare, drifting ice particles.
- Scene 9: the ship over Earth with a bright sun.
- Scene 10, SECO: the plume blooms into a blue-white haze, then clears to a starfield.
- Reuse t1_3's primitives; add only what's missing (glare/bloom, starfield).
- Extend the scene-progression tests: signatures for the 5 scenes, their boundaries, and no
  placeholder colour left in them. Run `make perf EFFECT=starship RES=4k`: the bloom and starfield
  ticks must stay within the pre-phase budget.
- Commits: ttfx `Add the starship space scenes`; then the workspace pointer bump
  `feature: ... (t1_4)`. Run the `frame_data_guard` check first.

### t1_5 — catch scene 11, branding reveal, full-timeline perf and polish (ttfx)
- Return and catch, the longest scene: two towers on the coast, overcast sky, the ship descending
  on its engines, the chopstick arms closing, then a top-down close-up of the ship held in the arms.
- Branding reveal: after the catch, the input characters (`input_chars`, at their real
  centre-anchored `input_coord`s) form out of the smoke, hold ~3 s, then fade into scene 1's
  opening colours before `None`.
- Tune the pacing against the t1_1 animatic at 60 fps
  (`make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`) and
  at 120 fps (`make headless EFFECT=starship FRAMES=7320`, plus the timeline bench).
- **Full-timeline perf:** `make perf EFFECT=starship RES=1080p` and `RES=4k`, over the **whole**
  60 s: smoke, plume bloom, transitions, catch and branding reveal. That covers step, VT parse and
  pixel raster per tick.
  - Acceptance: p99 tick < 8.3 ms and max < 16 ms at 4K, and no catch-up bursts (no run of ≥ 2
    consecutive ticks over 8.3 ms).
  - Inspect the 10 slowest ticks: map them to scenes via their timeline seconds, profile them
    (`perf record` on the bench, or `--start-at` + bench), and fix hot spots instead of accepting
    a good average.
  - Record the before and after numbers in the plan notes.
- Final test pass: every one of the 9 scenes has a signature check, there are **no placeholder
  colours anywhere** on the timeline, and the loop and "no flash" tests pass.
- Commits: ttfx `Add the starship catch scene and branding reveal`; then the workspace
  `feature: ... (t1_5)`. Run the `frame_data_guard` check first.

### Manual-verification follow-up (queued explicitly; does not block t1)
Created right after the implementation children with `aitask_create_manual_verification.sh
--related 1 --verifies 1_1,1_2,1_3,1_4,1_5 --name manual_verification_starship_flight_screensaver`.
That is the **standalone follow-up mode**, not a child, so it never holds up the archival of t1 or
its children. The task's acceptance asks for it to be *queued*, and it is, explicitly, not left as
an optional offer. When the planning workflow's "manual verification sibling" prompt fires, the
answer is "No", because this standalone follow-up covers it. The automated tests show the scenes
progress; this checklist checks they are **recognisable**. It stays pending until someone with
the monitors runs it, and each child's final report says so.
Checklist:
- `make run EFFECT=starship` on real monitors (1080p and 4K, and multi-monitor if available): every
  one of the 9 scenes is recognisable next to `frames2text play`, and there is no booster landing;
- smooth at 120 Hz: no stutter, tearing or catch-up jumps, especially in the smoke, bloom and catch;
- the branding text forms legibly after the catch;
- the loop restarts with no flash;
- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"` runs
  about 60 s in a terminal and looks the same;
- it shows up in the random rotation: run `make run EFFECT=random` a few times (the Makefile's
  default `EFFECT` is `stub`, so a bare `make run` never picks at random).

## Verification (for the parent, after all children)
- `make check` passes, including the `ttfx/tests/starship.rs` scene-progression, boundary,
  determinism and loop tests.
- `make perf EFFECT=starship RES=1080p` and `RES=4k` meet the tick budget over the whole timeline.
- `make headless EFFECT=starship FRAMES=7200` runs without error. It is only a smoke test; its
  `non_space` count is not taken as scene evidence.
- Seeded determinism from the CLI, with identical explicit input and dimensions, so the result
  doesn't depend on the terminal:
  `ttfx/target/release/ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt > <scratch>/a.out`,
  run twice (`a.out`, `b.out`), then `cmp a.out b.out`.
- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"` plays
  the effect full-screen for about 60 s.
- `frames2text` refuses tracked and symlinked-to-tracked destinations, and `git status` is clean
  after a run. No frame-derived data is in any diff.
- The manual-verification follow-up **exists and is queued** (that is t1's acceptance condition).
  Whether a human has passed it does not gate t1's archival; the final report says plainly that
  the on-monitor visual check is still outstanding.
- Step 9 (Post-Implementation) archives the children and then the parent.

### Post-phase (risk mitigations)
1. [frame_data_guard] In every child, before each commit (workspace, ttfx and screensaver), run
   `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and check by hand that no hex dumps,
   ANSI frames or pixel arrays are staged. Also run `git status --ignored` and confirm that
   `.refs/` stays ignored and untracked. Every child task's Verification section repeats this step.

## Risk

### Code-health risk: low
- Adding `starship` puts it in the screensaver's random rotation. A slow tick at 120 Hz causes catch-up bursts (stutter) whenever it's picked. · severity: medium · → mitigation: inline pre-phase renderer_spike
- The effect is additive: a new module, three alphabetical registry lines, Makefile variables and a generic bench. The blast radius is small. · severity: low · → mitigation: none needed

### Goal-achievement risk: medium
- Scenes may not be recognisable at 137×66 half-block "pixels"; procedural smoke, plumes and the catch could read as abstract blobs. Automated signature tests show progression but not recognisability. · severity: medium · → mitigation: the t1_1 animatic as a same-grid reference, the storyboard signatures, and the queued manual-verification follow-up
- Frame-derived data could leak into the repo, either from the tool's output or from commits. · severity: medium · → mitigation: inline post-phase frame_data_guard, plus t1_1's mandatory output-destination rule
- Engine assumption: copying a buffer onto every canvas character through `set_appearance` stays within the tick budget under full-screen colour churn and heavy particle loads, and the ttfx CLI renders it correctly through `ctx.frame()`. · severity: medium · → mitigation: inline pre-phase renderer_spike

### Planned mitigations
- timing: pre-phase | name: renderer_spike | type: test | priority: high | effort: medium | inline_risk: low | added_complexity: low | addresses: 120 Hz stutter in the random rotation; buffer→fill-char pipeline assumption | desc: stress the pipeline (every cell changing each tick + ~5k particles) and time step+parse+raster per tick with the new timeline bench at 1080p/4K before building scenes (t1_3)
- timing: post-phase | name: frame_data_guard | type: chore | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into commits | desc: grep the staged diff for large literals and confirm .refs/ is ignored before every child commit
