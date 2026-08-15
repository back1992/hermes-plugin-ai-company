# AI Company Plugin — Structure & Installation

The AI Company workflow is implemented as both a **Skill** (teaches the orchestrator how to run the workflow) and a **Plugin** (provides execution tools). The plugin is the primary execution path. Per pitfall #3 the two must be updated together — that is why the skill ships inside this repo.

## Plugin Location

```
~/.hermes/plugins/ai-company/
├── plugin.yaml      — Plugin metadata (name, version, kind: backend, 9 tools)
├── __init__.py      — register(ctx) function, registers tools via ctx.register_tool()
├── engine.py        — CompanySession (SQLite), ContextStore, TaskManager, WAVE_DEFINITIONS
├── prompts.py       — ROLE_PROMPTS: source of truth for the 7 subagent system prompts
├── tools.py         — 9 tool schemas (JSON Schema) + handlers
└── skills/ai-company-workflow/ — the companion skill (also installable via `hermes skills install`)
```

## Tool API

| Tool | Params | Returns |
|------|--------|---------|
| `company_start` | `project_path`, `feature_name` | `{session_id, wave_plan, status}` |
| `company_dispatch` | `session_id`, `wave_number`, `role?`, `extra_context?`, `result?` | Without `result`: `{prompt, context_items}` for dispatch. With `result`: records wave; reviewer CHANGES_REQUESTED/FAIL returns `fix_wave_hint`. Wave 3 without `role`: per-task overview |
| `company_dispatch_task` | `session_id`, `task_index`, `result?` | Without `result`: implementer prompt. With `result`: records implementation, returns task_reviewer prompt |
| `company_status` | `session_id` | `{completed_waves, files_created, task_progress, status}` |
| `company_config` | `session_id`, `roles_yaml` | Per-session role prompt overrides |
| `company_report` | `session_id` | Full session report dict |
| `company_list` | `project_path?`, `status?`, `limit?` | List of sessions |
| `company_delete` | `session_id` | Deletes session + waves + tasks + context |
| `company_create_issue` | `title`, `description`, `project_path?`, `priority?`, ... | Files an issue via the project's `tracker.file_issue_cmd` (`.ai-company.yaml`); Linear helper fallback |

## Key Design Decisions

1. **Engine handles state, orchestrator handles delegation.** The plugin does NOT call `delegate_task`. It builds the context pack; the orchestrator agent calls `delegate_task` with that context.

2. **`company_dispatch` is dual-mode:**
   - Without `result` param → builds context for the wave (auto-injects previous results)
   - With `result` param → records wave completion

3. **SQLite DB** at `~/.hermes/ai-company-sessions.db` with 4 tables:
   - `sessions` (id, project_path, feature_name, status, created_at)
   - `waves` (session_id, number, role, status, summary, files_created)
   - `tasks` (session_id, index, description, files, status, result, review verdict) — Wave 3 per-task tracking
   - `context_store` (session_id, wave_number, key, value)

4. **Hyphenated directory name** (`ai-company`) requires relative imports (`.tools`, `.engine`) when loaded as a package.

## Installation on Another Machine

### Method 1: GitHub (recommended)
```bash
hermes plugins install back1992/hermes-plugin-ai-company --enable
hermes skills install back1992/hermes-plugin-ai-company/skills/ai-company-workflow
```

### Method 2: Tarball
```bash
# On source machine:
cd ~/.hermes/plugins/
tar czf ~/ai-company-plugin.tar.gz ai-company/

# On target machine:
cd ~/.hermes/plugins/
tar xzf ~/ai-company-plugin.tar.gz
hermes plugins enable ai-company
```

### Method 3: Local path
```bash
hermes plugins install file:///path/to/ai-company-plugin --enable
```

## Verification After Install

```bash
hermes plugins list | grep ai-company
# Expected: enabled

# Test engine:
cd ~/.hermes/plugins/ai-company
python3 -c "
from engine import CompanySession
mgr = CompanySession()
r = mgr.create_session('/tmp/test', 'demo')
sid = r['session_id']
ctx = mgr.build_context_for_wave(sid, 1, 'brainstormer')
print(f'Wave 1 prompt: {len(ctx[\"prompt\"])} chars')
print('OK')
"
```

## Wave Definitions (v2.x)

```python
WAVE_DEFINITIONS = [
    {"number": 1, "name": "Brainstorm + Design", "roles": ["brainstormer"],                  "parallel": False, "max_agents": 1, "per_task": False},
    {"number": 2, "name": "Planning",            "roles": ["planner"],                       "parallel": False, "max_agents": 1, "per_task": False},
    {"number": 3, "name": "Implementation",      "roles": ["implementer", "task_reviewer"],  "parallel": False, "max_agents": 1, "per_task": True},
    {"number": 4, "name": "Verification",        "roles": ["verifier"],                      "parallel": False, "max_agents": 1, "per_task": False},
    {"number": 5, "name": "Review",              "roles": ["reviewer"],                      "parallel": False, "max_agents": 1, "per_task": False},
    {"number": 6, "name": "Fix + Finish",        "roles": ["fixer"],                         "parallel": False, "max_agents": 1, "per_task": False, "auto_trigger": "on_review_fail"},
]
```
