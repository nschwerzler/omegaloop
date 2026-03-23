# Win 017: Implementation Blueprint — Playwright MCP + Entra Agent ID

## Experiment exp-017-47795f

### Recommended Production Architecture

```
[AI Agent (Claude/GPT/Gemini)]
    │
    ├── Auth Layer (NO browser)
    │   ├── Entra Agent ID → service principal
    │   ├── MSAL → client credentials → access token
    │   └── Token cache (SerializableTokenCache)
    │
    ├── Browser Layer (Playwright MCP)
    │   ├── --storage-state auth.json (pre-authenticated)
    │   ├── Accessibility tree output (snapshot mode)
    │   ├── Interactive-only filtering (97% token reduction)
    │   └── Scoped to main content region
    │
    ├── Extraction Layer (optional)
    │   ├── AgentQL for structured data
    │   └── Firecrawl for markdown
    │
    └── Security Layer
        ├── Firecracker microVM sandbox
        ├── Default-deny egress
        ├── PII redaction middleware
        ├── Ephemeral browser profiles
        └── 15-min JWT with auto-revocation
```

### Step-by-Step Setup

1. Register agent as Entra Agent ID (service principal, confidential client)
2. Issue certificate credential (not client secret)
3. Configure Conditional Access exclusion group with access reviews
4. Implement MSAL token acquisition with SerializableTokenCache
5. Export storageState from authenticated Playwright session
6. Configure Playwright MCP with --storage-state and --isolated flags
7. Enable snapshot mode (accessibility tree, not screenshots)
8. Deploy in Firecracker microVM with network egress allowlist
9. Implement session validation before each task run
10. Set up immutable audit logging for all agent actions
