---
Task: t1_2_starship_storyboard.md
Parent Task: aitasks/t1_starship_flight_screensaver.md
Sibling Tasks: aitasks/t1/t1_*.md
Archived Sibling Plans: aiplans/archived/p1/p1_*_*.md
Branch: main
Base branch: main
Output branch: main
plan_verified:
  - claudecode/opus5_5 @ 2026-11-15 17:05
---

# p1_2: starship storyboard

## Context

t1 is the `starship` screensaver effect. This child writes `aidocs/starship/storyboard.md`, the
numeric spec that t1_3–t1_5 implement and test against: the timeline, per-scene elements as
parameters, palettes sampled from the reference, motion with ttfx easings, particle budgets,
transitions and test signatures. It contains numbers and words only. Full spec:
`aitasks/t1/t1_2_starship_storyboard.md`. Settled decisions: the parent plan
`aiplans/p1_starship_flight_screensaver.md`. Measured cuts and motion fits: the archived p1_1
plan, `## Notes for t1_2`. Workspace repo only, no submodule changes.

## Verification notes (2026-11-15, verify pass)

- `aidocs/starship/` holds only `reference_tooling.md`. `storyboard.md` is new.
- `.refs/starship/` already holds the extracted animatic (9 scene dirs, 604 frames, `NNNNN.{rgb,png,ans}`,
  manifest total 60.4 s, converter chafa). Each `.rgb` is 137×66×3 bytes, so palettes can be sampled
  without re-extracting.
- `ttfx/src/utils/easing.rs`: 31 named easings (`Linear`, `In/Out/InOut` × Sine, Quad, Cubic, Quart,
  Quint, Expo, Circ, Back, Elastic, Bounce; CLI names `out_cubic` etc.) **plus
  `Easing::CubicBezier(x1,y1,x2,y2)`**, so the measured `cubic-bezier(...)` fits can be used directly.
  There is no spring easing: the catch settle uses its cubic-bezier fit.
- **Correction (total length):** the t1_1 notes (acknowledged) say the user allows a few seconds
  past 60 s. The doc fixes **64.0 s** (58.0 s of scenes plus 6.0 s for branding form, hold and fade),
  stated explicitly with the tick counts: 7680 @120 fps, 3840 @60 fps, `PERF_SECONDS` = 65,
  `FRAMES` = 7800. That replaces the old plan's "totalling 60 s".
- **Correction (doc pointers):** t1_1 added its row to CLAUDE.md **and** AGENTS.md (mirrored table)
  and a pointer line to README.md, so do the same here. README.md has someone else's uncommitted
  "Development workflow" edits (8 lines). Stage **only** our line (see step 6).
- Grid geometry: `omarchy-screensaver/src/raster.rs` computes the cell size from `FONT_PX = 24`
  (`advance_width('M')` × line height). The pixel aspect ratio is derived in step 1, not assumed.

## Steps

1. **Measure the grid geometry.** Run `make headless EFFECT=stub`, or read the printed cols/rows, to
   confirm 137×33 at 1920×1080 scale 1. Derive the cell size (≈14×32 screen px) and the half-block
   pixel aspect (≈14×16, w/h ≈ 0.87). The doc gives every shape in **screen-height units (H)** with
   that aspect correction, and gives speeds in H/s and in px/s at the reference 137×66.
2. **Sampling script (scratchpad only, never committed):**
   `<scratchpad>/sample.py`, run as `python3 -I sample.py .refs/starship`. It reads `NNNNN.rgb`
   (137×66 RGB). First view 2–3 PNGs per scene with Read to locate the webcast HUD (timer and gauge
   bands) and name the regions: sky band, ground/sea, plume core, hull, limb, and so on. It
   implements the two shared rules from step 4 and nothing else:
   - **`map_time(sub_shot, t_local)`**, the time mapping. The storyboard's local time maps
     linearly into the sub-shot's source range in video time:
     `v = src_start + (t_local − sb_start) · (src_end − src_start) / (sb_end − sb_start)`.
     Animatic frame k of a toml scene sits at `v_k = scene.start + k · 0.1 · scene.speed`
     (target_fps 10, from the manifest). Frames are never chosen from `v` directly; only
     `pick` (below) chooses them.
   - **`measure(frame, region)`**, the measurement area. It counts only half-block pixels whose
     centre lies inside the scene's normalised **measurement region** (step 4), and the
     denominator is that pixel count.

   - **`valid_frames(sub_shot)`**, the one valid set that all sampling draws from. It is not a
     formula on the range boundaries: the toml ranges start slightly *after* real cuts (179.15 vs
     the 179.11 cut, 191.75 vs 191.69, 220.15 vs 220.09, 37.5 vs 37.47, 67.35 vs 67.30, 77.6 vs 77.58).
     The set is every animatic frame k of the sub-shot's toml scene whose own video time
     `v_k = scene.start + k · 0.1 · scene.speed` passes all three checks:
     - **shot membership**: `src_start ≤ v_k < src_end`;
     - **cut distance**: `|v_k − c| ≥ 0.3 s` for **every** cut c in the p1_1 cut list (in-scene
       cuts such as 11.01 included), regardless of where the range boundary sits;
     - **fade**: the frame's storyboard time (the inverse mapping
       `t = sb_start + (v_k − src_start) / f`) is not inside an incoming cross-fade window
       `[sb_start, sb_start + d)`.

       The outgoing side needs no check, because the fade lives in the incoming scene's time.

     The set is empty, or spans < 0.2 s of storyboard time → an error naming the sub-shot (the doc
     then widens that sub-shot or moves its boundary). It is never a silent fallback.
   - **`pick(sub_shot, t)`** maps t to `v` and returns the frame in `valid_frames` nearest to `v`.
     It is an error if that frame lies > 0.5 s of storyboard time from t: the signature time is then
     moved, not the rule. Every sample therefore comes from the valid set by construction.

   Per sub-shot, it prints the following for the first, middle (nearest the set's time centre) and
   last frame of `valid_frames`:
   - region means as hex;
   - a 4-bit-per-channel quantised histogram, giving the top 6 colours with fractions inside the
     measurement region;
   - the near-black fraction (Rec.709 luma < 0.08) and the bright fraction (luma > 0.70), over the
     same region.

   Only the resulting hex values and percentages go into the doc, **at most about 8 hex values per scene**.
3. **Optional extra motion fits** where t1_1 had none: the booster falling away (hot staging,
   ~81–84 s) and the ice-flake drift (coast). Use `aitask_screen_recording.sh anim --window ... --out
   <scratchpad>/video-prep/...`. If a fit degenerates, estimate by eye from 1 s frames and say
   so in the doc.
4. **Write `aidocs/starship/storyboard.md`:**
   - **Global**:
     - grid: 137×33 cells → 137×66 half-block pixels, plus the larger grids (4K at scale 1) that
       scale with H;
     - coordinates: origin at the top-left, y down, world units = H, x scaled by the pixel aspect;
     - camera model: pan, zoom and shake (amplitude in H, frequency), all eased;
     - the "near" metric: RGB Euclidean distance ≤ 48 over 0–255 unless stated, measured over
       half-block pixels (cell fg = top pixel, bg = bottom pixel);
     - the near-black and bright definitions;
     - the transition convention: a cross-fade of length d occupies the first d s of the incoming
       scene, the outgoing scene keeps its own clock past its nominal end, and the blend weight is
       `InOutSine`;
     - the timeline table: scene | sub-shots | start s | duration s | into next. The totals are
       below.

     | # | scene | start | dur | sub-shots | into next |
     |---|---|---|---|---|---|
     | 1 | liftoff | 0.0 | 10.0 | 1a pad wide 6.0, 1b aerial 4.0 | cross-fade 0.5 (camera tilt) |
     | 2 | ascent | 10.0 | 6.0 | 2a plume over horizon 2.5, 2b small rocket 3.5 | cut |
     | 3 | onboard | 16.0 | 6.0 | | cut |
     | 4 | high altitude | 22.0 | 3.0 | | cut |
     | 5 | hot staging | 25.0 | 5.0 | | cross-fade 1.0 (same framing) |
     | 6 | coast | 30.0 | 5.0 | | cut |
     | 9 | ship over Earth | 35.0 | 4.0 | | cut |
     | 10 | SECO | 39.0 | 6.0 | | cut |
     | 11 | catch | 45.0 | 13.0 | 11a wide 2.0, 11b descent+catch 4.5, 11c top-down 2.5, 11d wide caught 4.0 | continuous |
     | B | branding | 58.0 | 6.0 | form 1.5, hold 3.0, fade to scene 1 frame 0 1.5 | loop (`None`) |

     The total is **64.0 s**, with the tick counts above. These are the animatic lengths, with coast
     −1.0 s and SECO −1.0 s (the slackest shots) and catch −0.3 s, so the branding fits.
   - **Reference time mapping table** (Global). One row per sub-shot: storyboard local range
     `[sb_start, sb_end)` | source range `[src_start, src_end)` in video seconds | toml scene |
     time factor `(src_end − src_start)/(sb_end − sb_start)`. The source ranges come from the
     p1_1 cut times. 1a 0.0–11.01, 1b 11.01–18.0, 3 37.5–67.25, 4 67.35–77.5, 5 77.6–85.0, 6 85.0–124.3,
     9 179.15–183.2, 10 191.75–219.9, 11a 220.15–223.72, 11b 223.72–231.53, 11c 231.53–236.47 and 11d 236.47–244.0.
     The 2a/2b boundary has no hard cut, so it is set from 1 s frames between 18.0 and 37.4 and
     recorded. The mapping is linear within a sub-shot. It is the **single rule** for:
     - choosing the reference frame of each signature;
     - converting every measured motion into screen time: screen speed = source speed × time
       factor, and screen duration = source duration ÷ time factor (e.g. the catch settle's 2.3 s
       of source becomes 2.3 / factor_11b);
     - t1_5's pacing comparison against the animatic.

     A signature's reference frame is `pick(sub_shot, t)` from the sub-shot's `valid_frames`
     (step 2: shot membership, ≥ 0.3 s from every actual cut, outside incoming fades). The doc
     lists, next to each mapping row, the storyboard span that the valid set covers (first…last
     valid frame), and each signature time lies inside that span.
   - **Measurement region** (Global, plus a per-scene override). Signatures are fractions of the
     half-block pixels whose centre lies inside a normalised rectangle `[x0,x1)×[y0,y1)` of the grid
     (0–1, which works for any grid size). The default is the full screen minus the webcast HUD
     bands found in step 2. A scene without a HUD uses the full screen. **The same region applies
     on both sides.** The reference self-check (post-phase) and the effect's tests (t1_3–t1_5) both
     measure inside it, with the region's pixel count as the denominator. The effect itself draws
     the full screen and has no HUD, and what it draws under the excluded bands is unconstrained.
     Note that the reference's 854×480 aspect (1.78) vs the grid's ≈1.82 is a ≤ 2 % stretch, which
     is ignored.
   - **Particle budget** (Global). The 5 000 limit is a **global cap on live particles at any tick**,
     which is the workload t1_3's renderer_spike covers, not a per-scene figure. Rules:
     - at the start of a cross-fade (= end_A), the outgoing scene's emitters stop spawning;
     - its surviving particles fade with the blend weight and are killed at the end of the fade;
     - the incoming scene's emitters ramp up from 0, so in its first d s it holds at most
       rate_B × d particles;
     - the implementation uses one pool with a fixed capacity of 5 000 (allocated in `build`), and
       spawns over capacity are dropped deterministically.

     The doc carries a **combined-peak table**, one row per overlap, giving
     `peak_A(at end_A) + peak_B(within d) ≤ 5 000`:
     - 1→2 (0.5 s);
     - 5→6 (1.0 s);
     - 11→B, which is continuous: the post-catch smoke *is* the branding smoke, so it is counted
       once;
     - B→loop. Scene 1 at t = 0 has **no live particles** (smoke spawns from t > 0), so the outro
       fade's target holds none, and B's smoke is killed by the end of the fade.

     Every per-scene peak is set so that its row holds.
   - **Per scene (1–6, 9, 10, 11)**, with fixed subsections:
     - **Elements**, as parameters: the rocket is 123 m (booster 71 m + ship 52 m) by 9 m, aspect
       13.7, with its height in H per shot; the fins and flaps; the tower (height ratio, width, bay
       spacing in H); the chopsticks (pivot height, length, open → closed angles over time); the
       Earth limb (radius as a multiple of the screen width, centre offset); the sun (position,
       glare radius); the hex tiles (cell size in H).
     - **Palette**: sampled hex values.
     - **Motion**: direction, H/s and px/s, `Easing` name or `CubicBezier(...)` from the p1_1 fits.
       The liftoff smoke uses `CubicBezier(0.325,0.912,0,0.7)` over 6.1 s, ascent is `Linear`
       ~0.128 H/s screen time, SECO bloom uses `CubicBezier(0.05,0.7,0.1,1)`, and the catch settle
       uses `CubicBezier(0.3,0.866,0,1.078)`, with the durations converted to screen time.
     - **Particles**: per system, the spawn rate /s, life s, velocity H/s, size px, colour ramp,
       drag and buoyancy, and the peak count, plus the scene's live count at its end (the input
       to the combined-peak table). Each scene's peak is ≤ 5 000, and every overlap row in the
       global table also stays ≤ 5 000.
     - **Transitions** in and out.
     - **Signature**: dominant colours with fractions ± tolerance (≥ ±10 pp), plus scene-specific
       darkness/variety limits (e.g. scene 1 pad < 30 % near-black; scene 10 starfield ≥ 90 %
       near-black with ≥ N bright cells). All of these are measured inside the scene's
       measurement region. Each signature names its storyboard test time (mid-scene, or per
       sub-shot for 1, 2 and 11), the mapped source time, and the animatic frame from the
       mapping table.
   - **Branding reveal and outro**: the input chars at their centre-anchored coords. The reveal
     order is weighted by local smoke density, from 0 → 100 % of chars over 1.5 s (`OutCubic`),
     in colours from the post-catch smoke palette. Then a 3.0 s hold with smoke drifting at a
     given H/s. Then a 1.5 s `InOutSine` fade of every pixel to scene 1's frame-0 colours, with
     the chars fading to their bg. The last frame equals scene 1 frame 0 within the per-tick step
     limit, so there is no flash.
   - **Signatures summary table**: one row per scene/sub-shot (time, colours/fractions, limits), for
     the tests.
   - A short "Not in this effect" note: scenes 7 and 8 are dropped, and the webcast HUD is ignored.
5. **Self-check the doc:** all 9 scenes have every subsection, the durations sum to 64.0, there are
   no code blocks of art, and no ANSI.
6. **Doc pointers:**
   - add a CLAUDE.md row and the same row in AGENTS.md: "write or implement against the `starship`
     storyboard (timeline, per-scene parameters, palettes, signatures)" →
     `aidocs/starship/storyboard.md`;
   - add a README.md pointer line under the aidocs list. Stage only our README hunk: build the blob
     from `git show HEAD:README.md` plus our line, then `git hash-object -w` and
     `git update-index --cacheinfo 100644,<blob>,README.md`, leaving the other edits unstaged.

### Post-phase (risk mitigations)
1. [signature_feasibility] Re-run `sample.py` in check mode on each signature's test frame,
   choosing it **only through `pick` over `valid_frames` and the mapping table** (never by global
   time or by unmapped scene-local seconds), and measuring **only through `measure` and the scene's region**.
   Every reference frame must satisfy its own signature line: fractions within tolerance and the
   darkness/variety limits met. Also check `pick(sub_shot, t − 0.5)` and `pick(sub_shot, t + 0.5)`,
   drawn from the **same `valid_frames` set**, so a signature doesn't hinge on one moment. A pick
   that returns the main frame is skipped. If the set covers < 1 s, its first and last frames are
   used instead (the 0.5 s distance error does not apply to these neighbour checks). Widen or correct any line that fails, and record
   "reference passes its own signature" with the frame id in the doc's summary table. Also
   check that every combined-peak row sums to ≤ 5 000.
2. [frame_data_guard] Stage, then run `git diff --cached | grep -nE '"[^"]{200,}"|\[[^]]{400,}\]'`
   and review the staged diff by hand: no pixel arrays, ANSI or more than about 8 hex values per
   scene. `git status --ignored`: `.refs/` stays ignored and untracked, and the sampler stays in
   the scratchpad.
3. [timeline_handoff] After the commit, run `./ait note` to t1_3, t1_4 and t1_5 (`--from 1_2`):
   the exact total 64.0 s, 7680/3840 ticks, `PERF_SECONDS=65`, `FRAMES=7800`, the
   transition convention, and the doc section names to read. Also hand over the three shared
   rules that the tests and implementation must follow:
   - signatures are measured inside the normalised measurement region, with the region's pixel
     count as the denominator;
   - the reference time mapping is used for any comparison with the animatic;
   - particles live in one 5 000-capacity pool, with outgoing emitters stopped at end_A and
     their particles killed at the end of the fade.

## Verification

- The doc covers all 9 kept scenes, each with elements, palette, motion, particles, transitions and
  a signature line. The timeline sums to 64.0 s, and the total and tick counts are stated.
- The Global section has the reference time mapping table (every sub-shot), the measurement
  region rule (default + per-scene overrides), and the particle-cap rule with the combined-peak
  table (every overlap ≤ 5 000). Each signature names its test time, source time and frame.
- No images, ASCII/ANSI art or frame data. The post-phase guard has been run.
- Commit, workspace repo: `documentation: Add the starship storyboard (t1_2)`. It contains
  `aidocs/starship/storyboard.md`, CLAUDE.md, AGENTS.md and README.md (our line only).

Step 9 (Post-Implementation): archive via the workflow.

## Risk

### Code-health risk: low
- Docs only: one new doc and three pointer lines. README.md carries a third party's uncommitted
  edits that must not be swept into this commit · severity: low · → mitigation: none needed
  (step 6 stages only our hunk)

### Goal-achievement risk: low
- Frame-derived data leaks into the commit (oversized palettes, sampled tables) · severity: low
  (residual, addressed by inline post-phase frame_data_guard) · → mitigation: inline post-phase frame_data_guard
- Signature fractions taken from the footage may be unattainable for a procedural approximation,
  or ambiguous to compute, so the t1_3–t1_5 tests are flaky or meaningless · severity: low
  (residual, addressed by inline post-phase signature_feasibility plus the explicit metric
  definitions) · → mitigation: inline post-phase signature_feasibility
- Siblings keep hard-coding 60 s / 7320 frames while the storyboard fixes 64 s · severity: low
  (residual, addressed by inline post-phase timeline_handoff) · → mitigation: inline post-phase timeline_handoff
- Review findings (2026-11-15), all valid and resolved in steps 2 and 4: (a) there was no mapping
  between storyboard time and reference time once scenes are retimed; (b) the reference (HUD
  excluded) and the effect tests (full canvas) measured different areas with different
  denominators; (c) cross-fades could run two scenes' particles above the 5 000 the
  renderer_spike covers; (d) exact start and end samples contradicted the cut-margin and fade
  refusal rules (e.g. 1b starts on the 11.01 cut); (e) the first fix only applied the
  margin when a range boundary *was* a cut, but the toml ranges start just after real cuts (scene 9:
  179.15 vs 179.11). All sampling therefore draws from one `valid_frames` set per sub-shot,
  filtered by shot membership, distance ≥ 0.3 s from every actual cut, and the fade windows, via
  `pick`; the ±0.5 s checks use the same set · severity: low (residual: the reference time mapping table, the shared
  measurement region, and the global particle cap with its combined-peak table) · → mitigation:
  inline post-phase signature_feasibility (validates all three), inline post-phase timeline_handoff
  (hands the rules to t1_3–t1_5)
- Proportions and parameters read off a 137×66 reference are coarse, so scenes may still read as
  abstract · severity: low · → mitigation: none needed (the parent's queued manual-verification
  follow-up and the animatic comparison cover it)

### Planned mitigations
- timing: post-phase | name: frame_data_guard | type: test | priority: high | effort: low | inline_risk: low | added_complexity: low | addresses: frame-derived data leaking into the commit | desc: grep the staged diff for large literals, cap hex values per scene, confirm .refs/ stays ignored
- timing: post-phase | name: signature_feasibility | type: test | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: unattainable/ambiguous signature lines | desc: check every signature against the reference's own halfblock frame with the scratch sampler; widen or fix failing lines
- timing: post-phase | name: timeline_handoff | type: chore | priority: medium | effort: low | inline_risk: low | added_complexity: low | addresses: siblings hard-coding 60 s | desc: ait note t1_3/t1_4/t1_5 with the exact total, tick counts, PERF_SECONDS/FRAMES and the transition convention

## Post-Review Changes

### Change Request 1 (2026-11-15 16:10)
- **Requested by user:** five review findings, all verified as valid:
  1. (medium) 2b's endpoints (0.35 H in 3.5 s) contradicted its 0.16 H/s speed.
  2. (medium) the global rule called every sub-shot boundary a hard cut, but 2a → 2b is continuous.
  3. (medium) several particle systems were missing velocity, size, colour ramp or drag/buoyancy.
  4. (medium) the branding fg `#f3efe6` against 11d's light sky and smoke could not meet the
     promised ≥ 0.35 luma contrast.
  5. (low) reveal starts up to 59.5 s plus a 0.25 s fade overran the 59.5–62.5 full-text hold.
- **Changes made:**
  1. Re-measured the 2b rocket tip from the valid reference frames (per-row median background).
     2b has two phases: a camera zoom-out (12.5–13.4: tip v 0.24 → 0.57, body 0.30 → 0.10 H,
     modelled as camera zoom 1.0 → 0.33 about (0.50, 0.75), `InOutSine`), then the climb
     (13.4–16.0: tip (0.51, 0.57) → (0.57, 0.11), progress `CubicBezier(0.25, 0.65, 1.0, 1.0)`,
     fit rmse 0.005; mean 0.18 H/s; 0.047 H/s of source, consistent with p1_1's ≈0.04).
     That is now the single authoritative trajectory; the 0.16 H/s line is gone.
  2. 1.4 now lists the hard-cut boundaries and names 2a → 2b as the one continuous exception; 1.5
     "Continuous" covers it; 1.7 says a continuous boundary does not clear the pool.
  3. 1.7 gained a "Particle system fields" block (every field required, plus shared defaults: spawn
     and speed jitter, linear size/colour interpolation, `OutQuad` alpha fade, pixel/disc drawing).
     All 21 systems in section 2 and the branding smoke now state rate, life, velocity, size, ramp,
     drag, buoyancy and peak (checked mechanically).
  4. Text cells get a bg **luma cap**, `bg = c · min(1, 0.50 / luma(c))`, ramped in with each
     character's fade and released during the loop fade. Contrast is then ≥ 0.938 − 0.50 = 0.438 by
     construction. Verified on 11d's reference frames (k 101/112/130): without the cap the default
     30×5 text box under 0.6-alpha smoke reaches only 0.30 (whole screen 0.155); with it, 0.438.
  5. Reveal start times are now in [58.0, 59.25], so every 0.25 s fade ends by 59.5.
- **Files affected:** `aidocs/starship/storyboard.md`

### Change Request 2 (2026-11-15 16:35)
- **Requested by user:** (medium, verified valid) scene 2's sizes were still inconsistent across the
  continuous 2a → 2b boundary (2a body 0.45 H / plume 0.35 H, 2b starting at 0.30 H / 0.25 H at
  zoom 1.0), and the 0.25 H plume contradicted "plume = 1.2 × body".
- **Changes made:** re-measured the body (steel) and the pink plume separately in the valid 2a/2b
  reference frames. Scene 2 now uses one rocket model: body `B = 0.55 H · z · s`, width `B/13.7`,
  pink plume `P = 0.67 · B` (measured ratio, at both ends of the scene) plus a 0.5·B grey trail.
  The zoom-out actually starts inside 2a: z 1.0 → 0.29 over 11.95–13.3 (`InOutSine`), across the
  continuous boundary, about the pivot (0.50, 0.77), fitted to the tip (0.08 → 0.57) and the plume
  start (0.63 → 0.73). The tilt pan ends at 11.6 (measured), and the distance scale s goes
  1.0 → 0.375 during the climb. A single schedule table (10.0 / 11.6 / 11.95 / 12.5 / 13.3 / 13.4 /
  16.0) gives camera, s, tip, B, P and tilt, all consistent with the formulas (12.5: z 0.75, tip
  v 0.25, B 0.41 vs measured 0.23 / 0.37). The climb's bezier and speeds are unchanged.
- **Files affected:** `aidocs/starship/storyboard.md`

## Final Implementation Notes
- **Actual work done:** `aidocs/starship/storyboard.md` (Global: grid/units, camera, colour
  metrics, 64.0 s timeline, transitions, measurement region, particle budget with field defaults
  and the combined-peak table, reference time mapping with valid spans, easings; the 9 scenes, each
  with elements, palette, motion, particles, transitions and signature; branding reveal and loop;
  signatures summary). Doc pointers: one row each in CLAUDE.md and AGENTS.md, one line in README.md.
  Scratch-only tools (never committed): `sample.py` (map_time / valid_frames / pick / measure,
  palette, features, rect and check), `fontmetrics.py`, contact-sheet scripts.
- **Deviations from plan:**
  - Step 1: `make headless` uses a fixed 120×40 grid, so the cell geometry was read from the
    rasterizer's font file instead (JetBrainsMono Nerd Font: advance 600, ascent 1020, descent −300,
    1000 upm → 14×32 px at FONT_PX 24 → 137×33 at 1080p, 274×67 at 4K, pixel aspect 0.875).
  - Step 3 (optional anim fits) was skipped. The booster fall is an eye estimate from 1 s frames
    (marked as such). The 2b climb was measured instead by tracking the rocket tip in the valid
    frames (bezier fit, rmse 0.005).
  - Step 6: README needed no blob staging. The other README edits had meanwhile been committed by
    another session (t3, `6dc9005`), so the working-tree diff was exactly our line.
  - Hex cap: the plan said "about 8 hex values per scene". The palette lines are 5–10 per scene,
    and with particle ramps and signature colours the distinct values are 6–15 per scene (23 for
    the four-shot catch), 100 in the doc. It is all short palette data, flagged at review, and the
    user approved.
  - Signature list: scene 10 has two signatures (before the bloom, during it) instead of one;
    2a's is deliberately loose (camera tilt).
- **Issues encountered:**
  - The hot-staging range's first frame (77.6 s) still shows the high-altitude whiteout. The
    cut-distance rule excludes it, as designed.
  - The parent's "orange flames" at hot staging: the reference shows a blue-white burst, so the
    doc follows the footage. "Clears to a starfield" at SECO is not in the reference; it was kept
    as a faint stylistic addition with no signature depending on it.
  - Two review rounds fixed: the 2b trajectory, the 2a → 2b continuity, incomplete particle
    definitions, branding contrast and reveal timing (CR1); and scene 2's sizes across the
    continuous boundary (CR2).
- **Key decisions:**
  - total 64.0 s (7680 ticks @120, 3840 @60, PERF_SECONDS 65, FRAMES 7800);
  - measurement region `v < 0.82` (the HUD band starts at row 55 of 66);
  - the "near" distance is 48 RGB;
  - near-black luma < 0.08, bright luma > 0.70;
  - cross-fades occupy the incoming scene's first d s;
  - one 5 000 pool with emitters stopped at end_A;
  - large smoke masses that must pre-exist are billow discs, not particles;
  - branding text gets a bg luma cap of 0.50 (contrast ≥ 0.438 by construction).
- **Upstream defects identified:** None
- **Notes for sibling tasks:**
  - Read the Global section first. The rules t1_3–t1_5 must follow are 1.3 (metrics), 1.5
    (transitions), 1.6 (measurement region), 1.7 (particle pool and field defaults) and 1.8 (time
    mapping, for any animatic comparison).
  - The tests should render at each signature's t and measure exactly as in section 4. Every line
    passes against the reference itself, including the ±0.5 s neighbours.
  - Scene 2 has one rocket model (`B = 0.55 H · z · s`, plume 0.67·B) and a schedule table. The
    zoom crosses the continuous 2a → 2b boundary.
  - Scene 1 at t = 0 must have no particles (the loop fade's target).
  - The scratch sampler was not committed. To re-check a changed signature, reimplement section
    1.8's valid-frames/pick rules (small, stdlib) against `.refs/starship/` after
    `frames2text.py extract`.
