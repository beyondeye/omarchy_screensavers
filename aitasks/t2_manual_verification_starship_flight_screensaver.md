---
priority: medium
effort: medium
depends: [1]
issue_type: manual_verification
status: Ready
labels: [verification, manual]
verifies: [1_1, 1_2, 1_3, 1_4, 1_5]
premise_baseline: 860b90834499f4b28ada8078da1c60f4a18d33ad @ 2026-11-15 10:00
anchor: 1
followup_kind: manual_verification
created_at: 2026-11-15 10:00
updated_at: 2026-11-15 10:00
---

## Manual Verification Task

This task is handled by the manual-verification module: run
`/aitask-pick <id>` and the workflow will dispatch to the
interactive checklist runner. Each item below must reach a
terminal state (Pass / Fail / Skip) before the task can be
archived; Defer is allowed but creates a carry-over task.

**Related to:** t1

## Verification Checklist

- [ ] [t1_3/t1_4/t1_5] make run EFFECT=starship on real monitors (1080p and 4K, multi-monitor if available): all 9 scenes are recognisable next to frames2text play, and there is no booster landing
- [ ] [t1_3/t1_5] Smooth at 120 Hz: no stutter, tearing or catch-up jumps, especially during the smoke, plume bloom and catch
- [ ] [t1_5] The branding text forms legibly out of the smoke after the catch and holds ~3 s
- [ ] [t1_5] The loop restarts with no flash (outro fades into scene 1)
- [ ] [t1_3] make try EFFECT=starship TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60" runs ~60 s in a terminal and looks the same
- [ ] [t1_3] It appears in the random rotation: run make run EFFECT=random several times (bare make run defaults to stub)
- [ ] [t1_1] frames2text all plays the ~60 s animatic, and git status stays clean afterwards
