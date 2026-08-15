# Hermes Plugin Building Pattern

Learned from building the `ai-company` plugin (2026-05-28). Follow the **spotify plugin** pattern exactly.

## File Structure

```
~/.hermes/hermes-agent/plugins/<plugin-name>/
├── plugin.yaml      # Metadata (name, version, description, author, kind, provides_tools)
├── __init__.py      # register(ctx) function — entry point
├── engine.py        # Core logic (classes, DB, state management)
└── tools.py         # Tool schemas (JSON Schema) + handler functions
```

## plugin.yaml

```yaml
name: my-plugin
version: 1.0.0
description: "What it does — N tools (list them)"
author: YourName
kind: backend              # backend = auto-loaded, no user opt-in
provides_tools:
  - tool_name_1
  - tool_name_2
```

For hook-based plugins (like disk-cleanup), use `hooks:` instead:
```yaml
hooks:
  - post_tool_call
  - on_session_end
```

## __init__.py — Registration

```python
def register(ctx) -> None:
    """Called once by plugin loader."""
    for name, schema, handler, emoji in TOOLS:
        ctx.register_tool(
            name=name,
            toolset="my_toolset",     # Groups tools in `hermes tools list`
            schema=schema,
            handler=handler,
            check_fn=lambda: True,    # Gate: return False to hide tool
            emoji=emoji,
        )
```

**Hyphenated directory names** (e.g., `ai-company`, `disk-cleanup`): Use **relative imports** in `__init__.py`:
```python
from .tools import TOOL_SCHEMA, _handle_tool  # NOT: from plugins.ai_company.tools
```

## tools.py — Schema + Handler

```python
from tools.registry import tool_result, tool_error

MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"]
    }
}

def _handle_my_tool(param1: str, **kwargs) -> str:
    try:
        result = do_something(param1)
        return tool_result(result)    # Returns JSON string
    except Exception as e:
        return tool_error(str(e))
```

**All handlers must return JSON strings.** Use `tool_result()` and `tool_error()` from `tools.registry`.

## engine.py — Core Logic

Keep all state management, DB operations, and business logic in engine.py. Tools.py should be thin wrappers that parse args, call engine methods, and return formatted results.

**SQLite pattern** (for persistent state):
```python
import sqlite3, os
DB_PATH = os.path.join(os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes')), 'my-plugin.db')

class MyEngine:
    def __init__(self, conn=None):
        self.conn = conn or sqlite3.connect(DB_PATH)
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS ...")
        self.conn.commit()
```

## Enable / Test

```bash
hermes plugins enable my-plugin    # Takes effect on next session
hermes plugins list | grep my-plugin
```

To test without restarting Hermes:
```bash
cd ~/.hermes/hermes-agent/plugins/my-plugin
python3 -c "
import sys; sys.path.insert(0, '.')
from engine import MyEngine
e = MyEngine()
result = e.do_something('test')
print(result)
"
```

## Packaging for Other Machines

### GitHub (recommended)
```bash
# Push to GitHub
hermes plugins install username/hermes-plugin-my-plugin --enable
```

### Tarball (offline)
```bash
tar czf hermes-plugin-my-plugin.tar.gz my-plugin/
# On target machine:
cd ~/.hermes/hermes-agent/plugins/
tar xzf ~/hermes-plugin-my-plugin.tar.gz
mv hermes-plugin-my-plugin my-plugin
hermes plugins enable my-plugin
```

### Local path
```bash
hermes plugins install file:///path/to/my-plugin --enable
```

## Key Constraints
- Python 3.11+ (Hermes runs on 3.11)
- No external pip dependencies (use stdlib only for maximum portability)
- `check_fn` controls tool visibility — return False to hide when prerequisites aren't met
- Plugin takes effect on **next session** after enable (not immediately)
- `kind: backend` = auto-loaded on startup, no user opt-in needed
