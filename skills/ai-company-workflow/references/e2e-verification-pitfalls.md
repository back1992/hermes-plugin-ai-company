# E2E Verification After Deployment (User-Corrected 2026-06-17)

## The Rule: "Deployed" ≠ "Verified"

After deploying ANY fix, NEVER claim success until you have E2E proof through the LIVE stack.

**User frustration signal**: "are you really tested?" — I had changed gunicorn timeout from 120→600, restarted, saw clean logs, and declared "fixed". User tried again and upload STILL hung at 55%. The real root cause was `current_app.logger` crashing SSE generators — a completely different layer. My timeout fix was correct but insufficient, and I never verified the user-reported symptom was actually resolved.

## E2E Verification Checklist

Run ALL of these BEFORE reporting to user:

- [ ] **Service restarted**: `systemctl restart <service>` (with whatever privilege mechanism the host uses) + `systemctl status` confirms running
- [ ] **New config loaded**: Check startup log for the specific changed value (e.g., `grep "Using worker" logs/gunicorn-error.log` shows `gthread`, not `sync`)
- [ ] **Real request through production URL**: Test via `https://your-prod.example.com/api/...` (not just the local dev port) — this exercises nginx, CORS, SSL, the full chain
- [ ] **User-reported symptom is resolved**: If user says "hangs at 55%", verify the progress bar actually reaches 100%. If "download fails", verify the file actually downloads. Don't just check that YOUR change works — check that THEIR problem is gone.
- [ ] **Error log is clean**: `grep -c "Error" logs/gunicorn-error.log` after deployment timestamp should be 0 (or only pre-existing errors)

## Multi-Bug Cascade: When Your Fix Is Correct But Insufficient

Real case from 2026-06-17:
1. User reported: "upload hangs at 55%"
2. I found: gunicorn `--timeout 120` too short for large files
3. I fixed: Changed to `--timeout 600`, restarted, clean logs
4. I declared: "Fixed!" ❌
5. User tried again: STILL hangs at 55%
6. Real root cause: SSE generator crashed with `RuntimeError: Working outside of application context` — progress events stopped arriving, frontend progress bar froze
7. The timeout fix was correct but addressed a DIFFERENT layer

**Lesson**: When a bug involves multiple layers (upload → processing → streaming → frontend), fixing one layer doesn't guarantee the end-to-end flow works. Always test the FULL user journey, not just the layer you touched.

## Verification Script Pattern

Write a standalone Python script that tests the full flow:

```python
# /tmp/e2e_verify.py
import requests

BASE = "https://your-prod.example.com"  # Production URL, not localhost

# 1. Login
r = requests.post(f"{BASE}/api/v1/login", json=load_test_credentials())  # creds from env/secret store
assert r.status_code == 200, f"Login failed: {r.status_code}"
token = r.json()["data"]["access_token"]

# 2. Test the specific operation that was failing
headers = {"Authorization": f"Bearer ***
r2 = requests.get(f"{BASE}/api/v1/download/{task_id}.pptx", headers=headers, timeout=30)
assert r2.status_code == 200, f"Download failed: {r2.status_code}"
assert len(r2.content) > 1000, f"Download too small: {len(r2.content)} bytes"

print("✅ E2E verification PASSED")
```

Run it: `.venv/bin/python3 /tmp/e2e_verify.py`

## Common "Declared Fixed Prematurely" Patterns

| What you checked | What you missed |
|-----------------|-----------------|
| Gunicorn restarted, no errors | SSE generator still crashes (different code path) |
| Nginx config updated | Next.js ISR cache serving stale HTML |
| Code fix passes unit tests | Integration with auth-service still 401s |
| `curl` to the local dev port works | Production URL goes through different nginx config |
| No errors in error log | Error logged at WARNING level, not ERROR |
