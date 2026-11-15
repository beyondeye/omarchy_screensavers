# Starship storyboard

The numeric spec for the `starship` effect: a 64 s procedural animation of the
Starship Flight 15 mission, from liftoff to the tower catch, followed by the
branding reveal. The effect children (t1_3 skeleton and scenes 1–3, t1_4 space
scenes, t1_5 catch, branding and perf) implement this document and test against
its signature lines.

It is **numbers and words only**. Every colour is a hex value sampled from the
local reference animatic (`aidocs/starship/reference_tooling.md`). Nothing else
derived from the video's pixels is in this repo. Positions and sizes come from
1 s frame grabs at 137×66 and are approximate (≈); treat them as starting values
to tune against the animatic, not as measurements.

Scenes 7 and 8 of the original task (the booster's descent and landing) are
**not in this effect**: after hot staging the booster just falls out of frame.
The webcast HUD (timer, gauges, logos) is not drawn.

## 1. Global

### 1.1 Grid and units

| Quantity | Value |
|---|---|
| Reference grid | 137×33 cells (1920×1080 at scale 1) → 137×66 half-block pixels |
| Cell size | 14×32 screen px (`FONT_PX = 24`, JetBrainsMono Nerd Font: advance 600, ascent+descent 1320 per 1000 em) |
| Half-block pixel | 14×16 screen px, aspect w/h = **0.875** |
| Other grids | 2560×1440 → 182×45; 3840×2160 → 274×67 (same cell, scale 1) |
| `H` | the screen height; **all lengths are in H** |
| `A` | screen aspect = cols·14 / (rows·32): 1.816 at 1080p, 1.789 at 4K |

- **Positions** are given as normalised screen coordinates `(u, v)`, both in
  `[0, 1)`, with the origin at the top-left and `v` pointing **down**. World
  coordinates in H are `x = u·A`, `y = v`.
- Converting to half-block pixels: `px_x = x · rows·32/14`, `px_y = y · 2·rows`.
  At 1080p that is 75.4 px per H horizontally and 66 px per H vertically, so a
  circle of radius r H spans 2r·75.4 × 2r·66 pixels. Draw in H and let the
  aspect correction happen in one place.
- **Speeds** are in H/s of storyboard (screen) time, followed by px/s at the
  137×66 reference in brackets (vertical: × 66; horizontal: × 75.4).
- The rocket is 123 m tall (booster 71 m + ship 52 m) and 9 m across, an
  aspect of **13.7**. The booster is 0.577 of the stack and the ship 0.423.
  The tower is ≈146 m (1.19 × the stack).

### 1.2 Camera

Each shot has a 2-D camera: `pan (u, v)`, `zoom` (1.0 = the shot's framing
below) and `shake`. Shake is a sum of two sines per axis at the given frequency
and frequency × 1.7, amplitude in H, seeded phase from `ctx.rng`. Camera moves
use the easing named in the shot. A shot with no camera line is static.

### 1.3 Colour metrics (shared by the reference check and the effect tests)

- **near**: a pixel is near `#rrggbb` when the RGB Euclidean distance (0–255
  per channel) is **≤ 48**.
- **near-black**: Rec.709 luma `(0.2126 R + 0.7152 G + 0.0722 B)/255 < 0.08`.
- **bright**: the same luma `> 0.70`.
- All fractions are over **half-block pixels** (a cell contributes its fg as the
  top pixel and its bg as the bottom pixel), counted only inside the
  measurement region (1.6).

### 1.4 Timeline

The total is **64.0 s**: 58.0 s of scenes plus 6.0 s for the branding reveal
and the loop fade. At 120 fps (the screensaver) that is **7680 ticks**; at
60 fps (`ttfx` CLI default) **3840 ticks**. The effect returns `None` on the
tick after the last one. Bench and headless sizes derived from it:
`PERF_SECONDS = 65` (total + 1 s, so the rebuild tick and the restarted scene 1
are measured) and `FRAMES = 7800` (total × 120 + 120).

| # | Scene | Start s | Dur s | Sub-shots (dur s) | Into next |
|---|---|---|---|---|---|
| 1 | Liftoff | 0.0 | 10.0 | 1a pad wide (6.0), 1b aerial (4.0) | cross-fade 0.5 |
| 2 | Ascent | 10.0 | 6.0 | 2a tilt-up to the rocket over the horizon (2.5), 2b small rocket climbing (3.5) | cut |
| 3 | Onboard | 16.0 | 6.0 | | cut |
| 4 | High altitude | 22.0 | 3.0 | | cut |
| 5 | Hot staging | 25.0 | 5.0 | | cross-fade 1.0 |
| 6 | Coast | 30.0 | 5.0 | | cut |
| 9 | Ship over Earth | 35.0 | 4.0 | | cut |
| 10 | SECO | 39.0 | 6.0 | | cut |
| 11 | Catch | 45.0 | 13.0 | 11a wide (2.0), 11b descent and catch (4.5), 11c top-down (2.5), 11d wide caught (4.0) | continuous |
| B | Branding | 58.0 | 6.0 | form (1.5), hold (3.0), fade to scene 1's first frame (1.5) | loop (`None`) |
| | **Total** | | **64.0** | | |

The durations follow the animatic (60.4 s), with coast and SECO each 1.0 s
shorter and the catch 0.3 s shorter so that the branding fits.

Boundaries between sub-shots inside a scene are **hard cuts** (1a → 1b,
11a → 11b → 11c → 11d), with **one exception: 2a → 2b is continuous**. It is a
single camera move, so nothing is blended or cleared at 12.5 s. Particles and
billow discs carry over.

### 1.5 Transitions

- **Cut**: the next scene's first tick is drawn with no blending. At a cut every
  live particle of the outgoing shot is killed (1.7).
- **Cross-fade of length d** (1→2: 0.5 s; 5→6: 1.0 s): it occupies the
  **first d seconds of the incoming scene**. The outgoing scene keeps running
  its own clock past its nominal end, and the output is
  `mix(A, B, w)` per pixel with `w = InOutSine((t − start_B)/d)`, running
  monotonically from 0 to 1. `scene_at(t)` already reports B inside the window.
- **Continuous** (2a → 2b inside scene 2, and 11d → B): the same world keeps
  running with no blend and no pool clear. B adds the reveal on top of scene
  11's last shot.
- **Loop fade** (end of B): 1.5 s, `InOutSine`, from the branding frame to
  scene 1's frame at t = 0 (2.1). The last tick before `None` differs from scene 1's
  first frame by less than the tests' per-tick step limit, so the rebuild shows
  no flash.

### 1.6 Measurement region

The reference has a webcast HUD in its bottom band: the per-row luma drops from
row 55 of 66 in every scene. Signatures are therefore measured only in the
normalised rectangle

    u ∈ [0, 1),  v ∈ [0, 0.82)

and the pixel is counted when its **centre** lies inside (at 66 pixel rows:
rows 0–53). The denominator is the number of pixels in the region. **The same
region is used on both sides**: by the reference self-check and by the effect's
tests in t1_3–t1_5, at any grid size. The effect draws the full screen (it has
no HUD), and what it draws below `v = 0.82` is not constrained by any
signature. No scene overrides the default region.

### 1.7 Particle budget

5 000 is a **global cap on live particles at any tick**: the load that t1_3's
renderer spike measures. It is not a per-scene figure.

- One pool with a fixed capacity of 5 000, allocated in `build`. A spawn when
  the pool is full is dropped (deterministically: the pool is filled in order
  and the RNG is still advanced, so `--seed` runs stay identical).
- At the start of a cross-fade (= the end of scene A) A's emitters **stop
  spawning**. Its surviving particles fade with `1 − w` and are **killed at
  the end of the fade**.
- The incoming scene's emitters start from zero, so during the first d s it
  holds at most `rate_B × d` particles. Large smoke masses that must already be
  on screen when a shot starts (2a's smoke column, B's smoke) are drawn as
  **billow discs** (noise-modulated filled circles, not particles), with
  particles only for edge detail.
- At a hard cut the pool is cleared. At a continuous boundary it is not.

**Particle system fields.** Every system in section 2 states all of these:
*spawn rate* (/s), *life* (s), *velocity* (H/s and direction), *size* (px,
birth → death), *colour ramp* (birth → … → death), *drag* (/s, velocity × e^(−drag·t))
and *buoyancy* (H/s², negative = upward), and *peak* (live count). Shared
defaults, which apply only where a line does not say otherwise:

- the spawn point is jittered ±0.01 H around the emitter;
- life and speed are jittered ±20 %, direction ±15°, all from `ctx.rng`;
- size and colour interpolate linearly over life, with the ramp stops evenly
  spaced;
- alpha runs 1 → 0 with `OutQuad` over life (a particle is never cut off at full
  opacity);
- a particle is one half-block pixel per 1 px of size (a disc for size ≥ 2),
  alpha-blended over the scene.

Combined peaks during the overlaps (each scene's own peak is in its section):

| Overlap | A at end_A | B within d | Total |
|---|---|---|---|
| 1 → 2 (0.5 s) | 3 000 | 450 | 3 450 |
| 5 → 6 (1.0 s) | 500 | 150 | 650 |
| 11d → B (continuous: one smoke system, counted once) | 3 200 | 0 | 3 200 |
| B → loop (1.5 s; scene 1 at t = 0 has no particles) | 3 200 | 0 | 3 200 |

Every row is ≤ 5 000; the largest single-scene peak is scene 1 (3 600).

### 1.8 Reference time mapping

Storyboard time maps to source video time **linearly within each sub-shot**:

    v = src_start + (t − sb_start) · factor,   factor = (src_end − src_start)/(sb_end − sb_start)

This one rule is used to choose every signature's reference frame, to convert
measured motion into screen time (screen speed = source speed × factor; screen
duration = source duration ÷ factor), and for t1_5's pacing comparison against
the animatic. Ranges are half-open.

The **valid frames** of a sub-shot are the animatic frames `k` of its scene list
entry (`tools/frames2text/scenes/starship_flight15.toml`) whose own video time
`v_k = scene.start + k · 0.1 · scene.speed` satisfies all three conditions:

- it lies inside `[src_start, src_end)`;
- it is ≥ 0.3 s from **every** cut in the cut list (11.01, 37.47, 67.30, 77.58,
  124.36, 144.01, 153.62, 179.11, 183.25, 188.12, 191.69, 219.95, 220.09, 223.72,
  231.53, 236.47, 244.04), wherever the range boundary sits. The scene list's
  ranges start slightly after real cuts (e.g. 179.15 vs 179.11);
- its storyboard time is not inside an incoming cross-fade window.

A reference frame for storyboard time t is the valid frame nearest to the mapped
`v`, and it must be within 0.5 s of storyboard time of t. Exact sub-shot
endpoints are never sampled.

| Sub-shot | Storyboard [s) | Source [s) | Scene list entry | Factor | Valid span (storyboard s) | Valid k |
|---|---|---|---|---|---|---|
| 1a | 0.0–6.0 | 0.00–11.01 | liftoff | 1.835 | 0.00–5.79 | 0–59 |
| 1b | 6.0–10.0 | 11.01–18.00 | liftoff | 1.748 | 6.19–9.90 | 63–99 |
| 2a | 10.0–12.5 | 18.00–24.00 | ascent | 2.400 | 10.53–12.40 | 4–18 |
| 2b | 12.5–16.0 | 24.00–37.40 | ascent | 3.829 | 12.52–15.86 | 19–59 |
| 3 | 16.0–22.0 | 37.50–67.25 | onboard | 4.958 | 16.10–21.85 | 1–58 |
| 4 | 22.0–25.0 | 67.35–77.50 | high_altitude | 3.383 | 22.10–24.91 | 1–29 |
| 5 | 25.0–30.0 | 77.60–85.00 | hot_staging | 1.480 | 25.20–29.86 | 2–48 |
| 6 | 30.0–35.0 | 85.00–124.30 | coast | 7.860 | 31.08–34.88 | 13–59 |
| 9 | 35.0–39.0 | 179.15–183.20 | ship_over_earth | 1.012 | 35.30–38.65 | 3–37 |
| 10 | 39.0–45.0 | 191.75–219.90 | seco | 4.692 | 39.09–44.88 | 1–69 |
| 11a | 45.0–47.0 | 220.15–223.72 | catch | 1.785 | 45.20–46.82 | 2–18 |
| 11b | 47.0–51.5 | 223.72–231.53 | catch | 1.736 | 47.22–51.27 | 22–61 |
| 11c | 51.5–54.0 | 231.53–236.47 | catch | 1.976 | 51.66–53.76 | 65–88 |
| 11d | 54.0–58.0 | 236.47–244.00 | catch | 1.883 | 54.22–57.86 | 93–131 |

The 2a/2b boundary (24.0 s of source) has no hard cut. It was set from 1 s
frames: the camera has finished tilting up and the rocket starts to shrink.
The first frame of the hot-staging range (77.6 s) still shows the end of the
high-altitude whiteout; the cut-distance rule excludes it.

### 1.9 Easings

Easings are `ttfx::utils::easing::Easing` values: the 31 named functions
(`InOutSine`, `OutCubic`, …) or `CubicBezier(x1, y1, x2, y2)`. The measured
motion fits (archived p1_1 plan, "Notes for t1_2") are given as cubic-beziers.
ttfx has no spring easing, so the catch settle uses its bezier fit.

## 2. Scenes

Each scene has the same subsections. Particle lines read: *system: spawn rate,
life, velocity, size, colour ramp (birth → death), drag / buoyancy, peak*.

### 2.1 Scene 1: Liftoff (0.0–10.0 s)

**Elements**

- *1a pad wide* (0.0–6.0): a static camera looking at the pad.
  - The stack stands at `u ≈ 0.47`, from its tip at `v ≈ 0.12` to its base at
    `v ≈ 0.75` (height 0.63 H, width 0.046 H ≈ 3–4 px).
  - Booster (lower 0.577) and ship (upper 0.423), four grid fins just below the
    interstage, and two small forward flaps near the tip.
  - The tower is a lattice column just left of the stack: `u ≈ 0.43–0.46`,
    top at `v ≈ 0.05`, bays of 0.05 H.
  - The chopstick arms stick out from the tower at `v ≈ 0.17`, 0.10 H long on
    each side, open (±15° from horizontal).
  - A low ground band from `v ≈ 0.72` down.
- *1b aerial* (6.0–10.0): a high aerial view looking down-ish over the coast.
  - The rocket climbs straight up at `u ≈ 0.52`, body 0.30 H long, with a short
    flame 0.06 H at its base.
  - One large smoke column rises from the pad (`u 0.5, v 0.75`) and leans
    up-left to (`u 0.15, v 0.05`), 0.35 H wide at the top.
  - The ground is dark marsh with water channels; the coastline is an arc in the
    upper right.

**Palette**: sky top `#23465a`, sky by the horizon `#406e88`, steel stack
`#60615a`, ground haze `#799298`, smoke light `#dacbad`, smoke shadow
`#b3a086`, flame `#e2af7b` with core `#f3d592`; 1b ground `#272929` and
`#11171b`.

**Motion**

- 1a camera: shake 0.004 H at 7 Hz from t = 0.3 s, rising to 0.008 H at 2.0 s.
- The stack rises 0.08 H over 1a (`InQuad`; ends at about 0.03 H/s, [2 px/s]).
- The smoke billows grow from nothing at t = 0 to their full size with
  `CubicBezier(0.325, 0.912, 0, 0.7)` over **3.3 s** (6.1 s of source ÷ 1.835).
  At full size they cover `u 0.05–0.95, v 0.35–0.82` on both sides of the pad.
- 1b: the rocket climbs at 0.08 H/s [5 px/s] `Linear`. The smoke column's top
  drifts up-left at 0.02 H/s.

**Particles**

- Smoke billows (1a): 0 → 900/s (ramp `OutCubic` over 1.5 s), life 4.0 s,
  velocity 0.10–0.35 H/s outward from the pad (left and right, ±25° above
  horizontal), size 1 → 4 px, `#dacbad` → `#b3a086` → `#8f785f`, alpha 1 → 0,
  drag 0.8/s, buoyancy −0.03 H/s², peak **3 400**.
- Smoke column (1b): 700/s, life 4.0 s, 0.05 H/s along the column (up-left,
  35° from vertical), size 2 → 5 px, `#d9c9b3` → `#b19e89`, drag 0.5/s,
  buoyancy −0.01 H/s², peak 2 800.
- Flames: 400/s, life 0.4 s, 0.3 H/s downward ±40°, size 1 px,
  `#f3d592` → `#e2af7b` → `#9e7f60`, drag 3.0/s, buoyancy 0, peak 160.
- Scene peak 3 600 (1a smoke and flames); live at the end of 1b: 3 000.

**Transitions**: in, from the branding fade (the loop) or the effect's start; at
t = 0 there are **no live particles** (smoke starts at t > 0). Between 1a and
1b: a hard cut. Out: cross-fade 0.5 s into 2a.

**Signature**

- 1a at t = 3.0 (source 5.58, frame k 31): near `#1e3d4e` 45 ± 15 %, near
  `#dacbad` 15 ± 12 %; near-black ≤ 30 %; bright ≥ 5 %.
- 1b at t = 8.0 (source 14.58, k 81): near `#272929` 65 ± 12 %, near `#11171b`
  60 ± 12 %, near `#d9c9b3` 11 ± 10 %; near-black ≤ 30 %; bright ≥ 3 %.

### 2.2 Scene 2: Ascent (10.0–16.0 s)

**Elements**

The whole scene uses **one rocket model**, so its sizes stay continuous across
the 2a → 2b boundary:

- the **body length** on screen is `B(t) = 0.55 H · z(t) · s(t)`, where z is the
  camera zoom and s the distance scale (both defined under Motion);
- the body width is `B / 13.7`;
- the **pink plume** directly behind the body is `P(t) = 0.67 · B(t)`, followed
  by a faint grey trail of `0.5 · B(t)` that fades to transparent.

These were measured from the valid reference frames, splitting the steel body
from the pink plume. The body is 0.55 H through the tilt and the plume
0.37 H (0.67 × body), reaching the bottom of the frame. At 15.9 s the body is
0.06 H and the plume 0.04 H, the same ratio.

- *2a* (10.0–12.5): the camera tilts up from the coast to the sky. The horizon
  line moves from `v ≈ 0.05` to `v ≈ 0.80`.
  - The rocket is vertical and centred at `u 0.50`.
  - The remaining smoke column sits lower left (billow discs, sliding down out
    of frame with the tilt).
  - The zoom-out starts here, at 11.95 (see Motion).
- *2b* (12.5–16.0, continuous from 2a): a clear blue sky, with a lighter haze
  band at the bottom (`v > 0.70`). The zoom-out finishes (to 13.3), the rocket
  holds briefly, then climbs up-right and recedes.

**Palette**: sky `#2c507a` (top) and `#305581` (bottom), mid sky `#3b6187`,
2a horizon haze `#4f6271`, steel `#7b8894`, plume `#d0b3bd`, plume edge
`#a692a0`.

**Motion**: the authoritative schedule for the whole scene. The tip
positions in the table are measured, and the curves interpolate between them.

| Time (s) | Camera | Distance scale s | Tip (u, v) | Body B | Plume P | Tilt |
|---|---|---|---|---|---|---|
| 10.0 | tilt starts, z 1.0 | 1.0 | (0.50, 0.20) | 0.55 H | 0.37 H | 0° |
| 11.6 | tilt done, z 1.0 | 1.0 | (0.50, 0.08) | 0.55 H | 0.37 H | 0° |
| 11.95 | zoom-out starts, z 1.0 | 1.0 | (0.50, 0.08) | 0.55 H | 0.37 H | 0° |
| 12.5 | z 0.75 (boundary 2a → 2b) | 1.0 | (0.50, 0.25) | 0.41 H | 0.28 H | 4° |
| 13.3 | zoom-out done, z 0.29 | 1.0 | (0.51, 0.57) | 0.16 H | 0.11 H | 10° |
| 13.4 | z 0.29, climb starts | 1.0 | (0.51, 0.57) | 0.16 H | 0.11 H | 10° |
| 16.0 | z 0.29 | 0.375 | (0.57, 0.11) | 0.06 H | 0.04 H | 20° |

- **Camera tilt** (10.0–11.6): the scene pans by −0.75 H in v, `InOutSine`.
  The rocket's tip rises on screen from v 0.20 to v 0.08 with the same easing,
  as the camera settles on it.
- **Camera zoom-out** (11.95–13.3, across the continuous boundary): z goes
  1.0 → 0.29 with `InOutSine`, about the pivot (`0.50, 0.77`). It applies to
  the whole world (rocket, horizon, haze). The pivot is fitted to the measured
  tip (0.08 → 0.57) and plume start (0.63 → 0.73). The tip's on-screen descent
  and the body's shrink in this window come from the zoom alone; the tilt grows
  0° → 10° with the same easing.
- **Climb** (13.4–16.0): the tip goes from (`0.51, 0.57`) to (`0.57, 0.11`),
  0.46 H up and 0.11 H right.
  - Progress along that line follows `CubicBezier(0.25, 0.65, 1.0, 1.0)`,
    fitted to the reference tip positions (rmse 0.005; `OutSine` is 0.042).
  - The mean speed is 0.18 H/s [11.7 px/s]. It starts at about 0.46 H/s and
    decelerates to about 0.05 H/s.
  - In source time that is 0.46 H over 9.6 s of footage = 0.047 H/s,
    consistent with the archived ≈0.04 frame-heights/s.
  - The distance scale s falls linearly 1.0 → 0.375, so B shrinks 0.16 → 0.06 H.
  - The tilt goes 10° → 20° linearly.

**Particles**

- Plume: 300/s, life 0.6 s, 0.2 H/s backwards along the rocket's axis,
  size 1 → 2 px, `#d0b3bd` → `#a692a0`, drag 1.0/s, buoyancy 0, peak 180.
- Smoke edge detail (2a only, spawned on the billow discs' rims): 300/s,
  life 1.5 s, 0.04 H/s outward from the disc centre, size 2 px,
  `#c3b2b9` → `#7d8488`, drag 0.5/s, buoyancy −0.01 H/s², peak 450. Its
  emitter stops at 12.5. The remaining particles carry over into 2b and expire
  by 14.0.
- Scene peak 630; within its first 0.5 s at most 450.

**Transitions**: in, the 0.5 s cross-fade from 1b. 2a → 2b is **continuous**
(the exception in 1.4: no blend, no pool clear). Out: a cut to 3.

**Signature**

- 2a at t = 11.5 (source 21.52, k 11): near `#3b6187` 55 ± 20 %; near-black
  ≤ 10 %; bright ≤ 5 %. The tilt changes the frame quickly, so this one is loose.
- 2b at t = 14.2 (source 30.48, k 39): near `#2b4e77` 90 ± 10 %; near-black
  ≤ 5 %; bright ≤ 3 %.

### 2.3 Scene 3: Onboard (16.0–22.0 s)

**Elements**: a fixed camera on the ship's side, looking aft and down.

- The hull is a large dark polygon on the left: (`0, 0`), (`0.45, 0`),
  (`0.63, 0.52`), (`0.30, 0.82`), (`0, 0.82`).
  - Its surface is a hexagonal heat-tile pattern: hex cells 0.03 H across,
    with 1 px darker seams.
  - A bright stainless band (the flap edge) runs along its upper-right edge,
    0.04 H wide.
- The engine end is at the apex (`0.63, 0.52`): a fire puff of radius
  0.06–0.10 H.
- The Earth's surface below fills the right of the frame: sea blue, with a
  grey-green coast region left of a boundary curve from (`0.45, 0.82`) to
  (`0.85, 0`).
- The first 0.5 s is darker (the camera's exposure settling).

**Palette**: sea `#44709b` and `#3b70a7`, deep sea `#255687`, high sky
`#355e8e`, land `#5d6570`, hull `#454448`, tiles dark `#262734`, stainless
`#eaebe4`.

**Motion**: shake 0.003 H at 11 Hz. The ground drifts down-right at 0.01 H/s.
The fire puff pulses in radius ±20 % at 3 Hz.

**Particles**: exhaust and fire: 1 200/s, life 0.8 s, 0.25 H/s away from the
apex (down-right ±20°), size 1–3 px, `#f1e9d3` → `#df9e54` → `#999fa8`, drag
1.5/s, buoyancy 0, peak **960**. Debris and ice: 60/s, life 1.0 s, 0.15 H/s
down-right ±30°, size 1 px, `#eaebe4` → `#879299`, drag 0, buoyancy 0, peak 60.
Scene peak 1 020.

**Transitions**: in a cut, out a cut.

**Signature**: at t = 19.0 (source 52.50, k 30): near `#497197` 47 ± 12 %,
near `#5d6570` 50 ± 12 %, near `#eaebe4` 4 ± 10 %; near-black ≤ 10 %;
bright ≥ 2 %.

### 2.4 Scene 4: High altitude (22.0–25.0 s)

**Elements**

- A near-black navy sky over the whole frame.
- The engine point: a white dot at (`0.50, 0.46`), radius 0.015 H, with a
  glare of radius 0.05 H.
- A pink/mauve plume trailing down from the engine to `v ≈ 0.80`: 0.04 H wide
  at the top, widening to 0.07 H.
- In the last 1.0 s the plume opens into a translucent cone (half-angle 25°,
  alpha 0.25), which the hot-staging whiteout follows.

**Palette**: sky `#0e1826` and `#0d1725`, plume `#392d3a` and `#694f5c`,
cone `#414550`, engine core `#e6e1db`.

**Motion**: the engine and plume drift up 0.01 H/s. The plume length pulses
±10 % at 2 Hz. The cone grows with `OutQuad` over the last 1.0 s.

**Particles**: plume: 1 500/s, life 1.2 s, 0.15 H/s downward, size 1–2 px,
`#e6e1db` → `#694f5c` → `#392d3a`, drag 0.6/s, buoyancy 0, peak **1 800**.

**Transitions**: in a cut, out a cut.

**Signature**: at t = 23.5 (source 72.45, k 15): near `#0d1725` 95 ± 10 %,
near `#392d3a` 25 ± 12 %; bright ≤ 2 %. `#0d1725` sits right at the
near-black threshold (luma 0.0796), so this scene has no near-black limit.

### 2.5 Scene 5: Hot staging (25.0–30.0 s)

**Elements**: the onboard framing of scenes 5 and 6 (another camera from
scene 3).

- The hull fills the left 55 %: (`0, 0`), (`0.40, 0`), (`0.66, 0.45`),
  (`0.20, 0.82`), (`0, 0.82`). It has the same hex tiles, a stainless flap edge,
  and a dark aft-flap block at (`0.08–0.22, 0.45–0.70`).
- Space is black along the bottom-right edge (`v > 0.75`).
- The atmosphere is a bright band along the Earth's limb, from the lower left to
  the right.
- The sun's glare is lower right (`0.90, 0.60`).
- **Staging burst** at t = 25.95 (source 79.0): a blue-white puff at the engine
  apex (`0.66, 0.45`). It grows to radius 0.25 H in 0.6 s (`OutCubic`) and
  disperses over 1.5 s. The reference shows it **blue-white, not orange**.
- **The booster drops away**: a dark cylinder 0.30 H × 0.04 H with glowing
  engines appears below the apex at t ≈ 27.4. It falls down-left and leaves the
  frame by t ≈ 29.8.

**Palette**: sky `#313a56`, atmosphere `#094287` and `#5a8bbf`, limb glow
`#4887ce`, hull `#1f2636`, shadow `#0d0e15`, vapour `#c9d2d9`, booster engine
glow `#e7bb68`.

**Motion**: the booster accelerates away at 0.04 → 0.20 H/s
[2.6 → 13 px/s], `InQuad`. (Estimated by eye from 1 s frames: about 0.25 H over
3.6 s of source × 1.48.) It rotates 10° anticlockwise as it falls. Shake
0.012 H at 9 Hz during the burst (25.95–26.6), 0.003 H otherwise.

**Particles**

- Burst: 2 500 spawned over 0.6 s from t = 25.95, life 1.5 s, 0.3–0.6 H/s
  radial, size 1 → 3 px, `#fafcfb` → `#c9d2d9` → `#5a8bbf`, drag 2.0/s,
  buoyancy 0, peak 2 500.
- Booster engine sparks (emitter rides on the booster's engine end, from
  27.4): 200/s, life 0.5 s, 0.08 H/s opposite the booster's fall ±30°, size
  1 px, `#e7bb68` → `#8d7581`, drag 1.0/s, buoyancy 0, peak 100.
- Ice flakes: 100/s, life 4.0 s, 0.03 H/s up-right, size 1 px,
  `#cfdce6` → `#5a8bbf`, drag 0, buoyancy 0, peak 400.
- Scene peak **3 000** (at about 26.5). Live at end: 500 (flakes and sparks; the
  burst is gone).

**Transitions**: in a cut. Out: a cross-fade of 1.0 s into 6. The framing is the
same, so only the burst remains, the booster and the sky colour change.

**Signature**: at t = 27.5 (source 81.35, k 25): near `#094287` 30 ± 12 %,
near `#1f2636` 30 ± 12 %, near `#0d0e15` 25 ± 12 %; near-black 3–25 %;
bright ≥ 1 %.

### 2.6 Scene 6: Coast (30.0–35.0 s)

**Elements**: the same framing as scene 5, with no burst and no booster.

- The sky is a deep blue upper right.
- The Earth's limb is an arc through (`0.30, 0.80`) and (`1.00, 0.58`). Its
  centre is below-right, at a radius of 2.5 × the screen width. A bright
  atmosphere band, 0.06 H thick, lies along it, with black space below it in the
  lower-right corner.
- The sun's glare is centred at (`0.95, 0.62`), radius 0.12 H, with a soft
  radial falloff.
- White ice flakes drift across the upper right (`u > 0.6, v < 0.5`).

**Palette**: sky `#0a397b` and `#0e448a`, limb `#477db9` and `#5897d9`, glare
`#8d9da6` and `#b8c9d5`, hull `#222736`, shadow `#0d0f16`.

**Motion**: the flakes drift up-right at 0.02–0.06 H/s [1.5–4.5 px/s] with
±0.01 H of jitter. The limb and glare are static. The glare breathes ±8 % at
0.3 Hz.

**Particles**: ice flakes, spawned over `u 0.55–1.0, v 0–0.55`: 150/s, life
5.0 s, 0.02–0.06 H/s up-right (30° above horizontal), size 1 px,
`#fafaf7` → `#b8c9d5`, drag 0, buoyancy 0, peak **750**. Within its first 1.0 s
at most 150.

**Transitions**: in, the 1.0 s cross-fade from 5. Out: a cut to 9.

**Signature**: at t = 33.0 (source 108.40, k 36): near `#0e448a` 30 ± 12 %,
near `#222736` 30 ± 12 %, near `#477db9` 17 ± 10 %; near-black 3–25 %;
bright ≥ 1 %.

### 2.7 Scene 9: Ship over Earth (35.0–39.0 s)

**Elements**: the camera is on the other side of the ship.

- The hull comes in from the upper left: (`0, 0`), (`0.30, 0`), (`0.62, 0.55`),
  (`0.55, 0.82`), (`0, 0.82`).
  - Its surface is dark plum tiles.
  - A bright steel flap panel sits at (`0.30–0.55, 0–0.35`).
  - A dark grey engine-bay block sits at (`0.08–0.30, 0.30–0.60`).
  - A small red navigation glow sits at (`0.02, 0.77`), radius 0.03 H.
- The Earth is a large disc behind the hull. Its visible edge runs from
  (`0.68, 0`) down to (`0.40, 0.82`) and it fills the space between that edge
  and the hull. It has ocean blue with grey-white cloud patches (value noise,
  0.05 H scale, threshold 0.55).
- Black space lies right of the edge.
- The sun is at (`0.86, 0.18`): core radius 0.04 H, glare 0.12 H, plus six
  thin radial flare spikes 0.30 H long.

**Palette**: hull `#2d2633`, deep shadow `#110d16`, engine bay `#424554`, ocean
`#61758e`, clouds `#99abb7`, space `#191421`, sun `#ddedf7` with core
`#e3edef`, nav glow `#62263c`.

**Motion**: almost static. The Earth rotates under the camera: the cloud noise
scrolls 0.01 H/s down-left. Shake 0.002 H at 5 Hz.

**Particles**: ice, spawned in the black space right of the Earth's edge: 60/s,
life 5.0 s, 0.03 H/s up-right, size 1 px, `#e2ecee` → `#99abb7`, drag 0,
buoyancy 0, peak **300**.

**Transitions**: in a cut, out a cut.

**Signature**: at t = 37.0 (source 181.15, k 20): near `#2d2633` 44 ± 12 %,
near `#110d16` 39 ± 12 %, near `#61758e` 12 ± 10 %, near `#e3edef` 7 ± 10 %;
near-black 10–35 %; bright ≥ 5 %.

### 2.8 Scene 10: SECO (39.0–45.0 s)

**Elements**

- The hull is on the left, the same shape as scene 5, lit grey.
- The Earth's limb is a thin blue arc across the top (`u 0.42–0.60, v < 0.06`).
- Black space covers the rest.
- At engine cutoff the plume **blooms**: a blue-white haze centred at the engine
  apex (`0.62, 0.55`). It grows from radius 0 to 0.60 H and fills the right half.
- After the bloom peaks, it thins: its alpha falls to 0.6 by 45.0.
- A faint starfield appears where the haze thins in the last 1.0 s: 60 stars
  with luma ≤ 0.35. The reference shows none, so this is a stylistic addition
  and no signature depends on it.

**Palette**: space `#000000` and `#010205`, hull `#444348`, limb `#6f95ab`,
haze edge `#121b2d`, haze mid `#565b67`, haze core `#d5e5e9`.

**Motion**: the bloom radius follows `CubicBezier(0.05, 0.7, 0.1, 1)` from
t = 39.05 over **4.6 s** (21.6 s of source ÷ 4.692). The haze colour ramp runs
from the core to the edge by radius.

**Particles**: bloom haze: 1 200/s from 39.05 to 43.7, life 2.5 s, 0.1–0.3 H/s
radial, size 2 → 4 px, `#d5e5e9` → `#565b67` → `#121b2d`, drag 0.7/s,
buoyancy 0, peak **3 000**. Ice: 40/s, life 2.5 s, 0.05 H/s radial from the
apex, size 1 px, `#d5e5e9` → `#565b67`, drag 0, buoyancy 0, peak 100. Scene
peak 3 100. The stars are static points, not particles.

**Transitions**: in a cut, out a cut.

**Signature**

- At t = 39.6 (source 194.55, k 7), before the bloom: near `#010205` 60 ± 15 %;
  near-black ≥ 45 %; bright ≥ 3 %.
- At t = 42.0 (source 205.75, k 35), the bloom spreading: near `#010205`
  35 ± 15 %, near `#121b2d` 37 ± 12 %; near-black 15–55 %; bright ≥ 3 %.

### 2.9 Scene 11: Catch (45.0–58.0 s)

**Elements**

- *11a wide* (45.0–47.0): an overcast sky in the top 45 %, with flat brown
  ground from the horizon at `v ≈ 0.50` down.
  - Two towers at `u ≈ 0.48` and `u ≈ 0.65`: 0.22 H and 0.20 H tall, 0.025 H
    wide, standing on the horizon.
  - The ship is a small dark streak 0.04 H long at (`0.52, 0.22`), descending
    slowly.
- *11b descent and catch* (47.0–51.5): the camera tracks the ship.
  - The ship is upper-middle at (`0.50, 0.25`), 0.35 H long, a steel cylinder
    with flaps and a short orange-pink engine flame of 0.05 H.
  - The tower rises into view from below: its top climbs from `v = 1.10` to
    `v ≈ 0.30`. It is a lattice 0.12 H wide with bays of 0.05 H.
  - The chopstick arms pivot at the tower's top-front. Each is 0.20 H long,
    open at ±35° from horizontal, and closes to ±5° around the ship
    (50.3–51.3, `OutCubic`).
- *11c top-down* (51.5–54.0): looking straight down at the steel ship.
  - It lies in the middle (`u 0.38–0.62, v 0–0.80`), with flaps at both sides of
    its top.
  - The two arms are dark lattice diagonals coming from the bottom-left and
    bottom-right and meeting under the ship.
  - Sandy ground and a water edge lie on the right.
- *11d wide caught* (54.0–58.0): the ship hangs on the tower.
  - The tower is at `u ≈ 0.67`, spanning `v 0.20–0.75` and 0.06 H wide, with
    the ship held beside it near the top.
  - A second tower is in the distance at `u ≈ 0.85` (0.10 H).
  - The sky fills the top 30 %, then a sea band, then flat ground with paths.
  - Steam rises from the tower base.

**Palette**: sky `#aaa197` and `#a8a69e`, light cloud `#c3b8ac`, ground
`#635b4d` and `#4b483d`, tower lattice `#2d2c22` and `#37352b`, ship steel
`#9a8d7c` and `#c7bbab`, mid grey `#9f9c94`. No engine flame is measurable at
137×66 (it is under one pixel), so the flame reuses scene 1's `#e2af7b` and
`#f3d592`.

**Motion**

- 11a: the ship descends at 0.02 H/s.
- 11b: the tower rises against the tracking camera and decelerates to rest at
  t = 50.33 (source 229.5). The settle is `CubicBezier(0.3, 0.866, 0, 1.078)`
  over **1.32 s** (2.3 s of source ÷ 1.736), from 49.0. It overshoots slightly,
  which is the spring with damping ≈ 0.8.
- 11c: a slow zoom-in, 1.00 → 1.05, `Linear`.
- 11d: static, with shake 0.001 H at 3 Hz.

**Particles**

- 11a exhaust (behind the falling ship): 200/s, life 0.5 s, 0.10 H/s
  downward, size 1 px, `#f3d592` → `#e2af7b`, drag 2.0/s, buoyancy 0, peak 100.
- 11b engine flame: 800/s, life 0.4 s, 0.3 H/s downward ±15°, size 1 → 2 px,
  `#f3d592` → `#e2af7b`, drag 3.0/s, buoyancy 0, peak 320.
- 11b steam and smoke (spawned along the tower's lower half): 600/s, life
  3.0 s, 0.05 H/s up, size 2 → 4 px, `#c4bcb0` → `#afaaa1`, drag 0.5/s,
  buoyancy −0.02 H/s², peak 1 800.
- 11c steam (a top-down view, so it spreads instead of rising): 300/s, life
  3.0 s, 0.03 H/s radially outward from under the ship, size 2 → 4 px,
  `#c8bcad` → `#9e9786`, drag 0.5/s, buoyancy 0, peak 900.
- 11d steam at the tower base (`0.67, 0.75`; the system B continues): 300/s,
  life 4.0 s, 0.04 H/s up ±20°, size 2 → 5 px, `#c7c0b4` → `#afaca3`, drag
  0.4/s, buoyancy −0.02 H/s², peak 1 200.
- Scene peak 2 120 (11b). The sub-shot cuts clear the pool.

**Transitions**: in a cut from 10. The four sub-shots are separated by hard
cuts. Out: continuous into B.

**Signature**

- 11a at t = 46.0 (source 221.95, k 10): near `#b2a99e` 50 ± 12 %, near
  `#6a6054` 33 ± 12 %, near `#524c3e` 22 ± 12 %; near-black ≤ 5 %; bright ≥ 8 %.
- 11b at t = 49.3 (source 227.71, k 42): near `#9f9c94` 66 ± 15 %, near
  `#ada79e` 58 ± 12 %, near `#2d2c22` 16 ± 10 %; near-black ≤ 5 %.
- 11c at t = 52.7 (source 233.83, k 76): near `#9a8d7c` 51 ± 12 %, near
  `#c7bbab` 27 ± 12 %, near `#2f2e2b` 12 ± 10 %; near-black ≤ 5 %; bright ≥ 3 %.
- 11d at t = 56.0 (source 240.31, k 112): near `#a3a39b` 52 ± 12 %, near
  `#56544a` 26 ± 12 %, near `#37352b` 25 ± 12 %; near-black ≤ 5 %; bright ≥ 3 %.

## 3. Branding reveal and loop (58.0–64.0 s)

The branding text is `~/.config/omarchy/branding/screensaver.txt`, or else
`omarchy-screensaver/assets/screensaver.txt`, which is the effect's input. Its
characters keep their own symbols at their centre-anchored input coordinates.

1. **Form (58.0–59.5)**:
   - 11d's steam system ramps up to the branding smoke, drawn as billow discs
     plus particles: spawned uniformly over the text's bounding box plus a
     margin of 2 cells, 800/s, life 4.0 s, 0.03 H/s up ±20°, size 2 → 5 px,
     `#c7c0b4` → `#afaca3`, drag 0.4/s, buoyancy −0.01 H/s², peak **3 200**.
   - Each input character gets a reveal **start** time in **[58.0, 59.25]**.
     Characters where the local smoke density is higher start earlier: rank by
     density sampled at the character's cell at 58.0, ties broken by `ctx.rng`,
     then map the rank to time with `OutCubic`.
   - A character's fade-in takes 0.25 s, so even the last one is fully visible
     at 59.5. Over the fade:
     - its fg goes from the smoke colour `#afaca3` to `#f3efe6`;
     - its bg is the scene under it (smoke included) with a **luma cap** applied
       with the same weight: `bg = c · min(1, 0.50 / luma(c))`, where c is the
       composited scene colour of the cell (the two half-block pixels averaged).

     The cap darkens a bright cell without changing its hue, and leaves darker
     cells alone. It applies only to the cells the input characters cover.
2. **Hold (59.5–62.5)**: every character is fully visible. The smoke keeps
   drifting up at 0.03 H/s and thins to alpha 0.6. Contrast is guaranteed **by
   construction**: fg luma 0.938 − capped bg luma ≤ 0.50 gives **≥ 0.438**,
   whatever is behind the text.
   - Checked against 11d's reference colours: without the cap, the default text
     box (30×5 cells at the centre: `u 0.39–0.61, v 0.42–0.58`) under 0.6-alpha
     smoke reaches only 0.30, and the whole screen 0.155 at worst. With the cap
     both are 0.438.
3. **Loop fade (62.5–64.0)**:
   - The smoke emitters stop at 62.5, and all particles fade with `1 − w` and
     are killed by 64.0.
   - Every pixel fades with `w = InOutSine((t − 62.5)/1.5)` to **scene 1's frame
     at t = 0**: the pad shot with sky, tower and stack, and no smoke or
     particles.
   - The characters' fg fades to their bg over the same window, and the luma cap
     is released with the same weight, so the end frame has no darkened text
     plate.
   - The last tick (t = 64.0 − 1 tick) differs from scene 1's first frame by
     less than the per-tick step limit. Then `next_frame` returns `None` and the
     screensaver rebuilds the effect.

**Signature** (not from the reference; the reference has no branding):

- at t = 61.0, ≥ 95 % of the input characters are drawn with their own symbol,
  with fg/bg luma contrast ≥ 0.35 (the cap gives ≥ 0.438, leaving margin);
- at t = 64.0 − 1 tick, the frame matches scene 1 at t = 0 within the per-tick
  step limit.

## 4. Signatures summary

Measured inside the region `u ∈ [0,1), v ∈ [0, 0.82)` (1.6), with the metrics
in 1.3. "Ref" is the valid reference frame chosen by the mapping (1.8).
**Every line was checked against the reference itself**: the reference frame
passes its own signature, and so do the valid frames picked at t ± 0.5 s.

| Sub-shot | t (s) | Ref (source s, k) | Colours (near, % ± tol) | Limits | Ref passes |
|---|---|---|---|---|---|
| 1a | 3.0 | 5.58, 31 | `#1e3d4e` 45±15, `#dacbad` 15±12 | near-black ≤30, bright ≥5 | yes (k 25, 31, 36) |
| 1b | 8.0 | 14.58, 81 | `#272929` 65±12, `#11171b` 60±12, `#d9c9b3` 11±10 | near-black ≤30, bright ≥3 | yes (k 76, 81, 85) |
| 2a | 11.5 | 21.52, 11 | `#3b6187` 55±20 | near-black ≤10, bright ≤5 | yes (k 7, 11, 15) |
| 2b | 14.2 | 30.48, 39 | `#2b4e77` 90±10 | near-black ≤5, bright ≤3 | yes (k 33, 39, 45) |
| 3 | 19.0 | 52.50, 30 | `#497197` 47±12, `#5d6570` 50±12, `#eaebe4` 4±10 | near-black ≤10, bright ≥2 | yes (k 25, 30, 35) |
| 4 | 23.5 | 72.45, 15 | `#0d1725` 95±10, `#392d3a` 25±12 | bright ≤2 | yes (k 10, 15, 20) |
| 5 | 27.5 | 81.35, 25 | `#094287` 30±12, `#1f2636` 30±12, `#0d0e15` 25±12 | near-black 3–25, bright ≥1 | yes (k 20, 25, 30) |
| 6 | 33.0 | 108.40, 36 | `#0e448a` 30±12, `#222736` 30±12, `#477db9` 17±10 | near-black 3–25, bright ≥1 | yes (k 30, 36, 42) |
| 9 | 37.0 | 181.15, 20 | `#2d2633` 44±12, `#110d16` 39±12, `#61758e` 12±10, `#e3edef` 7±10 | near-black 10–35, bright ≥5 | yes (k 15, 20, 25) |
| 10 | 39.6 | 194.55, 7 | `#010205` 60±15 | near-black ≥45, bright ≥3 | yes (k 1, 7, 13) |
| 10 | 42.0 | 205.75, 35 | `#010205` 35±15, `#121b2d` 37±12 | near-black 15–55, bright ≥3 | yes (k 29, 35, 41) |
| 11a | 46.0 | 221.95, 10 | `#b2a99e` 50±12, `#6a6054` 33±12, `#524c3e` 22±12 | near-black ≤5, bright ≥8 | yes (k 5, 10, 15) |
| 11b | 49.3 | 227.71, 42 | `#9f9c94` 66±15, `#ada79e` 58±12, `#2d2c22` 16±10 | near-black ≤5 | yes (k 37, 42, 47) |
| 11c | 52.7 | 233.83, 76 | `#9a8d7c` 51±12, `#c7bbab` 27±12, `#2f2e2b` 12±10 | near-black ≤5, bright ≥3 | yes (k 71, 76, 82) |
| 11d | 56.0 | 240.31, 112 | `#a3a39b` 52±12, `#56544a` 26±12, `#37352b` 25±12 | near-black ≤5, bright ≥3 | yes (k 106, 112, 117) |
| B | 61.0 | none | ≥95 % of the input characters visible | fg/bg luma contrast ≥0.35 | n/a |

Colour fractions overlap: one pixel can be near two listed colours, so the
fractions of one line need not add up to 100 %. A procedural scene meets a line
when its fractions fall inside the tolerances at the test time. The tests in
t1_3–t1_5 render the effect at the listed t and measure it exactly as above.
Changing a signature means re-checking it against the reference the same way.
