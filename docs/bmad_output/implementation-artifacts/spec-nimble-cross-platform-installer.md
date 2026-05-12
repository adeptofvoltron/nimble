---
title: 'Nimble Cross-Platform Installer'
type: 'feature'
created: '2026-05-12'
status: 'done'
baseline_commit: 'd451d00315a1dc67b4897c4450bf71824c2895f4'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nimble has no user-facing install mechanism — the only path to a working binary is `pip install -e ".[dev]"` in a cloned repo, requiring Python 3.10+ and blocking anyone without a dev environment.

**Approach:** Add a PyInstaller-based GitHub Actions release pipeline that publishes standalone binaries to GitHub Releases, and `install/install.sh` + `install/install.ps1` scripts that give any user a single-command install with no Python prerequisite.

## Boundaries & Constraints

**Always:**
- Binary targets: `linux-x64`, `darwin-x64`, `darwin-arm64`, `windows-x64` — each built natively on its platform runner (no cross-compilation)
- Default install paths: `/usr/local/bin` (Linux/Mac), `$env:ProgramFiles\Nimble` (Windows); both overridable via `NIMBLE_INSTALL_DIR`
- SHA256 checksum published alongside every binary; both scripts verify before placing binary on PATH
- Sudo/admin requirement stated upfront before any action is taken
- `aarch64` normalized to `arm64` in install.sh before constructing download URL
- WSL detected via `/proc/version` containing `Microsoft`; script prints confirmation and continues with Linux path
- All path variables double-quoted throughout both scripts
- Download failure exits non-zero and prints: `"Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry"`
- Checksum mismatch exits non-zero, deletes partial file, prints: `"Download may be corrupted — retry the install"`
- Post-install always prints: `"Nimble installed! Open a new terminal to use it."`
- GitHub Releases base URL: `https://github.com/adeptofvoltron/nimble/releases/download/`

**Ask First:**
- Adding binary targets beyond the four defined above
- Changing default install location

**Never:**
- PyPI packaging, Homebrew tap, Scoop, winget — post-launch
- `nimble update` self-update — post-launch
- `linux-arm64` target — deferred (no free native runner)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path Mac/Linux | `curl -fsSL .../install.sh \| sh`, no Python installed | Binary in `/usr/local/bin`, post-install message | — |
| Happy path Windows | `powershell -c "iwr .../install.ps1 \| iex"` | Binary on PATH, post-install message | — |
| Apple Silicon | `uname -m` returns `aarch64` | Normalized to `arm64`, correct binary fetched | — |
| WSL | `/proc/version` contains `Microsoft` | Prints WSL confirmation, continues with linux-x64 | — |
| `NIMBLE_INSTALL_DIR` set | Env var points to writable dir | Installs there, no sudo required | — |
| No sudo | User lacks sudo on Linux/Mac | Upfront warning printed, exits with `NIMBLE_INSTALL_DIR` hint | Exit non-zero |
| Corrupt/partial download | SHA256 mismatch | Partial file deleted, human-readable error printed | Exit non-zero |
| Network blocked | GitHub Releases unreachable | Proxy hint printed | Exit non-zero |
| Path with spaces/Unicode | `NIMBLE_INSTALL_DIR=/home/ján/bin` | Installs correctly via quoted paths | — |

</frozen-after-approval>

## Code Map

- `nimble/__main__.py` — new; PyInstaller entry point wrapping `nimble.cli.commands:app`
- `nimble/cli/commands.py` — existing typer app; imported by `__main__.py`
- `install/install.sh` — new; POSIX sh installer for Mac/Linux
- `install/install.ps1` — new; PowerShell installer for Windows
- `.github/workflows/release.yml` — new; matrix release workflow across 4 platforms
- `.github/workflows/ci.yml` — existing; no changes
- `pyproject.toml` — add `pyinstaller>=6.0` to `[project.optional-dependencies] dev`

## Tasks & Acceptance

**Execution:**
- [x] `nimble/__main__.py` -- create with `from nimble.cli.commands import app` and `if __name__ == "__main__": app()` -- enables both `python -m nimble` and PyInstaller targeting
- [x] `pyproject.toml` -- add `pyinstaller>=6.0` to `[project.optional-dependencies] dev` -- makes PyInstaller available in dev and CI environments
- [x] `.github/workflows/release.yml` -- create release workflow triggered on `push` to `v*` tags; matrix: `[{os: ubuntu-latest, target: linux-x64}, {os: macos-latest, target: darwin-arm64}, {os: macos-13, target: darwin-x64}, {os: windows-latest, target: windows-x64}]`; each job: checkout → setup-python 3.10 → `pip install -e ".[dev]"` → `pyinstaller --onefile --name nimble nimble/__main__.py` → rename output to `nimble-{target}` (append `.exe` on Windows) → generate SHA256 sidecar → upload both files as release assets using `softprops/action-gh-release@v2`
- [x] `install/install.sh` -- create POSIX sh installer: detect OS/arch → normalize `aarch64`→`arm64` → detect WSL → check sudo upfront with warning → fetch latest tag via GitHub API → construct download URL → download with `curl -fsSL` (fallback `wget`) → verify SHA256 → install to `${NIMBLE_INSTALL_DIR:-/usr/local/bin}` (with sudo if default path) → print post-install message
- [x] `install/install.ps1` -- create PowerShell installer: detect arch → fetch latest tag via GitHub API → download binary with `Invoke-WebRequest` → verify SHA256 via `Get-FileHash` → install to `$env:NIMBLE_INSTALL_DIR` or `$env:ProgramFiles\Nimble` → add install dir to system PATH registry key if absent → print post-install message

**Acceptance Criteria:**
- Given a published `v*` tag, when the release workflow completes, then GitHub Releases contains 8 files: `nimble-linux-x64`, `nimble-darwin-arm64`, `nimble-darwin-x64`, `nimble-windows-x64.exe` and their four `.sha256` companions
- Given `uname -m` returns `aarch64`, when install.sh runs, then it downloads `nimble-darwin-arm64` (not `nimble-darwin-aarch64`)
- Given `NIMBLE_INSTALL_DIR=~/.local/bin`, when install.sh runs, then binary is placed there and sudo is never invoked
- Given a SHA256 mismatch (simulated), when install.sh verifies, then it exits non-zero and prints the human-readable corruption message without leaving a partial binary behind
- Given `/proc/version` contains `Microsoft`, when install.sh runs, then it prints the WSL confirmation line before proceeding

## Design Notes

**PyInstaller entry point:** PyInstaller requires a plain script path, not a package entry-point string. `nimble/__main__.py` serves both PyInstaller and `python -m nimble` for dev use.

**SHA256 generation in CI:**
- Linux/Mac: `sha256sum nimble-linux-x64 > nimble-linux-x64.sha256`
- Windows: `(Get-FileHash nimble-windows-x64.exe -Algorithm SHA256).Hash | Out-File nimble-windows-x64.exe.sha256 -NoNewline`

**Latest-tag resolution in install.sh:**
```sh
LATEST=$(curl -fsSL https://api.github.com/repos/adeptofvoltron/nimble/releases/latest \
  | grep '"tag_name"' | cut -d'"' -f4)
```

**Windows PATH update:** Add install dir to the `HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment` `Path` key via `[Environment]::SetEnvironmentVariable` with `Machine` scope.

## Verification

**Commands:**
- `python -m nimble --help` -- expected: typer help output, confirms `__main__.py` wiring
- `pip install -e ".[dev]" && pyinstaller --onefile --name nimble-test nimble/__main__.py && ./dist/nimble-test --help` -- expected: help output from standalone binary with no Python on PATH
- `shellcheck install/install.sh` -- expected: exit 0, no POSIX compliance warnings

**Manual checks:**
- Push a `v0.0.1-test` tag; confirm Actions shows 4 matrix jobs green and GitHub Releases page lists 8 assets
- On Windows: run `powershell -c "iwr .../install.ps1 | iex"`, open new terminal, confirm `nimble --help` works

## Suggested Review Order

**Entry point**

- Thin wrapper enabling `python -m nimble` and PyInstaller targeting in one file
  [`__main__.py:1`](../../../nimble/__main__.py#L1)

**Release pipeline**

- `permissions: contents: write` — required for `softprops/action-gh-release@v2` to upload assets
  [`release.yml:10`](../../../.github/workflows/release.yml#L10)

- `macos-14` pinned explicitly — guarantees Apple Silicon runner, not subject to `macos-latest` drift
  [`release.yml:19`](../../../.github/workflows/release.yml#L19)

- `--collect-all pynput` — bundles all pynput backends; static analysis misses dynamic platform imports
  [`release.yml:48`](../../../.github/workflows/release.yml#L48)

- Smoke test runs built binary before upload — catches PyInstaller import failures before they ship
  [`release.yml:51`](../../../.github/workflows/release.yml#L51)

**Unix installer**

- Target validation rejects unsupported platforms with a clear message instead of a silent download failure
  [`install.sh:33`](../../../install/install.sh#L33)

- Writability check instead of string comparison — catches `NIMBLE_INSTALL_DIR=/usr/local/bin` edge case
  [`install.sh:56`](../../../install/install.sh#L56)

- Version format guard — catches GitHub API rate-limit responses before constructing a garbage URL
  [`install.sh:80`](../../../install/install.sh#L80)

- Single-line error messages match spec exactly; HTTPS_PROXY hint on any download failure
  [`install.sh:99`](../../../install/install.sh#L99)

**Windows installer**

- Null-safe `$env:TEMP` resolution — falls back through `$env:TMP` to `GetTempPath()`
  [`install.ps1:52`](../../../install/install.ps1#L52)

- Error messages updated to "set HTTPS_PROXY" matching spec wording
  [`install.ps1:63`](../../../install/install.ps1#L63)

- PATH check uses `-split ';'` exact match — glob `-like` matched partial directory names
  [`install.ps1:91`](../../../install/install.ps1#L91)

- Null PATH registry value guarded — prevents leading semicolon on fresh Windows images
  [`install.ps1:94`](../../../install/install.ps1#L94)

**Dev dependencies**

- PyInstaller added to dev extras — available in CI and local builds via `pip install -e ".[dev]"`
  [`pyproject.toml:29`](../../../pyproject.toml#L29)
