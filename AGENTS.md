# NexSkill - agent guidance

These rules apply when an AI agent works in this project. This file currently
records the shared owner-facing reporting preference; add project-specific
workflow rules here as they become durable.

## Owner-facing Progress Reporting

Progress reports to the owner must be feature/functionality focused, not broad
subsystem or file/checker focused. Name the concrete capability or operating
function, for example `Web UI - Agent report output`, `Web UI - Owner decision
panel`, `Advisory router - Agent recommendation`, or `Active routing -
Controlled pilot envelope`.

Each row should include:

- `Feature / function`
- `Global progress`: `done/total - NN%` when the task set is known; otherwise
  `unknown` plus the missing evidence.
- `Lifecycle status`: one of `Planned`, `Proposal drafted`,
  `Requires approval`, `Approved`, `Spec done`, `Dev started`, `In review`,
  `Implemented`, `Verified`, `Shipped`, or `Parked`.
- `Owner task`: one of `No action`, `Requires approval`, `Approved`,
  `Deferred`, or `Blocked`.
- `Owner meaning`: one short plain-language sentence explaining why it matters.

Avoid command-by-command, file-by-file, or checker-by-checker progress reports
unless a failure changes the owner's decision. Routine closeouts should report
feature impact, verification summary, commit/SHA, pushed branch, and what
remains.
