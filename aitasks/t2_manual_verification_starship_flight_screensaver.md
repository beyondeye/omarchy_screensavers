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

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_5** id=2026-11-16T20:32:54Z.ba773ad3f8b266d34012fbb5 from=t1_5 from_verified=yes at=2026-11-16T20:32:54Z base=ab2945c2571cd1cb1859def47a6922ea853963c5 base_branch=main dirty=yes host=omg16
>
> | Advisory, from t1_5 (catch scene + branding), as of workspace commit ab2945c (ttfx 228fd59).
> | 
> | - `make try` uses the CLI's default text anchor (bottom left). To see the branding where the
> |   screensaver draws it, add `--anchor-text c` to TTFX_ARGS. Start times: 45 catch (47 descent and
> |   arms closing 50.3-51.3, 51.5 top-down, 54 wide caught), 57.5 smoke, 58 reveal.
> | - Branding timing, now: the reveal starts in [58.0, 59.13], with 0.33 s fades. All letters are in
> |   hold by 59.5 (fg #f3efe6 on a darkened plate). Each letter appears from a flat cell of its plate
> |   colour, never popping onto the scene. In the loop fade the letters dissolve in reverse order over
> |   62.5-63.7 (user decision, instead of an fg->bg fade). The frame from 63.7 to 64 is the plain scene.
> | - The checklist item "forms legibly out of the smoke and holds ~3 s" still applies (hold
> |   59.5-62.5). Watch for plate flicker or letter pops: the tests bound them, but this is the visual
> |   check.
> | - Perf caveat: with the default text the 120 Hz budget holds at 4K (p99 3.2 ms). A huge input (a
> |   full 4K grid of glyphs) measured fine in 2 of 3 runs. One loaded run had slow ticks at the loop
> |   fade start (62.6 s). Worth a look only if the branding file is very large.
