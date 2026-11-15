---
priority: medium
effort: high
depends: [t1_3]
issue_type: feature
status: Ready
labels: [effect, screensaver]
gates: [risk_evaluated]
anchor: 1
created_at: 2026-11-15 09:59
updated_at: 2026-11-15 09:59
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
