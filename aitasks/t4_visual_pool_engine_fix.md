---
priority: medium
effort: high
depends: []
issue_type: performance
status: Ready
labels: [effect, screensaver, tooling]
gates: [risk_evaluated]
anchor: 1
followup_kind: risk_mitigation
created_at: 2026-11-15 23:12
updated_at: 2026-11-15 23:12
---

## Origin

Risk-mitigation ("after") follow-up for t1_3, created at Step 8d after implementation landed.

## Risk addressed

unbounded visual-pool growth (root cause)

- ttfx's visual pool never frees appearances, and the screensaver re-seeds every loop, so an unconstrained continuous-colour effect grows memory without bound. · severity: high (residual low: the fixed palette bounds the reachable set at |P|² by construction, and an isolated-process saturation of all of P×P measures the byte ceiling) · → mitigation: inline pre-phase renderer_spike; visual_pool_engine_fix

## Goal

Design (and, if it holds up, implement) an engine-side fix in our ttfx fork (`beyondeye/ttfx`,
branch `feat/stub-effect`) so effects that draw their own buffer do not depend on a hand-picked
palette to keep memory bounded.

Background (verified in t1_3, see its archived plan `aiplans/archived/p1/p1_3_starship_effect_skeleton.md`):
- `ttfx/src/engine/animation.rs:228` `CharacterVisual::interned` `Box::leak`s every distinct
  `(symbol, colours, flags)` visual into a thread-local `VISUAL_POOL` for the life of the
  process. `Visual = &'static CharacterVisual`; `Terminal::render_visuals` / `emitted_visuals`
  compare **raw pointers** to decide which rows to re-emit, so freeing a visual while its
  address can still be compared (or reused by the allocator) breaks row-change detection.
- Each visual costs ~318 B (a 200 B struct, the `▀` String, two `ColorCode::Rgb(String)`s, the
  pool slot). `set_appearance` also has a 4096-slot direct-mapped memo that thrashes at
  full-screen churn (starship works around it with its own per-pair visual cache).
- starship today: fixed palette P (|P| = 317, `P_CAP` 340), worst case measured by
  `ttfx/tests/starship_pool_ceiling.rs` = 55.7 MB including the screensaver's rebuild overlap.

What to decide:
- a bounded or evictable visual path (e.g. a per-effect arena freed on rebuild, generation-
  tagged handles instead of raw pointer equality, or a direct "raw cell" visual that formats
  `(fg, bg)` on the fly without pooling) that keeps `ctx.frame()` output byte-identical for
  every existing effect (ttfx is a parity port: the goldens must not change);
- how starship would use it, and whether `P_CAP` can then be lifted;
- whether it can go upstream to omacom/ttfx.

Done when: the design is written up (aidocs/), and either implemented with the existing ttfx
test suite + starship tests green and the ceiling test re-run, or explicitly rejected with
reasons.
