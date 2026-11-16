---
Task: t1_4_starship_space_scenes.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
plan_verified:
  - claudecode/opus5_5 @ 2026-11-16 11:44
---

# p1_4: space scenes 4, 5, 6, 9 and 10

## Context

Child 4 of t1 (the `starship` effect). t1_3 built the renderer, palette, particles, timeline,
test harness and scenes 1–3; scenes 4–11 and B are still the magenta placeholder. This child
replaces the five **space scenes** (4 high altitude, 5 hot staging, 6 coast, 9 ship over Earth,
10 SECO) with procedural scenes that match `aidocs/starship/storyboard.md` §2.4–2.8 and its §4 signatures.
Scene 11 and B stay placeholders (t1_5).

**Verified 2026-11-16 (verify pass)** against ttfx `de82884` (branch `feat/stub-effect`):

- `timeline.rs` already has every space scene in `SCENES`/`SUBSHOTS`, the 5→6 cross-fade (1.0 s)
  and cuts elsewhere. `pool_event` clears at cuts and `KillOwner(S5)` at 31.0. `World::step` runs
  only `scene_at(t1)`'s emitters, so scene 5 stops spawning at 30.0. Transitions therefore need
  **no timeline change**: only the `World::step`/`World::draw` dispatch arms.
- `Starship::compose` mixes `draw(from)` and `draw(to)` by `w`, so A's particles fade with 1 − w.
- `scenes/onboard.rs` has private `inside`, `on_seam` (hex seams, grid-scaled), `to_px` to reuse.
- `World::spawn` spawns at one point (±0.01 H jitter). Area emitters (ice flakes) need a new
  `spawn_area`.
- Shake phases: `phases[0]` (pad) and `[1]` (onboard) are used; `[2]`, `[3]` are free. Do **not**
  enlarge `phases` or draw extra RNG numbers in `World::new`: that would shift every later random
  number and move the scene 1–3 signatures.
- **Palette:** every storyboard colour of scenes 4–10 is already in `STORYBOARD`; ramps are not.
  |P| = 317, `P_CAP` = 340 (memory gate), so 23 entries of headroom; the new ramps need ~55.
- Tests: `PLACEHOLDER_SCENES`, `SIGS`, `cuts_are_cuts`, `hard_cuts_clear_the_pool`,
  `implemented_shots_move` and `calibrate_distances` are the lists to extend; the 5→6 fade is
  already in `fades_are_smooth_and_hit_their_endpoints`.
- Reference frames exist locally in `.refs/starship/0{4..8}_*/NNNNN.{png,rgb}` (137×66), ignored.

**Spec conflicts, resolved by the storyboard (the spec; t1_2's note confirms):**
- hot staging is a **blue-white** vapour burst, not orange (only the booster's engines glow orange);
- SECO's starfield is **60 faint stars, luma ≤ 0.35**, appearing in the last 1.0 s; the haze alpha
  falls only to 0.6. No signature depends on the stars, so they get a unit test, not a signature.

## Steps

### Pre-phase (risk mitigations)

1. [palette_budget] Make room in the palette before writing any scene:
   - In `palette.rs`, replace the 4×4×4 coverage cube (`CUBE_LEVELS = 4`, ~60 unique entries)
     with a 3×3×3 cube (`CUBE_LEVELS = 3`, ~25 unique). This frees ~35 entries (→ ~58 headroom).
   - Add `RAMPS_S4`, `RAMPS_S5`, `RAMPS_S6`, `RAMPS_S9`, `RAMPS_S10` (below) to `ALL_RAMPS`, with
     few steps: endpoints are storyboard colours (already in P), so a ramp of n steps costs n − 2.
     Starting set (~55 new entries; trim steps if over the cap):
     - S4: `0d1725→392d3a` 6, `392d3a→694f5c` 4, `694f5c→e6e1db` 6, `0d1725→414550` 4;
     - S5: `313a56→094287` 4, `094287→5a8bbf` 6, `5a8bbf→c9d2d9` 4, `1f2636→0d0e15` 4, `e7bb68→8d7581` 3;
     - S6: `0a397b→0e448a` 3, `0e448a→477db9` 6, `477db9→5897d9` 3, `5897d9→b8c9d5` 4, `222736→0d0f16` 4;
     - S9: `2d2633→110d16` 4, `191421→61758e` 4, `61758e→99abb7` 4, `ddedf7→191421` 6;
     - S10: `010205→121b2d` 4, `121b2d→565b67` 5, `565b67→d5e5e9` 6, `444348→010205` 4.
   - Gate before continuing: `palette_cap_and_constancy`, `palette_error_synthetic`,
     `palette_error_real_frames`, `signatures_1080`, `signatures_4k` (scenes 1–3 unchanged within
     tolerance) and `cargo test --release --test starship_pool_ceiling` (≤ 64 MB, rebuild overlap).
     If the 3-level cube breaks a budget, keep 4 levels and cut ramp steps instead. Record |P|,
     the ceiling MB and palette errors.

### 1. Shared helpers

- `scenes/onboard.rs`: make `inside`, `on_seam`, `to_px` `pub(super)` (no behaviour change).
- `scenes/mod.rs`:
  - new `Slot`s (alphabetical within scene order): `S4Plume, S5Burst, S5Sparks, S5Flakes,
    S6Flakes, S9Ice, S10Haze, S10Ice`; `SLOTS = 16`.
  - `World::spawn_area(rng, slot, spec, (u0,u1), (v0,v1), owner, dt, rate)`: for each due spawn,
    draw u, v from `rng` (always, even when the pool is full) and call `pool.spawn(.., 1)` at
    `(u·A, v)`.
  - dispatch arms for S4, S5, S6, S9, S10 in `World::step` and `World::draw`;
    `pub mod {high_altitude, hot_staging, coast, over_earth, seco, space};`.
- New `scenes/space.rs` (shared by 5, 6, 9, 10):
  - `limb(buf, cam, centre, radius, band, sky: &[(f64, Rgb)], band_cols, space)`: per pixel the
    signed distance to the Earth circle (in H, aspect-correct). Space on the centre side, a
    0.06 H atmosphere band (`lerp` through `band_cols`) just outside it, sky beyond (a gradient
    by distance). For 5/6 the circle goes through (0.30, 0.80) and (1.00, 0.58) with radius
    2.5·A H, centre below-right (storyboard §2.6); scene 5 reuses it with its own colours.
  - `glare(buf, cam, (u,v), r, core, halo)`: a bloom as two `Pixbuf::radial` passes (a small
    opaque core, then a 2.5× halo at alpha 0.5 → 0).
  - `spikes(buf, cam, (u,v), n, len, col)`: n thin radial triangles, alpha 1 → 0 along the length
    (via `polygon_with`), 1 px wide at the 137×66 reference, scaled by `buf.h / 66`.
  - `tiled_hull(buf, cam, poly, base, seam, shake)`: the hull fill with hex seams (`on_seam`).
  - `star(i) -> (u, v, luma, phase)` and `stars(buf, t, alpha)`: 60 stars from `hash01` with a
    constant salt (no RNG draws; the same sky every loop), luma ≤ 0.35, twinkle ±30 % at
    0.5–1.5 Hz, 1 px scaled by the grid.

### 2. Scene 4: `scenes/high_altitude.rs` (22–25 s, §2.4)

- Sky: `vstops` `#0e1826` → `#0d1725`; static camera.
- Engine at (0.50, 0.46) drifting up 0.01 H/s: white core r 0.015 H (`#e6e1db`) + `glare` r 0.05.
- Plume: a `polygon_linear` quad from the engine down to v ≈ 0.80, 0.04 → 0.07 H wide, length
  ×(1 ± 0.10) at 2 Hz, `#694f5c` → `#392d3a`; plus a wide, low-alpha radial glow around it so
  that ≈ 25 % of the region is near `#392d3a` (signature) while ≥ 85 % stays near `#0d1725`
  (the dim mixes in `0d1725→392d3a` are within 48 of both).
- Last 1.0 s: a translucent cone (half-angle 25°, alpha 0.25, `#414550`), length by `OutQuad`.
- Particles: plume 1 500/s, life 1.2, 0.15 H/s down, size 1–2, `#e6e1db→#694f5c→#392d3a`,
  drag 0.6 (peak ≈ 1 800).

### 3. Scene 5: `scenes/hot_staging.rs` (25–30 s, §2.5)

- Background: `space::limb` with sky `#313a56`, band `#094287`/`#5a8bbf`/`#4887ce`, black
  space lower right; `glare` at (0.90, 0.60).
- Hull poly (0,0), (0.40,0), (0.66,0.45), (0.20,0.82), (0,0.82): `tiled_hull` in `#1f2636`, the
  dark aft-flap block (0.08–0.22, 0.45–0.70) and a shadowed region in `#0d0e15`, a dimmer
  stainless edge (`#8d9da6`→`#c9d2d9`) along the upper-right side.
- Burst at 25.95: a radial `#fafcfb→#c9d2d9→#5a8bbf` puff at the apex growing to 0.25 H in 0.6 s
  (`OutCubic`), fading over 1.5 s; particles 2 500 over 0.6 s (rate 4 167/s on [25.95, 26.55)),
  life 1.5, 0.3–0.6 H/s radial (full circle), size 1→3, drag 2.0.
- Booster: **the whole body leaves the view through the bottom edge by 29.8 s.**
  - `pub fn booster(t) -> Option<Booster>` with `Booster { corners: [(u, v); 4], engine: (u, v),
    glow }`. It is `None` before 27.4 and from 29.8. The body is a 0.30 × 0.04 H rectangle,
    `#1f2636`-dark with an `#e7bb68` engine glow at its lower end. Its top end starts just
    below the apex (0.66, 0.47). It falls along a mostly-down direction (≈ 115° from +x, steeper
    than the hull's lower edge, so it never crosses into the hull). It rotates 10°
    anticlockwise and shrinks 1 → 0.6 as it recedes. The booster layer (body polygon from
    exactly `corners`, plus the engine glow) is drawn by one function, before the hull (so any
    overlap is hidden behind the hull), and skipped when `draw_opts(.., booster: false)`.
  - Speed keeps the storyboard's `InQuad` shape (start 0.04 H/s) but its end speed is set so
    the travel carries the top end, after rotation and scale, below v = 1.0 by 29.75 (a
    small margin before 29.8). That is ≈ 0.6 H of travel (end ≈ 0.6 H/s), not the ≈ 0.22 H the storyboard's by-eye
    0.04 → 0.20 H/s estimate gives. Those two storyboard statements conflict, and "leaves the frame by
    29.8" is the visible event, so it wins. The storyboard §2.5 motion line is corrected
    in the workspace commit, and the deviation is recorded in the Final Implementation Notes.
  - Sparks 200/s ride the engine end (life 0.5, 0.08 H/s opposite the fall ±30°,
    `#e7bb68→#8d7581`). The emitter runs only while `booster(t)` is `Some`, so none spawn after
    29.8. The last ones spawn off-screen near the bottom edge and die within 0.5 s.
- Flakes: `spawn_area` u 0.55–1.0, v 0–0.55, 100/s, life 4.0, 0.03 H/s up-right.
- Camera: shake 0.012 H at 9 Hz on 25.95–26.6, 0.003 H otherwise (`phases[2]`).

### 4. Scene 6: `scenes/coast.rs` (30–35 s, §2.6)

- Same framing and hull as 5 (`#222736`, shadow `#0d0f16`), no burst or booster; static camera.
- `space::limb` with sky `#0a397b`/`#0e448a`, band `#477db9`/`#5897d9`, black space below.
- Glare at (0.95, 0.62), r 0.12 H (`#b8c9d5` core → `#8d9da6`), radius breathing ±8 % at 0.3 Hz.
- Flakes: `spawn_area` u 0.55–1.0, v 0–0.55, 150/s, life 5.0, 0.02–0.06 H/s at −30°,
  `#fafaf7→#b8c9d5` (peak ≈ 750; ≤ 150 in the first second).

### 5. Scene 9: `scenes/over_earth.rs` (35–39 s, §2.7)

- Space `#191421`. The Earth: a disc whose edge runs from (0.68, 0) to (0.40, 0.82) (circle
  centre to the left, behind the hull), ocean `#61758e` with clouds `#99abb7` from `noise2` at
  0.05 H scale, threshold 0.55, scrolling 0.01 H/s down-left.
- Sun at (0.86, 0.18): core r 0.04 `#e3edef`, `glare` r 0.12 `#ddedf7`, six `spikes` 0.30 H.
- Hull poly (0,0), (0.30,0), (0.62,0.55), (0.55,0.82), (0,0.82): plum tiles `#2d2633` with
  `#110d16` seams and shadow, steel flap panel (0.30–0.55, 0–0.35) clipped to the hull, engine
  bay `#424554` (0.08–0.30, 0.30–0.60), nav glow `#62263c` r 0.03 at (0.02, 0.77).
- Ice: `spawn_area` right of the Earth's edge (u 0.72–1.0, v 0.30–0.82), 60/s, life 5.0,
  0.03 H/s up-right. Shake 0.002 H at 5 Hz (`phases[3]`).

### 6. Scene 10: `scenes/seco.rs` (39–45 s, §2.8)

- Space `#010205`/`#000000`; limb arc `#6f95ab` across the top (u 0.42–0.60, v < 0.06).
- Hull: scene 5's shape, lit grey `#444348`, tiled.
- Bloom: `pub fn bloom(t) -> (radius, alpha)`; radius 0.60 H × `CubicBezier(0.05, 0.7, 0.1, 1)`
  over 39.05–43.65; alpha 1 until the peak, then down to 0.6 at 45.0. Drawn as a radial with
  the colour ramp core `#d5e5e9` → mid `#565b67` → edge `#121b2d` by radius, and alpha falling
  to 0 at the rim, so the outer haze stays near-black (needed for the 39.6 signature) while
  `#121b2d` covers ~37 % at 42.0. A small bright plume at the apex before the bloom
  (bright ≥ 3 % at 39.6).
- Particles: haze 1 200/s on [39.05, 43.7), life 2.5, 0.1–0.3 H/s radial, size 2→4, drag 0.7;
  ice 40/s, life 2.5, 0.05 H/s radial, size 1.
- Stars: `space::stars` with alpha ramping in over 44.0–44.5, weighted by (1 − haze alpha) at
  each star.

### 7. Tune against the signatures and the animatic

- Loop: `dump_frames` at the signature times into the scratchpad, compare with
  `.refs/starship/NN_*/NNNNN.png` (the §1.8 mapping gives each reference frame), adjust
  geometry/alpha/ramps until every §4 line passes at 137×33 and, for 5, 9 and 10b, at 274×67.
  Nothing from `.refs/` is copied into the source: only hand-set numbers.
- Record any deviation from the storyboard text (as t1_3 did) in the Final Implementation Notes.

### 8. Tests: `ttfx/tests/starship.rs`

- `SIGS` rows: `4` @ 23.5 (`#0d1725` 95±10, `#392d3a` 25±12; near-black 0–100, bright ≤ 2),
  `5` @ 27.5, `6` @ 33.0, `9` @ 37.0, `10a` @ 39.6, `10b` @ 42.0, exactly as §4.
  `signatures_1080` covers all 11 rows; `signatures_4k` adds `5`, `9`, `10b`.
- `PLACEHOLDER_SCENES = [S11, B]`.
- `cuts_are_cuts`: boundaries 6, 16, 22, 25, 35, 39, 45. If a real cut lands under the mean
  limit of 25 (25.0 is the riskiest: navy → dark hull), measure with `calibrate_distances` and
  add a changed-pixel-fraction criterion rather than lowering the limit; document the number.
- `hard_cuts_clear_the_pool`: add (25, S4), (35, S6), (39, S9), (45, S10).
- `implemented_shots_move`: add (23.0, 23.5), (26.0, 26.5), (32.0, 32.5), (36.0, 36.5),
  (40.0, 40.5), (43.0, 43.5).
- New `particle_budget_holds`: over a full 60 fps run the live count stays < `POOL_CAPACITY`
  (no dropped spawns), and the scene 5 and 10 peaks lie in [1 500, 4 000] (storyboard 3 000/3 100).
- New `booster_falls_away` (the body, not just the glow):
  - `booster(t)` is `None` before 27.4. On [27.4, 29.8) every corner's v increases
    monotonically and the rotation reaches +10°.
  - At 29.4 at least one corner still has v < 1.0 (it is still in view late in the shot). From
    29.75 every one of the 4 corners has v ≥ 1.0 (the whole rotated body is below the screen),
    and from 29.8 `booster(t)` is `None`.
  - Render check, specific to the booster (no scene-wide colour test: with the ≤ 48 "near"
    threshold the scene-5 sky `#313a56` (41.8) and shadow `#0d0e15` (44.6) are already "near"
    the body `#1f2636`). It compares two renders of the **same world state**, one with and one
    without the booster layer (see the hook below). The differing pixels are exactly the
    booster's footprint:
    - at 28.5: ≥ 80 % of the pixels whose centres lie inside `corners` differ (the body is
      really drawn there), and every differing pixel lies inside `corners` or the engine-glow
      disc (nothing else depends on the booster layer);
    - at 29.75, 29.8 and 29.85 (scene 5 still drawn under the fade): zero pixels differ (the
      booster contributes nothing to the frame).
  - Hooks for it: `hot_staging::draw_opts(world, t, buf, booster: bool)`, where `draw` is
    `draw_opts(.., true)` (the booster body and glow are the only part the flag touches), and a
    read-only `Starship::world() -> Option<&World>` test hook. The test builds a grid-sized
    `Pixbuf` and calls `draw_opts` twice at the run's current time.
  - No scene-5 spark is spawned at t ≥ 29.8 (all S5 sparks are older than t − 29.8).
- New `seco_stars`: 60 stars, every luma ≤ 0.35, alpha 0 before 44.0 and > 0 at 44.9; and
  `bloom(t)` radius is monotonic and reaches 0.60 H, alpha is 0.6 at 45.0.
- `palette_error_synthetic`: add the new ramps (automatic via `ALL_RAMPS`) and explicit realistic
  overlay pairs: plume `#e6e1db`/`#694f5c` over `#0d1725`, vapour `#c9d2d9` over `#1f2636` and
  `#094287`, flakes `#fafaf7` over `#0e448a`, haze `#d5e5e9`/`#565b67` over `#010205`, ice
  `#e2ecee` over `#191421`. `palette_error_real_frames` covers the new signature times.
- `calibrate_distances`: add the boundaries 25, 30–31, 35, 39, 45.
- New `events_step_smoothly`: at **120 fps** (the screensaver rate), for every consecutive tick
  pair in the staging burst with its shake (25.95–26.6), the booster fall (27.4–29.8) and the
  bloom start (39.05–40.0), the mean frame distance is < `STEP_LIMIT`, and the changed-pixel
  fraction never spikes above 3× its median over the window (no visible jump or stepping). It
  runs whether or not a perf fallback is used, so the fallback cannot hide a regression.

### Post-phase (risk mitigations)

1. [perf_gate_4k] On an idle machine, pinned (`taskset -c 0-7`): `make perf EFFECT=starship
   RES=4k` and `RES=1080p`. Pass = p99 < 8.3 ms, max < 16 ms, no run of ≥ 2 consecutive ticks
   over 8.3 ms; list the 10 slowest ticks and check which scene they fall in (burst shake
   25.95–26.6, the 5→6 fade, the bloom start 39.05–40). Contingency if a space scene fails:
   quantise that scene's camera shake to whole pixels (fewer changed cells per tick), then
   coarsen the bloom/glare animation step (redraw its radius at 30 Hz). Re-measure and record.
   **If a fallback is applied:** besides the timing numbers, inspect the affected event at
   playback rate. `events_step_smoothly` must still pass. Dump consecutive 120 fps frames across
   the event (`dump_frames` with `STARSHIP_DUMP_T` at 1/120 s steps, into the scratchpad) and
   look at them in sequence. Play it with `make try --start-at <event − 1>` at
   `--frame-rate 60` and `120`. Record in the Final Implementation Notes which fallback was
   used, the before/after timing, and whether the motion looks acceptable (no visible stepping
   in the shake or the bloom growth). If it does not, use the other fallback or ask the user.
   Also re-run `TTFX_STARSHIP_STRESS=1 make perf` (expected unchanged: the 4K stress exception).
2. [frame_data_guard] Before each commit: `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'`
   reviewed by hand, and `git status --ignored` shows `.refs/` ignored.

## Verification

- `make check` (both submodules, release), including `starship_pool_ceiling`.
- `make headless EFFECT=starship FRAMES=7800`: `non_space` > 0.
- `make perf` numbers as in the post-phase, recorded in the Final Implementation Notes.
- `make try EFFECT=starship EFFECT_ARGS="--start-at <s>" TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
  for 22, 25, 30, 35, 39: no magenta until 45, each scene recognisable next to the animatic
  (`tools/frames2text/frames2text.py play`).
- `aidocs/testing/manual_testing.md`: add the space scenes' `--start-at` times next to the existing
  scene 3 example.
- `aidocs/starship/storyboard.md` §2.5 Motion: replace the by-eye "0.04 → 0.20 H/s" with the
  implemented profile (`InQuad` 0.04 → ≈ 0.6 H/s, whole body below the frame by 29.8) and say
  why (the old estimate cannot reach the frame edge). No signature line changes.
- Commits: in `ttfx/`, `Add the starship space scenes`, push to `origin feat/stub-effect`; then in the
  workspace `feature: Add the starship space scenes (t1_4)` (`git add ttfx aidocs/testing/manual_testing.md aidocs/starship/storyboard.md`).
  Never commit `omarchy-screensaver/Cargo.lock`.

Step 9 (Post-Implementation): archive via the workflow.

## Risk

### Code-health risk: low
- The palette has 23 entries of headroom for ~55 new ramp colours; pruning the coverage cube or adding ramps changes how scenes 1–3 quantise (signature drift) and raises the P×P memory ceiling toward the 64 MB gate. · severity: low (residual — addressed by inline pre-phase palette_budget, which gates on the ceiling and scene 1–3 tests before any scene code) · → mitigation: inline pre-phase palette_budget
- Whole-frame changes (scene 5's 0.012 H burst shake, the 5→6 fade, the bloom's fast start) can make most cells change per tick; at 4K the raster's every-cell floor (~10 ms p99 in stress) is over budget, risking 120 Hz stutter. · severity: low (residual — addressed by inline post-phase perf_gate_4k, measured with a stated contingency) · → mitigation: inline post-phase perf_gate_4k
- Five new scene files plus `space.rs` follow the t1_3 pattern; the only edits to existing code are visibility of three onboard helpers, new slots and dispatch arms. Blast radius small. · severity: low · → mitigation: none needed
- Frame-derived data could leak into commits while tuning against `.refs/`. · severity: low (residual — addressed by inline post-phase frame_data_guard) · → mitigation: inline post-phase frame_data_guard

### Goal-achievement risk: medium
- Several signatures are demanding (scene 4's 25 % dim plume glow, scene 10's ≥ 45 % near-black only 0.55 s into a fast-start bloom); landing all 6 new lines at 1080p and 4K may take many tuning rounds. · severity: medium · → mitigation: none (tuning loop in step 7)
- The task body and the storyboard disagree (orange vs blue-white burst, bright vs faint stars); following the storyboard could read as missing a requirement. · severity: low · → mitigation: none (the storyboard is the spec; deviations recorded)
- The storyboard's booster speeds cannot carry the body out of the frame by 29.8; the plan raises the end speed so the whole body exits, checked on the body's corners and on a with/without-booster render diff of the same state (not the glow alone, not scene-wide colour absence), and corrects the storyboard line. · severity: low · → mitigation: none (step 3 + `booster_falls_away`)
- A perf fallback (pixel-quantised shake, 30 Hz bloom) could add visible stepping that the 0.5 s motion test cannot see. · severity: low · → mitigation: none (`events_step_smoothly` at 120 fps plus a recorded playback-rate inspection when a fallback is used)
- The cut at 25.0 (navy → dark hull) may fall under the mean-distance cut limit. · severity: low · → mitigation: none (step 8 criterion)

### Planned mitigations
- timing: pre-phase | name: palette_budget | type: chore | priority: high | effort: low | inline_risk: low | added_complexity: low | addresses: palette headroom; scene 1–3 drift; memory ceiling | desc: shrink the coverage cube to 3 levels, add the space-scene ramps, and pass the palette-error, scene 1–3 signature and starship_pool_ceiling (≤ 64 MB) tests before writing scenes
- timing: post-phase | name: perf_gate_4k | type: test | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: 120 Hz stutter at 4K | desc: pinned idle-machine make perf at 4K/1080p with slow ticks attributed to scenes; contingency pixel-quantised shake / 30 Hz bloom redraw
- timing: post-phase | name: frame_data_guard | type: chore | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into commits | desc: grep the staged diff for large literals and confirm .refs/ is ignored before each commit

## Post-Review Changes

### Change Request 1 (2026-11-16 12:50)
- **Requested by user:** (1) scene 9's sun sat inside the Earth disc (signed distance −0.106 H at 1080p), against storyboard §2.7 and the reference: put it in black space and add a positional check; (2) scene 10's top limb used a fixed 0.29 H radius, and on a 274×33 ultrawide (A = 3.633) the chord exceeds the diameter, so `space::circle_through` silently clamped and drew arc pixels down to v ≈ 0.2: derive the circle from the aspect and the arc depth, and cover an ultrawide grid.
- **Changes made:**
  - `space::circle_through` now returns the radius it used (`max(r, half chord)`), so it always passes through both points; new `space::arc_by_depth` derives the radius from the chord and the dip.
  - Scene 9: the Earth's edge is the storyboard's (0.68, 0) → (0.40, 0.82), radius 1.5 H, centre left (`over_earth::earth(aspect)`); the sun is 0.36 H outside it at 1080p. The larger black-space area was retuned: a plum airglow along the edge (`#352d3d` → `#191421` → `#0d0e15`), lit tiles `#352d3d` and seams `#2d2633`/`#3d3446` (tones on the far side of `#2d2633` from `#110d16`), and a solid sun core. One palette ramp added (`#2d2633→#3d3446`, 3 steps): |P| 336 → 338, ceiling 59.81 MB.
  - Scene 10: `seco::limb_arc(aspect)` via `arc_by_depth` (ends (0.42, 0)/(0.60, 0), dip 0.05 H).
  - Tests: `ship_over_earth_sun_is_in_space` and `seco_limb_arc_holds_on_any_aspect` over five aspects (100×33, 182×45, 274×67, 137×33, 274×33), the latter with a render probe on the 274×33 grid; mutation-checked (the old construction gives 10 stray limb pixels).
- **Files affected:** `ttfx/src/effects/starship/scenes/{space,over_earth,seco,hot_staging}.rs`, `ttfx/src/effects/starship/palette.rs`, `ttfx/tests/starship.rs`.

## Final Implementation Notes
- **Actual work done:**
  - `ttfx/src/effects/starship/scenes/`: `high_altitude.rs` (4), `hot_staging.rs` (5: vapour burst, the falling booster with `booster(t, aspect)` and the `draw_opts` hook, ice flakes, shared framing constants), `coast.rs` (6), `over_earth.rs` (9: `earth(aspect)`, `SUN_AT`, `SUN_CORE_R`), `seco.rs` (10: `bloom(t)`, `star_alpha(t)`, `limb_arc(aspect)`), and `space.rs` (shared: `world_of`, `circle_through` (returns the radius used), `arc_by_depth`, `limb`, `glare` (optional solid core), `spikes`, `tiled_hull` (alternating seam tones), `star`/`star_luma`/`stars`).
  - `scenes/mod.rs`: 8 new slots (`SLOTS = 16`), `World::spawn_area` (draws u, v for every due spawn, also on a full pool), dispatch arms. `onboard.rs`: `inside`/`to_px`/`on_seam` are `pub(super)`; `on_seam` takes the grid height (no per-tick probe buffer).
  - `palette.rs`: coverage cube 4 → 3 levels; `RAMPS_S4/S5/S6/S9/S10` in `ALL_RAMPS`. |P| 317 → 338 (cap 340).
  - `mod.rs`: read-only `Starship::world()` test hook.
  - `tests/starship.rs`: 6 signature rows (all 11 at 1080p; 1a/3/5/9/10b at 4K); `PLACEHOLDER_SCENES = [S11, B]`; cut/pool-clear/motion lists extended; new `particle_budget_holds`, `booster_falls_away`, `seco_stars_and_bloom`, `events_step_smoothly`, `ship_over_earth_sun_is_in_space`, `seco_limb_arc_holds_on_any_aspect`; space-scene overlay pairs in `palette_error_synthetic`; `calibrate_distances` boundaries. 33 tests + 3 ignored dev aids, about 5 s in release.
  - Workspace: storyboard §2.5 booster motion corrected; `manual_testing.md` lists the scene start times.
- **Measurements:**
  - Palette (pre-phase): |P| 336 → 338 after review; `starship_pool_ceiling` 59.40 → **59.81 MB ≤ 64** (model ratio 1.022, regrowth 0 bytes). Palette error synthetic mean 4.87 / p99 15.68; real frames (all 11 signature times) mean 3.21 / p99 12.69.
  - Signatures (1080p, seed 1): 4: `#0d1725` 98.5 / `#392d3a` 22.6, bright 0.1; 5: 25.5 / 32.0 / 27.3, nb 15.3, bright 2.3; 6: 31.9 / 31.4 / 12.9, nb 17.1, bright 2.9; 9: 47.4 / 45.2 / 7.4 / 2.3, nb 25.0, bright 7.2; 10a: 59.3, nb 59.3, bright 3.7; 10b: 38.6 / 40.9, nb 33.9, bright 3.4. 4K within ~0.5 points.
  - Particles: max live 3 783 (< 5 000, no drops); scene 5 peak 2 715, scene 10 peak 3 132.
  - `events_step_smoothly` (120 fps): burst 25.95–26.6 worst step 9.27 (limit 12; the storyboard's 0.012 H shake at peak velocity), booster 3.83, bloom start 0.56.
  - Perf (`taskset -c 0-7`, machine under unrelated load 6–14): 4K timeline p99 3.05 ms / max 7.78 ms, 0 over 8.3 (load 9); after review p99 4.20 / max 9.07, 2 isolated ticks over (the full first renders at 0 s and 64 s), longest run 1 (load 13.9). 1080p p99 2.33 / max 4.99, 0 over. Slowest space-scene ticks are the cuts at 25/35/39 (~5–6.5 ms). Stress 4K unchanged (p99 10.68, the kept exception). **No perf fallback was needed**, so the playback-rate inspection step did not apply.
  - `make headless EFFECT=starship FRAMES=7800`: `non_space=4800`. `make try --start-at 22` in a 137×33 tmux pane: all 4521 cells `▀`, no magenta until scene 11 (45 s).
- **Deviations from plan:**
  - Layouts follow the reference frames where the storyboard prose and the signatures disagree (scratch block-classification maps of `.refs/` frames; nothing derived was committed): scene 5's upper hull is in deep shadow (`#030509 → #1f2636`) and its lit tiles are `#414550`; scene 6 uses `#414550` tiles with alternating `#070b15`/`#2a2f3f` seams and a smaller shadow; scene 10's hull is the reference's upper-left block (not scene 5's shape), which leaves the black the 39.6 signature needs.
  - Scene 4's glow is a wide 0.46 × 0.40 H radial around the engine (the reference's dim halo), not a narrow plume only.
  - Scene 6's glare is a 0.24 H halo with a 0.12 H blown-out core, plus a hull glint at (0.06, 0.68) (the reference's bright pixels); scene 5's and 9's suns also got solid cores.
  - Flakes (scenes 5, 6) are drawn at 45 % alpha: at the storyboard's counts (peaks 400/750) full-opacity flakes read as a snowstorm.
  - Booster: end speed 0.75 H/s (storyboard corrected); rotation and shrink follow the distance fallen (time-based shrink made the far corners rise while it fell slowly).
  - Burst: alpha eases in over 0.12 s; shake amplitude ramps 0.003 ↔ 0.012 H over 0.05/0.1 s instead of stepping.
  - SECO haze builds up over 2.5 s (radius per the storyboard's bezier) so 39.6 stays mostly black; stars are drawn under the haze (the blend is the "1 − haze alpha" weighting).
  - `events_step_smoothly` allows the changed fraction up to 3 × median + 2 % (an absolute floor so a near-static window is not flagged).
- **Issues encountered:**
  - `#0d0e15`, `#1f2636` and `#313a56` (and `#110d16`/`#2d2633`) are all within the 48 "near" threshold of each other, so hull tones had to be chosen on the far side of the shared colours; at 1080p the 0.03 H hex tiles are ~2 px and almost every hull pixel is a seam, so seam tones decide a hull's class.
  - Review round 1 (both confirmed and fixed, see Post-Review Changes): scene 9's sun inside the Earth; scene 10's fixed-radius limb arc clamped on ultrawide grids.
- **Key decisions:** the storyboard is the spec where the task body disagrees (blue-white burst, faint stars); signatures are tuned to the reference frames' measured layout; one shared `space.rs` for the space scenes; every geometric circle goes through `circle_through`/`arc_by_depth`, which never miss their endpoints.
- **Upstream defects identified:** None
- **Notes for sibling tasks (t1_5):**
  - **Palette:** |P| = 338 of `P_CAP = 340`: only 2 entries of headroom. Scene 11 and the branding ramps will need room: the 3×3×3 cube (27) is the last obvious prune, or trim ramp steps; the branding text appearances add to the ceiling as noted in p1_3. Re-run `starship_pool_ceiling` (59.81 MB now) and `palette_error_*`.
  - **"Near" overlaps:** before choosing a scene's tones, check the pairwise distances of its signature colours; any tone within 48 of two of them counts for both. The scratch block-map approach (classify `.refs/` frames by signature colour) was the fastest way to see the layout.
  - **Tiles:** at 1080p the hex tiles are mostly seam pixels; use `space::tiled_hull` with two seam tones to steer a hull's class.
  - **Geometry:** use `space::circle_through` (returns the radius used) or `space::arc_by_depth` for any circle defined by points; test geometry on the `ASPECTS` list in `tests/starship.rs` (includes 274×33 ultrawide).
  - **Shared helpers:** `space::glare(.., solid, ..)` for blown-out light sources; `World::spawn_area` for area emitters; `Starship::world()` + a scene's `draw_opts` pattern for with/without render diffs.
  - **Perf:** scene cuts are the slowest ticks (full-frame change, ~5–6.5 ms at 4K); the burst shake changes ~11 % of pixels per tick at 120 fps.
