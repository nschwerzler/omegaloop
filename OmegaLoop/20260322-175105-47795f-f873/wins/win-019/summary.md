# Win 019: Quick Reference Card — Copy-Paste Patterns

## Experiment exp-019-47795f

### Pattern 1: Playwright MCP with Pre-Auth (Most Common)
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--storage-state", "auth.json"]
    }
  }
}
```

### Pattern 2: Export Storage State (One-Time Auth)
```python
from playwright.sync_api import sync_playwright
import pyotp

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://login.microsoftonline.com/...")
    page.fill("#i0116", "user@company.com")
    page.click("#idSIButton9")
    page.fill("#i0118", password)
    page.click("#idSIButton9")
    # Handle TOTP MFA
    page.fill("#idTxtBx_SAOTCC_OTC", pyotp.TOTP(totp_secret).now())
    page.click("#idSubmit_SAOTCC_Continue")
    # Save auth state
    context.storage_state(path="auth.json")
```

### Pattern 3: MSAL Client Credentials (No Browser)
```python
from msal import ConfidentialClientApplication

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT}",
    client_credential={"thumbprint": CERT_THUMB, "private_key": open("cert.pem").read()},
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
access_token = result["access_token"]
```

### Pattern 4: CDP Virtual Authenticator (WebAuthn/Passkey)
```javascript
const client = await page.context().newCDPSession(page);
await client.send('WebAuthn.enable');
const { authenticatorId } = await client.send('WebAuthn.addVirtualAuthenticator', {
  options: { protocol: 'ctap2', transport: 'internal',
             hasResidentKey: true, hasUserVerification: true, isUserVerified: true }
});
await client.send('WebAuthn.setAutomaticPresenceSimulation', { authenticatorId, enabled: true });
```

### Pattern 5: Accessibility Tree Extraction (Token-Efficient)
```python
# Scoped to main content, not full body
snapshot = await page.locator("main").aria_snapshot()
# Returns YAML: ~4,000 tokens vs ~140,000 for raw HTML
```
