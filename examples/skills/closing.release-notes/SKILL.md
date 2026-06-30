---
name: Release Notes
description: Drafts concise release notes from the verified changes and evidence so the owner can decide what ships.
---

# Release Notes

Turn verified changes into release notes the owner can act on.

## When to use

Use this skill at the **closing** stage, after review. It depends on the
`reviewing.self-review` skill's notes and the verified code change.

## Process

1. Read the verified change and the review notes.
2. Group changes by feature or function, not by file.
3. State the user or owner impact of each group in one line.
4. Flag anything that still needs an owner decision (license, release, tag).

## Output

Concise release notes focused on feature/function impact, plus a short list of
remaining owner decisions. NexSkill accelerates; it does not release or tag.
