"""TRA-1178 regression: tools.py must resolve `engine` the way hermes loads it.

Hermes imports a directory plugin as ``hermes_plugins.<slug>`` through
``hermes_cli/plugins_loader.py::_load_directory_module``:
``spec_from_file_location(name, plugin_dir/"__init__.py",
submodule_search_locations=[plugin_dir])``, then
``importlib.import_module(f"{module.__name__}.tools")``. The plugin dir is
never appended to ``sys.path``, so inside a handler a bare
``from engine import TaskManager`` raises ModuleNotFoundError at call time
while ``from . import engine`` resolves.

The rest of this suite masks that: ``tests/conftest.py`` and ``test_tools.py``
both put the plugin root on ``sys.path``, so the bare imports succeed there and
two of the five failures were additionally swallowed by ``except ImportError:
pass`` (wave-3 dispatch silently degraded to whole-wave mode; status silently
omitted task progress). The functional test below runs the handlers in a
subprocess that replicates the real loader with an empty ``PYTHONPATH`` and a
cwd outside the plugin dir; the AST test keeps new bare imports out.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SIBLING_MODULES = {"engine", "prompts", "tools"}

# Runs under the real hermes import shape, prints one JSON object on stdout.
_CHILD = textwrap.dedent(
    '''
    import importlib
    import importlib.util
    import json
    import sys
    import types
    from pathlib import Path

    plugin_dir = Path(sys.argv[1]).resolve()
    db_path = Path(sys.argv[2]).resolve()
    project_path = sys.argv[3]

    # --- replicate hermes_cli/plugins_loader.py::_load_directory_module ---
    ns_parent = "hermes_plugins"
    module_name = ns_parent + ".ai_company"
    if ns_parent not in sys.modules:
        ns_pkg = types.ModuleType(ns_parent)
        ns_pkg.__path__ = []
        ns_pkg.__package__ = ns_parent
        sys.modules[ns_parent] = ns_pkg

    spec = importlib.util.spec_from_file_location(
        module_name, plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)])
    module = importlib.util.module_from_spec(spec)
    module.__package__ = module_name
    module.__path__ = [str(plugin_dir)]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    tools_mod = importlib.import_module(module.__name__ + ".tools")

    # Guard the guard: if the plugin dir leaked onto sys.path the bare-import
    # fallback would work and this test would prove nothing (that is exactly
    # what tests/conftest.py does to the rest of the suite).
    assert str(plugin_dir) not in sys.path, sys.path
    try:
        import engine  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError("bare `import engine` resolved; plugin dir leaked onto sys.path")

    engine_mod = importlib.import_module(module.__name__ + ".engine")
    engine_mod.DB_PATH = db_path

    if "--break-engine" in sys.argv[4:]:
        def _broken():
            raise ImportError("simulated engine import failure")
        tools_mod._load_engine = _broken

    def as_dict(raw):
        return json.loads(raw) if isinstance(raw, str) else raw

    sessions = engine_mod.CompanySession()
    session_id = sessions.create_session(project_path, "tra-1178-feature")["session_id"]
    sessions.store_plan(session_id, "# Plan", [
        {"index": 0, "description": "Add user model", "files": ["src/models/user.py"]},
        {"index": 1, "description": "Add auth endpoint", "files": ["src/api/auth.py"]},
    ])

    out = {"session_id": session_id}
    out["dispatch_wave3"] = as_dict(tools_mod._handle_company_dispatch(
        {"session_id": session_id, "wave_number": 3}))
    out["dispatch_task"] = as_dict(tools_mod._handle_company_dispatch_task(
        {"session_id": session_id, "task_index": 0}))
    out["status"] = as_dict(tools_mod._handle_company_status(
        {"session_id": session_id}))
    print(json.dumps(out))
    '''
)


def _run_under_hermes_loader(tmp_path: Path, *, break_engine: bool = False) -> dict:
    """Load the plugin the way hermes does and exercise the three handlers."""
    child = tmp_path / "child.py"
    child.write_text(_CHILD)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": "",
        "HOME": str(tmp_path),
    }
    argv = [sys.executable, str(child), str(PLUGIN_ROOT),
            str(tmp_path / "sessions.db"), str(tmp_path / "project")]
    if break_engine:
        argv.append("--break-engine")
    proc = subprocess.run(
        argv, cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, f"child failed:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_wave3_dispatch_reports_per_task_mode_under_hermes_loader(tmp_path):
    """Wave 3 must reach per-task mode, not silently fall through."""
    data = _run_under_hermes_loader(tmp_path)
    result = data["dispatch_wave3"]
    assert "error" not in result, result
    assert "tasks_error" not in result, result
    assert result.get("mode") == "per_task", result
    assert result.get("task_count") == 2, result
    assert [t["index"] for t in result["tasks"]] == [0, 1], result


def test_task_dispatch_and_status_resolve_engine_under_hermes_loader(tmp_path):
    """dispatch_task needs TaskManager + ROLE_PROMPTS; status needs TaskManager."""
    data = _run_under_hermes_loader(tmp_path)

    dispatched = data["dispatch_task"]
    assert "error" not in dispatched, dispatched
    assert dispatched.get("role") == "implementer", dispatched
    assert "Add user model" in dispatched.get("prompt", ""), dispatched

    status = data["status"]
    assert "error" not in status, status
    assert "tasks_error" not in status, status
    assert status.get("task_progress", {}).get("total") == 2, status


def test_engine_import_failure_is_reported_not_swallowed(tmp_path):
    """If engine really cannot be imported, every handler must say so.

    Pre-TRA-1178 wave-3 dispatch and status hid the failure behind
    ``except ImportError: pass`` and returned a plausible-looking payload with
    the per-task data missing.
    """
    data = _run_under_hermes_loader(tmp_path, break_engine=True)

    dispatch = data["dispatch_wave3"]
    assert "per-task dispatch unavailable" in dispatch.get("error", ""), dispatch

    dispatched = data["dispatch_task"]
    assert "error" in dispatched, dispatched
    assert "simulated engine import failure" in dispatched["error"], dispatched

    status = data["status"]
    assert "task progress unavailable" in status.get("tasks_error", ""), status
    assert "simulated engine import failure" in status["tasks_error"], status


def _function_level_sibling_imports(tree: ast.AST) -> list[str]:
    offenders = []
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        if fn.name == "_load_engine":
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0 and (node.module or "").split(".")[0] in SIBLING_MODULES:
                    offenders.append(
                        f"tools.py:{node.lineno} in {fn.name}(): "
                        f"from {node.module} import "
                        f"{', '.join(a.name for a in node.names)}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in SIBLING_MODULES:
                        offenders.append(
                            f"tools.py:{node.lineno} in {fn.name}(): import {alias.name}"
                        )
    return offenders


def test_no_function_level_bare_sibling_imports():
    """In-function sibling imports must go through _load_engine().

    The module-level try-relative/except-absolute block is fine: a standalone
    ``import tools`` has no package context, so the absolute fallback is the
    only form that works there. Inside a function the relative form always
    works under hermes and the absolute form never does.
    """
    tree = ast.parse((PLUGIN_ROOT / "tools.py").read_text(), filename="tools.py")
    offenders = _function_level_sibling_imports(tree)
    assert not offenders, (
        "bare sibling imports inside functions break under hermes' plugin "
        "loader (plugin dir is not on sys.path) — use _load_engine():\n  "
        + "\n  ".join(offenders)
    )


def test_load_engine_helper_shape():
    """_load_engine must try the relative form first, then fall back."""
    tree = ast.parse((PLUGIN_ROOT / "tools.py").read_text(), filename="tools.py")
    helpers = [n for n in tree.body
               if isinstance(n, ast.FunctionDef) and n.name == "_load_engine"]
    assert len(helpers) == 1, "expected exactly one module-level _load_engine()"

    body = helpers[0].body
    assert isinstance(body[-1], ast.Return), "_load_engine must return the module"
    tries = [n for n in body if isinstance(n, ast.Try)]
    assert tries, "_load_engine must guard the relative import with try/except ImportError"
    trial = tries[0]
    relative = [n for n in ast.walk(trial)
                if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module is None]
    assert relative, "expected `from . import engine` in the try branch"
    handlers = [h for h in trial.handlers
                if isinstance(h.type, ast.Name) and h.type.id == "ImportError"]
    assert handlers, "expected an `except ImportError` branch"
    absolute = [n for n in ast.walk(handlers[0])
                if isinstance(n, ast.Import) and n.names[0].name == "engine"]
    assert absolute, "expected `import engine` in the except ImportError branch"


@pytest.mark.parametrize("handler", ["_handle_company_dispatch",
                                     "_handle_company_dispatch_task",
                                     "_handle_company_status"])
def test_no_silent_importerror_swallow(handler):
    """A failed engine import must surface, never `except ImportError: pass`."""
    tree = ast.parse((PLUGIN_ROOT / "tools.py").read_text(), filename="tools.py")
    fns = [n for n in tree.body
           if isinstance(n, ast.FunctionDef) and n.name == handler]
    assert fns, f"{handler} not found"
    silent = []
    for node in ast.walk(fns[0]):
        if not isinstance(node, ast.Try):
            continue
        for h in node.handlers:
            name = getattr(h.type, "id", None) if isinstance(h.type, ast.Name) else None
            if name not in ("ImportError", "ModuleNotFoundError"):
                continue
            if all(isinstance(s, ast.Pass) for s in h.body):
                silent.append(f"tools.py:{h.lineno} except {name}: pass")
    assert not silent, (
        f"{handler} swallows engine import failures ({', '.join(silent)}); "
        "return tool_error / report the reason instead"
    )
