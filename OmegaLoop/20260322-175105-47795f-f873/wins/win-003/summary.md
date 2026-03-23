# Win 003: Selenium Deep Evaluation

## Experiment exp-003-47795f
**Hypothesis**: Selenium 4+ BiDi improvements may make it viable for agent use.

## Key Findings

### SSO/Auth: WEAK
- No native SSO primitives; all auth flows require manual scripting
- Cookie persistence via `driver.get_cookies()` / `driver.add_cookie()` (manual, fragile)
- Cross-domain cookie injection restricted by browser security
- Selenium docs explicitly DISCOURAGE automating 2FA
- BiDi `add_authentication_handler` covers Basic/Digest auth only, NOT OAuth/SAML/OIDC

### Agent Output: POOR
- **NO accessibility tree API** (open feature request #16135, not merged)
- All locators DOM-based (CSS, XPath) — brittle against UI changes
- Community `mcp-selenium` (74 tools) adds `accessibility://current` resource, but not core
- Raw HTML parsing required — verbose, layout-dependent

### BiDi Improvements (4.6+, maturing through 4.38+)
- WebSocket bidirectional communication (replaces HTTP polling)
- Console log streaming, network interception, JS error capture
- Cross-browser (Chrome + Firefox)
- But: NO accessibility tree in BiDi spec yet

### Why Agents Avoid Selenium
- No accessibility tree (decisive gap)
- Separate driver executables (version mismatch breakage)
- Synchronous HTTP polling architecture
- Verbose boilerplate (explicit waits, driver lifecycle)
- Headless detection easier than Playwright
- Slower execution (HTTP round-trips per command)

## Verdict
**Selenium is NOT recommended for new AI agent work.**
The absence of accessibility tree support is disqualifying. BiDi improvements help
diagnostics but don't close the fundamental gap. Use Playwright instead.
Legacy Selenium Grid infrastructure is the only reason to stay.
