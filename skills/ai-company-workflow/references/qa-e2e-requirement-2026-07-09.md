# QA Wave Must Run Real E2E Tests (2026-07-09)

## Pattern
AI Company workflow completes all 5 waves, code review passes, but user asks "does ai company workflow, not run e2e test, check everything is ok?" — the QA wave only checked code quality and static analysis, never tested the live application.

## Root Cause
QA agent reads code files and checks syntax/imports, but doesn't make HTTP requests to the running app. Static analysis catches type errors but not runtime integration bugs (wrong endpoint URL, stale static assets, auth token issues).

## User Correction (verbatim)
"does ai company workflow, not run e2e test, check everything is ok?" — User expected the workflow to verify the app actually works end-to-end.

## Correct QA Wave Must Include
1. **HTTP endpoint tests**: `curl` or `requests` against the live backend to verify endpoints respond correctly
2. **Authentication flow**: Login with test credentials, get token, use token for protected endpoints
3. **Frontend page loads**: Verify all pages return 200 via `requests.get()`
4. **Static asset serving**: Verify JS/CSS files are served with correct MIME types
5. **End-to-end user flow**: Login → list items → view detail → trigger action → check result

## E2E Test Script Template
```python
import requests
BASE = "http://localhost:<backend-port>"
FRONT = "http://localhost:<frontend-port>"

# 1. Backend health
assert requests.get(f"{BASE}/").status_code == 200

# 2. Auth flow
token = requests.post(f"{BASE}/api/auth/login/",
    json=load_test_credentials()).json().get("access")  # creds from env/secret store
assert token

# 3. Protected endpoint
headers = {"Authorization": f"Bearer {token}"}
assert requests.get(f"{BASE}/api/books/", headers=headers).status_code == 200

# 4. Frontend pages
for page in ["/", "/login", "/dashboard", "/library"]:
    assert requests.get(f"{FRONT}{page}").status_code == 200

# 5. Static assets
assert "javascript" in requests.get(f"{FRONT}/_next/static/chunks/webpack-xxx.js").headers.get("content-type", "")
```

## Key Insight
"Code review passed" ≠ "App works". The QA wave MUST include live HTTP tests. If the QA agent only reads files, it's doing static analysis, not QA.

## Prevention
In the QA agent's goal/context, explicitly require:
- "Run at least 5 HTTP requests against the live backend"
- "Verify authentication flow works end-to-end"
- "Check that all frontend pages load (status 200)"
- "Report any 4xx/5xx responses as failures"
