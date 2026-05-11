---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Nimble app startup/shutdown stability'
session_goals: 'Reliable skill activation verification, graceful process termination, improved overall stability'
selected_approach: 'ai-recommended'
techniques_used: ['Five Whys', 'Reverse Brainstorming', 'SCAMPER Method']
ideas_generated: [35]
context_file: ''
session_active: false
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Bernard
**Date:** 2026-05-10

## Session Overview

**Topic:** Nimble app startup/shutdown stability
**Goals:** Reliable skill activation verification, graceful process termination, improved overall stability

### Session Setup

Pain points identified:
- `nimble start` reports skills as started but they don't actually work (e.g. `explain` skill doesn't trigger)
- `nimble stop` frequently returns "Nimble did not stop in time"
- Goal: make the app more stable, predictable, and trustworthy to operate

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Nimble app stability with focus on process management, health checking, and graceful shutdown

**Recommended Techniques:**

- **Five Whys:** Root cause analysis — drill past symptoms into why signals are wrong (race conditions, missing health probes, process detection gaps)
- **Reverse Brainstorming:** Flip the problem to surface hidden failure modes, each revealing a hardening opportunity
- **SCAMPER Method:** Systematic 7-lens redesign of the start/stop mechanism into concrete implementation ideas

**AI Rationale:** Solo technical problem-solving sequence: diagnose root causes → map failure space → engineer concrete solutions

---

## Technique Execution Results

### Five Whys — Root Cause Analysis

**Interactive Focus:** Traced "total silence + logs show success" symptom through 5 levels to two precise, code-confirmed root causes.

**Key Discovery — reading `worker/entrypoint.py:192-196`:**
The worker's `{"status": "ok"}` handshake is accurate — it fires after class load, instantiation, and `on_load()`. The worker IS genuinely ready when it says so. It then enters `for line in sys.stdin:` and waits. The silence is not a worker bug — it's a broken delivery chain. Nobody sends it anything.

**Root Cause #1 — The Stranded Worker**
The handshake (runner.py:156–208) confirms "process alive and stdin loop running." It does NOT confirm that the adapter successfully registered this skill's trigger with Claude Code. A skill can pass the handshake and then wait on stdin forever, with Nimble confidently reporting it as "loaded."

**Root Cause #2 — Sequential Shutdown Math Bug**
`_shutdown_workers()` (runner.py:387–402) is a sequential for-loop with 5s per worker. CLI waits 10s (commands.py:160–164). With 3+ skills: 3 × 5s = 15s > 10s. The CLI gives up before the daemon finishes legitimate work. Both constants are correct in isolation — the bug is the undocumented dependency between them.

---

### Reverse Brainstorming — Sabotage → Hardening

**Interactive Focus:** 12 deliberate sabotage scenarios, each flipped into a hardening directive. Key user insight: fire-and-forget subprocess spawning is *intentional design*, making orphan management a structural concern, not an edge case.

| Sabotage | Hardening Flip |
|----------|---------------|
| Race the PID file — write before adapter confirms | Write PID file only after full adapter confirmation |
| One global timeout — slow `on_load` always fails | Per-skill configurable startup timeout in manifest |
| Silent config fallback — bad JSON becomes `{}` | Malformed `NIMBLE_SKILL_CONFIG` = hard startup failure |
| Swallow notifier errors — startup looks clean | Surface notifier failures separately from skill failures |
| Sequential shutdown — N skills × 5s > CLI timeout | Parallel shutdown OR dynamic CLI timeout |
| Orphaned grandchildren — SIGTERM misses subtree | `os.setsid()` per worker + `os.killpg()` on shutdown |
| PID file lies — OS recycled the PID | Verify `/proc/<pid>/cmdline` on start |
| State diverges forever — zombie passes `poll()` | Stdin ping/pong health probe; no pong = actually dead |
| Accumulating ghost processes — each restart leaks | Session UUID tokens; next start reaps previous session |
| Unkillable restart race — old subprocesses finish late | Session tombstone; fire-and-forget checks before writing back |
| No spawn budget — misbehaving skill forks unbounded | Lifecycle registry with max-per-skill process count |
| Port squatting between sessions — old orphan holds port | Skills declare resource footprint in manifest |

---

### SCAMPER Method — Systematic Redesign

**Interactive Focus:** 7 lenses applied to the start/stop mechanism. 21 ideas generated.

**Substitute:** Two-phase handshake (S1) · inotify instead of sleep loops (S2) · Unix socket instead of PID file (S3)

**Combine:** state.json + PGID tracking (C1) · workers-loaded + adapter-registered combined gate (C2) · stop + orphan reaper in one operation (C3)

**Adapt:** systemd `sd_notify` readiness protocol (A1) · supervisor/foreman process model (A2) · browser session token pattern for orphan tracking (A3)

**Modify:** Parallel shutdown with ThreadPoolExecutor (M1) · Dynamic CLI timeout = N × 5s + buffer (M2) · Config parse failure = hard error (M3)

**Put to other uses:** Heartbeat extended to functional stdin probe (P1) · `on_unload` as documented cleanup contract (P2) · Registry extended with `"unresponsive"` status (P3)

**Eliminate:** Sequential shutdown loop → killpg() (E1) · PID-file-as-liveness → Unix socket (E2) · Silent config fallback (E3)

**Reverse:** Pull-based readiness check (R1) · Adapter starts first, workers second (R2) · Daemon signals CLI completion, CLI doesn't time out blindly (R3)

---

## Idea Organization and Prioritization

### Theme 1: Startup Verification & Readiness

| # | Idea | Source |
|---|------|--------|
| 1.1 | **Two-phase handshake** — process `ok` + stdin probe confirms full dispatch pipeline | S1 |
| 1.2 | **Adapter-first startup order** — adapter confirmed before any worker spawns | R2 |
| 1.3 | **Combined readiness gate** — CLI "started!" only after workers + adapter both confirmed | C2 |
| 1.4 | **Pull-based readiness** — daemon asks workers if ready rather than workers self-reporting | R1 |
| 1.5 | **systemd-style ready signal** — worker signals ready only after processing a no-op end-to-end | A1 |
| 1.6 | **Write PID file last** — PID file written only after full adapter confirmation | Sab.#1 |

### Theme 2: Shutdown Reliability

| # | Idea | Source |
|---|------|--------|
| 2.1 | **Parallel shutdown** — ThreadPoolExecutor, total time = max not sum | M1 |
| 2.2 | **Dynamic CLI timeout** — `n_workers × 5s + 2s_buffer` stays correct at any scale | M2 |
| 2.3 | **Daemon signals CLI completion** — daemon owns timeline, CLI just listens | R3 |
| 2.4 | **Process group kill** — `os.killpg()` replaces per-worker SIGTERM loop | E1 |

### Theme 3: Process Tree & Orphan Management

| # | Idea | Source |
|---|------|--------|
| 3.1 | **Session tokens** — UUID inherited by all spawned processes; next start reaps old session | Sab.#9, A3 |
| 3.2 | **Session tombstone** — fire-and-forget processes discard results if session is dead | Sab.#10 |
| 3.3 | **Stop = reaper** — `nimble stop` kills daemon + sweeps previous session orphans | C3 |
| 3.4 | **Worker process groups** — `os.setsid()` per worker; `killpg()` kills full subtree | Sab.#6 |
| 3.5 | **`on_unload` cleanup contract** — skills that spawn must reap in `on_unload`, enforced with timeout | P2 |
| 3.6 | **Per-skill spawn budget** — lifecycle registry with max subprocess count per skill | Sab.#11 |
| 3.7 | **Manifest resource declarations** — skills declare ports/paths; Nimble checks conflicts on start | Sab.#12 |
| 3.8 | **Supervisor process model** — dedicated layer owns all process lifecycle | A2 |

### Theme 4: Health Monitoring & Liveness

| # | Idea | Source |
|---|------|--------|
| 4.1 | **Heartbeat stdin probe** — every 30s, no-op ping/pong per worker; no pong = unresponsive | P1, Sab.#8 |
| 4.2 | **`"unresponsive"` status** — new SkillStatus value, surfaced in `nimble status` | P3 |
| 4.3 | **Unix socket replaces PID file** — daemon binds socket; CLI connection = genuine liveness | S3, E2 |
| 4.4 | **Process identity verification** — check `/proc/<pid>/cmdline` before trusting PID file | Sab.#7 |
| 4.5 | **inotify/waitpid instead of sleep loops** — kernel-level events replace polling | S2 |
| 4.6 | **state.json includes PGID** — full-tree kill handle stored in state | C1 |

### Theme 5: Error Visibility & Config Integrity

| # | Idea | Source |
|---|------|--------|
| 5.1 | **Hard config failure** — malformed `NIMBLE_SKILL_CONFIG` = explicit startup error, not `{}` | M3, Sab.#3, E3 |
| 5.2 | **Surface notifier failures** — separate "skill failed" from "notifier failed" | Sab.#4 |
| 5.3 | **Per-skill startup timeout** — configurable in manifest, not one global constant | Sab.#2 |

---

## Action Plans

### Quick Wins (Week 1)

---

**QW-1: Parallel Shutdown**
`nimble/skills/runner.py` — replace `_shutdown_workers()` for-loop

```python
from concurrent.futures import ThreadPoolExecutor, wait

def _shutdown_workers(self, workers: list[SkillWorker]) -> None:
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(self._terminate_worker_process, w.process)
                   for w in workers]
        wait(futures)
```

Effort: ~5 lines. Fixes the shutdown math bug completely.

---

**QW-2: Dynamic CLI Timeout**
`nimble/cli/commands.py` ~line 160 — replace hardcoded `range(100)`

```python
n_skills = len(config.skills)
stop_polls = max(100, n_skills * 60)  # 5s per worker + 1s buffer in 0.1s ticks
for _ in range(stop_polls):
    time.sleep(0.1)
```

Effort: ~3 lines. Stays correct as skill count grows.

---

**QW-3: Hard Config Failure**
`worker/entrypoint.py` lines 141–146 — replace `except: pass` with explicit error response

```python
raw = os.environ.get("NIMBLE_SKILL_CONFIG", "") or "{}"
try:
    parsed = json.loads(raw)
except (json.JSONDecodeError, ValueError) as exc:
    sys.stdout.write(json.dumps({
        "invocation_id": "",
        "status": "error",
        "error": {"type": "ConfigError",
                  "message": f"Invalid NIMBLE_SKILL_CONFIG: {exc}",
                  "skill_file": "", "line": 0}
    }) + "\n")
    sys.stdout.flush()
    return
skill_config = parsed if isinstance(parsed, dict) else {}
```

Effort: ~10 lines. Turns a silent bug into a visible one.

---

**QW-4: Write PID File Last**
`nimble/daemon.py` ~lines 88–98 — verify `adapter.start()` raises on failure; confirm PID write comes after.

Effort: Audit adapter.start() for error propagation. Move is free if it already raises.

---

### High Impact (Weeks 2–4)

---

**HI-1: Adapter-First Startup Order** (Week 2)
`nimble/daemon.py` — reorder initialisation sequence

New order: load config → `adapter.start()` → signal handlers → spawn workers → register hotkeys → write PID file

Why: if adapter fails today, workers are already spawned and orphaned. With this order, adapter failure = zero processes spawned, clean error, no cleanup needed.

Requires: adapter API supports deferred per-skill trigger registration (register after workers confirm ready).

---

**HI-2: Two-Phase Handshake + Combined Readiness Gate** (Week 3, depends on HI-1)

Files: `worker/entrypoint.py`, `nimble/skills/runner.py`, `nimble/daemon.py`

- Worker: handle `__probe__` invocation_id as a no-op, respond immediately
- Runner: after phase-1 handshake, send probe via stdin, wait for response
- Daemon: gate PID file write on (all workers pass probe) AND (adapter confirms triggers)

CLI "started!" becomes truthful for the first time.

Effort: ~40 lines across 3 files.

---

**HI-3: Heartbeat Stdin Probe + `"unresponsive"` Status** (Week 4, independent)

Files: `nimble/daemon.py`, `nimble/skills/registry.py`, `nimble/cli/commands.py`

- Registry: add `"unresponsive"` to `SkillStatus` Literal
- Daemon heartbeat: every 30s send no-op ping to each loaded worker; no pong within 3s → status = `"unresponsive"`
- CLI: `nimble status` displays per-skill status so broken skills are visible without log diving

Effort: ~35 lines across 3 files.

---

### Recommended Implementation Order

```
Week 1:  QW-3 → QW-4 → QW-1 → QW-2   (safe, isolated, no dependencies)
Week 2:  HI-1  (adapter-first order)
Week 3:  HI-2  (two-phase handshake — depends on HI-1)
Week 4:  HI-3  (heartbeat probe — independent, can run parallel with HI-2)
```

---

## Session Summary and Insights

**Key Achievements:**
- 35 ideas across 3 techniques: 2 root causes, 12 sabotage→hardening pairs, 21 SCAMPER directions
- Traced "total silence" symptom to a specific architectural gap: adapter registration is never confirmed per-skill
- Identified the shutdown timeout as a pure math bug: two independently set constants that were never reconciled
- Revealed that fire-and-forget subprocess spawning is intentional design, making orphan management a structural requirement
- Produced a 4-week implementation roadmap from zero-risk quick wins to architectural hardening

**Breakthrough Moments:**
- Reading `worker/entrypoint.py:192` confirmed the worker is NOT lying — it genuinely is ready. The problem is upstream of the worker entirely.
- Bernard's sabotage idea (#6) about untracked worker PIDs revealed that the orphan problem is architectural, not incidental — leading directly to the session token and process group ideas.

**Session Reflections:**
The Five Whys grounded in real code turned a vague "something is wrong with startup" into two precise, fixable root causes. Reverse Brainstorming then surfaced the deeper structural issue (fire-and-forget subprocesses) that standard analysis would have missed. SCAMPER provided the bridge from diagnosis to concrete implementation options.
