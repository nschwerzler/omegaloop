# Win 007: AgentQL Evaluation

## Experiment exp-007-47795f

### Key Findings

**What it is**: AI-powered semantic query language for web elements. Write structured queries; get typed JSON back. Self-healing against layout changes.

**SSO/Auth: WEAK**
- No native SSO/OAuth/SAML support
- Uses Playwright session primitives (cookie save/load)
- MCP server is SESSIONLESS (cannot access authenticated pages)
- REST API path only works for public pages

**Agent Output: EXCELLENT for extraction**
- Structured query language returns typed dictionaries matching query shape
- Agent defines expected output schema upfront; gets ONLY requested fields
- `query_elements()` returns live Playwright handles (no serialization cost)
- `get_by_prompt()` finds single elements by natural language
- Very high token efficiency for targeted data extraction

**Integration**: Playwright (Python/JS), LangChain, LlamaIndex, Google ADK, Dify, MCP server

**Pricing**: Free tier (10 calls/min), Starter $29/mo, Professional $149/mo (50/min)

**Verdict**: Best-in-class for POST-LOGIN structured extraction. Self-healing queries are genuinely valuable. But zero SSO support and sessionless MCP make it unsuitable as the primary browser tool for SSO workflows. Use it as the extraction layer after Playwright handles auth.
