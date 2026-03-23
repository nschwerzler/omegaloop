# Win 012: Production Agent-Browser Architectures

## Experiment exp-012-47795f

### Platform Comparison

| | Claude Computer Use | OpenAI CUA | Google Mariner | Playwright MCP |
|--|---|---|---|---|
| Perception | Screenshots (vision) | Screenshots (vision) | Screenshots (vision) | Accessibility tree (text) |
| Token/step | ~1500 img tokens | Subscription | Not published | ~500-2000 text |
| SSO | Caller responsibility | Human pause | Human pause | Storage state + MSAL |
| Scope | Full desktop | Web only | Web only | Web only |
| Credential exposure | Risk (in screenshots) | Blocked by design | Not documented | Not exposed |

### 5 Production Architecture Patterns

1. **Brokered Auth** (most common): Composio/Nango/Arcade holds tokens; agent never sees credentials
2. **Pre-Authenticated Session Injection**: Export storage state, load before agent starts. 78% failure reduction
3. **Human-in-the-Loop Auth Gate**: Agent pauses at login, human completes, agent resumes
4. **Service Account + API-First** (preferred): Client credentials flow, no browser needed
5. **Short-Lived JWTs with HSM**: 5-minute scoped tokens, 92% reduction in credential theft

### Critical Findings

1. **Playwright MCP + storage state is the most SSO-friendly approach** for non-interactive pipelines
2. **Screenshot-based approaches (Claude, OpenAI, Mariner) all struggle with SSO** — redirects, MFA, bot detection
3. **"Never let the LLM touch credentials"** is universal across all serious deployments
4. **Cloud-hosted agents (Operator, Mariner) CANNOT access intranet SSO** behind VPNs
5. **Session validation before every task run is critical** — stale cookies cause mid-task failures
6. **Accessibility tree approaches are LESS fingerprinted** than screenshot loops by anti-bot systems
