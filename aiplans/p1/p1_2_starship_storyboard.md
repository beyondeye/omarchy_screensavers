---
Task: t1_2_starship_storyboard.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
---

# p1_2 — starship storyboard

Context: `aitasks/t1/t1_2_starship_storyboard.md` (full spec), the parent plan, and the archived
p1_1 (`## Notes for t1_2`: the refined cuts and motion fits).

## Steps

1. Create `aidocs/starship/storyboard.md` with these sections: Global (grid, coordinates, camera,
   timeline table totalling 60 s); scenes 1, 2, 3, 4, 5, 6, 9, 10, 11; Branding reveal and outro;
   Signatures (one summary table for the tests).
2. Sample palettes with `frames2text.py extract` into `.refs/` and a `python3 -I` one-off that
   averages regions of the `.rgb` frames (kept in the scratchpad, not committed). Only the hex
   values go in the doc.
3. For each scene, give the elements as parameters, the palette, the motion (an easing name from
   `ttfx/src/utils/easing.rs`), particles (including the peak count ≤ ~5 000), transitions, and a
   signature line with **scene-specific** darkness/variety limits.
4. Add the CLAUDE.md table row.

### Post-phase (risk mitigations)
1. [frame_data_guard] Run the staged-diff grep, review it by hand, and check that `.refs/` stays
   ignored.

## Verification

- All 9 scenes are complete, and the durations add up to ~60 s.
- There are no images, art or frame data in the doc.
- Commit: `documentation: Add the starship storyboard (t1_2)`.

Step 9 (Post-Implementation): archive via the workflow.
