# Win 010: Token Optimization — Output Strategies for Agents

## Experiment exp-010-47795f

### Measured Token Costs by Format

| Format | Tokens (typical page) | vs Raw HTML |
|--------|----------------------|-------------|
| Raw HTML | 138,550 | baseline |
| Full accessibility tree | 14,000-19,000 | ~87% reduction |
| Interactive-only AT | 3,000-8,000 | ~95% reduction |
| Clean Markdown | 9,364 | ~93% reduction |
| Refs-only (agent-browser) | ~1,000 | ~99% reduction |

### Highest-Impact Techniques (ranked)

| Technique | Reduction | Complexity |
|-----------|-----------|------------|
| Interactive-elements-only extraction | 90-95% | Medium |
| HTML to Markdown with boilerplate strip | 80-93% | Low |
| DOM downsampling (D2Snap k=0.6,l=0.9,m=0.3) | ~96% bytes | High |
| Single-snapshot retention (no history) | Eliminates linear growth | Low |
| Prefix caching (static/dynamic prompt split) | 89% on long sessions | Low |
| Pre-filter LLM on snapshots | 57% cost reduction | Medium |
| Scoped locator (main vs body) | 20-60% | Low |
| Viewport-only filtering | 10-40% | Low |

### Recommended Architecture for Agent Browser Output

1. Scope to `main` content region (not full `body`)
2. Filter to interactive elements + ancestor hierarchy
3. Collapse overlapping bounding boxes
4. Filter to viewport-visible elements
5. Cap at 50,000 chars; truncate repetitive lists
6. Keep only current snapshot in prompt (discard history)
7. Screenshot only for visual verification
8. Set-of-Mark annotation for dense UIs (numbered bounding boxes)
9. Prefix-cache system prompt separately from page state

### Key Findings
- **Hierarchy preservation is critical**: Flattening the DOM to a list hurts LLM performance. D2Snap preserves hierarchy while reducing size
- **AgentOccam "pivotal node" selection**: +161% success rate improvement on WebArena by keeping only task-relevant subtrees
- **Vision is expensive**: Each screenshot adds ~0.8s latency + 800-3000 tokens. Use text-first, vision-fallback
- **Set-of-Mark prompting**: Converts coordinate prediction (hard) to numbered box identification (easy). Critical for dense enterprise UIs
