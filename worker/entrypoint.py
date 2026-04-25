import sys
from pathlib import Path

_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import os  # noqa: E402

_env_root = os.environ.get("NIMBLE_REPO_ROOT")
if _env_root and _env_root not in sys.path:
    sys.path.append(_env_root)

import importlib.util  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402
import traceback  # noqa: E402
from typing import Any  # noqa: E402

from worker.context import Context  # noqa: E402
from nimble.manifest.parser import AiConfig  # noqa: E402
from nimble.tools import ToolRegistry  # noqa: E402
from nimble.tools.ai import AiTool  # noqa: E402
from nimble.tools.clipboard import ClipboardTool  # noqa: E402
from nimble.tools.popup import PopupTool  # noqa: E402

_invocation_local = threading.local()


def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
    tb = args.exc_traceback
    last_frame = traceback.extract_tb(tb)[-1] if tb else None
    response: dict[str, Any] = {
        "invocation_id": getattr(_invocation_local, "invocation_id", ""),
        "status": "error",
        "error": {
            "type": type(args.exc_value).__name__ if args.exc_value else "UnknownError",
            "message": str(args.exc_value) if args.exc_value else "",
            "skill_file": last_frame.filename if last_frame else "",
            "line": last_frame.lineno if last_frame else 0,
        },
    }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


threading.excepthook = _thread_excepthook


def _load_skill_class(module_path: str, class_name: str) -> type:
    spec = importlib.util.spec_from_file_location("skill_module", module_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load module from path: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skill_class = getattr(module, class_name)
    if not callable(skill_class):
        raise TypeError(
            f"'{class_name}' in {module_path} is not callable; expected a class"
        )
    return skill_class  # type: ignore[no-any-return]


def _build_tools() -> ToolRegistry:
    raw = os.environ.get("NIMBLE_AI_CONFIG", "").strip()
    ai_config: AiConfig | None = None
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid NIMBLE_AI_CONFIG: not valid JSON ({exc})"
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid NIMBLE_AI_CONFIG: expected a JSON object with "
                "provider, model, and api_key_env"
            )
        try:
            ai_config = AiConfig(
                provider=data["provider"],
                model=data["model"],
                api_key_env=data["api_key_env"],
            )
        except KeyError as exc:
            key = exc.args[0]
            raise RuntimeError(
                "Invalid NIMBLE_AI_CONFIG: missing required key "
                f"{key!r} (need provider, model, api_key_env)"
            ) from exc
    return ToolRegistry(
        ai=AiTool(ai_config), popup=PopupTool(), clipboard=ClipboardTool()
    )


def _extract_error(exc: BaseException) -> dict[str, Any]:
    tb = exc.__traceback__
    last_frame = traceback.extract_tb(tb)[-1] if tb else None
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "skill_file": last_frame.filename if last_frame else "",
        "line": last_frame.lineno if last_frame else 0,
    }


def run(module_path: str, class_name: str) -> None:
    try:
        skill_class = _load_skill_class(module_path, class_name)
        skill = skill_class()
    except Exception as exc:
        startup_response: dict[str, Any] = {
            "invocation_id": "",
            "status": "error",
            "error": _extract_error(exc),
        }
        sys.stdout.write(json.dumps(startup_response) + "\n")
        sys.stdout.flush()
        return
    try:
        tools: ToolRegistry = _build_tools()
    except RuntimeError as exc:
        startup_tools_error: dict[str, Any] = {
            "invocation_id": "",
            "status": "error",
            "error": _extract_error(exc),
        }
        sys.stdout.write(json.dumps(startup_tools_error) + "\n")
        sys.stdout.flush()
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        invocation_id: str = ""
        response: dict[str, Any]
        try:
            payload = json.loads(line)
            invocation_id = payload["invocation_id"]
            _invocation_local.invocation_id = invocation_id
            context = Context.from_dict(payload["context"])
            skill.run(context, tools)
            response = {
                "invocation_id": invocation_id,
                "status": "ok",
                "error": None,
            }
        except Exception as exc:
            response = {
                "invocation_id": invocation_id,
                "status": "error",
                "error": _extract_error(exc),
            }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("Usage: worker/entrypoint.py <module_path> <class_name>\n")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
