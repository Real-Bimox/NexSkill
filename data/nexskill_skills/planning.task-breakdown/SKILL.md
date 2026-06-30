---
name: Task Breakdown
description: Breaks a development request into small, verifiable tasks before any code is written.
---

# Task Breakdown

Turn a development request into a short, ordered list of verifiable tasks
before writing any code.

## When to use

Use this skill at the **planning** stage of any non-trivial development work:
a new feature, a bug fix that touches more than one file, or a refactor.

## Process

1. State the request in one sentence.
2. List the smallest set of tasks that, when done and verified, satisfy the
   request.
3. For each task, name the single artifact it produces (a file, a test, a
   config change) and how it will be verified.
4. Mark any task that is irreversible or outward-facing so it is confirmed
   before running.

## Output

A concise implementation plan: an ordered task list where every task has a
verifiable outcome. This plan feeds the rest of the workflow.
