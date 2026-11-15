---
Task: t1_5_starship_catch_branding_perf.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
---

# p1_5 — catch scene 11, branding reveal, full-timeline perf, final tests

Context: `aitasks/t1/t1_5_starship_catch_branding_perf.md`, the storyboard, and the archived
p1_3/p1_4.

## Steps

1. `scenes/catch.rs`: towers, overcast sky, the ship descending on its engines, the chopstick arms
   closing, then the top-down close-up.
2. Branding reveal: the input characters at their `input_coord`s appear out of the smoke, hold
   ~3 s, then fade to scene 1's first-frame colours. `None` at the total.
3. Tune the pacing at 60 fps (`make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"`)
   and at 120 fps (`make headless EFFECT=starship FRAMES=7320`, plus the bench).
4. Perf: `make perf EFFECT=starship RES=1080p` and `RES=4k`. Acceptance: p99 < 8.3 ms, max < 16 ms,
   no run of ≥ 2 consecutive ticks over 8.3 ms. Inspect and profile the 10 slowest ticks and fix
   them. Record the before and after numbers.
5. Final tests: all 9 signatures; no placeholder colour anywhere; branding visible during the hold;
   the loop assertions un-ignored and passing.

### Post-phase (risk mitigations)
1. [frame_data_guard] Run the staged-diff grep, review it by hand, and check that `.refs/` stays
   ignored.

## Verification

- `make check`.
- `make perf` acceptance at 1080p and 4K.
- `make headless EFFECT=starship FRAMES=7320` runs.
- CLI determinism `cmp` (the command is in the task file).
- Commits: ttfx `Add the starship catch scene and branding reveal`, then push. Then the workspace
  `feature: Add the starship catch scene and branding reveal (t1_5)`.
- Report that the manual-verification follow-up (the on-monitor check) is still outstanding.

Step 9 (Post-Implementation): archive this child; the parent t1 archives once all 5 children are
done. The standalone manual-verification follow-up does not block it.
