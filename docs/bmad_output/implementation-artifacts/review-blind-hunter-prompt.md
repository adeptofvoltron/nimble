# Blind Hunter Review Prompt

**Story:** 8-2-configuration-in-config-yaml-and-worker-injection  
**Review Layer:** Blind Hunter (no project context, diff only)  
**Instructions:** Review this diff cynically for bugs, logic errors, security issues, and code quality problems. Output findings as a Markdown list with titles and descriptions.

---

## DIFF TO REVIEW

```diff
diff --git a/docs/bmad_output/implementation-artifacts/sprint-status.yaml b/docs/bmad_output/implementation-artifacts/sprint-status.yaml
index 356aaff..2bf9bbd 100644
--- a/docs/bmad_output/implementation-artifacts/sprint-status.yaml
+++ b/docs/bmad_output/implementation-artifacts/sprint-status.yaml
@@ -35,7 +35,7 @@
 # - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
 
 generated: "2026-04-16"
-last_updated: "2026-05-05"  # updated by dev-story: 8-1 review
+last_updated: "2026-05-05"  # updated by dev-story: 8-2
 project: "pixi (Nimble)"
 project_key: NOKEY
 tracking_system: file-system
@@ -108,6 +108,6 @@ development_status:
   # Epic 8: Skill Configuration — Pass Parameters from config.yaml to Skills
   epic-8: in-progress
   8-1-config-fields-schema-in-manifest-yaml-and-parsing: done
-  8-2-configuration-in-config-yaml-and-worker-injection: backlog
+  8-2-configuration-in-config-yaml-and-worker-injection: review
   8-3-interactive-config-prompting-in-nimble-add: backlog
   epic-8-retrospective: optional
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
diff --git a/tests/unit/manifest/test_parser.py b/tests/unit/manifest/test_parser.py
index f9d5921..c3a5617 100644
--- a/tests/unit/manifest/test_parser.py
+++ b/tests/unit/manifest/test_parser.py
@@ -798,3 +798,71 @@ def test_parse_manifest_config_fields_default_must_be_in_possible_values() -> No
         ManifestError, match="field 'default' must be one of 'possible_values'"
     ):
         parse_manifest_yaml(content)
+
+
+# ---------------------------------------------------------------------------
+# SkillConfig.configuration tests (AC: 1, 2)
+# ---------------------------------------------------------------------------
+
+
+def test_load_config_skill_with_configuration(tmp_path: Path) -> None:
+    cfg = _write_config(
+        tmp_path,
+        "skills:\n"
+        "  - name: translator\n"
+        "    source: local\n"
+        "    path: skills/translator/skill.py\n"
+        "    class_name: Translator\n"
+        "    binding: ctrl+shift+t\n"
+        "    configuration:\n"
+        "      target_language: es\n"
+        "      fallback: en\n",
+    )
+    result = load_config(cfg)
+    assert len(result.skills) == 1
+    assert result.skills[0].configuration == {"target_language": "es", "fallback": "en"}
+
+
+def test_load_config_skill_no_configuration_defaults_to_empty(tmp_path: Path) -> None:
+    cfg = _write_config(
+        tmp_path,
+        "skills:\n"
+        "  - name: my_skill\n"
+        "    source: local\n"
+        "    path: skills/my_skill/skill.py\n"
+        "    class_name: MySkill\n"
+        "    binding: ctrl+x\n",
+    )
+    result = load_config(cfg)
+    assert result.skills[0].configuration == {}
+
+
+def test_load_config_skill_configuration_non_dict_raises(tmp_path: Path) -> None:
+    cfg = _write_config(
+        tmp_path,
+        "skills:\n"
+        "  - name: bad_skill\n"
+        "    source: local\n"
+        "    path: skills/bad_skill/skill.py\n"
+        "    class_name: BadSkill\n"
+        "    binding: ctrl+b\n"
+        "    configuration: not_a_dict\n",
+    )
+    with pytest.raises(ConfigError):
+        load_config(cfg)
+
+
+def test_load_config_skill_configuration_coerces_values_to_str(tmp_path: Path) -> None:
+    cfg = _write_config(
+        tmp_path,
+        "skills:\n"
+        "  - name: my_skill\n"
+        "    source: local\n"
+        "    path: skills/my_skill/skill.py\n"
+        "    class_name: MySkill\n"
+        "    binding: ctrl+x\n"
+        "    configuration:\n"
+        "      count: 5\n",
+    )
+    result = load_config(cfg)
+    assert result.skills[0].configuration == {"count": "5"}
diff --git a/tests/unit/skills/test_runner.py b/tests/unit/skills/test_runner.py
index a669d1e..4735370 100644
--- a/tests/unit/skills/test_runner.py
+++ b/tests/unit/skills/test_runner.py
@@ -643,3 +643,45 @@ def test_spawn_workers_skips_check_when_manifest_has_no_api_version() -> None:
     assert registry.get("my-skill").status == "loaded"  # type: ignore[union-attr]
     assert len(notifier.sent) == 0
     mock_logger.warning.assert_not_called()
+
+
+# ---------------------------------------------------------------------------
+# configuration injection tests (AC: 3)
+# ---------------------------------------------------------------------------
+
+
+def test_spawn_workers_passes_configuration_in_skill_config_json() -> None:
+    config = SkillConfig(
+        name="my-skill",
+        source="local",
+        binding="ctrl+shift+a",
+        path="/path/to/skill.py",
+        class_name="MySkill",
+        configuration={"target_language": "es"},
+    )
+    registry = SkillRegistry()
+    runner = _make_runner(registry=registry)
+    ok_response = {"invocation_id": "abc", "status": "ok", "error": None}
+    fake_proc = _make_fake_proc(ok_response)
+
+    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
+        runner.spawn_workers([config])
+        _, kwargs = mock_popen.call_args
+        env = kwargs["env"]
+        skill_config = json.loads(env["NIMBLE_SKILL_CONFIG"])
+        assert skill_config["configuration"] == {"target_language": "es"}
+
+
+def test_spawn_workers_passes_empty_configuration_when_none_set() -> None:
+    config = _make_config()
+    registry = SkillRegistry()
+    runner = _make_runner(registry=registry)
+    ok_response = {"invocation_id": "abc", "status": "ok", "error": None}
+    fake_proc = _make_fake_proc(ok_response)
+
+    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
+        runner.spawn_workers([config])
+        _, kwargs = mock_popen.call_args
+        env = kwargs["env"]
+        skill_config = json.loads(env["NIMBLE_SKILL_CONFIG"])
+        assert skill_config["configuration"] == {}
diff --git a/tests/unit/worker/test_entrypoint.py b/tests/unit/worker/test_entrypoint.py
index 02e964e..dba6a1a 100644
--- a/tests/unit/worker/test_entrypoint.py
+++ b/tests/unit/worker/test_entrypoint.py
@@ -16,6 +16,8 @@ from worker.context import Context
 
 
 class _FakeSkill:
+    configuration: dict[str, str]
+
     def run(self, context: Context, tools: Any) -> None:
         pass
 
@@ -325,3 +327,78 @@ def test_thread_excepthook_serialises_to_stdout() -> None:
     assert "boom" in response["error"]["message"]
     assert response["error"]["skill_file"] != ""
     assert response["error"]["line"] > 0
+
+
+# ---------------------------------------------------------------------------
+# skill.configuration injection tests (AC: 4, 5, 6, 7)
+# ---------------------------------------------------------------------------
+
+
+def test_worker_sets_skill_configuration_before_on_load() -> None:
+    on_load_config: dict[str, Any] = {}
+
+    class _ConfigSkill:
+        configuration: dict[str, str]
+
+        def on_load(self, config: dict[str, Any]) -> None:
+            on_load_config.update(config)
+
+        def run(self, context: Context, tools: Any) -> None:
+            pass
+
+    skill_instance = _ConfigSkill()
+    stdout_buf = io.StringIO()
+    fake_class = MagicMock(return_value=skill_instance)
+
+    env = {
+        **os.environ,
+        "NIMBLE_SKILL_CONFIG": json.dumps(
+            {
+                "name": "translator",
+                "source": "local",
+                "binding": "ctrl+t",
+                "path": "skills/translator/skill.py",
+                "class_name": "Translator",
+                "configuration": {"target_language": "es"},
+            }
+        ),
+    }
+    with (
+        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
+        patch("sys.stdin", io.StringIO("")),
+        patch("sys.stdout", stdout_buf),
+        patch.dict(os.environ, env, clear=True),
+    ):
+        entrypoint_mod.run("fake/path.py", "FakeSkill")
+
+    assert skill_instance.configuration == {"target_language": "es"}
+    assert on_load_config["name"] == "translator"
+    assert on_load_config["configuration"] == {"target_language": "es"}
+
+
+def test_worker_configuration_defaults_to_empty_dict() -> None:
+    skill_instance = _FakeSkill()
+    stdout_buf = io.StringIO()
+    fake_class = MagicMock(return_value=skill_instance)
+
+    env = {
+        **os.environ,
+        "NIMBLE_SKILL_CONFIG": json.dumps(
+            {
+                "name": "my_skill",
+                "source": "local",
+                "binding": "ctrl+x",
+                "path": "skills/my_skill/skill.py",
+                "class_name": "MySkill",
+            }
+        ),
+    }
+    with (
+        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
+        patch("sys.stdin", io.StringIO("")),
+        patch("sys.stdout", stdout_buf),
+        patch.dict(os.environ, env, clear=True),
+    ):
+        entrypoint_mod.run("fake/path.py", "FakeSkill")
+
+    assert skill_instance.configuration == {}
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

Review this diff cynically for **bugs, logic errors, security issues, and code quality problems**. Find at least 5-10 issues if they exist.

Output as a **Markdown list** with:
- Issue title
- Description and impact
- Location in code (if available)

Be specific and skeptical. Assume problems exist.
