---
name: Self Review
description: Reviews a change against the task, the plan, and the surrounding conventions before handing off.
---

# Self Review

Review your own change before it reaches a checkpoint.

## When to use

Use this skill at the **verifying** stage, once a code change exists but before
closeout. It is a self-check, not a substitute for the owner or project review.

## Process

1. Re-read the task and the approved plan, and confirm the change addresses them.
2. Walk the diff against the surrounding code: naming, structure, and idioms.
3. List anything that is incomplete, risky, or unverified, with the evidence.
4. Run the relevant check or test and attach the outcome.

## Output

A short, plain-language review note: what was checked, what passed, what still
needs attention. Attach the deterministic check outcome where one exists.
