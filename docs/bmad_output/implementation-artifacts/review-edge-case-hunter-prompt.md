# Edge Case Hunter Review Prompt

**Story:** 8-2-configuration-in-config-yaml-and-worker-injection  
**Review Layer:** Edge Case Hunter  
**Instructions:** Exhaustively trace every branching path and boundary condition. Report only unhandled paths that lack explicit guards.

---

## DIFF TO REVIEW

```diff
diff --git a/nimble/manifest/parser.py b/nimble/manifest/parser.py
index 34b7bab..6236602 100644
--- a/nimble/manifest/parser.py
+++ b/nimble/manifest/parser.py
@@ -367,6 +367,26 @@ def _parse_ai_config(data: dict[str, Any]) -> AiConfig | None:
     )
 
 
+def _parse_skill_configuration(
+    entry: dict[str, Any], i: int
+) -> dict[str, str]:
+    raw = entry.get("configuration")
+    if raw is None:
+        return {}
+    if not isinstance(raw, dict):
+        raise ConfigError(
+            f"Skill entry at index {i} 'configuration' must be a mapping"
+        )
+    result: dict[str, str] = {}
+    for k, v in raw.items():
+        if not isinstance(k, str):
+            raise ConfigError(
+                f"Skill entry at index {i} 'configuration' keys must be strings"
+            )
+        result[k] = str(v)
+    return result
+
+
 def _parse_skills(raw: Any) -> list[SkillConfig]:
     if not isinstance(raw, list):
         raise ConfigError("'skills' must be a list")
@@ -401,6 +421,7 @@ def _parse_skills(raw: Any) -> list[SkillConfig]:
                 binding=entry["binding"],
                 path=entry["path"],
                 class_name=entry["class_name"],
+                configuration=_parse_skill_configuration(entry, i),
             )
         )
 
diff --git a/nimble/skills/registry.py b/nimble/skills/registry.py
index d0b38d0..1d9aab8 100644
--- a/nimble/skills/registry.py
+++ b/nimble/skills/registry.py
@@ -2,7 +2,7 @@ from __future__ import annotations
 
 import logging
 import subprocess
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from typing import Literal
 
 logger = logging.getLogger(__name__)
@@ -18,6 +18,7 @@ class SkillConfig:
     binding: str
     path: str
     class_name: str
+    configuration: dict[str, str] = field(default_factory=dict)
 
 
 @dataclass
diff --git a/nimble/skills/runner.py b/nimble/skills/runner.py
index 3f39b34..92fdc51 100644
--- a/nimble/skills/runner.py
+++ b/nimble/skills/runner.py
@@ -128,6 +128,7 @@ class SkillRunner:
                         "binding": config.binding,
                         "path": config.path,
                         "class_name": config.class_name,
+                        "configuration": config.configuration,
                     }
                 )
                 proc = subprocess.Popen(
diff --git a/worker/entrypoint.py b/worker/entrypoint.py
index 0120bc5..7c3322b 100644
--- a/worker/entrypoint.py
+++ b/worker/entrypoint.py
@@ -169,6 +169,12 @@ def run(module_path: str, class_name: str) -> None:
         sys.stdout.flush()
         return
 
+    configuration: dict[str, str] = {}
+    raw_cfg = skill_config.get("configuration")
+    if isinstance(raw_cfg, dict):
+        configuration = {str(k): str(v) for k, v in raw_cfg.items()}
+    skill.configuration = configuration
+
     if hasattr(skill, "on_load"):
         try:
             skill.on_load(skill_config)
```

---

## YOUR TASK

Exhaustively trace every branching path and boundary in the diff. Report ONLY unhandled paths that lack explicit guards.

**Scope:** Changed lines and directly reachable boundaries.

**Output as JSON array** with exactly these fields:

```json
[
  {
    "location": "file:line or file:start-end",
    "trigger_condition": "condition that lacks handling (max 15 words)",
    "guard_snippet": "minimal code to close the gap (one line)",
    "potential_consequence": "what goes wrong (max 15 words)"
  }
]
```

**No extra text, no markdown wrapping.** Empty array `[]` if no unhandled paths found.

### Path Classes to Examine

- Missing else/default branches
- Null/empty/None inputs
- Type coercion edge cases
- Off-by-one or boundary conditions
- State/data inconsistencies
- Implicit assumptions that could break
