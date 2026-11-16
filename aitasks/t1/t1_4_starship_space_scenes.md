---
priority: medium
risk_code_health: low
risk_goal_achievement: medium
effort: high
depends: [t1_3]
issue_type: feature
status: Implementing
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
updated_at: 2026-11-16 11:45
---

## Context

Child 4 of t1 (the `starship` screensaver effect: a ~60 s procedural animation of the Starship
Flight 15 mission). Parent plan: `aiplans/p1_starship_flight_screensaver.md`. Read the archived
t1_3 plan (`aiplans/archived/p1/p1_3_*.md`) for the renderer, primitives, particles, timeline,
test harness and perf numbers it built. `aidocs/starship/storyboard.md` is the spec.

This child replaces the **space-scene placeholders** with real scenes: 4, 5, 6, 9 and 10.
Settled: 9 scenes in total (no booster descent or landing; the booster just falls away after hot
staging). Original ttfx engine only. No frame-derived data: only hand-authored parameters and
palettes from the storyboard.

## Key Files to Modify

- `ttfx/src/effects/starship/scenes/` (or `starship.rs`): add the 5 scenes, wired into the
  timeline in place of the placeholders.
- `ttfx/src/effects/starship/raster.rs` / `particles.rs`: add only what is missing (glare/bloom,
  starfield, a large-radius disc with a limb glow).
- `ttfx/tests/starship.rs`: signatures and boundary checks for the new scenes. Remove them from the
  "still placeholder" list.

## Reference Files for Patterns

- The t1_3 scenes 1–3 and the primitives, for structure and conventions.
- `aidocs/starship/storyboard.md`: each scene's elements, palette, motion, particles, transitions
  and signature line.
- `tools/frames2text/frames2text.py play`: the animatic, to compare against (outputs only in `.refs/`).

## Implementation Plan

1. Scene 4, high altitude: dark gradient sky, glowing pink/white plume (additive, radial falloff).
2. Scene 5, hot staging: a burst of orange flame around the interstage (an expanding particle
   ring); the booster drops away and out of frame (easing per the storyboard).
3. Scene 6, ship coast:
   - the Earth limb as a very-large-radius disc (centre below the screen) with an atmosphere glow
     gradient band;
   - sun glare (radial gradient with bloom);
   - drifting ice particles.
4. Scene 9: the ship over Earth with a bright sun against black space.
5. Scene 10, SECO: the plume blooms into a blue-white haze (radial bloom growing and fading), then
   clears to a starfield (seeded star positions, twinkle).
6. Transitions per the storyboard (cuts and cross-fades) through the timeline's `blend_weight`.
7. Tests: signatures for scenes 4, 5, 6, 9, 10 using the **scene-specific** darkness limits (e.g.
   the starfield may be ≥95 % near-black but needs ≥ N bright stars); cut/fade checks on their
   boundaries (consecutive-tick step limits plus `render_scene_only` endpoints); and no placeholder
   colour in these scenes.

## Verification Steps

- `make check` passes.
- `make perf EFFECT=starship RES=4k`: the bloom and starfield ticks stay within the budget
  (p99 < 8.3 ms, max < 16 ms, no runs of ≥ 2 consecutive ticks over 8.3 ms). Record the numbers.
- `make try EFFECT=starship EFFECT_ARGS="--start-at 20" TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`:
  the space scenes look right next to the animatic. Set `--start-at` to each scene's start time
  from the storyboard.
- **frame_data_guard** before each commit: run
  `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review it by hand.
  `.refs/` stays ignored.
- Commits: in ttfx, `Add the starship space scenes`, then push. Then in the workspace,
  `feature: Add the starship space scenes (t1_4)` (`git add ttfx`).

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_2** id=2026-11-15T15:48:57Z.042e2e6a3e9221e4c46ede17 from=t1_2 from_verified=yes at=2026-11-15T15:48:57Z base=0a42c015f1bee2afddc3320cad0ebd28c541fb0e base_branch=main dirty=no host=omg16
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

> **✉ note:t1_3** id=2026-11-15T21:30:55Z.e97b1b44bef5fcb5b996b58b from=t1_3 from_verified=yes at=2026-11-15T21:30:55Z base=b35a6054cd70fa4762e4dfd47a45bd22f64909da base_branch=main dirty=no host=omg16
>
> | Advisory, from t1_3 (starship skeleton), as of commit b35a605 (ttfx de82884, omarchy-screensaver e39c449).
> | The full record is the archived plan aiplans/archived/p1/p1_3_starship_effect_skeleton.md ("Notes for sibling tasks").
> | 
> | - Bounded palette: every fg/bg the effect emits must be an entry of the fixed palette P
> |   (ttfx/src/effects/starship/palette.rs). ttfx never frees cell appearances, so P×P is the
> |   memory bound. P_CAP = 340 and |P| = 317 today: only about 23 entries of headroom for scenes
> |   4/5/6/9/10. Add each scene's gradients as RAMPS_* in ALL_RAMPS, reuse storyboard colours, or
> |   prune the 4×4×4 coverage cube first.
> | - After any palette change, re-run `cargo test --release --test starship_pool_ceiling`. It
> |   saturates P×P, replays the screensaver's rebuild overlap and requires ≤ 64 MB (55.7 MB now).
> |   Also re-run `palette_error_*`.
> | - The plan's `render_scene_only(scene, t)` is `Starship::render_only(scene)` in the code: the
> |   last frame's state with one scene's layer.
> | - One emission path: only `emit_appearance` may call `set_appearance` (test
> |   `emission_path_shared`).
> | - Scenes: `scenes/<name>.rs` with `step(world, rng, t, dt)` and `draw(world, t, buf)`,
> |   dispatched in `scenes/mod.rs`. Emitters use `World::spawn` with a `Slot`. Particle sizes and
> |   1 px details are defined at 137×66 and must scale with `buf.h / 66`, or the 4K signatures
> |   drift.
> | - Tests: drop scenes from PLACEHOLDER_SCENES and add their rows to SIGS in
> |   ttfx/tests/starship.rs.
> | - Perf: `make perf EFFECT=starship RES=4k` (and `TTFX_STARSHIP_STRESS=1` for the
> |   every-cell-changes stress). On this hybrid CPU, pin with `taskset -c 0-7` and compare runs
> |   taken under the same load. render_delta now redraws only changed cells, so raster cost
> |   follows the changed-cell count.

> **👁 note:read** id=2026-11-16T06:31:30Z.5f38a5605324a0769f1ace64 by=t1_4 at=2026-11-16T06:31:30Z mode=explicit ids=2026-11-15T15:48:57Z.042e2e6a3e9221e4c46ede17,2026-11-15T21:30:55Z.e97b1b44bef5fcb5b996b58b

## Gate Runs
<!-- Appended by the gate framework. Do not edit by hand; use `./.aitask-scripts/aitask_gate.sh append` for corrections. -->

> **✅ gate:plan_approved** run=2026-11-16T09:45:52Z status=pass attempt=1 type=human

> **✅ gate:review_approved** run=2026-11-16T11:23:21Z status=pass attempt=1 type=human
