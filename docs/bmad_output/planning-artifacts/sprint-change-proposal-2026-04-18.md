# Sprint Change Proposal — Cross-Platform Context Capture (Windows + macOS)

**Date:** 2026-04-18
**Author:** Bernard
**Scope:** Moderate — backlog addition + PRD/Architecture update

---

## Section 1: Issue Summary

**Problem:** `build_context()` in `nimble/context/assembler.py` returns empty strings for `selection`, `clipboard`, and `active_app` on Windows and macOS. All three helpers guard with `if sys.platform != "linux": return ""`. Only `mouse_position` works cross-platform.

**Discovery:** Story 2.4 was completed with this limitation explicitly documented as "valid v1 behavior — Windows context enrichment deferred." The user has now decided to address it, and has expanded scope to include macOS (previously absent from the PRD entirely).

**Evidence:** `nimble/context/assembler.py:9,25,40` — three explicit platform guards. Story 2.4 dev notes confirm the deferral was intentional.

---

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 2 (A Hotkey Fires a Skill): Story 2.4 done and untouched — new Story 2.10 added to backlog
- Epic 4 (Reliability): Story 4.6 expanded to include macOS Accessibility edge case

**Artifact Conflicts:**
- **PRD:** macOS was out of scope — updated executive summary, FR1, OS-Level Constraints, risk table, journey summary
- **Architecture:** Technical constraints and module structure updated to include macOS adapter and context capture tools
- **Epics:** Epic 2 description updated; Story 4.6 title and AC expanded; Story 2.10 added

**Technical Impact:**
- `nimble/context/assembler.py` — three helpers need Windows + macOS branches
- `nimble/hotkeys/macos.py` — new file (pynput-based, mirrors `windows.py`)
- `nimble/hotkeys/__init__.py` — factory needs `darwin` platform branch
- No new pip dependencies for baseline implementation (uses subprocess + stdlib ctypes)

---

## Section 3: Recommended Approach

**Option 1: Direct Adjustment** ✅ Selected

Add Story 2.10 to Epic 2 backlog. Implement Windows and macOS context capture in `assembler.py` without touching the done Story 2.4. Also add `macos.py` hotkey adapter (minimal — pynput handles macOS natively).

**Rationale:**
- No rollback needed — Story 2.4 implementation is correct and reusable
- No MVP reduction — this is additive scope
- Bounded effort: `assembler.py` changes are isolated; no IPC contract changes; no architectural restructuring
- Zero new pip dependencies for baseline (PowerShell, pbpaste, osascript, ctypes are all stdlib/OS-native)
- Clipboard simulation for `selection` is the pragmatic cross-platform approach used by Alfred, Raycast, and KDE Connect

**Effort:** Medium | **Risk:** Low-Medium (platform-specific subprocess calls; CI may need macOS runner)

---

## Section 4: Detailed Change Proposals

### PRD (`docs/bmad_output/planning-artifacts/prd.md`) ✅ Applied

| Section | Change |
|---|---|
| Executive Summary | "Linux + Windows" → "Linux, Windows, and macOS" throughout |
| Differentiator #2 | Updated to name all three platforms and updated competitor analysis |
| FR1 | Added macOS to supported platforms |
| OS-Level Constraints | Added macOS block documenting pbpaste/osascript/clipboard simulation |
| Known Operational Risks | Added two macOS rows (Accessibility, Gatekeeper) |
| Journey Requirements Summary | Updated cross-platform row |

### Architecture (`docs/bmad_output/planning-artifacts/architecture.md`) ✅ Applied

| Section | Change |
|---|---|
| Technical Constraints | Added pynput for macOS, osascript for notifications, macOS context capture tools |
| Module Structure | Added `macos.py` to `hotkeys/` directory |

### Epics (`docs/bmad_output/planning-artifacts/epics.md`) ✅ Applied

| Item | Change |
|---|---|
| Epic 2 description | Added "on Linux, Windows, or macOS" |
| Story 4.6 title | Added "macOS Accessibility" |
| Story 4.6 AC | Added macOS Accessibility one-time INFO log AC |
| Story 2.10 | New story added — full cross-platform context capture spec |

---

## Section 5: Implementation Handoff

**Scope classification: Moderate** — backlog addition + docs updated; no strategic replan needed.

**Next steps for Developer agent:**

1. **Story 2.10** — implement in `nimble/context/assembler.py`:
   - `_get_clipboard()`: add `elif sys.platform == "win32"` (PowerShell `Get-Clipboard`) and `elif sys.platform == "darwin"` (`pbpaste`)
   - `_get_active_app()`: add Windows branch (ctypes `GetForegroundWindow` + `GetWindowTextW`) and macOS branch (`osascript`)
   - `_get_selection()`: add Windows branch (clipboard simulation via `pynput` keyboard + ctypes clipboard read) and macOS branch (clipboard simulation via `pynput` keyboard + `pbpaste`)
   - All new branches: `try/except Exception` → `""`, `timeout=0.1` on subprocess calls

2. **macOS hotkey adapter** — create `nimble/hotkeys/macos.py` (copy `windows.py` structure, remove Win32-reserved hotkey warning logic, add darwin platform guard)

3. **Factory update** — `nimble/hotkeys/__init__.py`: add `elif sys.platform == "darwin": return MacOSHotkeyAdapter()`

4. **Tests** — extend `tests/unit/context/test_assembler.py` with mocked Windows and macOS branches; add `tests/unit/hotkeys/test_macos_adapter.py`

**Success criteria:**
- `build_context()` returns non-empty `clipboard`, `active_app`, and `selection` on Windows and macOS when content/text is available
- All existing 31 tests continue to pass
- New platform branches fully mocked in CI (no real OS APIs in tests)
- `mypy --strict`, `black`, `flake8` all green
