---
priority: medium
risk_code_health: low
risk_goal_achievement: medium
effort: high
depends: [t1_4]
issue_type: feature
status: Done
labels: [effect, screensaver]
gates: [risk_evaluated]
active_gates: [risk_evaluated]
active_gates_filtered: []
active_gates_profile: fast
active_gates_digest: 5892c63ff1b4.681bafac2cb9.d73bba2fc21f
assigned_to: dario-e@beyond-eye.com
anchor: 1
implemented_with: claudecode/opus5_5
created_at: 2026-11-15 09:59
updated_at: 2026-11-16 22:33
completed_at: 2026-11-16 22:33
---

## Context

Child 5 of t1 (the `starship` screensaver effect: a ~60 s procedural animation of the Starship
Flight 15 mission), and the last implementation child. Parent plan:
`aiplans/p1_starship_flight_screensaver.md`. Read the archived t1_3 and t1_4 plans
(`aiplans/archived/p1/`) for the renderer, the test harness and the perf numbers so far.
`aidocs/starship/storyboard.md` is the spec.

This child adds:
- the **catch scene (11)**, the longest scene;
- the **branding reveal** after the catch;
- **perf tuning over the whole timeline**;
- the final test pass, with no placeholders left anywhere.

Settled: 9 scenes, no booster landing. The branding text is revealed after the catch: it forms out
of the smoke, holds ~3 s, then fades into scene 1's opening colours before `next_frame` returns
`None` (the screensaver then rebuilds the effect with the same seed, so it loops). Original ttfx
engine only. No frame-derived data.

## Key Files to Modify

- `ttfx/src/effects/starship/scenes/catch.rs` (or the equivalent) and the timeline wiring.
- The branding reveal: the effect's input characters (`CharacterFilter` with `input_chars`, at
  their real `input_coord`s; the screensaver centre-anchors the text).
- `ttfx/tests/starship.rs`: a signature for scene 11, a branding check, the real loop/no-flash
  assertions (remove any `#[ignore]` t1_3 left), and an empty placeholder list.

## Reference Files for Patterns

- t1_3/t1_4 scenes, primitives and particles.
- `ttfx/src/effects/matrix.rs` / `stub.rs`: how the input characters are handled.
- `omarchy-screensaver/benches/timeline.rs` and `make perf` (t1_3).

## Implementation Plan

1. Scene 11, return and catch:
   - two towers on the coast and an overcast sky;
   - the ship descends on its engines (easing from the t1_1 `anim` fit in the storyboard), with
     exhaust and smoke;
   - the chopstick arms close on the ship;
   - then a top-down close-up of the ship held in the arms.
2. Branding reveal:
   - the input characters appear out of the post-catch smoke (e.g. smoke-density-weighted reveal
     order), using their own symbols in a palette from the storyboard;
   - they hold ~3 s;
   - then everything fades to scene 1's first-frame colours, so the loop restart has no flash.

   Return `None` at the total.
3. Pacing: tune it against the t1_1 animatic. At 60 fps, run
   `make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`. At
   120 fps, run `make headless EFFECT=starship FRAMES=7320` plus the timeline bench.
4. **Full-timeline perf:** run `make perf EFFECT=starship RES=1080p` and `RES=4k`
   (PERF_SECONDS=61, which covers the whole timeline plus the rebuild tick).
   - Acceptance: **p99 tick < 8.3 ms and max < 16 ms at 4K, and no run of ≥ 2 consecutive ticks
     over 8.3 ms** (those runs are catch-up bursts in the overlay).
   - Inspect the 10 slowest ticks: map them to scenes by their timeline second, profile them
     (`perf record` on the bench, or `--start-at` plus the bench), and fix the hot spots.
   - Record the before and after numbers in the plan notes.
5. Final tests:
   - all 9 scenes have signature checks, and no placeholder colour remains anywhere on the timeline;
   - the branding characters are visible during the hold;
   - loop: the rebuilt first frame equals the first run's first frame cell for cell, the
     position-sensitive distance from the last frame to the first frame is under the per-tick
     step limit, and the last 0.5 s is checked tick by tick like a fade.

## Verification Steps

- `make check` passes.
- The `make perf` acceptance above is met at 1080p and 4K.
- `make headless EFFECT=starship FRAMES=7320` runs. It is a smoke test only.
- CLI determinism: run
  `ttfx/target/release/ttfx --ignore-terminal-dimensions --canvas-width 120 --canvas-height 40 --frame-rate 60 --seed 1 starship < omarchy-screensaver/assets/screensaver.txt > <scratch>/a.out`
  twice, then `cmp` the outputs.
- **frame_data_guard** before each commit: run
  `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review it by hand.
  `.refs/` stays ignored.
- Commits: in ttfx, `Add the starship catch scene and branding reveal`, then push. Then in the
  workspace, `feature: Add the starship catch scene and branding reveal (t1_5)` (`git add ttfx`).
- The final report states that the on-monitor visual check (the manual-verification follow-up
  task) is still outstanding until a human runs it.

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_1** id=2026-11-15T10:59:06Z.565a39e63339669b80dded5a from=t1_1 at=2026-11-15T10:59:06Z base=572ad6a5a5f04a6bfb7e0dd03f26560242fa0428 base_branch=main dirty=yes host=omg16
>
> | Advisory: the user said the starship loop may run a few seconds past 60 s if needed (expect roughly
> | 63-65 s; the storyboard in t1_2 fixes the exact total). The verification commands here assume 60 s:
> | `make headless EFFECT=starship FRAMES=7320` and PERF_SECONDS=61. Recompute both from the final
> | total (total x 120 + 120 frames; PERF_SECONDS = total + 1), or use whatever constant t1_3 exposes.

> **✉ note:t1_2** id=2026-11-15T15:48:59Z.31534e50e3b6564f0e143dc9 from=t1_2 from_verified=yes at=2026-11-15T15:48:59Z base=0a42c015f1bee2afddc3320cad0ebd28c541fb0e base_branch=main dirty=no host=omg16
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

> **✉ note:t1_3** id=2026-11-15T21:30:57Z.378ae362617f8f2289dc93d3 from=t1_3 from_verified=yes at=2026-11-15T21:30:57Z base=b35a6054cd70fa4762e4dfd47a45bd22f64909da base_branch=main dirty=no host=omg16
>
> | Advisory, from t1_3 (starship skeleton), as of commit b35a605 (ttfx de82884, omarchy-screensaver e39c449).
> | The full record is the archived plan aiplans/archived/p1/p1_3_starship_effect_skeleton.md ("Notes for sibling tasks").
> | 
> | - Bounded palette: every fg/bg the effect emits must be an entry of the fixed palette P
> |   (ttfx/src/effects/starship/palette.rs); ttfx never frees cell appearances. P_CAP = 340 and
> |   |P| = 317 today, with little headroom (t1_4 needs some too).
> | - Branding: text cells add symbols, so the bound grows to
> |   |P|² + |text symbols| · |fg ramp| · |bg set|. Give the text fg a bounded ramp (e.g. ≤ 16
> |   steps of #afaca3 → #f3efe6), take bg from P after the luma cap (quantise again), and extend
> |   ttfx/tests/starship_pool_ceiling.rs to saturate those appearances too. The gate is ≤ 64 MB
> |   including the rebuild overlap (55.7 MB now). Emit through `emit_appearance` or a sibling that
> |   also takes only palette indices, and keep `emission_path_shared` true.
> | - No `#[ignore]` is left on real assertions. The loop test already runs: the loop fade
> |   (62.5–64.0 → scene 1 at t = 0) is generic in timeline.rs, and B's content replaces only the
> |   placeholder. The only ignored tests are dev aids (palette_preview, calibrate_distances,
> |   dump_frames).
> | - The verification commands are already 64 s-based: PERF_SECONDS defaults to 65 in the
> |   Makefile, and the headless smoke run is `make headless EFFECT=starship FRAMES=7800`.
> | - The plan's `render_scene_only` is `Starship::render_only(scene)` in the code.
> | - Perf: render_delta (omarchy-screensaver) now redraws only changed cells. The 4K timeline
> |   passes with scenes 1–3 (p99 about 2.4 ms unpinned). The every-cell-changes stress
> |   (`TTFX_STARSHIP_STRESS=1`) still misses p99 at 4K, as an accepted exception. On this hybrid
> |   CPU, pin with `taskset -c 0-7` and compare runs taken under the same load.

> **✉ note:t1_4** id=2026-11-16T11:25:59Z.6b90052ecc467edafa194176 from=t1_4 from_verified=yes at=2026-11-16T11:25:59Z base=6a3162487b481f6c84ffe916dbc432dd221eb52c base_branch=main dirty=yes host=omg16
>
> | Advisory, from t1_4 (starship space scenes), as of commit 6a31624 (ttfx 7b8f9a4).
> | The full record is the archived plan aiplans/archived/p1/p1_4_starship_space_scenes.md
> | ("Notes for sibling tasks"). It updates t1_3's note:
> | 
> | - Palette budget is now |P| = 338 of P_CAP = 340: 2 entries left, not ~23. t1_4 already
> |   shrank the coverage cube from 4x4x4 to 3x3x3 to fit the space ramps. Scene 11 and the
> |   branding ramps need room: the 3x3x3 cube (27 entries) is the last obvious prune, otherwise
> |   trim ramp steps. starship_pool_ceiling now measures 59.81 MB of 64 (it was 55.7), so the
> |   branding text appearances have less memory headroom than t1_3's note assumed.
> | - Signature "near" (RGB distance <= 48) overlaps: before choosing a scene's tones, check the
> |   pairwise distances of its signature colours. Any tone within 48 of two of them counts for
> |   both (e.g. #0d0e15/#1f2636/#313a56 and #110d16/#2d2633 were all mutually "near").
> | - At 1080p the 0.03 H hex tiles are about 2 px, so almost every hull pixel is a seam pixel.
> |   space::tiled_hull takes two seam tones, and those decide how a hull counts.
> | - Geometry: use space::circle_through (it returns the radius actually used) or
> |   space::arc_by_depth for circles defined by points, and test on the ASPECTS list in
> |   tests/starship.rs (it includes a 274x33 ultrawide).
> | - Shared helpers: space::glare(.., solid, ..) gives blown-out light sources;
> |   World::spawn_area handles area emitters; Starship::world() plus a scene's draw_opts gives
> |   with/without render diffs.
> | - Perf: scene cuts are the slowest ticks (full-frame change, about 5-6.5 ms at 4K pinned
> |   under load). Also, p1_5's "FRAMES=7320" is stale: the headless smoke run is FRAMES=7800.

> **👁 note:read** id=2026-11-16T11:42:32Z.022e185aac42343e73377c73 by=t1_5 at=2026-11-16T11:42:32Z mode=explicit ids=2026-11-15T10:59:06Z.565a39e63339669b80dded5a,2026-11-15T15:48:59Z.31534e50e3b6564f0e143dc9,2026-11-15T21:30:57Z.378ae362617f8f2289dc93d3,2026-11-16T11:25:59Z.6b90052ecc467edafa194176

## Gate Runs
<!-- Appended by the gate framework. Do not edit by hand; use `./.aitask-scripts/aitask_gate.sh append` for corrections. -->

> **✅ gate:plan_approved** run=2026-11-16T15:10:01Z status=pass attempt=1 type=human

> **✅ gate:review_approved** run=2026-11-16T20:31:52Z status=pass attempt=1 type=human

> **🔄 gate:risk_evaluated** run=2026-11-16T20:33:03Z-risk_evaluated-a1 status=running attempt=1 type=machine
>
> Verifier: `aitask-gate-risk`
> Note: stuckhash:cc05d8d1fd181636

> **✅ gate:risk_evaluated** run=2026-11-16T20:33:03Z-risk_evaluated-a1 status=pass attempt=1 type=machine
>
> Verifier: `aitask-gate-risk`
> Result: risk evaluated (## Risk section + both levels present)
> Log: `.aitask-gates/1_5/risk_evaluated_2026-11-16T20:33:03Z-risk_evaluated-a1.log`
