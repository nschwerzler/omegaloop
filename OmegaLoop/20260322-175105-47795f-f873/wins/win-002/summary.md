# Win 002: Puppeteer Deep Evaluation

## Experiment exp-002-47795f
**Hypothesis**: Puppeteer's direct CDP access gives it advantages for advanced agent use cases.

## Key Findings

### SSO/Auth: ADEQUATE
- No native SSO support; manual form automation + cookie serialization
- `userDataDir` persists full browser profile (cookies, localStorage, IndexedDB, service workers)
- No built-in `storageState` equivalent (manual cookie + storage extraction)
- Same MFA limitations as Playwright (TOTP yes, push no)

### Agent Output: GOOD (via CDP)
- `page.accessibility.snapshot()` returns accessibility tree via CDP
- ~15-25% of raw HTML token cost with `interestingOnly: true`
- `DOMSnapshot.captureSnapshot` for layout-aware extraction (larger)
- Third-party `snapshotForAI()` (Midscene) adds agent-optimized output
- `backendNodeId` from AT enables selector-free element targeting

### CDP Advantages: UNIQUE STRENGTH
- First-class CDP access via `page.createCDPSession()`
- Raw CDP eliminates Playwright's Node.js relay hop (measured speed improvement)
- Cross-origin iframe (OOPIF) handling via explicit targetId+frameId
- Google's official `chrome-devtools-mcp` server is Puppeteer-backed

### Weaknesses vs Playwright
- Chrome/Chromium only (no Firefox, no WebKit)
- JavaScript/TypeScript only (no Python bindings)
- No auto-wait (manual timing = fragility on SPA login flows)
- Multi-agent: requires separate browser processes (vs Playwright's contexts)
- `puppeteer-extra-plugin-stealth` needed for anti-detection

## Verdict
**Puppeteer excels when you need raw CDP access or Google's MCP ecosystem.**
For most agent use cases, Playwright is simpler. Puppeteer's niche: performance-critical
CDP-heavy workloads and Chrome DevTools MCP integration.
