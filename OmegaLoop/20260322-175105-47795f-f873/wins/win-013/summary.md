# Win 013: Security Assessment — Agent Browser + SSO Risks

## Experiment exp-013-47795f — CRITICAL SECURITY FINDINGS

### Top Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| Prompt injection via hidden HTML | Critical | High | Sanitize HTML before LLM; spotlighting |
| Credential exfiltration via injection | Critical | Medium | Never put creds in LLM context |
| Human account lockout from bot detection | High | High | Use formal non-human identities |
| Session cookie theft from disk | High | Medium | Ephemeral profiles, memory-only |
| MFA bypass via stolen session | High | Medium | Short-lived tokens, SameSite=Strict |
| GDPR/HIPAA violation from PII in prompt | High | High | PII redaction middleware |

### Critical Findings

**Prompt Injection is NOT solvable** (OpenAI Dec 2025): Hidden text (white-on-white, zero-width Unicode, HTML comments, img alt tags) can inject prompts into agents. CVE-2025-47241 scored 9.3 CVSS.

**MFA does NOT protect stolen sessions**: Once a cookie is issued, it represents a post-MFA session. Stealing the cookie bypasses MFA entirely.

**Bot detection locks out HUMAN accounts**: An agent repeatedly failing auth against a human's delegated account triggers Smart Lockout on that HUMAN user, locking out the real employee.

**Standard Docker is INSUFFICIENT**: Shared kernel = container escape risk. Use Firecracker microVM or gVisor for untrusted agent code.

### Defense-in-Depth Stack
1. Firecracker microVM (compute isolation)
2. Default-deny network egress
3. Read-only root filesystem
4. Ephemeral browser profiles (destroyed on exit)
5. Resource limits (CPU, memory, I/O)
6. Immutable audit logs exported in real-time
7. Human-approval gates for high-risk operations
8. Short-lived OAuth tokens (15-30 min, narrow scope)
9. PII/credential redaction before LLM context
10. Formal agent identity (NOT delegated human credentials)
