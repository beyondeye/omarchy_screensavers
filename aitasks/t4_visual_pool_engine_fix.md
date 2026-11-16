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

## Inbox
<!-- Appended by the note framework. Do not edit by hand; use `./ait note`. -->

> **✉ note:t1_5** id=2026-11-16T20:32:56Z.72f1f1241b8868a41108d1fd from=t1_5 from_verified=yes at=2026-11-16T20:32:56Z base=ab2945c2571cd1cb1859def47a6922ea853963c5 base_branch=main dirty=yes host=omg16
>
> | Advisory, from t1_5, as of ttfx 228fd59. Numbers relevant to the engine-side visual-pool fix:
> | 
> | - The engine interns a default CharacterVisual per distinct input symbol (Animation::new ->
> |   CharacterVisual::interned, engine/animation.rs:594-605). A 4K grid filled with 18 358 distinct
> |   symbols measures 62.87 MB of the 64 MB gate (build 16.7 MB; P x P at |P| = 317), with no
> |   effect-side glyphs at all. starship therefore counts these defaults in its text budget
> |   (text.rs SYMBOL_BUDGET = 10 240, combined with the glyph appearances).
> | - starship now emits glyph cells (the input's own symbols) with colours from fixed per-tier
> |   sets, plus a second visual cache keyed by (symbol, fg, bg). Like the existing per-pair cache,
> |   it holds only pointers the engine already interned, and it works around set_appearance's
> |   4096-slot memo at heavy churn.
> | - palette: |P| = 317 (cap 320; the cube and the placeholder were removed). The ceiling test is
> |   now a fresh-process case runner (tests/starship_pool_ceiling.rs, 5 cases) and could serve as
> |   the harness for measuring an engine fix.
