---
title: 'Fix flake8 E501 violations in nimble/ and tests/'
type: 'chore'
created: '2026-05-01'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** Four E501 (line too long) violations in `nimble/manifest/parser.py` and `tests/unit/manifest/test_parser.py` caused flake8 to exit non-zero, blocking CI.

**Approach:** Split each offending line using implicit string concatenation (for f-strings) or multi-line call formatting (for the test), preserving exact runtime semantics.

## Suggested Review Order

- [`nimble/manifest/parser.py:48-50`](../../nimble/manifest/parser.py) — f-string split for list-of-strings error message
- [`nimble/manifest/parser.py:244-252`](../../nimble/manifest/parser.py) — two f-string splits for api_version error messages
- [`tests/unit/manifest/test_parser.py:410-412`](../../tests/unit/manifest/test_parser.py) — reformatted `.replace()` call, no semantic change
