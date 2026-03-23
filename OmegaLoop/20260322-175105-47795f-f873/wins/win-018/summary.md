# Win 018: Open Questions and Future Directions

## Experiment exp-018-47795f

### Unsolved Problems (as of March 2026)

1. **Prompt injection in web content**: OpenAI acknowledged it's "unlikely to ever be fully solved." Current mitigations (spotlighting, sanitization) reduce but don't eliminate risk.

2. **MFA push notifications**: No tool can automate Microsoft Authenticator push approvals. TOTP and CBA are the only automatable MFA methods.

3. **Conditional Access device compliance**: Headless browsers cannot satisfy Intune device compliance or Hybrid Azure AD Join requirements. Service principals bypass this entirely.

4. **Session expiry detection**: No tool provides proactive notification when SSO sessions expire. Agents must implement their own logged-out detection (redirect to login page, 401 responses).

5. **Cross-origin iframe handling in SSO**: Still fragile. browser-use's CDP migration with OOPIF super-selectors is the best approach, but not universally reliable.

### Emerging Trends to Watch

1. **Entra Agent ID**: Microsoft's formal non-human identity framework. Will likely become the standard for enterprise agent auth.

2. **Browser MCP convergence**: Expect consolidation as Playwright MCP absorbs features from Chrome DevTools MCP and community servers.

3. **Accessibility tree standardization**: WebDriver BiDi may eventually expose accessibility tree, closing Selenium's gap. Not yet in the spec.

4. **Agent-specific OAuth scopes**: IdPs may introduce fine-grained scopes for agent use (read-only, time-bounded, action-limited).

5. **Hardware-rooted agent identity**: HSM-backed certificates for agent authentication, enabling zero-trust verification of agent identity.
