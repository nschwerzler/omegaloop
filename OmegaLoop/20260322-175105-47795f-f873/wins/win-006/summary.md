# Win 006: Steel.dev Evaluation

## Experiment exp-006-47795f

### Key Findings

**SSO/Auth: GOOD (cloud-only)**
- Profiles API: full Chrome User Data Dir persistence (cookies, localStorage, auth tokens, extensions)
- Credentials API (beta): AES-256-GCM encrypted storage, TOTP code generation, auto-injection into login forms
- Field blurring prevents vision agents from reading credentials in screenshots
- **Critical gap**: Both Profiles and Credentials APIs are CLOUD-ONLY, not available in self-hosted Steel Local

**Agent Output: MODERATE**
- Clean Markdown, raw HTML, screenshots, PDFs
- Mobile Mode: simulated mobile viewport for simpler DOM (lower tokens)
- MCP server uses annotated screenshots with numbered bounding boxes (NOT accessibility tree)
- Claims 80% token reduction vs raw HTML via Markdown extraction

**Open Source**
- Core browser API: MIT license, self-hostable via Docker
- Auth features: cloud-only (proprietary)
- Self-hosted: single concurrent session only

**Pricing**: $29-499/mo, browser hours $0.05-0.10/hr

**Verdict**: Good infrastructure with strong credential security (field blurring, KMS encryption). But auth features locked to cloud, and MCP output is screenshot-based not accessibility-tree-based. Weaker than Browserbase for SSO, weaker than Playwright for structured output.
