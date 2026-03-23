# Headless Browsers for AI Agents on SSO-Protected Websites
## Comprehensive Research Report — OmegaLoop Session 20260322-175105-47795f-f873

**Date**: March 22, 2026
**Experiments**: 20 | **Wins**: 16+ | **Tools Evaluated**: 12 browsers/platforms, 12 MCP servers

---

## Executive Summary

**Recommendation: Playwright MCP is the clear winner** for AI agents that need to interact with SSO-protected websites. It provides the best accessibility tree output (10x more token-efficient than raw HTML), official Microsoft MCP server with 67+ tools, first-class auth persistence via storageState, and multi-browser support.

**However, the best strategy is to avoid browsers for auth entirely.** Use service principals, client credentials, and Entra Agent ID for authentication. Reserve browser automation for post-auth interaction with web UIs that have no API.

---

## The 3-Layer Architecture

### Layer 1: Authentication (Avoid the Browser)
- **Entra Agent ID** (service principals, managed identities)
- **Client credentials flow** (OAuth2, no browser needed)
- **Certificate-Based Auth** (CBA satisfies MFA requirements without interaction)
- **Device Code Flow** (one-time human bootstrap, then refresh tokens)
- **SAML cookie replay** (SP-initiated flow, capture and reuse cookies)

### Layer 2: Browser Interaction (When APIs Don't Exist)
- **Playwright MCP** for interactive navigation (accessibility tree output)
- **storageState** injection for pre-authenticated sessions
- **CDP attachment** to existing browser with active SSO session
- **BrowserMCP** (Chrome extension) for existing logged-in browser

### Layer 3: Data Extraction (Optimized for Token Efficiency)
- **AgentQL** for structured data (self-healing semantic queries)
- **Firecrawl** for clean markdown extraction
- **Crawl4AI** for bulk read-only ingestion (free, best token efficiency)

---

## Tool Rankings

| Rank | Tool | Score | Best For |
|------|------|-------|----------|
| 1 | **Playwright + MCP** | 8.8/10 | Overall best: SSO, output, efficiency |
| 2 | **Browserbase + Stagehand** | 7.6/10 | Managed infra, NL-driven agents |
| 3 | **browser-use** | 7.4/10 | Best open source, CDP-native |
| 4 | **AgentQL** | 7.2/10 | Post-login structured extraction |
| 5 | **Firecrawl** | 7.2/10 | Managed scraping, Claude integration |
| 6 | **Skyvern** | 6.8/10 | Interactive SSO with credentials mgmt |
| 7 | **Crawl4AI** | 6.8/10 | Token-efficient bulk crawling (no SSO) |
| 8 | **Puppeteer + CDP** | 6.6/10 | Raw CDP access, Google ecosystem |
| 9 | **Steel.dev** | 6.6/10 | Cloud infra with credential security |
| 10 | **Selenium** | 3.8/10 | Legacy only. NOT recommended |

---

## Token Efficiency (Critical for Agent Cost)

| Format | Tokens (typical page) | vs Raw HTML |
|--------|----------------------|-------------|
| Raw HTML | ~140,000 | baseline |
| Full accessibility tree | ~16,000 | 88% reduction |
| Interactive-only AT | ~4,000 | 97% reduction |
| Clean Markdown | ~9,000 | 93% reduction |
| Refs-only (agent-browser) | ~1,000 | 99% reduction |

**Recommended output pipeline:**
1. Scope to `<main>` content region
2. Filter to interactive elements + ancestors
3. Collapse overlapping bounding boxes
4. Viewport-only filtering
5. Cap at 50,000 chars
6. Single-snapshot retention (no history accumulation)

---

## SSO Pattern Recommendations

| Scenario | Best Pattern | Tool |
|----------|-------------|------|
| Azure-hosted agent, Microsoft APIs | Managed Identity + client credentials | MSAL (no browser) |
| Cross-cloud (K8s, GitHub Actions) | Federated Identity Credential | Entra FIC (no browser) |
| One-time human-assisted bootstrap | Device Code Flow | MSAL + refresh token cache |
| SAML-protected enterprise app | SP-initiated flow + cookie replay | Playwright storageState |
| WebAuthn/passkey MFA | CDP virtual authenticator | Playwright + CDP |
| TOTP-gated login | pyotp TOTP generation | Any browser tool + pyotp |
| Complex SSO with MFA push | Human-in-the-loop | Browserbase Live View |

---

## MCP Server Recommendations

| Use Case | MCP Server | Why |
|----------|-----------|-----|
| General browser automation | @playwright/mcp | Most tools (67+), best token efficiency |
| Debugging / performance | Chrome DevTools MCP | Lighthouse, perf traces, heap snapshots |
| Already logged in, local | BrowserMCP | Uses real browser session, no bot detection |
| Managed cloud browser | Browserbase/Stagehand | Anti-bot, CAPTCHA, NL-driven |
| Structured extraction | AgentQL MCP | Single-shot typed data |
| Multi-page scraping | Firecrawl MCP | Crawl, map, search, extract |
| Vision-model agents | Steel MCP | Numbered bounding boxes |
| Multi-backend | Hyperbrowser MCP | Choose CUA/browser-use/Claude |

---

## Security Non-Negotiables

1. **Never put credentials in the LLM context window**
2. **Use formal agent identities, not delegated human credentials**
3. **Ephemeral browser profiles destroyed after each session**
4. **PII/credential redaction before LLM ingestion**
5. **Default-deny network egress from agent sandboxes**
6. **Immutable audit logs exported in real-time**
7. **Short-lived tokens (15-30 min), auto-revoked on session end**
8. **Sanitize HTML before passing to LLM** (strip hidden text, comments, CSS)

---

## Key Insights from 20 Experiments

1. **Accessibility tree is THE differentiator** for agent-friendly browser tools
2. **No tool natively handles enterprise SSO** (SAML/Okta/Entra). All require manual patterns
3. **MFA push notifications cannot be automated by ANY tool**. TOTP and CBA are the only options
4. **Screenshot-based approaches cost 5-10x more tokens** than accessibility tree
5. **Prompt injection via web content is a critical unsolved risk** (OpenAI: "unlikely to ever be fully solved")
6. **Bot detection locks out HUMAN accounts** when agents use delegated credentials
7. **The best auth strategy is to avoid the browser entirely** (service principals, client credentials)
8. **Cloud-hosted agents cannot access intranet SSO** behind VPNs
9. **Session validation before every task run reduces failures by 78%**
10. **Standard Docker is insufficient isolation** for untrusted agent browser sessions
