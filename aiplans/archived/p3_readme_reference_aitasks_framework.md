---
Task: t3_readme_reference_aitasks_framework.md
Created by: aitask-wrap (retroactive documentation)
---

## Summary

Document in the root README that the project is developed with the aitasks framework, and add the Starship reference tooling doc to the README's documentation list.

## Files Modified

- `README.md`: new "Development workflow" section before the documentation list. It describes aitasks (task files in `aitasks/`, plans in `aiplans/`, agents working through the framework's skills) and the `./ait` entry point: `./ait setup`, `./ait board`, and `./ait ide` (starts the tmux session and launches `ait monitor`). Also adds a link to `aidocs/starship/reference_tooling.md` in the documentation list (an earlier uncommitted change included in this wrap).

## Probable User Intent

Make the framework used for development visible to readers of the repo, including the `ait ide` one-command startup for running and watching agents.

## Final Implementation Notes

- **Actual work done:** Added the "Development workflow" section and the Starship doc link to `README.md`.
- **Deviations from plan:** N/A (retroactive wrap, no prior plan existed)
- **Issues encountered:** N/A (changes were already made before wrapping)
- **Key decisions:** `./ait board` and `./ait ide` were verified against `./ait help` / `./ait ide --help`. The aitasks GitHub URL was written from memory and is unverified.
