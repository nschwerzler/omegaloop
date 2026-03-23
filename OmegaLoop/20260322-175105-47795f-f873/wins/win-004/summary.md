# Win 004: Browserbase + Stagehand Evaluation

## Experiment exp-004-47795f
**Hypothesis**: Browserbase's managed cloud browser + Contexts API solves SSO persistence for agents.

## Key Findings

### SSO/Auth: STRONG (infrastructure-level)
- **Contexts API**: Persists full Chromium user data dir (cookies, localStorage, IndexedDB, service workers)
- Encrypted at rest, indefinite lifetime, restored on session creation
- **Live View**: Human-in-the-loop for manual SSO completion (SAML, MFA, passkeys)
- CDP passkey override: virtual authenticator disables WebAuthn prompts
- **Gap**: No IdP-level connectors (Okta, Entra), no session-expiry notification

### Agent Output: GOOD (via Stagehand)
- Stagehand provides `act()`, `extract()`, `observe()`, `agent()` primitives
- Natural language actions resolved to XPath selectors via LLM
- Accessibility tree available via standard Playwright APIs
- **Selector caching**: After first resolution, XPath cached; LLM calls drop to zero for known flows
- Server-side cache deduplicates identical `extract()` calls

### Pricing
| Plan | Browser Hours | Concurrency | Key Features |
|------|-------------|-------------|--------------|
| Free | 1 hr | 3 | 15-min session cap |
| Developer | 100 hrs ($0.12/hr after) | 25 | CAPTCHA solving, stealth |
| Startup | 500 hrs ($0.10/hr after) | 100 | 10k fetch calls |
| Scale | Custom | 250+ | Advanced stealth, HIPAA, org SSO |

### Strengths
- Purpose-built for AI agents (fingerprinting, CAPTCHA, proxies handled)
- Contexts API is the RIGHT abstraction for SSO persistence
- Live View is pragmatic for MFA completion
- SOC-2, HIPAA compliance available

### Weaknesses
- No native SSO protocol support (you handle the flow, they persist cookies)
- Silent session invalidation (no webhook on re-auth needed)
- Concurrent same-context sessions risk IdP lockout
- Enterprise features gated behind Scale tier (custom pricing)
- Functions: TypeScript only, us-west-2 only

## Verdict
**Best managed infrastructure for agent browsers. Contexts API + Live View is the
most practical SSO solution. Not cheap at scale.**
