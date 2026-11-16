---
Task: t1_5_starship_catch_branding_perf.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
plan_verified:
  - claudecode/opus5_5 @ 2026-11-16 17:09
---

# p1_5: catch scene 11, branding reveal, full-timeline perf, final tests

## Context

Child 5 of t1 (the `starship` effect), and the last implementation child. t1_3 built the renderer,
palette, particles, timeline and test harness, plus scenes 1–3. t1_4 added the space scenes 4–10.
Scene 11 (45–58 s) and B (58–64 s) are still the magenta placeholder. This child:

- adds the catch scene (11a–d);
- adds the branding reveal B: the input characters form out of smoke, hold, then dissolve into the
  loop fade;
- tunes perf over the whole 64 s;
- finishes the tests, with no placeholder left anywhere.

The spec is `aidocs/starship/storyboard.md` §2.9, §3 and §4.

**Verified 2026-11-16 (verify pass)** against ttfx `7b8f9a4` (`feat/stub-effect`) and the workspace
`6a31624`. The plan's earlier text was corrected as follows:

- **Lengths.** The timeline is 64.0 s (`TOTAL_SECONDS`). The headless smoke run is
  `FRAMES=7800`, not 7320, and the Makefile default is already `PERF_SECONDS=65`, not 61.
- **Timeline.** `timeline.rs` already has S11 (45–58, `Continuous` into B), B (58–64, `Loop`),
  sub-shots 11a/11b/11c/11d (hard cuts, which `pool_event` clears) and B (continuous). The loop fade
  (`Blend::Loop`, 62.5–64 → `pad::draw_static(0)`) is generic and `loop_rebuild_is_seamless`
  already runs. So **no timeline change** is needed, only dispatch arms.
- **Placeholder.** `World::step`/`draw` route S11 and B to the `_ =>` arm (`draw_placeholder`).
  `PLACEHOLDER_SCENES = [S11, B]` in `tests/starship.rs`.
- **Palette.** |P| = 338 of `P_CAP` = 340. `starship_pool_ceiling` measures 59.81 MB of the 64 MB
  gate, and a P×P pair costs about 318 B. Every scene-11 storyboard colour is already in
  `STORYBOARD`; the ramps are not.
- **Emission.** The only emitted symbol is `▀`: `emit_appearance(ctx, id, fg, bg)` is the single
  `set_appearance` call (`emission_path_shared`). `set_appearance(.., symbol: None, ..)` falls back
  to the character's own `input_symbol`, which is how a glyph is drawn.
- **Test helper.** The `engine_pixels()` test helper asserts that every cell is `▀`.
- **Shake phases.** `World.phases` has 4 slots and all are used (pad, onboard, S5, S9). Reuse
  one; do not enlarge it or draw more RNG in `World::new`.
- **Inputs.** The default text (`omarchy-screensaver/assets/screensaver.txt` = test fixture
  `tests/fixtures/starship_input.txt`) has 13 distinct non-space symbols. The user's branding file
  has 3 symbols (`▄█▀`, an 81×10 logo).

**Decisions (user, 2026-11-16):**
- The branding text uses a **reverse dissolve** in the loop fade: each letter steps back down to
  the scene colour and dissolves into the scene, in reverse reveal order. The storyboard's
  fg → bg fade is not used. That keeps the text colours to a small bounded set (memory) and allows
  a finer plate. It is a recorded deviation from storyboard §3.3; the end frame and the no-flash
  guarantee are unchanged.
- **Supported input scope: a 10,240 appearance budget.** The limit and the overflow behaviour
  are documented explicitly. The measured ceiling must stay ≤ 64 MB, and the fade checks are
  foreground-aware.
  - The budget is **combined**: it counts the engine's own default visual per distinct input
    symbol (`Animation::new` → `CharacterVisual::interned`, `engine/animation.rs:594–605`) as well
    as the glyph appearances.
  - So every symbol is revealed for up to **5,119** distinct non-space symbols. That matches the
    approved 5,120 scope and covers every input that fits a 1080p screen (4,521 cells).
  - Overflow degrades gradually (below). The ceiling is measured for the maximum supported input
    and for a full-grid overflow.

Review findings addressed (2026-11-16):
- **(high) Symbol limit.** The earlier draft dropped symbols past 56, which breaks §3's ≥ 95 %
  rule for more than ~59 symbols. Now: a tier ladder keeps every symbol visible up to 5,119 (combined
  budget, see the memory finding). A
  strict guarantee for every input cannot exist under a fixed memory bound: each distinct visible
  symbol needs at least one retained appearance. So the scope is set, and the overflow is defined
  and documented.
- **(medium) Glyph fade verification.** The glyph now enters and leaves through an approach path
  from the flat plate state `▀`(g, g) (see the handoff finding), instead of jumping from a fixed
  `#6e6c66`. The
  tests read the engine's real (symbol, fg, bg) per cell and bound foreground steps and on/off
  switches directly. The bg-only representation is kept only for scene metrics.
- **(medium) Background handoff.** A glyph at fg == bg was still a flat plate cell, up to ~96 RGB
  units from the scene restored next tick (for example T6's single plate against the opening sky
  `#1e3d4e`). Now the handoff runs through **`▀` blend states**: the cell goes from the scene's own
  two half-block pixels to the plate colour g as `▀` pairs, which are P×P pairs and cost no extra
  memory. Only then does it switch to the glyph. `▀`(g, g) and an invisible glyph look identical,
  so that switch moves no pixel. This is tested in coarse tiers and over contrasting regions.
- **(medium) Memory ceiling coverage.** A 512-symbol saturation cannot prove the ceiling for larger
  inputs: the engine interns a default visual per distinct input symbol, and a bigger input adds
  scheduling and input bookkeeping.
  - The budget now includes those default visuals.
  - `starship_pool_ceiling` runs one **fresh process per case**: the default text, the T0 maximum,
    the T4 saturation, the maximum supported input (5,119 symbols), and a full-grid 4K overflow
    (18,358 distinct symbols).
  - Each case includes the rebuild overlap and its retained appearance sets, with the same 64 MB
    gate.
- **(medium) Discrete fade endpoints.** `round(p·last)` did not pin the first or last active tick to
  the invisible state. Now the state index is tick-aligned: it changes by ≤ 1 per tick, it is the
  scene state (0) on the first and last active tick, and it still reaches hold and completion on
  schedule at 60 and 120 fps. This is tested with non-aligned starts and ends, including
  start = 58.91875.

## Design: bounded branding appearances

A glyph cell's appearance is (its input symbol, fg, bg), all from P. Every reachable glyph
(fg, bg) pair comes from a fixed, seed-independent set per tier.

- **F**, the text ramp, has 8 entries: `#6e6c66` → `#afaca3` → `#f3efe6`. They come from
  `RAMPS_TEXT`, so every step is an exact P member. Hold is always `#f3efe6`.
- **G**, the plate set, is a deterministic order over P (a linear nearest search over ≤ 48 entries,
  no LUT tables):
  - It is a greedy farthest-point order over the candidates `{p ∈ P : luma(p) ≤ 0.60, p within 32
    of a scene-1 or scene-11 colour (their `STORYBOARD` entries, `RAMPS_S1`, `RAMPS_S11`) or of a
    grey}`. It is seeded by the entry nearest `#6e6c66` (luma ≤ 0.50), so every prefix has a
    capped entry.
  - A tier's G is a prefix.
  - Two lookups: `nearest(G, c)` and `nearest_capped(G, c)` (only the entries with luma ≤ 0.50).
    Hold uses the capped one, which gives contrast ≥ 0.938 − 0.50 = 0.438 **by construction**.
- **Cell states** (per glyph cell, given its composited pixels `top`, `bottom`, their mean c and
  the current plate g):

  | s | Drawn as | Pairs it can emit |
  |---|---|---|
  | 0 | the scene: `▀`(top, bottom) | P×P (already budgeted) |
  | 1 … B (B = 6) | `▀`(nearest_P(lerp(top, g, s/B)), nearest_P(lerp(bottom, g, s/B))). s = B is `▀`(g, g), a flat cell in the plate colour | P×P (no extra memory) |
  | B+1 … B+m | glyph (q_j(g), g), q_j(g) = nearest_P(lerp(g, F_t[0], j/(m+1))) | m·|G| per symbol |
  | B+m+1 … S | glyph (F_t[i], g), up to `#f3efe6` (hold) | |F_t|·|G| per symbol |

  - g = `nearest(G_t, bg_raw)`, with bg_raw = c·(1 + cap_w·(min(1, 0.48/luma(c)) − 1)). cap_w ramps
    0 → 1 over the glyph states (0 in the `▀` states). At hold, g = `nearest_capped`.
  - The `▀`(g, g) → glyph(q₁, g) switch keeps bg = g, so only the glyph's strokes change, by one
    path step.
  - Reveal walks s up and the dissolve walks it down.
  - So a symbol costs **c = (|F_t| + m)·|G_t|** appearances. The handoff costs nothing extra.
- **Tick-aligned state index.**
  - At tick i (time t = i·dt) of a window [start, start + T), with i₀ = the first tick with
    t ≥ start:
    - reveal: `s(i) = min(⌊S·(t − start)/T⌋, i − i₀, S)`;
    - dissolve: `s(i) = min(⌊S·(end − t)/T⌋, i_last − i, S)`, with i_last = the last tick with
      t < end.
  - So s changes by ≤ 1 per tick at any frame rate; s = 0 (the scene) on the first and last active
    tick; and, because S ≤ T/dt at 60 and 120 fps, s reaches S on schedule.
  - T = 0.30 s (S = 18 for T0 = 18 ticks at 60 fps).
  - starts ∈ [58.0, 59.18], so the latest hold is ≤ 59.18 + 0.30 + 1/60 < 59.5.
  - The dissolve begins at `d = 63.4 − (start − 58)·0.9/1.18` ∈ [62.5, 63.4] and ends by 63.7. Every
    cell is the plain scene from 63.7.
  - These are pure functions of (slot, tick, dt), so `--start-at` stays exact.
- **Tier ladder** (`SYMBOL_BUDGET = C = 10_240`). With n_d distinct input symbols (space
  included: the engine's default visuals) and n of them non-space, the tier is the first row with
  `n_d + n·c ≤ C`. The max-n column assumes n_d = n + 1.

  | Tier | F_t | m | G | c / symbol | max n | per-tick fg step ≤ 48 |
  |---|---|---|---|---|---|---|
  | T0 | 8 | 4 | 48 | 576 | 17 | guaranteed (tested) |
  | T1 | 8 | 4 | 24 | 288 | 35 | guaranteed (tested) |
  | T2 | 8 | 4 | 12 | 144 | 70 | guaranteed (tested) |
  | T3 | 6 | 2 | 8 | 64 | 157 | coarser |
  | T4 | 4 | 1 | 4 | 20 | 487 | coarser |
  | T5 | 2 | 0 | 2 | 4 | 2 047 | coarser |
  | T6 | 1 | 0 | 1 | 1 | 5 119 | coarser |

  - F_t is an evenly spaced subset of F that keeps both ends (T6 = {`#f3efe6`}).
  - The **background handoff bound holds in every tier**: each `▀` blend step moves a pixel by
    ≤ |pixel − g|/6 + quantisation. Coarse tiers only have larger *foreground* steps, between glyph
    states.
  - **Overflow** (`n_d + n > C`): the k = max(0, C − n_d) most frequent symbols (ties by first
    occurrence) are drawn at T6, and the rest stay `▀` scene cells. The visible share degrades
    gradually: 5 200 equally frequent symbols still show 5 039 (96.9 %). With n_d ≥ C (for example
    a full 4K grid of distinct symbols) no glyph is drawn, because the engine's own default visuals
    already use the budget. ≥ 95 % visibility is guaranteed only within the scope. This is
    documented.
  - The default text (13 symbols) and the user's logo (3) are T0.
- **Bound.** For any input, seed or loop count, the effect's glyph appearances plus the engine's
  per-symbol defaults are ≤ max(C, n_d). Inputs with n_d > C are pure engine cost, the same as any
  effect run on that input; the effect adds 0.
- **Memory target.** |P| ≤ 330 (P×P about 1.7 MB below today's) ≈ 58.1 MB, plus 10 240 × ~318 B
  ≈ 3.3 MB, ≈ 61.4 MB. A full 4K grid of distinct symbols adds 18 358 engine defaults
  (~200–318 B each, ≈ 3.7–5.8 MB) on top of 58.1.
  - `starship_pool_ceiling` measures every case and is the authority.
  - If a case exceeds 64 MB: first trim P (each entry ≈ 0.21 MB of P×P), then lower C. A lower C
    shrinks the scope.
  - If no C keeps the scope ≥ 4 521 symbols (a full 1080p screen) under 64 MB, **stop and ask the
    user**.

## Steps

### Pre-phase (risk mitigations)

1. [palette_budget] Make room in the palette before writing any scene, in `palette.rs`:
   - Remove the coverage cube (`CUBE_LEVELS`, 27 entries). Remove the placeholder: the `PLACEHOLDER`
     const, `0xff00ff` in `STORYBOARD`, and `scenes::draw_placeholder`. Its test assertions are
     replaced in step 6.
   - Add `RAMPS_S11` (≤ 14 new entries). The starting set:
     - `aaa197→c3b8ac` 4 (sky to light cloud);
     - `a8a69e→9f9c94` 3;
     - `635b4d→4b483d` 4 (ground);
     - `2d2c22→37352b` 3 (lattice);
     - `9a8d7c→c7bbab` 5 (steel);
     - `c4bcb0→afaaa1` 3 and `c8bcad→9e9786` 4 (steam);
     - `56544a→a3a39b` 5 (11d sea/sky).
     Trim steps if over the budget.
   - Add `RAMPS_TEXT`: `6e6c66→afaca3` 3 and `afaca3→f3efe6` 6 (F = 8 entries).
   - Append both to `ALL_RAMPS`. Update the module doc's budget numbers.
   - Gate before continuing:
     - `palette_cap_and_constancy`, `palette_error_synthetic`, `palette_error_real_frames`;
     - `signatures_1080`, `signatures_4k` (scenes 1–10 unchanged within tolerance);
     - `stress_changes_every_cell` (it uses palette halves, not the cube);
     - `cargo test --release --test starship_pool_ceiling`.
   - Record |P|, the palette errors and the ceiling. If removing the cube breaks a palette-error
     bound, keep a 2-level cube (8 entries) and trim ramp steps instead.
2. [text_bound_ceiling] Before the branding scene, write the bounded text path and saturate it in
   the ceiling test.
   - `src/effects/starship/text.rs` (new, with the module doc stating the supported scope and the
     overflow rule):
     - `SYMBOL_BUDGET`, `HANDOFF_STATES = 6`,
       `TIERS: [Tier { f, m, g }; 7]`;
     - `plan_for(n_distinct, n_nonspace) -> TextPlan { tier, k_symbols }`;
     - `plate() -> &'static [PalIdx]` (the full G order) and `text_fg(tier) -> &[PalIdx]`;
     - `cell_state(tier, s, top, bottom, g) -> CellDraw::{HalfBlock(fg, bg), Glyph(fg, bg)}`
       (the state table above);
     - `state_index(window, tick, dt, S) -> u8` (the tick-aligned rule);
     - `reachable_pairs(tier) -> Vec<(PalIdx, PalIdx)>` (glyph pairs only; `▀` handoff pairs are P×P);
     - `glyph_symbols(symbol_counts, k) -> Vec<String>` (all of them, or the k most frequent);
     - `text_appearance_bound(n_distinct, n_nonspace) -> usize`.
   - `mod.rs`:
     - `pub enum Glyph { HalfBlock, Input }`;
     - `emit_appearance(ctx, id, glyph, fg, bg)` passes `Some(HALF_BLOCK)` or `None` (the
       character's own `input_symbol`). It stays the only `set_appearance` call.
     - Existing callers pass `Glyph::HalfBlock`.
     - Glyph emission `debug_assert!`s that (fg, bg) is in `reachable_pairs(tier)`.
   - `tests/starship_pool_ceiling.rs` becomes a case runner. `main()` re-executes itself
     (`std::env::current_exe()` with `STARSHIP_CEILING_CASE=<name>`) once per case, so **each case
     runs in a fresh process** with an empty thread-local visual pool. It fails if any child fails.
   - Every case runs at the 4K grid (274×67) and does the same steps:
     - build the old instance from the case's input;
     - emit P×P, then every glyph symbol × `reachable_pairs(tier)` through
       `emit_appearance(.., Glyph::Input, ..)` on a character of that symbol;
     - play to the end (the buffers are released);
     - build the replacement while the old one still exists, and play 2 s;
     - re-emit everything on it (regrowth 0).
   - Inputs are generated in the test (not files): single-width Private Use Area symbols, U+E000…
     and, past 6 400, PUA-A U+F0000….

     | Case | Input | Tier / k | What it bounds |
     |---|---|---|---|
     | `fixture` | `tests/fixtures/starship_input.txt` (13 symbols) | T0 | the real default |
     | `t0_max` | 17 symbols | T0 | the full F × path × G set |
     | `t4_saturate` | 487 symbols | T4 (10 227 + 1) | the earlier saturation case, kept |
     | `max_supported` | 5 119 symbols, once each | T6 | the largest fully revealed input |
     | `overflow_full_grid` | 18 358 distinct symbols filling the 4K grid | k = 0 | the engine's own per-symbol cost, with no glyphs |

   - Each case reports peak MB, the model and the ratio, and asserts:
     - `distinct_visuals == |P|² + (glyph pairs not in P×P) + n_d` (the engine defaults; the
       `overflow_full_grid` case confirms the effect adds 0);
     - regrowth 0;
     - **peak ≤ 64 MB**;
     - ratio ≤ 1.25.
   - The analytic model gains the terms `n_d × default-visual cost` and `glyph pairs × visual cost`,
     plus the text schedule (`Vec<GlyphSlot>`).
   - Record every case's MB in the plan notes.
   - If ttfx does not lay PUA out one per cell, use Latin Extended/Cyrillic/Braille single-width
     symbols where the count allows (≤ ~1 200), and generate the large cases from PUA-A after
     checking its layout. If neither works, state that in the notes and ask the user before claiming
     the large-n bound.
   - Unit tests (`tests/starship.rs`):
     - `text_appearance_bound(n_d, n) + n_d ≤ max(C, n_d)` for every n_d in 0..=20_000 (n = n_d − 1
       and n = n_d);
     - `plan_for` matches the table at every boundary (17/18, 35/36, 70/71, 157/158, 487/488,
       2047/2048, 5119/5120) and gives k = C − n_d in overflow (0 when n_d ≥ C);
     - `glyph_symbols` keeps every symbol when k ≥ n, else the k most frequent (ties by first
       occurrence);
     - `state_index` over 2 000 non-aligned windows per frame rate (60 and 120 fps, random start
       offsets plus the review's start = 58.91875 and its dissolve end), at every tick:
       - |Δs| ≤ 1;
       - s = 0 on the first and last active tick and outside the window;
       - s = S by start + T + dt (≤ 59.5 for every start in [58.0, 59.18]);
       - s = 0 by the window's end;
       - the dissolve of every start ends ≤ 63.7;
     - G ⊂ P and every prefix has a luma ≤ 0.50 entry;
     - `reachable_pairs(t).len() ≤ c(t)`;
     - `cell_state`: s = 0 equals the plain `▀` path; s = B is `▀`(g, g); s = B+1 has bg = g; every
       glyph pair is in `reachable_pairs`; the last state is (`#f3efe6`, capped g); consecutive glyph
       fg steps are ≤ 48 for T0–T2;
     - a plate quantisation error test on real composited text-box colours (the fixture's text
       cells at 59.5, 61.0, 62.5, 63.0): mean ≤ 10 and p99 ≤ 28. Tune G's candidate rule if not.

### 1. Scene 11: `scenes/catch.rs` (45–58 s, storyboard §2.9)

Four sub-shots, hard cuts between them (the pool is already cleared by `pool_event`). Public
helpers for tests:

- `tower_top_11b(t) -> f64`;
- `arm_angle(t) -> f64`;
- `arms(t, aspect) -> [(pivot, tip); 2]`;
- `ship_11b(aspect) -> (x0, x1, y0, y1)`.

**11a wide (45–47):**
- Overcast sky in the top 45 %: a `vstops` of `#c3b8ac` light cloud top → `#aaa197` →
  `#a8a69e`, with noise2 cloud mottling (some pixels with luma > 0.70: the 11a signature needs
  bright ≥ 8 %).
- Horizon at v 0.50. Flat brown ground below: `#635b4d`/`#4b483d` bands with noise (signature
  `#6a6054` 33 % and `#524c3e` 22 %).
- Two towers at u 0.48 (0.22 H tall) and 0.65 (0.20 H), 0.025 H wide, `#2d2c22`, standing on the
  horizon.
- The ship: a dark 0.04 H streak at (0.52, 0.22), descending 0.02 H/s.
- Exhaust 200/s, life 0.5, 0.10 H/s down, size 1, `#f3d592→#e2af7b`, drag 2.0.

**11b descent and catch (47–51.5):**
- The tracking camera holds the ship at (0.50, 0.25): a steel cylinder 0.35 H long and
  0.35/5.8 H wide (`#9a8d7c` body, `#c7bbab` lit side), with flaps near the top and the bottom.
  The flame is 0.05 H (`#f3d592`/`#e2af7b`).
- Engine flame 800/s, life 0.4, 0.3 H/s down ±15°, size 1→2, drag 3.0.
- Tower top (v):
  - linear from 1.10 at 47.0 to 0.449 at 49.0;
  - then `CubicBezier(0.3, 0.866, 0, 1.078)` to 0.30 over 49.0–50.32. The overshoot dips to
    about 0.288 and returns.
  - 0.449 makes the speed continuous at 49.0: the linear speed equals the bezier's initial
    slope 0.866/0.3 × (0.449 − 0.30)/1.32.
- The lattice is 0.12 H wide with 0.05 H bays and X braces, `#2d2c22`/`#37352b`. The tower is
  placed so that its front edge is 0.20·cos 5° H from the ship's near side.
- Chopstick arms:
  - Both pivot at the tower's top-front, 0.20 H long.
  - The angle is ±35° from horizontal until 50.3, then `OutCubic` to ±5° at 51.3. Tips point
    toward the ship.
  - At 51.3 the tips touch the hull, so they close "around the ship".
- Steam along the tower's lower half: 600/s, life 3, 0.05 H/s up, size 2→4,
  `#c4bcb0→#afaaa1`, drag 0.5, buoyancy −0.02 (`spawn_area` over the tower's lower half).
- The sky gradient and a low ground strip are tuned so that `#9f9c94` covers 66 %, `#ada79e`
  58 % and `#2d2c22` 16 % at 49.3.

**11c top-down (51.5–54):**
- Camera zoom 1.00 → 1.05, `Linear`, about the centre.
- Sandy ground `#9a8d7c`-family, with a water edge on the right.
- The ship lies vertically over u 0.38–0.62, v 0–0.80: a steel body `#9a8d7c`/`#c7bbab` with
  lengthwise panel lines, and flaps at both sides of its top.
- Two dark lattice diagonals (`#2f2e2b`/`#2d2c22`) come from the bottom-left and bottom-right
  corners and meet under the ship.
- Steam 300/s, life 3, 0.03 H/s radially out from under the ship (spawned around the ship's
  centre, full circle), `#c8bcad→#9e9786`.

**11d wide caught (54–58):**
- Static camera with shake 0.001 H at 3 Hz (`phases[0]`).
- Sky in the top 30 % (`#a3a39b` family), then a sea band, then flat ground `#56544a` with
  lighter paths (noise lines).
- The tower at u 0.67, v 0.20–0.75, 0.06 H wide (`#37352b`), with the ship held beside it near
  the top (closed arms visible). A distant tower at u 0.85, 0.10 H.
- Steam at the tower base (0.67, 0.75): 300/s, life 4, 0.04 H/s up ±20°, size 2→5,
  `#c7c0b4→#afaca3`, drag 0.4, buoyancy −0.02.
- The branding smoke layer (step 2) is drawn on top from 57.5.

**Plumbing in `scenes/mod.rs`:**
- New `Slot`s: `S11Exhaust, S11Flame, S11Steam, S11SteamTop, S11SteamBase, BSmoke`;
  `SLOTS = 22`.
- `pub mod catch; pub mod branding;`.
- `World::step`/`draw` get explicit arms for **every** `SceneId`, with no `_` arm. That makes "no
  placeholder" a compile-time property.

### 2. Branding B: `scenes/branding.rs` (58–64 s, storyboard §3) and the text overlay

**World state:**
- `World::set_text(cells: Vec<(f64, f64)>)` is called from `Starship::build` with the (u, v)
  centre of every glyph cell, before `advance_to`.
- World keeps `text: Vec<TextSlot { u, v, start, dissolve }>` and the text bbox: the cells' extent
  ± 2 cells. With no glyph cells it falls back to u 0.39–0.61, v 0.42–0.58.

**Smoke (step and draw):**
- `branding::step` (scene B) runs the 11d steam slot's successor `BSmoke`:
  - the rate ramps 300 → 800/s over 58.0–58.5;
  - `spawn_area` over the bbox, life 4, 0.03 H/s up ±20°, size 2→5, `#c7c0b4→#afaca3`,
    drag 0.4, buoyancy −0.01;
  - it stops at 62.5.
  - The peak is about 3 200, counted with 11d's decaying steam: 1200·(1 − x/4) + 800x.
- `branding::draw_smoke(world, t, buf)`:
  - 12 billow discs laid out over the bbox (fixed fractional offsets, radius ∝ bbox height,
    ≥ 0.08 H);
  - each starts growing at 57.5 + j·0.08 (`OutCubic` over 1.2 s) and drifts up 0.03 H/s;
  - the alpha eases to 0.6 over 59.5–60.5 (the smoke "thins").
  - Drawn by `catch::draw` for t ≥ 57.5 and by `branding::draw`. B's draw is
    `catch::draw_11d(world, t)` + `draw_smoke` + the particles of owners S11 and B. 11d → B is
    continuous: no pool clear, same picture.
  - Starting at 57.5 (not 58.0) is a recorded deviation. Without it the smoke density at 58.0 is
    zero over the text and the density ranking would be random.

**Reveal ranking** (in `World::step` on the tick that crosses 58.0):
- density_i = (live S11/B particles inside the cell rect expanded by one cell) + 4 × (billow
  coverage at the cell at 58.0).
- Draw one `rng.random()` per cell (always N draws).
- Sort by density descending, ties by the random draw. Rank r → `start = 58 + 1.18·OutCubic(r/(N−1))`
  (58 when N = 1), which lies in [58, 59.18]. The storyboard's [58, 59.25] still holds; its
  0.25 s fade becomes 0.30 s to fit the handoff states.
- `dissolve = 63.4 − (start − 58)·0.9/1.18`, which lies in [62.5, 63.4]: reverse order, every
  dissolve done by 63.7.
- `--start-at` stays simulation-exact (computed in `step`).

**Glyph state** (pure: `branding::state(slot, tick, dt, tier) -> (s, cap_w)`):
- Before the reveal window and after the dissolve window: s = 0 (the plain scene path).
- Reveal window [start, start + 0.30): s by `text::state_index` (ascending).
- Hold until `dissolve`: s = S, cap_w = 1.
- Dissolve window [dissolve, dissolve + 0.30): s by `text::state_index` (descending).
- cap_w = clamp((s − B)/(S − B), 0, 1).

**Emission** (in `Starship::emit`, after compose):
- For a glyph cell with s > 0, compute top, bottom, c, bg_raw and g as in the design.
- Draw `text::cell_state(tier, s, top, bottom, g)`:
  - `HalfBlock(fg, bg)` goes through the normal `▀` shadow key and visual cache;
  - `Glyph(fg, g)` uses the shadow key `GLYPH_BIT (1<<31) | fg<<16 | g`, and on a change calls
    `emit_appearance(.., Glyph::Input, fg, g)` (no cache; glyph cells are few).
- s = 0 is exactly the normal path, so the scene ↔ glyph handoff is always a `▀` blend step.

**Test hooks:**
- `Starship::glyph_slots() -> Vec<GlyphSlot { col, row, start, dissolve, density }>` (the
  schedule) and `Starship::text_tier()`.
- `pixels()` keeps reporting a glyph cell as its bg in both halves, **for the scene metrics only**
  (signatures, palette error).
- Tests get a new `engine_cells()` helper that reads the engine's real per-cell
  `(symbol, fg, bg)`. Every branding, fade and loop check uses it.
- A glyph-aware `cell_pixels()` view, for the frame-distance means:
  - `▀` → (fg, bg), `▄` → (bg, fg), `█` → (fg, fg);
  - any other glyph → each half = bg + 0.25·(fg − bg), an ink estimate.

### 3. Pacing against the animatic

- `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
  (run in a tmux pane, captured), with `EFFECT_ARGS="--start-at 45"` and `"--start-at 57"`.
- Compare with `tools/frames2text/frames2text.py play`, using the §1.8 mapping (11a–11d factors
  1.785/1.736/1.976/1.883).
- At 120 fps: `make headless EFFECT=starship FRAMES=7800` (expect `non_space` > 0), plus the bench.
- Layout tuning against the reference frames uses scratch block maps of `.refs/starship/09_catch/`
  (signature frames k 10, 42, 76, 112). Only hand-set numbers go into the source. Record every
  deviation from the storyboard prose in the Final Implementation Notes and in storyboard §2.9/§3.

### 4. Full-timeline perf

- **Before**: once scenes 11 and B draw (before any tuning), take pinned runs of
  `taskset -c 0-7 make perf EFFECT=starship RES=1080p` and `RES=4k` (`PERF_SECONDS=65`), and note
  the load average.
- Acceptance:
  - p99 < 8.3 ms and max < 16 ms at 4K (and at 1080p);
  - no run of ≥ 2 consecutive ticks over 8.3 ms.
- Map the 10 slowest ticks to scenes by their second. For hot spots, profile with
  `perf record` on the bench, or `--start-at` plus the bench.
- Likely suspects:
  - the cuts at 47/51.5/54 (full-frame change);
  - the B smoke (about 3 200 discs up to 5 px × grid scale, plus 12 billows);
  - the per-pixel noise in 11a/11d.
- Fix order, smallest visual cost first:
  - precompute static per-pixel noise layers once per sub-shot, into a scratch `Pixbuf` allocated
    in `build`;
  - draw particles under 2 px as single pixels;
  - draw the billows at half resolution only if still needed.
- Record the before and after numbers in the plan notes. Re-run `TTFX_STARSHIP_STRESS=1 make perf`
  (expected unchanged, the 4K stress exception).

### 5. Docs and cleanup

- `aidocs/starship/storyboard.md`:
  - §3: the reverse dissolve (user decision); the `▀` handoff and the approach path (the reveal
    starts from the scene's own pixels, a refinement of "from the smoke colour"); 0.30 s fades with
    starts in [58.0, 59.18] and dissolves done by 63.7; the billows from 57.5;
  - §3, a new **Supported input** paragraph:
    - up to 5 119 distinct non-space symbols are all revealed;
    - the combined budget C (engine defaults + glyph appearances) and the tier ladder;
    - a smooth background handoff in every tier; smooth (≤ 48 per tick) foreground steps for ≤ 70
      symbols, coarser above;
    - the gradual overflow rule, its effect on the ≥ 95 % line, and the no-glyph full-grid case;
    - the measured ceilings;
  - §2.9: any tuned layout deviations;
  - §3's text signature: unchanged numbers.
- `aidocs/testing/manual_testing.md`: the `--start-at` times 45, 47, 51.5, 54, 57.5.
- `palette.rs` / `mod.rs` / `text.rs` doc comments: the P budget, glyph cells, `Glyph`, and the
  same supported-scope and overflow statement.

### 6. Tests: `ttfx/tests/starship.rs`

- **Signatures.** `SIGS` rows for 11a @46.0, 11b @49.3, 11c @52.7 and 11d @56.0, exactly as §4.
  `signatures_1080` covers all 15 rows; `signatures_4k` adds 11b and 11d.
- **No placeholder.** Replace `PLACEHOLDER_SCENES`/`placeholders_listed_honestly` with
  `no_placeholder_anywhere`: a full 60 fps run, every 2nd tick, where no emitted pixel is within 48
  of `#ff00ff`. Drop the `PLACEHOLDER` assertion from `palette_cap_and_constancy`.
- **Cuts and motion.**
  - `cuts_are_cuts`: add 47.0, 51.5 and 54.0. Measure with `calibrate_distances`; if one lands under
    25, add a changed-pixel-fraction criterion and document it.
  - `hard_cuts_clear_the_pool`: add (47, S11), (51.5, S11), (54, S11).
  - `implemented_shots_move`: add (45.5, 46.0), (48.0, 48.5), (52.0, 52.5), (55.0, 55.5) and
    (60.0, 60.5) (smoke drift).
  - New `continuous_11d_b_keeps_the_world`: S11 particles survive 58.0 and the step across it is
    < `STEP_LIMIT`.
- **Catch geometry** (`catch_geometry`, over `ASPECTS`):
  - the tower top is monotonic to its overshoot minimum, then rests at 0.30 ± 0.002 from 50.33;
  - the velocity is continuous at 49.0;
  - the arm angle is 35° until 50.3, monotonic down to 5° at 51.3;
  - at 51.3 both tips are within one pixel of the hull side;
  - no tip crosses the ship axis.
- **Branding** (`branding_reveal`, fixture text, 60 and 120 fps), all read through
  `engine_cells()`:
  - no glyph cells before 58.0;
  - every start is in [58.0, 59.18] (inside the storyboard's [58.0, 59.25]);
  - every glyph is in its hold state (fg `#f3efe6`) at 59.5;
  - at 61.0 ≥ 95 % of the non-space input characters show their own symbol with luma contrast
    ≥ 0.35. All of them should, at ≥ 0.438 by construction;
  - starts are non-increasing in density;
  - fill characters never become glyphs.
- **Foreground-aware fades and background handoff** (`glyph_fades_are_continuous`, every tick
  on 58.0–59.6 and 62.4–64.0, at 60 and 120 fps), per glyph cell from `engine_cells()`.
  - Handoff (all tiers):
    - consecutive ticks in `▀` states move each half-block pixel by ≤ 48;
    - a `▀` ↔ glyph switch happens only between `▀`(g, g) and a glyph with bg = g (exact
      equality);
    - no cell ever goes from a glyph straight to a non-flat `▀`.
  - Foreground (T0–T2): |fg_t − fg_{t−1}| ≤ 48 between glyph states.
  - The glyph-aware `cell_pixels()` mean step is < `STEP_LIMIT`.
  - Runs on:
    - the default fixture (T0);
    - a **wide contrasting** synthetic input (110 × 12 cells of mixed letters and `█▀▄`, T0). Its
      bbox spans 11d's sky, horizon, ground and tower and, in the loop fade, scene 1's sky, tower
      and stack;
    - the tier inputs below at T2, T5 and T6.
  - Mutation checks during implementation: (a) the old fixed-`#6e6c66` ending, (b) dropping the `▀`
    blend states, and (c) `round(p·last)` sampling must each fail this test.
- **Symbol tiers** (`branding_symbol_tiers`):
  - Generated inputs of single-width PUA symbols (each once, the worst case for the 95 % line):
    n = 60 (T2, crossing the old 56 limit), 72 (T3), 488 (T5), and 2 048 (T6, at 4K).
  - Each is played from `--start-at 57.9` through 64.0:
    - at 61.0, 100 % of the non-space characters show their own symbol with contrast ≥ 0.35;
    - the tier matches `plan_for`;
    - the distinct glyph appearances are ≤ `text_appearance_bound(n_d, n)`;
    - the handoff checks above hold at every tick of the reveal and the dissolve.
  - **Overflow:** a generated 5 200-symbol input at 4K. Exactly the k = 5 039 most frequent symbols
    become glyphs (≥ 95 % of the characters), the other cells stay plain `▀`, and the bound holds.
    A full-grid distinct input shows no glyphs (k = 0) and renders the plain scene.
  - If PUA cannot be laid out one per cell, use Latin Extended/Cyrillic/Braille ranges up to
    n = 488, and make n = 2 048 and the overflow unit tests of `plan_for`/`glyph_symbols`. The note
    says so.
- **Loop** (extends `loop_rebuild_is_seamless`, 60 and 120 fps):
  - the rebuilt first frame equals the first frame cell for cell (kept);
  - last → first distance < `STEP_LIMIT` (kept);
  - the last frame has no glyph cells (`engine_cells()`: every symbol is `▀`);
  - the last 0.5 s (63.5–64) is checked tick by tick: glyph-aware step < `STEP_LIMIT`, and no
    glyph from 63.7.
- **Smooth events.** `events_step_smoothly` (120 fps) adds the tower settle (49.0–50.4), the arm
  close (50.3–51.3) and the reveal (58.0–59.5).
- **Particle budget.** `particle_budget_holds` adds the scene 11 peak in [1 000, 3 500]
  (storyboard 2 120) and the B peak in [2 000, 4 500] (storyboard 3 200). The max stays below
  `POOL_CAPACITY`.
- **Palette.**
  - `palette_error_synthetic` adds overlay pairs: steam `#c4bcb0` over `#9f9c94`/`#aaa197`, flame
    `#f3d592` over `#9a8d7c`, `#c7c0b4` over `#56544a`.
  - `palette_error_real_frames` covers the new signature times automatically through `SIGS`.
- **Appearance bound.** `emitted_colours_in_palette_and_appearance_bound` counts `▀` pairs plus
  glyph triples from `engine_cells()`, and asserts ≤ |P|² + `text_appearance_bound(n_d, n)`.
- `emission_path_shared` stays at exactly 1 call.

### Post-phase (risk mitigations)

1. [frame_data_guard] Before each commit:
   - review the output of `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` by hand;
   - check that `git status --ignored` shows `.refs/` ignored;
   - commit the synthetic fixtures only (never the user's branding file).

## Verification

- `make check` (both submodules, release), including `starship_pool_ceiling` (≤ 64 MB, the text
  worst case included).
- `make perf EFFECT=starship RES=1080p` and `RES=4k` (pinned): the step 4 acceptance, with the
  before/after numbers recorded.
- `make headless EFFECT=starship FRAMES=7800` runs, with `non_space` > 0 (smoke test only).
- CLI determinism, run twice, then `cmp`:
  `ttfx/target/release/ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt > <scratch>/a.out`
- `make try` at `--start-at 45` and `57`: scene 11 and the reveal are recognisable, and nothing
  is magenta.
- Commits:
  - `git -C omarchy-screensaver checkout Cargo.lock` first;
  - in `ttfx/`: `Add the starship catch scene and branding reveal`, pushed to
    `origin feat/stub-effect`;
  - then in the workspace: `feature: Add the starship catch scene and branding reveal (t1_5)`
    (`git add ttfx aidocs/starship/storyboard.md aidocs/testing/manual_testing.md`).
- The final report states that the on-monitor visual check (manual-verification task t2) is still
  outstanding until a human runs it.

Step 9 (Post-Implementation): archive this child via the workflow. The parent t1 archives once all
5 children are done; t2 (manual verification) does not block it.

## Risk

### Code-health risk: low
- Removing the coverage cube and the placeholder, and adding the scene-11 and text ramps, changes
  how scenes 1–10 quantise (signature drift, palette-error bounds) and the P×P memory. · severity:
  low (residual: addressed by the inline pre-phase palette_budget, which gates on the palette-error,
  signature and ceiling tests before any scene code) · → mitigation: inline pre-phase palette_budget
- The glyph path widens the single emission function and moves the memory bound from |P|² to
  |P|² + text appearances. A mistake would make memory input-unbounded or push the ceiling over the
  64 MB gate (59.81 MB today). · severity: low (residual: addressed by the inline pre-phase
  text_bound_ceiling, which saturates the worst-case text set in the ceiling test before the branding
  scene) · → mitigation: inline pre-phase text_bound_ceiling
- `Starship::emit` (the hot loop) and the `World` dispatch change, and four new modules are added.
  The blast radius stays inside the starship module and follows the t1_3/t1_4 patterns. ·
  severity: low · → mitigation: none needed
- Frame-derived data could leak into commits while tuning against `.refs/`. · severity: low
  (residual: addressed by the inline post-phase frame_data_guard) · → mitigation: inline post-phase
  frame_data_guard

### Goal-achievement risk: medium
- Four new signatures are demanding: 11b's 16 % dark lattice in a tracking shot, and 11a's
  bright ≥ 8 % from an overcast sky. Landing them at 1080p and 4K may take many tuning rounds. ·
  severity: medium · → mitigation: none (tuning loop in step 3)
- At 4K, the B smoke (about 3 200 discs plus 12 billows over the text box) and three new cuts could
  miss p99 < 8.3 / max < 16. The fixes may cost visual fidelity. · severity: medium · → mitigation:
  none (step 4 is the task's own perf work, with a fix order)
- The reverse dissolve, the approach path, the billows starting at 57.5 and the 48-colour plate are
  deviations from the storyboard text. They are user-approved or recorded, but could read as
  missing spec. · severity: low · → mitigation: none (recorded in the storyboard and the notes)
- Inputs above 5 119 distinct symbols cannot all be revealed under the fixed memory bound. This is
  the user-approved budget and scope: documented, with a gradual overflow, and tested at the
  boundary. · severity: low · → mitigation: none (explicit scope; `branding_symbol_tiers`)
- A full 4K grid of distinct symbols carries ~18 k engine default visuals that no effect can avoid,
  so that case could measure over 64 MB even with no glyphs. It is measured in a fresh process;
  the contingency is to trim P, then lower C, and to ask the user if the 1080p-wide scope cannot be
  kept. · severity: medium · → mitigation: inline pre-phase text_bound_ceiling (the fresh-process
  case runner)
- The tick-aligned state rule makes fades lag their schedule below ~60 fps, because the cap is one
  state per tick. Hold and completion are guaranteed at 60 and 120 fps (tested), which covers the
  screensaver (120) and the CLI default (60). · severity: low · → mitigation: none (documented)
- The PUA-based generated inputs depend on ttfx laying out one PUA code point per cell. If not,
  smaller single-width ranges cover up to ~1 200 symbols; the large-n cases then need PUA-A, or the
  user is asked before the large-n bound is claimed. · severity: low · → mitigation: none (fallback stated in step 2)
- The plate quantisation could make the text plate look posterised next to 330-colour neighbours.
  · severity: low · → mitigation: none (plate-error test; G's candidate rule is tunable)

### Planned mitigations
- timing: pre-phase | name: palette_budget | type: chore | priority: high | effort: low | inline_risk: low | added_complexity: low | addresses: palette drift in scenes 1–10; P×P memory | desc: remove the cube and the placeholder, add the scene-11 and text ramps, and pass the palette-error, scene 1–10 signature and starship_pool_ceiling tests before any scene code
- timing: pre-phase | name: text_bound_ceiling | type: test | priority: high | effort: medium | inline_risk: low | added_complexity: low | addresses: an unbounded or over-gate glyph appearance set | desc: the tier ladder (F/G/approach-path sets, ▀ handoff, combined 10 240 budget incl. engine per-symbol defaults, 5 119-symbol scope) and Glyph in emit_appearance; a fresh-process ceiling case runner (fixture, T0 max, T4 saturation, max supported, full-grid overflow) enforces ≤ 64 MB before the branding scene
- timing: post-phase | name: frame_data_guard | type: chore | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into commits | desc: grep the staged diff for large literals, confirm .refs/ is ignored, commit only synthetic fixtures

## Post-Review Changes

### Change Request 1 (2026-11-16 21:40)
- **Requested by user:** four review findings, all confirmed:
  1. Fades ignored `--duration-scale`: the 1-state-per-tick cap made a 0.25 scale miss hold and jump states (37/61 cells late, a 205 RGB fg jump).
  2. Plates were reselected from the moving scene each tick, so emitted colours jumped (fg 86.7, bg 65.9 on a full 4K grid of `A`).
  3. The reveal ranking scanned the whole pool per glyph cell (22 ms on the 58.0 tick for 18 358 glyph cells).
  4. The fade test took glyph mode from the symbol, so `▀` input glyphs skipped their checks.
- **Changes made:**
  1. `text::glyph_state`: a pure storyboard-time schedule. The first and last active ticks are the plain scene, and a tick that would jump across the flat state B shows B. `glyph_state_index_is_tick_aligned` now covers scales 0.25 and 4, and `glyph_fades_are_continuous` adds ×0.25 runs (flat-switch checks and visibility right after 59.5).
  2. The plate is simulation state (`World::step_plates`, `text::step_plate`). It reads a still, particle-free branding scene (`branding::draw_plate_source`, static base cached) and moves by at most 48 RGB per tick through G's capped entries. It is held while the cell blends or is on its path. G is now anchored on the branding tones only, plus their halfway mixes. New test `glyph_fades_full_grid` (137×33 at 60 fps, 274×67 at 120 fps).
  3. `branding::rank` bins the smoke into a per-cell grid (allocated in `set_text`) in one pass; the RNG draw per cell is unchanged. A settled plate is re-checked only after its source mean moves by more than 2. Glyph visuals get a cache (as `▀`'s). `omarchy-screensaver/benches/timeline.rs` gains `SSAVER_BENCH_TEXT`.
  4. `check_glyph_fades` derives glyph mode from the state indices and asserts each cell's symbol separately (own symbol in glyph mode, `▀` otherwise).
- **Files affected:** `ttfx/src/effects/starship/{text.rs, mod.rs, scenes/mod.rs, scenes/branding.rs, scenes/catch.rs}`, `ttfx/tests/starship.rs`, `omarchy-screensaver/benches/timeline.rs`, `aidocs/starship/storyboard.md`, `aidocs/testing/manual_testing.md`.

## Final Implementation Notes
- **Actual work done:**
  - ttfx:
    - `scenes/catch.rs` (scene 11: 11a–11d, `tower_top_11b`, `arm_angle`, `arms`, `ship_11b`, `draw_11d_base`);
    - `scenes/branding.rs` (B: billows from 57.5, smoke emitter, density ranking, still plate source);
    - `text.rs` (bounded glyph cells: text ramp F, plate order G, approach path, tier ladder under a 10 240 combined budget, state schedule, plate stepping);
    - `mod.rs` (`Glyph` in `emit_appearance`, glyph emission with shadow keys and a visual cache, text plan, test hooks `text_plan`, `glyph_cells`, `glyph_symbols`, `glyph_state_of`, `dt`);
    - `scenes/mod.rs` (6 new slots, an exhaustive dispatch with the placeholder removed, text slots, plate stepping);
    - `palette.rs` (cube and placeholder removed, `RAMPS_S11`, `RAMPS_TEXT`, trims, `P_CAP` 320, `ramp_colors`/`rgb_of` public).
  - Tests: 33 → 44 (+4 ignored dev aids), and the ceiling test is now a fresh-process case runner (5 cases).
  - omarchy-screensaver: `SSAVER_BENCH_TEXT` in the timeline bench.
  - Workspace docs: storyboard §2.9 notes and §3 rewritten (reveal, reverse dissolve, plates, supported input); `manual_testing.md` (start times, `--anchor-text c`, bench text, memory/stress notes).
- **Measurements:**
  - **Palette:** |P| 338 → 317. Palette error synthetic mean 4.94 / p99 14.90; real frames mean 3.11 / p99 12.17. Plate error mean 7.68 / p99 9.11.
  - **Ceiling** (4K, rebuild overlap, fresh process each):

    | Case | Ceiling (MB) |
    |---|---|
    | fixture | 58.72 |
    | t0_max | 59.22 |
    | t4_saturate | 59.51 |
    | max_supported | 59.53 |
    | overflow_full_grid | 62.87 |

    Model ratio ≤ 1.036 and regrowth 0 in every case.
  - **Signatures (1080p):**

    | Shot | Near colours | Near-black | Bright |
    |---|---|---|---|
    | 11a | `#b2a99e` 54.8, `#6a6054` 36.7, `#524c3e` 31.5 | 0 | 20.6 |
    | 11b | `#9f9c94` 53.8, `#ada79e` 53.8, `#2d2c22` 17.0 | 0 | 0.9 |
    | 11c | `#9a8d7c` 56.9, `#c7bbab` 33.7, `#2f2e2b` 10.1 | 0 | 16.9 |
    | 11d | `#a3a39b` 51.4, `#56544a` 19.6, `#37352b` 28.6 | 0 | 5.2 |

    4K is within 1 point.
  - **Particles:** max 3 783; scene 11 peak 2 139, B 3 152.
  - **Perf, default text** (`taskset -c 0-7`, load 3–5): 4K p99 3.24 ms, max 7.6–8.3 ms (the rebuild tick at 64.000 s), 0 over 8.3, longest run 0 or 1; 1080p p99 0.76 ms, max 2.22 ms. Slowest ticks: the first and the rebuild render, then the cuts (6, 35, 25, 16, 54, 51.5, 45: 4.4–5.5 ms at 4K). No perf fallback was needed for the default text. 4K stress (10 s): p99 5.80 ms (t1_4: 10.68).
  - **Perf, full 4K grid of `A`** (18 358 glyph cells):
    - effect tick in the branding: p50 2.6 ms, max 3.9 ms (before the fixes p50 8.6, max 16.4; the rank tick was 22 ms);
    - overlay bench, 3 runs at load 3.5–4: two passed (p99 5.60 / 4.72, max 9.81 / 8.57 at the rebuild tick, 1 over, run 1);
    - one did not (p99 7.36, max 14.53 at 62.66 s, 26 over, run 4) at the loop fade start, where every cell changes plus the dissolving glyphs.
    - 1080p full grid: p99 1.78 ms, max 3.36 ms.
  - **Smoke runs:** `make headless EFFECT=starship FRAMES=7800`: `non_space=4800`. The CLI determinism `cmp` is identical. In a tmux 137×34 pane, `--anchor-text c` shows the box and "omarchy" in hold.
- **Deviations from plan:**
  - **Reveal timing:** fades 0.33 s (B = 7 handoff states keep blend steps ≤ 48); starts in [58.0, 59.13]; dissolves in [62.5, 63.37], all done by 63.70.
  - **Plates:** the full cap is applied in every glyph state, with the cap "weight" carried by the `▀` blend. Plates are stepped simulation state from a still, particle-free branding scene (review). G anchors on 11d/smoke tones only.
  - **Tower settle:** its height is derived from ttfx's eased curve at x = 1e-3, about 0.449 (the solver uses a lower linear slope below 1e-4).
  - **Tests:** `events_step_smoothly` gives the tower windows a 5 % changed-fraction floor (a textured lattice moving at sub-pixel speed). The fade test's handoff allowance is 48 + 2 × the cell's own scene change. A `▀` ↔ glyph switch requires a flat neighbour and a plate step ≤ 48, not exact plate equality. The `round(p·last)` mutation is caught by `glyph_state_index_is_tick_aligned`.
  - **Distinct-visuals assertion:** the ceiling test asserts `|P|² + glyph pairs`. The engine's per-symbol defaults are measured (peak and model) but not counted directly: ttfx has no pool-size accessor, and the engine is not modified.
  - **Palette trims:** greys stay 16 (trimming them broke the 1→2 fade endpoint). Trimmed instead: S1 none; S2 `3b6187→4f6271` 6, `3b6187→7b8894` 6, `7b8894→4f6271` 4, `d0b3bd→a692a0` 4; S3 three ramps 8 → 6; S6 `0e448a→477db9` 5.
- **Issues encountered:** the full-grid overflow first measured 65.69 MB at |P| 332 (engine cost: a 16.4 MB build plus 18 k default visuals); trimming P to 317 gives 62.87. The review findings are listed under Post-Review Changes.
- **Key decisions:**
  - one combined budget (engine defaults + glyph appearances), so the bound is a constant for any input;
  - `▀` handoff states cost no memory;
  - the plate is simulation state, which keeps seeks exact;
  - the storyboard is the spec, and every deviation is written into §2.9/§3.
- **Upstream defects identified:** None
- **Notes for sibling tasks:**
  - t2 (the manual on-monitor check) is still outstanding.
  - `make try` needs `--anchor-text c` to show the branding centred as the screensaver does.
  - `SSAVER_BENCH_TEXT=<file>` benches any input.
  - The palette has 3 entries of headroom under `P_CAP` 320 (overflow ceiling 62.87 MB of 64).
