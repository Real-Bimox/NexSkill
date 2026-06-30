---
name: Summary Only
description: Produces a minimal closeout summary without release notes, for changes that are not released.
---

# Summary Only

A minimal closeout for changes that are internal and not released.

## When to use

Use this skill at the **closing** stage when a change is not being released and
release notes are not needed. It conflicts with `closing.release-notes`: pick one
closeout style per change.

## Process

1. Confirm the change is internal and not headed for a release.
2. Summarize what changed and what was verified.
3. Note any follow-up the owner should be aware of.

## Output

A short closeout summary. No release notes, because the change does not ship.
