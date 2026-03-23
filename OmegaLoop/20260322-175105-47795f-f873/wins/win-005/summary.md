# Win 005: browser-use Evaluation

## Experiment exp-005-47795f
**Hypothesis**: browser-use's CDP migration solves cross-origin iframe issues critical for SSO.

## Key Findings

### SSO/Auth: ADEQUATE
- Persistent browser profiles (`user_data_dir`) for session reuse
- `sensitive_data` parameter hides credentials from LLM prompts
- Kerberos/NTLM support via Chromium launch args (community-documented)
- Profile sync script for cloud deployment
- **Gap**: No MFA interrupt handling, no SAML/OAuth awareness, Playwright storage_state incompatible

### Agent Output: VERY GOOD
- Compact accessibility tree with indexed interactive elements
- LLM sees numbered list of actionable elements, NOT raw HTML
- `flash_mode` skips evaluation steps for speed
- Configurable `page_extraction_llm` for vision tasks
- `max_history_items` limits context retention

### CDP Migration: KEY DIFFERENTIATOR
- Moved from Playwright to raw CDP WebSocket (no relay, no state drift)
- **OOPIF super-selectors**: `target_id + frame_id + backend_node_id` for cross-origin iframes
- Event-driven watchdog architecture (crash recovery, dialog handling)
- Faster element extraction and screenshots
- Custom `cdp-use` library: type-safe Python CDP bindings

### LLM Support
- Via LangChain: Anthropic, OpenAI, Google, Azure, Bedrock, Ollama
- `bu-2` (proprietary): fastest, purpose-built for browser tasks
- Gemini Flash: best third-party option
- Open-source models: <30% accuracy, not viable

### Stats
- 82k+ GitHub stars, Y Combinator backed ($17M)
- Production use: Amazon, Google, Microsoft, Stripe

### Weaknesses
- No MFA-awareness or conditional access handling
- Session crashes lose auth state (Cloud: must call `sessions.stop()`)
- Stealth mode is paid cloud feature only
- Open-source LLMs not production-viable
- Multi-redirect SSO chains generate many page states (token cost)

## Verdict
**Best open-source option for agent browser automation. CDP migration directly
addresses SSO's cross-origin iframe challenge. Primary gap: no MFA handling.**
