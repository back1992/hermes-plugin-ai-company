# Prevention Over Cleanup & Timeout Chain Alignment

*Added 2026-06-17 — production upload pipeline debugging*

## Pitfall: Prevention Over Cleanup (User Correction)

When a bug creates accumulating garbage (zombie KBs, orphan records, leaked files), the Coder agent will often propose a periodic cleanup task as the fix. **The user will reject this.** The correct response is to fix the code that CREATES the garbage in the first place.

**Real case (Open WebUI zombie KBs):**
- `setup_task_kb()` created KB, uploaded file, but if attachment failed, returned the empty KB ID — leaving zombies
- 222 empty zombie KBs accumulated over weeks
- Coder's first fix: periodic cleanup cron
- User: "can fix in code not create? not just clean after created"
- **Correct fix**: Make `setup_task_kb()` treat attachment failure as FATAL — delete both file AND KB, return `(None, None)`

**The 3-layer prevention pattern:**
1. **Code**: Fix the creation path so garbage is never produced (prevention)
2. **Tests**: Mock external services so tests don't create real garbage (isolation)
3. **Cleanup**: Periodic sweep as defense-in-depth only (recovery)

**For Coder context:**
```
When a feature creates resources in an external service:
- Creation path MUST clean up on ANY failure step
- If step N fails, delete resources from steps 1..N-1 before returning
- NEVER return a partially-created resource ID
- Tests MUST mock the external service (conftest.py autouse fixture)
- Periodic cleanup is defense-in-depth, NOT the primary fix
```

## Pitfall: Gunicorn Timeout Chain Misalignment

When an API endpoint does significant work (file I/O, external API calls, DB operations), gunicorn's `--timeout` can kill the worker mid-request. The user sees the request hang — but there are no application-level errors.

**Real case (283MB upload):**
- Upload endpoint: save file (24s) + MD5 (2s) + DB insert (1s) + KB setup (3-5 min) = 4-6 min total
- Gunicorn `--timeout 120` killed the worker at 2 minutes
- User saw progress bar freeze at ~55%
- 5 `WORKER TIMEOUT` events in `gunicorn-error.log` at exact 2-minute intervals
- Fix: `--timeout 600` matching nginx `proxy_read_timeout`

**The timeout chain must be aligned:**
```
Browser (Axios) timeout  ≥  Nginx proxy_read_timeout  =  Gunicorn worker timeout
     ↑                           ↑                            ↑
  Adaptive per file          All requests              All requests
  (120s + 3s/MB)            (600s)                    (600s)
```

**Detection**: `grep "WORKER TIMEOUT" logs/gunicorn-error.log` — if present, the timeout is too low.

**Key insight**: The application never sees the timeout — gunicorn sends SIGKILL to the worker. Look for WORKER TIMEOUT in gunicorn error logs, NOT application logs. The request appears to "hang" from the user's perspective but is actually killed.

**For Coder context:**
```
TIMEOUT ALIGNMENT: When adding endpoints with significant work:
1. Calculate worst-case duration (file I/O + external APIs + DB)
2. Check gunicorn --timeout in systemd service file
3. Check nginx proxy_read_timeout in nginx config
4. Check frontend Axios timeout for the specific request
5. All must be ≥ worst-case duration
```
