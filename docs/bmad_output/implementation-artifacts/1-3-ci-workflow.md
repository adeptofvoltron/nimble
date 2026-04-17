# Story 1.3: CI Workflow

Status: done

## Story

As a maintainer,
I want a GitHub Actions workflow that runs linting, typechecking, and tests automatically on every push and pull request,
So that regressions are caught before merging and the codebase always stays in a verifiable state.

## Acceptance Criteria

1. **Given** `.github/workflows/ci.yml` exists
   **When** a push or pull request event fires on any branch
   **Then** the workflow runs three jobs in sequence: `lint` (flake8), `typecheck` (mypy), and `test` (pytest)

2. **Given** the lint job runs
   **When** any Python file in `nimble/` or `tests/` violates flake8 rules
   **Then** the job fails with a non-zero exit code and the workflow is marked failed

3. **Given** the typecheck job runs
   **When** any type annotation error exists under `mypy --strict`
   **Then** the job fails and blocks the pull request

4. **Given** the test job runs
   **When** all tests pass
   **Then** the workflow completes successfully and reports a green status check on the commit

## Tasks / Subtasks

- [x] Task 1: Create `.github/workflows/ci.yml` (all ACs)
  - [x] Create `.github/` and `.github/workflows/` directories
  - [x] Trigger on both `push` and `pull_request` for all branches (no branch filter)
  - [x] Three jobs: `lint`, `typecheck`, `test` — each with `needs` set for sequential execution
  - [x] Each job: `ubuntu-latest`, Python 3.10, install via `pip install -e ".[dev]"`
  - [x] lint job: `flake8 nimble/ tests/`
  - [x] typecheck job: `mypy nimble/` (picks up `pyproject.toml [tool.mypy]` config — `--strict` already set there)
  - [x] test job: handle exit code 5 (no tests collected) — see Dev Notes for required shell pattern
  - [x] Use `actions/checkout@v4` and `actions/setup-python@v5`

- [x] Task 2: Verify locally before pushing
  - [x] Confirm `flake8 nimble/ tests/` exits 0
  - [x] Confirm `mypy nimble/` exits 0
  - [x] Confirm `pytest || [ $? -eq 5 ]` exits 0

## Dev Notes

### Files This Story Creates

```
.github/
    workflows/
        ci.yml    ← the only deliverable
```

Nothing in `nimble/` or `tests/` is modified.

### Exact `ci.yml` Content

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -e ".[dev]"
      - run: flake8 nimble/ tests/

  typecheck:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -e ".[dev]"
      - run: mypy nimble/

  test:
    needs: typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -e ".[dev]"
      - run: pytest || [ $? -eq 5 ]
```

**Do not deviate from this structure.** Specifically:
- No pip caching step — keep it simple for v1; caching can be added later
- No matrix strategy — Python 3.10 only (minimum required per architecture)
- No `on.push.branches` filter — runs on all branches
- `needs` chains lint → typecheck → test for strict sequence
- Each job reinstalls independently (no artifact sharing) — simpler and reliable

### Why `pytest || [ $? -eq 5 ]`

From Story 1.2 dev notes: pytest exits with code 5 when no test files are collected. GitHub Actions treats any non-zero exit code as a job failure. The shell pattern `pytest || [ $? -eq 5 ]` succeeds when pytest exits 0 (tests pass) OR exits 5 (no tests collected), and fails on any other exit code (test failures = codes 1/2, errors = code 3/4). This keeps the CI green during the epic build-up period while remaining sensitive to actual failures.

### Why `mypy nimble/` (no explicit `--strict`)

`pyproject.toml` already configures `[tool.mypy]` with `strict = true` and `python_version = "3.10"`. Running `mypy nimble/` picks up that config automatically. Do NOT add `--strict` on the command line (it's redundant but harmless) or change the target to `mypy .` (that would pick up test files and community skill code outside the engine).

### Current Codebase State

At the time of this story, the nimble package contains only:
```
nimble/__init__.py
nimble/cli/              (stub — no commands yet)
nimble/hotkeys/__init__.py    (empty)
nimble/hotkeys/base.py        (HotkeyAdapter ABC)
```

All three CI commands currently pass on this codebase. No pynput imports exist anywhere — that concern (deferred from Story 1.1 code review) does not affect this story. The ABC boundary in `nimble/hotkeys/base.py` keeps pynput out of the importable surface entirely.

### pynput and Headless CI (Important for Future Stories)

From deferred-work.md: pynput raises `ImportError` on headless Linux without `DISPLAY`. This CI workflow runs on `ubuntu-latest` which has no display server. This is NOT a concern for this story because nothing imports pynput yet. When `nimble/hotkeys/x11.py` is created in Story 2.2, it will import pynput — that story must ensure pynput is only imported via the platform factory (lazy import pattern or conditional import behind `if sys.platform == "linux"`), or CI must set `DISPLAY` or mock pynput. That deferred concern is for Story 2.2, not here.

### Architecture Compliance

| Rule | How applied |
|---|---|
| `flake8 nimble/ tests/` | Direct command — same targets as Story 1.1 validated locally |
| `mypy nimble/` with `--strict` | Config in `pyproject.toml` — `strict = true` already set |
| `pytest` with `testpaths = ["tests"]` | Config in `pyproject.toml` — no CLI override needed |
| `pip install -e ".[dev]"` | Same install command as all prior stories |
| Python 3.10 minimum | `python-version: "3.10"` in setup-python step |

### Cross-Story Context

- **Story 1.1** established `pyproject.toml` with all tool config (black, flake8, mypy, pytest). CI simply invokes those same commands.
- **Story 1.2** confirmed `mypy nimble/` and `flake8 nimble/ tests/` both exit 0 on current codebase; pytest exits 5 (no tests). All three are safe to run in CI now.
- **Story 2.x+** will add pynput imports in concrete adapter files — see pynput note above. This CI workflow needs no changes until that concern materialises.
- **This story creates NO test files** — the exit code 5 pattern is the correct solution, not adding a dummy test.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Created `.github/workflows/ci.yml` with exact structure from Dev Notes: three sequential jobs (lint → typecheck → test) triggered on push and pull_request.
- Verified locally: `flake8 nimble/ tests/` exits 0, `mypy nimble/` reports no issues (5 source files), `pytest || [ $? -eq 5 ]` exits 0 (no tests collected, exit 5 handled correctly).
- No deviations from specified ci.yml content. No pip caching, no matrix, no branch filters.

### File List

- `.github/workflows/ci.yml` (new)

## Change Log

- 2026-04-17: Story 1.3 created — CI workflow for lint, typecheck, and test jobs.
- 2026-04-17: Implemented `.github/workflows/ci.yml`; all local verification checks pass.
