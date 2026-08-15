# Pitfall 59: Verification Discipline — Test Before Declaring Complete

**Pattern**: Orchestrator makes code changes, restarts services, sees "active" status, and declares "fixed!" without actually verifying the fix works end-to-end. User retries and hits the same error, or a new one.

**User frustration signals**:
- "are you realy use e2e tested?"
- "are you realy TTD coding?"
- "always hangs up here?"
- Sending screenshots showing the same error persists

**Root causes**:
1. **Optimistic status checking**: `systemctl is-active` returns "active" even when the service crashes on first request
2. **Incomplete verification**: Only checking that service started, not that endpoints respond correctly
3. **Missing pre-flight checks**: Not verifying database schema matches models before testing
4. **Git merge conflicts**: Unresolved `<<<<<<< Updated upstream` markers cause SyntaxError on import

**Correct verification sequence**:
1. **Resolve all merge conflicts first**: `grep -rn "<<<<<<" backend/` before any testing
2. **Verify database schema**: Check new columns exist with `information_schema.columns` query
3. **Test actual endpoints**: `curl -X POST http://127.0.0.1:5000/api/v1/upload/check` with real payload
4. **Check logs for new errors**: `tail -50 logs/gunicorn-error.log` after each request
5. **Verify in browser**: User should refresh and retry, not just see "service active"

**Pre-flight checklist before declaring "fixed"**:
```bash
# 1. No merge conflicts
grep -rn "<<<<<<" backend/app/ 2>/dev/null | wc -l  # Should be 0

# 2. Database columns exist
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    result = db.session.execute(db.text('''
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = \"tasks\" AND column_name = \"chunks_json\"
    '''))
    print('chunks_json exists' if result.fetchone() else 'MISSING')
"

# 3. Service responds to requests
curl -s http://127.0.0.1:5000/api/v1/upload/check -X POST -H "Content-Type: application/json" -d '{"file_hash":"test"}' | grep -E "code|message"

# 4. No new errors in logs
tail -20 logs/gunicorn-error.log | grep -E "ERROR|Traceback" | tail -3
```

**Real case** (session fix-2026-06-25):
- Fixed `TaskChapter` import errors in 3 files
- Restarted backend, saw "active" status
- Declared "fixed!"
- User retried upload, got same 500 error
- **Actual cause**: Database missing `chunks_json` column, causing ProgrammingError on every query
- **Fix**: `ALTER TABLE tasks ADD COLUMN chunks_json JSON`
- **Lesson**: Service can be "active" but fail on first database query

**Key insight**: "Service active" ≠ "Service working". Always test the actual user action (upload file, generate the final output, etc.) before declaring complete. If you can't test it yourself, at minimum verify: (1) no import errors, (2) database schema matches models, (3) endpoints return 200/201/401 (not 500), (4) no new errors in logs after test request.

**TDD enforcement**: When user asks "did you test it?", they mean end-to-end from the browser, not "did the service start". Write a test that exercises the full path: frontend → API → database → response. If you can't write an automated test, at least manually verify each step and report what you checked.