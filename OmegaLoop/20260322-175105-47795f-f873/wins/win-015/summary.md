# Win 015: Decision Framework — Which Tool for Which Scenario

## Experiment exp-015-47795f

### Decision Tree

```
Need browser for auth? ─── NO ──→ Use service principal + client credentials
  │                                (Entra Agent ID, MSAL, no browser needed)
  YES
  │
SSO type? ─── OAuth/OIDC ──→ Token injection via Playwright storageState
  │                           or CDP attachment to existing browser
  │
  ├── SAML ──→ SP-initiated flow + cookie replay
  │            Tool: Playwright + storageState
  │
  ├── Kerberos/NTLM ──→ Chromium --auth-server-allowlist
  │                      Tool: browser-use or Playwright
  │
  └── Unknown/complex ──→ Human-in-the-loop for first auth
                          Tool: Browserbase Live View or BrowserMCP

After authenticated, need to:

Extract structured data? ──→ AgentQL (self-healing queries, typed output)
Read/scrape content? ──→ Firecrawl (clean markdown, managed)
Navigate complex SPAs? ──→ Playwright MCP (accessibility tree, auto-wait)
Fill forms autonomously? ──→ Stagehand act() or browser-use
Vision-based interaction? ──→ Claude Computer Use or Skyvern
```

### Architecture Recommendations by Scale

**Solo developer / prototype:**
- Playwright MCP + storageState file
- No infrastructure cost
- Works locally

**Small team / startup:**
- Browserbase (Developer plan, $20/mo)
- Contexts API for auth persistence
- Stagehand for AI-mediated navigation

**Enterprise / regulated:**
- Entra Agent ID + service principals (avoid browser for auth)
- Playwright MCP in Firecracker microVM for browser tasks
- PII redaction middleware
- Immutable audit logging
- Short-lived JWTs (15-30 min)

**High-volume data pipeline:**
- Crawl4AI for public content (free, best token efficiency)
- Firecrawl for managed scraping with anti-bot
- AgentQL for structured extraction from authenticated pages
