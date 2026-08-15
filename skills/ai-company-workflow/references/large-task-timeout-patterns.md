# Large Task Timeout Patterns

## Problem
`delegate_task` has a 600s (10min) hard timeout per subagent. Large implementation waves (5+ phases, 7+ files) routinely exceed this.

## Coder Wave: Split into Parallel Subtasks

### When to split
- PM plan has 4+ phases
- 5+ files to modify
- Task involves both new files AND refactoring existing ones

### How to split
Use `tasks` array (batch mode, up to 3 parallel) instead of single `goal`:
```python
delegate_task(tasks=[
  {"goal": "Phase 1-2: schema expansion + tests", "toolsets": ["terminal", "file"]},
  {"goal": "Phase 3: integration + tests", "toolsets": ["terminal", "file"]},
  {"goal": "Phase 4-5: prompts + tests", "toolsets": ["terminal", "file"]},
])
```

Each subtask should be independently completable within ~200s (leaving margin for test runs).

### Real case: Session f9fada28 (three-layer pipeline refactor)
- **Single coder goal**: Timed out at 600s with 29 API calls, partial work only
- **Split into 3 parallel**: All 3 completed in 180-270s each
  - Task 1: Schema expansion (14 layout types + new fields) → 32 tests, 180s
  - Task 2: Pipeline integration (core_service + theme + renderer) → 39 tests, 271s
  - Task 3: Prompt updates (14 layout descriptions) → 28 tests, 174s
- Total: 127 tests, all passing

### Task splitting guidelines
| Plan size | Coder tasks | QA approach |
|-----------|-------------|-------------|
| 2-3 phases, 3-4 files | Single goal OK | Subagent OK |
| 4-5 phases, 5-7 files | Split into 2-3 parallel | Run tests via terminal |
| 6+ phases, 8+ files | Split into 3 parallel | Run tests via terminal |

## QA Wave: Run Verification Directly

### Problem
QA subagent times out on large suites (reading all files + running tests + coverage analysis).

### Fix
Skip the QA subagent. Run directly:
```bash
# New tests
PYTHONPATH=backend .venv/bin/python -m pytest tests/test_new1.py tests/test_new2.py -v -q

# Syntax check
.venv/bin/python -m py_compile backend/app/services/new_file.py

# Record result
company_dispatch(result={"role": "qa", "status": "completed", "summary": "..."})
```

## Reviewer Wave: Usually Fine
Code review subagents typically complete in ~250s (read many files but don't run tests). No splitting needed for most features.

## Fix Wave: Usually Fine
Fix waves address 2-5 specific issues. Typically complete in ~240s. If more than 5 issues, consider splitting.
