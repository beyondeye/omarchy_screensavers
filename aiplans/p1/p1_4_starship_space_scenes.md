---
Task: t1_4_starship_space_scenes.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
---

# p1_4 — space scenes 4, 5, 6, 9, 10

Context: `aitasks/t1/t1_4_starship_space_scenes.md`, the storyboard, and the archived p1_3
(renderer, tests and perf notes).

## Steps

1. Add `scenes/{high_altitude,hot_staging,coast,over_earth,seco}.rs`, replacing their placeholders
   in the timeline table.
2. Add the missing primitives: additive glow/bloom (radial), a large-disc limb with an atmosphere
   band, and a seeded starfield with twinkle.
3. Transitions per the storyboard via `blend_weight`.
4. Tests: signatures with scene-specific darkness limits, boundary checks, and remove these 5
   scenes from the placeholder list.

### Post-phase (risk mitigations)
1. [frame_data_guard] Run the staged-diff grep, review it by hand, and check that `.refs/` stays
   ignored.

## Verification

- `make check`.
- `make perf EFFECT=starship RES=4k` is within budget (record the numbers).
- `make try EFFECT=starship EFFECT_ARGS="--start-at <scene start>" TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`
  for each scene, compared with the animatic.
- Commits: ttfx `Add the starship space scenes`, then push. Then the workspace
  `feature: Add the starship space scenes (t1_4)`.

Step 9 (Post-Implementation): archive via the workflow.
