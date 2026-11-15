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
