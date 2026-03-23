# Win 001: Playwright Deep Evaluation

## Experiment exp-001-47795f
**Hypothesis**: Playwright is the strongest candidate for SSO+agent use due to Microsoft backing, MCP server, and accessibility tree output.

## Key Findings

### SSO/Auth: STRONG
- `storageState` API serializes cookies + localStorage atomically for auth persistence
- Handles cross-domain SSO redirects transparently (Entra ID, SAML, OAuth)
- TOTP MFA automatable via `otpauth` library; push MFA NOT automatable
- CDP attachment mode connects to already-authenticated real browser, bypassing login entirely
- **Blocker**: Conditional Access device-compliance policies reject headless browsers

### Agent Output: BEST IN CLASS
- ARIA snapshots: YAML accessibility tree, ~5-10x more token-efficient than raw HTML
- Ref IDs enable deterministic element targeting without CSS/XPath selectors
- Incremental snapshot mode sends only diffs between calls
- Playwright CLI (2026): saves snapshots to disk, ~4x more efficient than MCP streaming

### MCP Server: OFFICIAL
- `@playwright/mcp` by Microsoft, 70+ tools, actively maintained
- `--storage-state`, `--user-data-dir`, `--cdp-endpoint` flags for auth
- Integrated with VS Code Copilot, Claude Code, Cursor, GitHub Copilot

### Weaknesses
- MFA push notifications require human interaction
- Conditional Access device compliance blocks headless
- `sessionStorage` not included in storageState (manual serialization needed)
- Canvas/shadow DOM elements may not appear in accessibility tree

## Verdict
**Playwright is the current gold standard for AI agent browser automation with SSO.**
Best auth persistence, best structured output, official MCP, strongest ecosystem.
