# The OmegaLoop Dashboard

Self-contained HTML dashboard for monitoring all research sessions.

## Generating

```bash
python omegaloop/scripts/generate-hub.py /path/to/repo/OmegaLoop
# Outputs: OmegaLoop/omegaloop.html
open OmegaLoop/omegaloop.html
```

Or from the cleanup script:
```bash
bash omegaloop/scripts/ol-cleanup.sh hub
```

## Data Source

The dashboard reads all `manifest.json` files from `OmegaLoop/*/` subdirectories.
It renders session summaries, experiment timelines, win/loss ratios, and per-session
drill-downs with insights and win summaries.

## Features

- **Session cards**: each session with status badge, experiment count, win count
- **Win/loss bar**: visual ratio per session
- **Experiment timeline**: last 30 experiments with win/discard/error dots
- **Win summaries**: markdown content from `wins/*/summary.md`
- **Insights**: accumulated learnings from the agent
- **No server needed**: static HTML, open in any browser

## React Dashboard (AR Hub)

For the dense, multi-project, multi-machine view with real-time data, see the
`ar-hub.jsx` artifact. This is a React component that can be embedded in any
web application or served as a standalone page.

Features: commit hashes, machine ID columns, pipeline step dots, grouping by
project/machine/status, filtering, search, compact mode, and a "New Loop" launcher.
