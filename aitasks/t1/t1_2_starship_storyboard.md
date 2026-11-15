---
priority: medium
effort: medium
depends: [t1_1]
issue_type: documentation
status: Implementing
labels: [effect, screensaver]
gates: [risk_evaluated]
assigned_to: dario-e@beyond-eye.com
anchor: 1
created_at: 2026-11-15 09:58
updated_at: 2026-11-15 13:06
---

## Context

Child 2 of t1 (the `starship` screensaver effect: a ~60 s procedural animation of the Starship
Flight 15 mission). The parent plan is `aiplans/p1_starship_flight_screensaver.md`; read it first.
Also read the archived t1_1 plan (`aiplans/archived/p1/p1_1_*.md`): it has the refined scene cuts
and the measured motion numbers.

This child writes the **storyboard**, the numeric spec that the effect children (t1_3–t1_5)
implement and test against. **Numbers and words only**: no images, no text-art, no frame dumps.

Decisions already settled (do not re-ask):
- **9 scenes: 1–6, 9, 10, 11.** Scenes 7 and 8 (the booster's descent and landing) are dropped by
  the user. After hot staging, the booster just falls away out of frame. Their ~11 s goes to the
  liftoff (1) and the catch (11).
- **Branding text** (`~/.config/omarchy/branding/screensaver.txt`, or
  `omarchy-screensaver/assets/screensaver.txt`) is revealed **after the catch**: it forms out of the
  smoke/clouds, holds ~3 s, then fades into scene 1's opening colours. Then the effect returns
  `None` and the screensaver rebuilds it, so it loops.
- Total: about 60 s, including the reveal and the loop transition.

## Key Files to Modify

- `aidocs/starship/storyboard.md` (new).
- `CLAUDE.md`: add a row to the docs table.

## Reference Files for Patterns

- `aidocs/starship/reference_tooling.md` and `tools/frames2text/` (from t1_1): use
  `frames2text.py extract`/`convert` and the raw `rgb24` frames in `.refs/` to sample hex colours
  (e.g. average a region with a few lines of stdlib Python, run with `python3 -I`). Only the
  resulting hex values go in the doc.
- `./.aitask-scripts/aitask_screen_recording.sh anim --window` for motion fits.
- The original task's scene table, in `aitasks/t1_starship_flight_screensaver.md`.

## Implementation Plan

1. Global section:
   - grid 137×33 cells → 137×66 half-block pixels;
   - coordinate system: world units vs. pixels, origin and y direction;
   - the camera model (pan/zoom/shake);
   - the timeline table: scene, start s, duration s, transition into the next (cut or cross-fade
     with its duration), totalling 60 s, including the ~3 s branding hold and the outro fade.
2. Per scene (1–6, 9, 10, 11):
   - **Elements as parameters**: rocket proportions (booster 71 m + ship 52 m, 9 m diameter → as
     ratios of the screen height in each shot), fins and flaps, the tower lattice (bay spacing,
     width, height ratio), chopstick arm geometry (pivot, length, closing angle over time), the
     Earth limb (radius as a multiple of the screen width, centre offset), sun position and glare
     radius.
   - **Palette**: hex values sampled from the reference.
   - **Motion**: direction, speed (px/s at 137×66), easing (an `Easing` name from
     `ttfx/src/utils/easing.rs`), from the t1_1 `anim` fits where they are measurable.
   - **Particle systems**: smoke billows, exhaust/flames, ice flakes, stars. For each: spawn rate,
     life, velocity, size, colour ramp, drag/buoyancy, and the expected peak particle count (the
     t1_3 perf budget assumes ≤ ~5 000).
   - **Transitions** in and out.
   - **Signature line**, used for the automated tests: the dominant colours with expected screen
     fractions and tolerances, plus **scene-specific** darkness/variety limits. For example:
     "scene 10 starfield: ≥95 % near #05070d, ≥ 20 bright star cells"; "scene 1 pad: < 30 %
     near-black". There is no universal near-black cap.
3. Branding-reveal section: how the text forms in the post-catch smoke, the hold, and the fade
   into scene 1's first-frame colours, with numbers for each step.
4. Add the CLAUDE.md table row.

## Verification Steps

- The doc covers all 9 kept scenes, each with a duration, elements, palette, motion, particles,
  transitions and a signature line, and the durations add up to ~60 s.
- It contains no images, ASCII/ANSI art or pasted frame data.
- **frame_data_guard**: before committing, run
  `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'` and review it by hand.
  `git status --ignored`: `.refs/` stays ignored.
- Commit: `documentation: Add the starship storyboard (t1_2)`.

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_1** id=2026-11-15T10:58:06Z.2ad0f5057bb5d090a9c7c064 from=t1_1 from_verified=yes at=2026-11-15T10:58:06Z base=572ad6a5a5f04a6bfb7e0dd03f26560242fa0428 base_branch=main dirty=yes host=omg16
>
> | Advisory, from t1_1 (frames2text reference tool), as of code commit 572ad6a:
> | 
> | 1. Timeline budget: the scene list tools/frames2text/scenes/starship_flight15.toml totals 60.4 s of
> |    footage (10.0 / 6.1 / 6.0 / 3.0 / 4.9 / 6.0 / 4.1 / 7.0 / 13.3 s for liftoff, ascent, onboard,
> |    high_altitude, hot_staging, coast, ship_over_earth, seco, catch). It holds no branding hold and no
> |    outro fade. If the storyboard keeps the ~3 s branding hold plus the outro inside 60 s, the scene
> |    durations need about 4 s of compression (the coast and catch have the most slack). The animatic
> |    speeds are a reference, not a constraint.
> | 2. The SpaceX footage ends at 244.04 s, not ~236 s as the parent t1 body says: 236.47-244.04 s is the
> |    wide shot of the caught ship on the tower (good reference for a final hold), and CNN starts at 244.04.
> | 3. Cut times, shot contents and anim motion fits are in the archived p1_1 plan, "Notes for t1_2".
> |    The full-frame anim fits are rough (camera shake and compression dominate); the decelerating
> |    smoke/bloom curves and the catch settle (spring, damping ratio about 0.8) are the usable ones.

> **✉ note:t1_1** id=2026-11-15T10:59:03Z.2e3a95571eabe0ec9cecab28 from=t1_1 at=2026-11-15T10:59:03Z base=572ad6a5a5f04a6bfb7e0dd03f26560242fa0428 base_branch=main dirty=yes host=omg16
>
> | Advisory correction to my earlier note (point 1, "about 4 s of compression"): the user said the
> | total may run a few seconds past 60 s if needed. So the storyboard can keep the animatic scene
> | lengths (60.4 s of footage) and add the ~3 s branding hold and outro fade on top: a total around
> | 63-65 s is acceptable. Compress only where it reads better, not to hit 60 s exactly. Whatever total
> | you settle on, state it explicitly in the timeline table: t1_3 and t1_5 size their tick counts and
> | perf/headless frame counts from it.

> **👁 note:read** id=2026-11-15T11:05:57Z.0dde34fb6aa34283a8738c74 by=t1_2 at=2026-11-15T11:05:57Z mode=explicit ids=2026-11-15T10:58:06Z.2ad0f5057bb5d090a9c7c064,2026-11-15T10:59:03Z.2e3a95571eabe0ec9cecab28
