# Workspace for developing Omarchy screensaver effects.
# Docs: aidocs/workspace/dev_workspace.md, aidocs/testing/manual_testing.md
#
#   make setup              init the submodules, put them on their branches, add upstream remotes
#   make use-forks          point the submodules at your own GitHub forks (ARGS="--user LOGIN --no-fork")
#   make sync               after git pull: fetch all remotes and check out the pinned submodule commits
#   make try  [EFFECT=stub] play an effect in this terminal (ttfx only, fast loop)
#             [TTFX_ARGS=...] ttfx options before the effect, e.g. full screen:
#                             TTFX_ARGS="--canvas-width 0 --canvas-height 0 --frame-rate 60"
#             [EFFECT_ARGS=...] options of the effect itself, e.g. "--start-at 16"
#   make run  [EFFECT=stub] launch the real screensaver overlay with that effect
#   make headless [EFFECT=stub] [FRAMES=120 COLS=120 ROWS=40]  render it without a display (smoke test)
#   make perf [EFFECT=stub] [RES=1080p|4k] [PERF_SECONDS=65] [PERF_SEED=1|entropy]
#                           tick-time distribution over a whole timeline (benches/timeline.rs)
#   make check              cargo tests in both repos
#   make status             git status of both clones

EFFECT ?= stub
TTFX_ARGS   ?=
EFFECT_ARGS ?=
FRAMES ?= 120
COLS   ?= 120
ROWS   ?= 40
RES    ?= 1080p
# starship's timeline is 64 s (TOTAL_SECONDS in ttfx/src/effects/starship/timeline.rs);
# + 1 s measures the rebuild tick and the restarted first scene. Keep in sync.
PERF_SECONDS ?= 65
PERF_SEED    ?= 1
TTFX   := ttfx/target/release/ttfx
SAVER  := omarchy-screensaver/build/rust/release/omarchy-launch-screensaver
TEXT   := $(firstword $(wildcard $(HOME)/.config/omarchy/branding/screensaver.txt) omarchy-screensaver/assets/screensaver.txt)

.PHONY: setup use-forks sync try run headless perf check status

setup:
	git submodule update --init
	@for r in ttfx omarchy-screensaver; do \
	  b=$$(git config -f .gitmodules submodule.$$r.branch); \
	  git -C $$r switch -q $$b 2>/dev/null || git -C $$r switch -q -c $$b --track origin/$$b; \
	  u=$$(git config -f .gitmodules submodule.$$r.upstream); \
	  git -C $$r remote get-url upstream >/dev/null 2>&1 || git -C $$r remote add upstream $$u; \
	done
	@echo "ready: submodules on their branches, upstream remotes added (local ttfx wired in via .cargo/config.toml)"

# Work through your own GitHub forks instead of the team's (aidocs/workspace/contributing_with_forks.md).
use-forks:
	scripts/use-forks.sh $(ARGS)

# After `git pull`: fetch every remote of each submodule (so pinned commits are found
# even if only the team fork has them), check out the pins, then back onto the branches.
sync:
	@for r in ttfx omarchy-screensaver; do git -C $$r fetch -q --all; done
	git submodule update
	@$(MAKE) --no-print-directory setup

$(TTFX) ttfx-build:
	cd ttfx && cargo build --release

try: ttfx-build
	$(TTFX) $(TTFX_ARGS) $(EFFECT) $(EFFECT_ARGS) < $(TEXT)

saver-build:
	$(MAKE) -C omarchy-screensaver

run: saver-build
	$(SAVER) force --effect $(EFFECT)

headless: saver-build
	$(SAVER) --headless --effect $(EFFECT) --frames $(FRAMES) --cols $(COLS) --rows $(ROWS)

# Env vars such as TTFX_STARSHIP_STRESS=1 pass through to the effect.
perf:
	@case "$(RES)" in 1080p) w=1920; h=1080;; 4k) w=3840; h=2160;; \
	  *) echo "RES must be 1080p or 4k" >&2; exit 2;; esac; \
	cd omarchy-screensaver && CARGO_TARGET_DIR=build/rust SSAVER_BENCH_EFFECT=$(EFFECT) \
	  SSAVER_BENCH_WIDTH=$$w SSAVER_BENCH_HEIGHT=$$h SSAVER_BENCH_SCALE=1 \
	  SSAVER_BENCH_SECONDS=$(PERF_SECONDS) SSAVER_BENCH_SEED=$(PERF_SEED) \
	  cargo bench --bench timeline

check:
	cd ttfx && cargo test --release
	$(MAKE) -C omarchy-screensaver check

status:
	@for r in ttfx omarchy-screensaver; do echo "== $$r ($$(git -C $$r branch --show-current))"; git -C $$r status --short; done

.PHONY: ttfx-build saver-build
