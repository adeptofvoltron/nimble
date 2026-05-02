# Story 7.2: Autostart Configuration (systemd + Windows Task Scheduler)

Status: done

## Story

As a user who wants Nimble to start automatically at login,
I want ready-to-use autostart configuration files for both Linux and Windows,
So that I can enable persistent daemon startup without writing service files from scratch.

## Acceptance Criteria

1. **Given** `autostart/nimble.service` exists in the template
   **When** a Linux user edits the `ExecStart` placeholders and runs `systemctl --user enable` with the path to that unit file (for example `systemctl --user enable "$(pwd)/autostart/nimble.service"` from the repository root, or any absolute path to the file), then runs `systemctl --user start nimble`
   **Then** the Nimble daemon starts automatically at graphical login and is manageable via `systemctl --user start/stop/restart nimble` (FR12, NFR18)

2. **Given** `autostart/nimble.xml` exists in the template
   **When** a Windows user edits the `<Command>` and `<Arguments>` paths and imports it via Task Scheduler (`taskschd.msc` → Action → Import Task)
   **Then** the Nimble daemon starts at login and is manageable via standard Task Scheduler controls (FR12, NFR18)

3. **Given** the autostart service is configured and the system restarts unexpectedly
   **When** the OS recovers and the user session starts
   **Then** the daemon restarts automatically without manual intervention (NFR12)
   — On Linux: `Restart=on-failure` in the unit file handles this
   — On Windows: `<RestartOnFailure>` in the XML handles this

## Tasks / Subtasks

- [x] Task 1: Create `autostart/` directory and `autostart/nimble.service` (AC: 1, 3)
  - [x] Create directory `autostart/` at repo root (same level as `nimble/`, `skills/`, `worker/`)
  - [x] Create `autostart/nimble.service` with the exact content specified in Dev Notes
  - [x] Verify the file has an `[Install]` section with `WantedBy=default.target`
  - [x] Verify `Type=simple` and `Restart=on-failure` are present

- [x] Task 2: Create `autostart/nimble.xml` Windows Task Scheduler file (AC: 2, 3)
  - [x] Create `autostart/nimble.xml` with the exact XML content specified in Dev Notes
  - [x] Verify `<LogonTrigger>` is present under `<Triggers>`
  - [x] Verify `<RunLevel>LeastPrivilege</RunLevel>` is set (NFR6)
  - [x] Verify `<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>` (no timeout)
  - [x] Verify `<RestartOnFailure>` block is present (NFR12)

- [x] Task 3: Quality gates
  - [x] Verify `autostart/nimble.service` exists at `autostart/nimble.service`
  - [x] Verify `autostart/nimble.xml` exists at `autostart/nimble.xml`
  - [x] `flake8 nimble/ tests/ worker/` — exits 0 (no Python files added; verify no accidental .py changes)
  - [x] No new Python files added anywhere

## Dev Notes

### What This Story Delivers

This is a **configuration files story**. The only deliverables are two static template files:
- `autostart/nimble.service` — systemd user service unit
- `autostart/nimble.xml` — Windows Task Scheduler task definition

**No Python code changes.** No new test files. No `nimble/` changes.

---

### Critical Design Decision: Use `nimble _run` Not `nimble start`

**Do NOT use `nimble start` as the `ExecStart` command.**

`nimble start` (in `nimble/cli/commands.py:_do_start`) forks a new subprocess via `Popen(..., start_new_session=True)` and then exits. If systemd or Task Scheduler calls `nimble start`, the launcher exits immediately — systemd loses track of the actual daemon PID and marks the service as failed.

**Use `nimble _run <repo_root>` instead.** This is the internal command (`commands.py:146`) that runs the daemon in the foreground. The process stays alive for the daemon's lifetime, which is exactly what service managers need.

---

### `autostart/nimble.service` — Complete Content

```ini
[Unit]
Description=Nimble cross-platform hotkey daemon
# Nimble requires a graphical session for X11 hotkey capture.
# Start after the graphical session is established.
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
# ────────────────────────────────────────────────────────
# SETUP REQUIRED: Replace both placeholder paths below.
#
#   <NIMBLE_BIN>   — absolute path to the nimble CLI binary.
#                    Find it with: which nimble
#                    Typical: /home/<user>/.local/bin/nimble
#
#   <REPO_ROOT>    — absolute path to the directory containing
#                    your config.yaml (your Nimble project root).
#                    Example: /home/<user>/projects/pixi
#
#   Paths with spaces: wrap each substituted path in double quotes on the
#   ExecStart= line (e.g. ExecStart="/opt/my app/nimble" _run "/home/u/my repo").
# ────────────────────────────────────────────────────────
ExecStart=<NIMBLE_BIN> _run <REPO_ROOT>
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

**Notes on the systemd unit:**
- `Type=simple` — `nimble _run` runs in the foreground; systemd tracks this PID directly
- `After=graphical-session.target` + `PartOf=graphical-session.target` — ensures X11/`$DISPLAY` is available for pynput and xdotool hotkey capture; service stops when the graphical session ends
- `Restart=on-failure` — daemon restarts automatically on crash (NFR12); `RestartSec=5` prevents a restart storm
- `WantedBy=default.target` — user-level service started at login without elevated privileges (NFR6)
- `DISPLAY` and `DBUS_SESSION_BUS_ADDRESS` are inherited from the graphical session environment automatically by systemd user services in modern desktop environments (GNOME, KDE, etc.)

**Linux user instructions (for README 7.3, but summarised here):**
```bash
# 1. Edit autostart/nimble.service — set <NIMBLE_BIN> and <REPO_ROOT>
# 2. Enable and start:
systemctl --user enable "$(pwd)/autostart/nimble.service"
systemctl --user start nimble
# 3. Verify:
systemctl --user status nimble
```

---

### `autostart/nimble.xml` — Complete Content

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Nimble cross-platform hotkey daemon — starts at login</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <!-- Task runs as the current user — no elevated privileges (NFR6) -->
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <!-- No execution time limit — daemon runs indefinitely -->
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <!-- Restart up to 3 times at 1-minute intervals on failure (NFR12) -->
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <!--
        SETUP REQUIRED: Replace both placeholder paths below.

          <NIMBLE_BIN>  — full path to nimble.exe
                          Find it with: where nimble
                          Typical: C:\Users\<user>\AppData\Local\Programs\Python\Python312\Scripts\nimble.exe

          <REPO_ROOT>   — full path to the directory containing config.yaml
                          Example: C:\Users\<user>\projects\pixi

        If a path contains spaces, quote it in <Command>, <Arguments>, and <WorkingDirectory>.
        In XML element text, escape & as &amp;.
      -->
      <Command><NIMBLE_BIN></Command>
      <Arguments>_run <REPO_ROOT></Arguments>
      <WorkingDirectory><REPO_ROOT></WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**Notes on the Windows XML:**
- `LogonTrigger` — fires when the user logs in interactively
- `LeastPrivilege` — runs with standard user token only (NFR6)
- `ExecutionTimeLimit=PT0S` — Task Scheduler imposes no timeout; daemon runs until stopped
- `RestartOnFailure` with `Count=3` / `Interval=PT1M` — auto-recovery on crash (NFR12)
- `MultipleInstancesPolicy=IgnoreNew` — prevents launching a second daemon if one is already running
- `StopIfGoingOnBatteries=false` / `DisallowStartIfOnBatteries=false` — daemon should run on laptops

**Windows user instructions (for README 7.3):**
```
1. Edit autostart\nimble.xml — set <NIMBLE_BIN> and <REPO_ROOT>
2. Open Task Scheduler (taskschd.msc)
3. Action → Import Task → select autostart\nimble.xml
4. Confirm settings and click OK
```

---

### Architecture Compliance

- `autostart/` at repo root is the canonical location per architecture (`docs/bmad_output/planning-artifacts/architecture.md`, Repository Module Structure, line 703-705)
- Both files ship in the template alongside `nimble/`, `skills/`, `worker/` — users fork the repo and these files are available immediately
- User-level service only — system-level service would require elevated privileges, violating NFR6

### Source Verification

| Requirement | Source |
|---|---|
| `nimble _run <path>` is the foreground daemon entrypoint | `nimble/cli/commands.py:146-153` |
| `nimble start` forks via `Popen(start_new_session=True)` — unsuitable for ExecStart | `nimble/cli/commands.py:121-143` |
| FR12 — autostart via systemd (Linux) + Task Scheduler (Windows) | `docs/bmad_output/planning-artifacts/epics.md:FR12` |
| NFR6 — no elevated privileges | `docs/bmad_output/planning-artifacts/epics.md:NFR6` |
| NFR12 — auto-recovery after restart | `docs/bmad_output/planning-artifacts/epics.md:NFR12` |
| NFR18 — standard start/stop/restart without daemon-specific tooling | `docs/bmad_output/planning-artifacts/epics.md:NFR18` |
| `autostart/` directory location in architecture | `docs/bmad_output/planning-artifacts/architecture.md:703-705` |

### Out of Scope for This Story

- README instructions (Story 7.3)
- macOS autostart (LaunchAgent plist) — not in FR12 or epics scope
- Any Python source changes
- Test files

### Previous Story Context

Story 7.1 (`7-1-skill-build-md-ai-authoring-contract`) created `.ai/skill-build.md` — documentation-only, no Python changes. This story follows the same pattern: config-files only, no Python. The `autostart/` directory does not yet exist.

### Next Story Context

Story 7.3 creates `README.md` with the quick-start instructions, inline skill example, security model, and links to `.ai/skill-build.md`. The README's "autostart" section will reference both `autostart/nimble.service` and `autostart/nimble.xml` created in this story.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. Pure config-file story — no Python changes required.

### Completion Notes List

- Created `autostart/` directory at repo root
- Created `autostart/nimble.service` — systemd user service unit using `nimble _run <REPO_ROOT>` as ExecStart (foreground daemon, not `nimble start` which forks and exits); `Type=simple`, `Restart=on-failure`, `WantedBy=default.target`
- Created `autostart/nimble.xml` — Windows Task Scheduler XML with `LogonTrigger`, `LeastPrivilege`, `ExecutionTimeLimit=PT0S`, `RestartOnFailure` (3 retries at 1-minute intervals)
- flake8 passes clean on `nimble/ tests/ worker/`; no Python files added
- All ACs satisfied: AC1 (nimble.service exists with correct structure), AC2 (nimble.xml exists with correct structure), AC3 (both files include failure-restart directives)

### File List

- autostart/nimble.service (new)
- autostart/nimble.xml (new)

### Review Findings

- [x] [Review][Patch] XML encoding declaration does not match on-disk encoding — fixed: `encoding="UTF-8"` in `autostart/nimble.xml`.
- [x] [Review][Patch] Path edge cases not called out in templates — fixed: SETUP comments in `autostart/nimble.service` and `autostart/nimble.xml`.
- [x] [Review][Patch] AC1 vs Dev Notes — fixed: AC1 wording aligned with `$(pwd)` / absolute-path enable flow.

## Change Log

- 2026-05-02: Created `autostart/nimble.service` and `autostart/nimble.xml` — autostart templates for systemd (Linux) and Task Scheduler (Windows)
- 2026-05-02: Code review — UTF-8 XML declaration, path/XML comment guidance, AC1 enable-path wording; story marked done
