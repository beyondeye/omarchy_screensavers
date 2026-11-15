# Workspace for developing Omarchy screensaver effects.
# Docs: aidocs/workspace/dev_workspace.md, aidocs/testing/manual_testing.md
#
#   make setup              init the submodules, put them on their branches, add upstream remotes
#   make use-forks          point the submodules at your own GitHub forks (ARGS="--user LOGIN --no-fork")
#   make sync               after git pull: fetch all remotes and check out the pinned submodule commits
#   make try  [EFFECT=stub] play an effect in this terminal (ttfx only, fast loop)
#   make run  [EFFECT=stub] launch the real screensaver overlay with that effect
#   make headless [EFFECT=stub]  render it without a display (smoke test)
#   make check              cargo tests in both repos
#   make status             git status of both clones

EFFECT ?= stub
TTFX   := ttfx/target/release/ttfx
SAVER  := omarchy-screensaver/build/rust/release/omarchy-launch-screensaver
TEXT   := $(firstword $(wildcard $(HOME)/.config/omarchy/branding/screensaver.txt) omarchy-screensaver/assets/screensaver.txt)

.PHONY: setup use-forks sync try run headless check status

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
	$(TTFX) $(EFFECT) < $(TEXT)

saver-build:
	$(MAKE) -C omarchy-screensaver

run: saver-build
	$(SAVER) force --effect $(EFFECT)

headless: saver-build
	$(SAVER) --headless --effect $(EFFECT) --frames 120 --cols 120 --rows 40

check:
	cd ttfx && cargo test --release
	$(MAKE) -C omarchy-screensaver check

status:
	@for r in ttfx omarchy-screensaver; do echo "== $$r ($$(git -C $$r branch --show-current))"; git -C $$r status --short; done

.PHONY: ttfx-build saver-build
