---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Packaging and distributing Nimble across different environments'
session_goals: 'List packaging/distribution options to evaluate; design the ideal install experience; identify edge cases and gotchas for each approach'
selected_approach: 'ai-recommended'
techniques_used: ['Constraint Mapping', 'Cross-Pollination', 'Reverse Brainstorming']
ideas_generated: 31
session_active: false
workflow_completed: true
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Bernard
**Date:** 2026-05-12

## Session Overview

**Topic:** Packaging and distributing Nimble across different environments
**Goals:**
1. Generate a comprehensive list of packaging/distribution options to evaluate
2. Design the ideal install experience — what it should feel and look like for users
3. Surface edge cases, failure modes, and gotchas for each approach

### Session Setup

AI-recommended technique sequence chosen for multi-angle exploration of a concrete technical challenge.

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Cross-platform distribution of a developer CLI tool with focus on install experience design, option evaluation, and risk mapping.

**Recommended Techniques:**

- **Constraint Mapping:** Establishes the playing field — what platforms, user types, and runtime dependencies define the solution space before generating options
- **Cross-Pollination:** Generates the distribution options list by studying how analogous tools (uv, rustup, mise, deno) handle the same challenge
- **Reverse Brainstorming:** Surfaces edge cases and gotchas by deliberately asking "how would this fail?" — directly informs install experience design

**AI Rationale:** Goals span three phases naturally: understand constraints → generate options → stress-test them. These three techniques map perfectly to that arc, moving from structured/deep analysis to creative generation to adversarial risk discovery.

---

## Phase 1: Constraint Mapping Results

| # | Constraint | Impact |
|---|-----------|--------|
| 1 | Dual persona — developers primary, semi-technical secondary (all must use terminal) | Keep install command simple and memorable |
| 2 | Python-based internally — but users should not need Python installed | Bundle Python or compile to standalone binary |
| 3 | All 3 platforms: Mac, Linux, Windows — Day 1 | Multi-arch binary build pipeline required from launch |
| 4 | One-command experience goal — channel is secondary to the feeling | Architecture must make one command reliably work everywhere |
| 5 | Python 3.10+ requirement — internal build concern, not user concern | User's system Python is irrelevant with binary distribution |
| 6 | Shell installer as primary vector — `install.sh` + `install.ps1` | Thin scripts that download the right binary from GitHub Releases |
| 7 | Windows Day 1 — dual installer required | Forces binary targets: mac-arm64, mac-x64, linux-x64, linux-arm64, windows-x64 |
| 8 | GitHub Actions as primary CI target — for testing install across environments | `setup-nimble` action or clean curl-in-run-step story |
| 9 | Sudo required — installs to `/usr/local/bin` | Must warn users upfront; future `--user` flag for escape hatch |
| 10 | No auto-update yet — `nimble update` planned | Installer script should be reusable internally by update command |
| 11 | Modern Linux only — Ubuntu 22.04+, Debian 12+, Fedora 38+ | Can target glibc 2.35+; Alpine/musl is a separate future concern |

---

## Phase 2: Cross-Pollination Results

### Distribution Options Inventory

#### Launch (Day 1)

**[Distribution #1]**: `install.sh` — Mac/Linux Primary Installer
*Concept*: `curl -fsSL https://get.nimble.sh | sh` — detects OS/arch, downloads the right binary from GitHub Releases, places it on PATH. The canonical install path for Mac and Linux users.
*Pattern borrowed from*: uv (Astral), rustup, mise

**[Distribution #2]**: `install.ps1` — Windows Primary Installer
*Concept*: `powershell -c "iwr https://get.nimble.sh/install.ps1 | iex"` — PowerShell equivalent, bypasses execution policy via inline execution, installs binary to system PATH.
*Pattern borrowed from*: uv Windows installer, Scoop installer

**[Distribution #3]**: GitHub Releases Binary Distribution
*Concept*: Every release publishes pre-built binaries to GitHub Releases (nimble-darwin-arm64, nimble-darwin-x64, nimble-linux-x64, nimble-linux-arm64, nimble-windows-x64.exe + SHA256 checksums). Both install scripts and power users point here.
*Pattern borrowed from*: ruff, deno, gh CLI

#### Install Script Internal Design

**[Distribution #8]**: OS + Arch Detection with Normalization
*Concept*: `uname -s` for OS, `uname -m` for arch. Must normalize: `aarch64` → `arm64` before constructing the download URL. Without normalization, Apple Silicon and Linux ARM users get "exec format error."

**[Distribution #9]**: SHA256 Checksum Verification
*Concept*: After downloading the binary, verify against a `.sha256` file published alongside each release on GitHub Releases. Fails loudly with a human-readable error if corrupted or tampered.

**[Distribution #10]**: Install Location Override via Env Var
*Concept*: Default to `/usr/local/bin` (requires sudo), but respect `NIMBLE_INSTALL_DIR` env var. `curl ... | NIMBLE_INSTALL_DIR=~/.local/bin sh` installs without sudo for restricted environments.

#### Post-Launch (add as demand materializes)

**[Distribution #4]**: Homebrew Formula (Mac/Linux)
*Concept*: `brew install nimble-ai/tap/nimble` — a Homebrew tap (GitHub repo with ~50 lines of Ruby formula). Native install for the large chunk of developers who reach for `brew` first. Includes `brew upgrade` for free.

**[Distribution #5]**: Scoop (Windows)
*Concept*: `scoop install nimble` — the most developer-friendly Windows package manager. No admin required (user scope install). Developers who use `gh`, `ruff`, `deno` on Windows already have Scoop.

**[Distribution #6]**: `pipx install nimble-ai` (PyPI)
*Concept*: Since Nimble is Python-based, publishing to PyPI gives the Python developer community their native install path. pipx isolates the environment. Requires Python 3.10+ on user's machine — works well for the Python dev persona.

**[Distribution #7]**: winget / Chocolatey (Windows)
*Concept*: winget is Microsoft-official and growing fast. Chocolatey has the largest catalog. Lower priority than Scoop for the developer persona, but broadens reach to IT-managed Windows environments.

---

## Phase 3: Reverse Brainstorming — Gotcha Map

### `install.sh` Gotchas (Mac/Linux)

**[Gotcha #1]**: The `curl | sh` Security Wall
*What fails*: Security-conscious users and corporate IT policies block or distrust `curl | sh` — they can't inspect what runs before executing.
*Fix*: Always publish the raw script URL separately. Document both forms:
- Fast: `curl -fsSL https://get.nimble.sh | sh`
- Inspect-first: `curl -o install.sh https://get.nimble.sh && cat install.sh && sh install.sh`

**[Gotcha #2]**: `uname -m` Arch Mismatch
*What fails*: Apple Silicon returns `arm64`, Linux ARM returns `aarch64`. Naive script downloads wrong binary → cryptic "exec format error."
*Fix*: Explicit normalization in script: map `aarch64` → `arm64` before constructing GitHub Releases URL.

**[Gotcha #3]**: GitHub Releases Blocked by Corporate Proxy
*What fails*: Enterprise environments proxy or block GitHub Releases. Script downloads nothing, fails with confusing TLS error.
*Fix*: Detect failed download explicitly. Print: *"Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry."*

**[Gotcha #10]**: Sudo Prompt Surprise
*What fails*: Script silently requires sudo mid-execution, hangs waiting for password prompt. Looks like it froze.
*Fix*: Check for sudo upfront, before any action. Print: *"Nimble installs to /usr/local/bin and requires sudo. You may be prompted for your password."*

### `install.ps1` Gotchas (Windows)

**[Gotcha #4]**: PowerShell Execution Policy Block
*What fails*: Windows defaults to `Restricted` or `RemoteSigned`. Downloaded `.ps1` gets Mark-of-the-Web flag and is blocked before running.
*Fix*: Use `iwr | iex` (inline execution) pattern in the recommended install command — bypasses execution policy entirely. Document `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` as alternative.

**[Gotcha #5]**: Windows Defender Quarantines the Binary
*What fails*: Even after successful download, Defender silently quarantines unsigned executable. `nimble` command missing after apparent success.
*Fix*: Code sign the binary. Self-signed cert reduces friction. EV cert (~$300/yr) eliminates it.

**[Gotcha #6]**: PATH Not Active in Current Session
*What fails*: Installer adds to PATH but change only takes effect in new sessions. User types `nimble` immediately after install → "command not found" → files bug thinking install failed.
*Fix*: Script ends with explicit message: *"Nimble installed! Open a new terminal to use it."* On Windows, attempt `$env:PATH` refresh for current session where possible.

### Cross-Platform Gotchas

**[Gotcha #7]**: WSL Identity Crisis
*What fails*: WSL users see Linux but live in Windows. Docs say "Windows → use install.ps1" — confused users try wrong script.
*Fix*: Docs need explicit WSL callout: *"On WSL, use the Linux installer."* Script detects WSL via `/proc/version` containing `Microsoft` and prints a confirmation.

**[Gotcha #8]**: Partial Download on Network Interruption
*What fails*: Network drops mid-download, corrupted binary placed on PATH. `nimble` crashes with bizarre error on every invocation.
*Fix*: Checksum verification catches this. Error message must say: *"Download may be corrupted — retry the install"* not a raw hash mismatch.

**[Gotcha #9]**: Spaces or Unicode in PATH
*What fails*: User with `C:\Users\André\` or a space in their username causes script to silently fail or misplace the binary.
*Fix*: All path operations in both scripts must be quoted. Sounds obvious; catches many scripts out.

---

## Idea Organization and Prioritization

### Thematic Organization

**Theme 1: Distribution Architecture** — what channels, in what order

- Day 1: `install.sh` + `install.ps1` + GitHub Releases multi-arch binaries
- Soon after: Homebrew tap, pipx/PyPI, Scoop
- Later: winget, Chocolatey, `nimble update` self-update

**Theme 2: Install Script Internal Design** — what the scripts must do

- OS/arch detection with normalization
- SHA256 checksum verification
- `NIMBLE_INSTALL_DIR` override
- Upfront sudo warning
- Clear post-install message
- WSL detection

**Theme 3: Windows-Specific** — the hardest platform

- `iwr | iex` pattern to bypass execution policy
- Code signing to prevent Defender quarantine
- PATH session refresh or clear message
- WSL callout in docs

**Theme 4: Resilience & User Trust** — silent failure prevention

- Checksum catches partial downloads → human-readable error
- Corporate proxy detection → HTTPS_PROXY hint
- Inspect-first install form documented
- Quoted paths throughout

### Prioritization Results

**Quick wins — implement inside the install scripts:**
1. Upfront sudo warning before any action
2. Clear "open a new terminal" message at completion
3. `aarch64` → `arm64` normalization
4. Quoted paths throughout both scripts
5. WSL detection and confirmation message

**Medium effort, high value — before launch:**
1. SHA256 checksum verification with human-readable error
2. `NIMBLE_INSTALL_DIR` env var for no-sudo installs
3. Corporate proxy failure detection with HTTPS_PROXY hint
4. `iwr | iex` pattern for PowerShell install command
5. Multi-arch binary build pipeline in CI (GitHub Actions on release tag)

**Invest before launch:**
1. Code signing for Windows binary (self-signed minimum)
2. GitHub Releases publish automation

**Post-launch when demand materializes:**
1. Homebrew tap, pipx/PyPI, Scoop
2. `nimble update` self-update command
3. EV code signing for Windows
4. winget / Chocolatey

---

## Action Plan

### This Week
1. **Set up binary build pipeline** — GitHub Actions workflow that builds multi-arch binaries (mac-arm64, mac-x64, linux-x64, linux-arm64, windows-x64) and publishes to GitHub Releases on every release tag, including SHA256 checksums
2. **Write `install.sh`** — OS/arch detection with normalization, checksum verification, upfront sudo check, `NIMBLE_INSTALL_DIR` support, WSL detection, clear post-install message
3. **Write `install.ps1`** — equivalent script, `iwr | iex` compatible, PATH refresh attempt, same messaging quality

### Before Launch
4. **Test on clean environments** — fresh Ubuntu 22.04, macOS Intel, macOS Apple Silicon, Windows 10, Windows 11, WSL2
5. **Document both install forms** — one-liner AND inspect-then-run, with WSL callout and platform guidance
6. **Self-sign the Windows binary** — reduce Defender friction from day one

### Post-Launch
7. **Monitor where users get stuck** — prioritize Homebrew tap, pipx/PyPI, or Scoop based on actual issue reports and questions
8. **Implement `nimble update`** — reuse install script internally, do not create a separate code path

---

## Session Summary and Insights

**Key Achievements:**
- 11 constraints mapped that filter the entire solution space
- Clear Day 1 distribution decision: `install.sh` + `install.ps1` only
- 10 gotchas identified before users find them
- Concrete action plan with sequenced priorities

**Breakthrough Insight:** The Python 3.10+ requirement is an *internal* build concern, not a user concern — the standalone binary approach decouples Nimble's runtime from the user's system entirely. This decision resolved the core distribution challenge.

**Key Decision Made:** Start lean with two installer scripts. Every other distribution channel (brew, pipx, scoop, winget) is a post-launch spoke pointing to the same GitHub Releases binaries. Low maintenance cost when added; no cost if deferred.

**Most Actionable Gotcha:** The sudo prompt surprise and the PATH-not-active-in-current-session issue are the two most likely to generate "install is broken" bug reports. Both are fixed with one line of output at the right moment in the script.
