# Win 008: Skyvern, Crawl4AI, Firecrawl Evaluation

## Experiment exp-008-47795f

### Skyvern: BEST for interactive SSO workflows
- **Vision-based** (not DOM-based): immune to layout changes
- Credential backends: native, Bitwarden, 1Password integration
- TOTP/2FA support built-in
- Persistent browser profiles
- Credentials never sent to LLM
- CDP tunnel for existing browser sessions
- MCP server, webhooks, OpenAPI
- **Weakness**: High token cost (vision), 20.9k stars vs browser-use's 82k

### Crawl4AI: BEST for read-only LLM ingestion
- 62.4k GitHub stars, pure Python
- Fit Markdown + BM25 noise filtering = best token efficiency reviewed
- Schema-driven extraction without LLM cost
- Semantic chunking: topic, regex, sentence-level
- **No SSO support** at all
- Free, self-hosted Docker

### Firecrawl: BEST managed scraping API
- 96.6k GitHub stars, most mature
- Clean markdown, schema JSON, screenshots
- Agent API (spark-1-mini/pro) for autonomous research
- Claude Code native skill + MCP server
- Browser API with persistent sessions
- **Weak SSO**: manual session setup only
- Credit-based pricing

### Synthesis Insight
**No tool natively handles enterprise SSO (SAML/Okta/Entra ID).** The closest approaches:
1. Skyvern: credential management + persistent profiles + TOTP
2. Browserbase: Contexts API + Live View human-in-the-loop
3. Playwright: storageState + CDP attachment to real browser

True automated enterprise SSO remains an unsolved problem across the entire space.
