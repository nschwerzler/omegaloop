# Win 011: MCP Browser Server Ecosystem — Complete Comparison

## Experiment exp-011-47795f

### 12 MCP Servers Compared

| Server | Tools | Output | Token Eff. | Best For |
|--------|-------|--------|-----------|----------|
| @playwright/mcp (Microsoft) | 67+ | Accessibility tree | Very High | General agent browser automation |
| Chrome DevTools MCP (Google) | 29 | DOM + perf traces | High | Debugging, Lighthouse, performance |
| Steel MCP | 9 | Numbered screenshots | Low | Vision-model agents |
| mcp-selenium | ~20 | JSON + BiDi diagnostics | Moderate | Selenium infra, Safari, cross-browser |
| Browserbase/Stagehand | ~7 | Natural language JSON | Moderate | NL-only agents, anti-bot |
| AgentQL MCP | 1 | Structured JSON | Very High | Single-shot data extraction |
| Firecrawl MCP | 12 | Markdown + JSON | High | Multi-page crawls, data pipelines |
| BrowserMCP | 12 | Accessibility tree | Good | Privacy, existing browser sessions |
| Browser Use MCP | 3-15 | Task status + content | Varies | Goal-oriented multi-step tasks |
| Hyperbrowser MCP | 10 | Markdown + JSON | Moderate | Multi-agent-backend selection |
| Bright Data MCP | 2-65+ | Markdown + structured | High | Enterprise extraction, vertical APIs |
| executeautomation/mcp-playwright | 28 | Screenshots + HTML | Moderate | Code generation recording |

### Token Efficiency Ranking
AgentQL > @playwright/mcp > Firecrawl > BrightData > Chrome DevTools (slim) > BrowserMCP > mcp-selenium > Browserbase > Hyperbrowser > Browser Use > Steel MCP

### Key Insight
**@playwright/mcp is the clear winner for SSO + agent use**. It has the most tools (67+), best token efficiency via accessibility tree, first-class auth persistence, and multi-browser support. Chrome DevTools MCP complements it for debugging/performance tasks.
