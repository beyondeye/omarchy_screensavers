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
