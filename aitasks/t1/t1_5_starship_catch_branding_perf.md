---
priority: medium
effort: high
depends: [t1_4]
issue_type: feature
status: Ready
labels: [effect, screensaver]
gates: [risk_evaluated]
anchor: 1
created_at: 2026-11-15 09:59
updated_at: 2026-11-15 09:59
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
