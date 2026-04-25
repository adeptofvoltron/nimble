---
title: 'Hello World skill: use popup tool'
type: 'refactor'
created: '2026-04-25'
status: 'done'
route: 'one-shot'
---

# Hello World skill: use popup tool

## Intent

**Problem:** The `HelloWorldSkill` directly imported and called `plyer` for its notification, bypassing the `tools.popup.show()` primitive added in Story 3.2 — leaving duplicate notification logic in userland that the tool layer is meant to own.

**Approach:** Replace the inline plyer call with a single `tools.popup.show(...)` delegation; the tool already handles exceptions and logging.

## Suggested Review Order

- Entry point: the only changed line — delegating to the tool layer instead of calling plyer directly.
  [`skill.py:5`](../../../skills/hello_world/skill.py#L5)

- Tool contract: confirms `show()` catches all exceptions internally, so the try/except wrapper was truly redundant.
  [`popup.py:9`](../../../nimble/tools/popup.py#L9)
