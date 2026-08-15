# Playwright E2E Proof Test Pattern (production incident, 2026-06-15, updated 2026-06-19)

When backend tests pass but user reports the feature still doesn't work, write a Playwright E2E test that proves the EXACT user scenario in a real browser.

## System Chromium Setup (China / No-Download)

Playwright's default `npx playwright install chromium` downloads Chrome from Google's CDN, which is **blocked in China**. Use the system-installed Chromium instead:

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        launchOptions: {
          executablePath: '/snap/bin/chromium',  // or /usr/bin/chromium-browser
          args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
        },
      },
    },
  ],
});
```

**Detect system Chromium:** `which chromium-browser chromium 2>/dev/null` or `ls /snap/bin/chromium`.
**Install if missing:** `sudo snap install chromium` (Ubuntu) or `sudo apt install chromium-browser`.

## QA Wave Integration (v1.3.1+)

The AI Company QA wave (plugin v1.3.1+) automatically runs Playwright if `playwright.config.ts` exists:
```bash
npx playwright test --reporter=list
```
If no E2E tests exist for new feature pages, QA writes them using the token injection pattern below.

## Token Injection Pattern

For apps that use external auth-service (JWT), bypass login UI by injecting token into localStorage:

```typescript
// Pre-generate token via backend Python script
// Store in /tmp/e2e_token.txt (24h expiry)
const token = fs.readFileSync('/tmp/e2e_token.txt', 'utf-8').trim();

await page.goto(`${BASE_URL}/login`);
await page.waitForLoadState('networkidle');
await page.evaluate((t: string) => {
  localStorage.setItem('auth_token', t);
  localStorage.setItem('auth_user', JSON.stringify({
    id: 'user-uuid', username: 'testuser', display_name: 'Test User', role: 'user'
  }));
}, token);
```

## Hidden File Input Pattern

File inputs in drop-zone UIs are `class="hidden"` by design. Use `toBeAttached()` not `toBeVisible()`:

```typescript
const fileInput = page.locator('input[type="file"]');
await expect(fileInput).toBeAttached({ timeout: 10000 }); // NOT toBeVisible
await fileInput.setInputFiles(testPdfPath);
```

## Dedup Proof Test Pattern

The definitive proof test for dedup features:

```typescript
// 1. Upload file (new upload)
await fileInput.setInputFiles(testPdfPath);
await page.locator('button:has-text("上传")').click();
// Capture upload response → get task_id

// 2. Mark task as COMPLETED (via backend Python script)
execSync(`bash -c 'cd backend && python -c "..." ${taskId}'`);

// 3. Upload SAME file again
await page.goto(`${BASE_URL}/upload`);
await fileInput.setInputFiles(testPdfPath);
await page.locator('button:has-text("上传")').click();

// 4. Verify response has skip_to_result: true
// 5. Verify redirect to /result/{taskId} (NOT /plan/)
// 6. Verify NO POST /api/v1/plan call was made
```

## Shell Command in Playwright

`source` doesn't work in `/bin/sh` (Playwright's default). Use `bash -c`:

```typescript
const { execSync } = require('child_process');
execSync(`bash -c 'cd /path && source venv/bin/activate && python script.py'`);
```

## Video Recording for Proof

When the user asks "are you really fixed?" or needs visual proof, record a Playwright browser session:

```javascript
const { chromium } = require('playwright');

const CHROME = '/home/<user>/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome';

const browser = await chromium.launch({ 
  headless: true, 
  executablePath: CHROME 
});
const context = await browser.newContext({
  baseURL: 'http://localhost:3000',
  viewport: { width: 1280, height: 900 },
  recordVideo: { 
    dir: '/tmp/proof-video/', 
    size: { width: 1280, height: 900 } 
  }
});
const page = await context.newPage();

// ... perform the test actions ...

// CRITICAL: Must close context to save video
await context.close();
await browser.close();

// Find and send the video
const files = fs.readdirSync('/tmp/proof-video/');
// Send via: send_message(action='send', message='MEDIA:/tmp/proof-video/' + files[0])
```

**Pitfalls:**
1. **Chrome binary path mismatch** — Playwright may have multiple versions installed. Check with `ls ~/.cache/ms-playwright/` and use the correct path. The `chromium-1217` version works; `chromium_headless_shell-1223` may not exist.
2. **Hidden file inputs** — `waitForSelector('input[type="file"]', { state: 'attached' })` not `state: 'visible'`. Drop-zone UIs use `class="hidden"`.
3. **Auth token injection** — Get token from auth-service, inject via `localStorage` BEFORE navigating to the upload page:
   ```javascript
   // Auth-service login (NOT the app's login endpoint)
   const resp = await fetch('http://localhost:8081/api/auth/login', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ username_or_email: 'admin', password: '<password>' })
   });
   const { access_token } = await resp.json();
   
   await page.goto('/login');
   await page.evaluate((t) => { localStorage.setItem('auth_token', t); }, access_token);
   ```
4. **Upload button click required** — `setInputFiles()` alone doesn't trigger the upload. Must click the submit button:
   ```javascript
   await page.locator('input[type="file"]').setInputFiles(pdfPath);
   await page.locator('button:has-text("上传")').click();
   await page.waitForURL('**/plan/**', { timeout: 30000 });
   ```
5. **Auth-service field name** — The auth-service expects `username_or_email`, not `username`. Using `username` returns 422 "Field required".

## Sending Video to User

After recording, send the video file to the user / team channel:
```python
send_message(
    action='send',
    target='<channel>',  # any configured hermes send target (slack/feishu/whatsapp...)
    message='MEDIA:/tmp/proof-video/page@xxxxx.webm\n\n📹 Proof video showing the fix works'
)
```

The `MEDIA:` prefix tells Hermes to upload the file as an attachment.

## What "PROOF" Means

A proof test must demonstrate ALL of:
1. **API response** contains the expected flag (e.g., `skip_to_result: true`)
2. **Browser URL** shows the correct destination page
3. **No unwanted API calls** (e.g., generatePlan NOT called)
4. **Only expected API calls** were made (list them all)
5. **Video recording** shows the exact user flow (if user is skeptical)

If you can't show all 5 in the test output, it's not proof.
