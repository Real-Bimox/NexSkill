---
name: Verification and Testing
description: Adds and runs deterministic tests that prove the behavior claimed by a change.
---

# Verification and Testing

Prove the behavior a change claims, with deterministic, repeatable checks.

## When to use

Use this skill at the **verifying** stage, once implementation is complete.

## Process

1. For each behavior the change adds, write a test that fails without it.
2. Prefer deterministic checks over checks that depend on the network or time.
3. Run the full relevant test suite, not only the new tests.
4. Record what was run and the outcome as evidence.

## Output

Test evidence: which checks were run and whether they passed. Failed checks are
recorded, not hidden.
