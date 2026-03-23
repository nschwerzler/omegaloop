# Win 009: SSO Authentication Patterns for AI Agents

## Experiment exp-009-47795f — CRITICAL FINDING

### Microsoft Entra Agent ID (New, Ignite 2025)
- Dedicated identity framework for AI agents
- Agent entities are confidential clients ONLY (no interactive flows)
- Three modes: interactive (OBO), autonomous (client credentials), user-principal
- NO redirect URIs, NO public client — fully headless by design

### Best Patterns by Scenario

| Scenario | Pattern | MFA? |
|----------|---------|------|
| Azure-hosted agent | Managed Identity + client credentials | No |
| Cross-cloud (K8s, GitHub Actions) | Federated Identity Credential (FIC) | No |
| Graph/M365 access | Service principal + certificate | No |
| One-time human bootstrap | Device Code Flow (RFC 8628) | User handles once |
| SAML-protected app | SP-initiated flow + cookie replay | TOTP or CBA |
| WebAuthn/passkey MFA | Playwright + CDP virtual authenticator | Simulated |
| TOTP-gated login | pyotp TOTP generation | Automated |

### Key Insight: AVOID THE BROWSER FOR AUTH
The single most important finding: **use service principals and client credentials whenever possible**. This eliminates the browser entirely from the auth flow. Browser-based SSO should be a fallback, not the primary strategy.

### SAML Automation
- Okta: Sessions API `/api/v1/authn` for programmatic auth, `sid` cookie replay
- ADFS: WS-Trust usernamemixed endpoint for headless token acquisition
- PingFederate: SP-initiated flow with form-based auth, headless-capable

### MFA Strategies
1. **TOTP** (pyotp): Fully automatable, requires shared secret from enrollment
2. **FIDO2/WebAuthn**: CDP virtual authenticator (`WebAuthn.addVirtualAuthenticator`)
3. **Certificate-Based Auth**: CBA with "multifactor" binding satisfies MFA with zero interaction
4. **Conditional Access exclusions**: Dedicated security group + access reviews

### Certificate-Based Auth: THE BEST OPTION
- X.509 client certificate at TLS layer
- No password, no OTP, no FIDO2 device
- CBA with multifactor binding = fully automated MFA satisfaction
- Works for Exchange Online, Graph API, and any Entra-protected resource
