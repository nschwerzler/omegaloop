#!/usr/bin/env python3
"""
The OmegaLoop Generator — produces a self-contained HTML dashboard from OmegaLoop session data.

Usage:
    python3 generate-hub.py /path/to/repo/OmegaLoop

Reads all manifest.json files from session folders and generates omegaloop.html.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_sessions(ol_dir: str) -> list[dict]:
    """Load all session manifests from the AR directory."""
    sessions = []
    ol_path = Path(ol_dir)

    if not ol_path.exists():
        print(f"ERROR: {ol_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    for session_dir in sorted(ol_path.iterdir()):
        manifest_path = session_dir / "manifest.json"
        if session_dir.is_dir() and manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                # Count actual win directories
                wins_dir = session_dir / "wins"
                if wins_dir.exists():
                    manifest["_win_dirs"] = len(
                        [d for d in wins_dir.iterdir() if d.is_dir()]
                    )
                else:
                    manifest["_win_dirs"] = 0
                # Count log files
                logs_dir = session_dir / "logs"
                if logs_dir.exists():
                    manifest["_log_count"] = len(list(logs_dir.glob("*.log")))
                else:
                    manifest["_log_count"] = 0
                # Load win summaries
                manifest["_win_summaries"] = []
                if wins_dir.exists():
                    for win_dir in sorted(wins_dir.iterdir()):
                        summary_path = win_dir / "summary.md"
                        if summary_path.exists():
                            manifest["_win_summaries"].append(
                                {
                                    "id": win_dir.name,
                                    "summary": summary_path.read_text()[:2000],
                                }
                            )
                        diff_path = win_dir / "changes.diff"
                        if diff_path.exists():
                            manifest["_win_summaries"][-1]["has_diff"] = True

                sessions.append(manifest)
            except (json.JSONDecodeError, KeyError) as e:
                print(
                    f"WARNING: Could not parse {manifest_path}: {e}", file=sys.stderr
                )

    return sessions


def generate_html(sessions: list[dict], ol_dir: str) -> str:
    """Generate the The OmegaLoop HTML dashboard."""
    sessions_json = json.dumps(sessions, indent=2, default=str)
    generated_at = datetime.now().isoformat()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The OmegaLoop — Live. Die. Repeat.</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --text-muted: #8b949e; --text-dim: #484f58;
    --accent: #58a6ff; --green: #3fb950; --red: #f85149;
    --yellow: #d29922; --purple: #bc8cff; --orange: #f0883e;
    --radius: 8px; --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    --mono: 'SF Mono', 'Cascadia Code', 'Fira Code', Consolas, monospace;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: var(--font); background: var(--bg); color: var(--text); padding: 24px; }}
  h1 {{ font-size: 28px; font-weight: 600; margin-bottom: 4px; }}
  .subtitle {{ color: var(--text-muted); font-size: 14px; margin-bottom: 24px; }}
  .stats-bar {{ display: flex; gap: 24px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
           padding: 16px 20px; min-width: 140px; }}
  .stat-value {{ font-size: 32px; font-weight: 700; font-family: var(--mono); }}
  .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
  .stat-value.green {{ color: var(--green); }}
  .stat-value.accent {{ color: var(--accent); }}
  .stat-value.yellow {{ color: var(--yellow); }}
  .stat-value.purple {{ color: var(--purple); }}
  .sessions {{ display: flex; flex-direction: column; gap: 16px; }}
  .session {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
              overflow: hidden; }}
  .session-header {{ padding: 16px 20px; cursor: pointer; display: flex; align-items: center;
                     justify-content: space-between; gap: 16px; }}
  .session-header:hover {{ background: rgba(88, 166, 255, 0.04); }}
  .session-title {{ font-weight: 600; font-size: 15px; flex: 1; }}
  .session-id {{ font-family: var(--mono); font-size: 12px; color: var(--text-dim); }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px;
            font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
  .badge-looping {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
  .badge-paused {{ background: rgba(210, 153, 34, 0.15); color: var(--yellow); }}
  .badge-completed {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
  .badge-analyzing {{ background: rgba(188, 140, 255, 0.15); color: var(--purple); }}
  .badge-initializing {{ background: rgba(139, 148, 158, 0.15); color: var(--text-muted); }}
  .session-stats {{ display: flex; gap: 16px; font-size: 13px; color: var(--text-muted); }}
  .session-stats span {{ white-space: nowrap; }}
  .session-body {{ display: none; padding: 0 20px 20px; border-top: 1px solid var(--border); }}
  .session.open .session-body {{ display: block; padding-top: 16px; }}
  .prompt-block {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
                   padding: 12px 16px; font-size: 14px; margin-bottom: 16px; line-height: 1.5; }}
  .timeline {{ position: relative; padding-left: 24px; }}
  .timeline::before {{ content: ''; position: absolute; left: 6px; top: 0; bottom: 0;
                       width: 2px; background: var(--border); }}
  .exp {{ position: relative; padding: 8px 0; font-size: 13px; }}
  .exp::before {{ content: ''; position: absolute; left: -20px; top: 14px; width: 10px; height: 10px;
                  border-radius: 50%; border: 2px solid var(--border); background: var(--bg); }}
  .exp.win::before {{ background: var(--green); border-color: var(--green); }}
  .exp.discard::before {{ background: var(--border); }}
  .exp.error::before {{ background: var(--red); border-color: var(--red); }}
  .exp-header {{ display: flex; gap: 8px; align-items: baseline; }}
  .exp-id {{ font-family: var(--mono); color: var(--text-dim); font-size: 11px; }}
  .exp-result {{ font-weight: 600; font-size: 12px; }}
  .exp-result.win {{ color: var(--green); }}
  .exp-result.discard {{ color: var(--text-muted); }}
  .exp-result.error {{ color: var(--red); }}
  .exp-desc {{ color: var(--text-muted); margin-top: 2px; }}
  .wins-section {{ margin-top: 16px; }}
  .wins-section h3 {{ font-size: 14px; margin-bottom: 8px; color: var(--green); }}
  .win-card {{ background: var(--bg); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 6px;
               padding: 12px 16px; margin-bottom: 8px; font-size: 13px; }}
  .win-card h4 {{ font-size: 13px; font-weight: 600; margin-bottom: 4px; }}
  .win-card pre {{ font-family: var(--mono); font-size: 11px; color: var(--text-muted);
                   white-space: pre-wrap; margin-top: 8px; max-height: 200px; overflow-y: auto; }}
  .arrow {{ transition: transform 0.2s; color: var(--text-dim); }}
  .session.open .arrow {{ transform: rotate(90deg); }}
  .empty {{ text-align: center; padding: 60px; color: var(--text-muted); }}
  .footer {{ text-align: center; color: var(--text-dim); font-size: 12px; margin-top: 32px;
             padding-top: 16px; border-top: 1px solid var(--border); }}
  .chart-bar {{ height: 16px; display: flex; border-radius: 4px; overflow: hidden; margin: 8px 0; }}
  .chart-bar .wins {{ background: var(--green); }}
  .chart-bar .discards {{ background: var(--border); }}
  .chart-bar .errors {{ background: var(--red); }}
</style>
</head>
<body>

<h1>&#x1f52c; The OmegaLoop</h1>
<p class="subtitle">OmegaLoop Dashboard &mdash; Generated {generated_at}</p>

<div id="app"></div>

<div class="footer">
  OmegaLoop &mdash; Autonomous research loops for any git repository<br>
  Refresh this page after new experiments to see updates. Re-run the generator to rebuild.
</div>

<script>
const sessions = {sessions_json};

function render() {{
  const app = document.getElementById('app');

  if (!sessions.length) {{
    app.innerHTML = '<div class="empty"><h2>No sessions found</h2><p>Run /omegaloop to start a research session.</p></div>';
    return;
  }}

  // Aggregate stats
  const totalSessions = sessions.length;
  const totalExperiments = sessions.reduce((s, x) => s + (x.experiment_count || 0), 0);
  const totalWins = sessions.reduce((s, x) => s + (x.win_count || 0), 0);
  const activeSessions = sessions.filter(s => s.status === 'looping').length;

  let html = `
    <div class="stats-bar">
      <div class="stat"><div class="stat-value accent">${{totalSessions}}</div><div class="stat-label">Sessions</div></div>
      <div class="stat"><div class="stat-value purple">${{totalExperiments}}</div><div class="stat-label">Experiments</div></div>
      <div class="stat"><div class="stat-value green">${{totalWins}}</div><div class="stat-label">Wins</div></div>
      <div class="stat"><div class="stat-value yellow">${{activeSessions}}</div><div class="stat-label">Active</div></div>
      <div class="stat"><div class="stat-value">${{totalExperiments ? ((totalWins / totalExperiments) * 100).toFixed(1) : 0}}%</div><div class="stat-label">Win Rate</div></div>
    </div>
    <div class="sessions">
  `;

  for (const session of sessions) {{
    const exps = session.experiments || [];
    const wins = exps.filter(e => e.result === 'win').length;
    const discards = exps.filter(e => e.result === 'discard').length;
    const errors = exps.filter(e => e.result === 'error').length;
    const total = exps.length || 1;

    const statusClass = 'badge-' + (session.status || 'initializing');
    const prompt = session.research_prompt || 'No prompt';
    const sid = session.session_id || 'unknown';

    // Truncate prompt for title
    const titlePrompt = prompt.length > 80 ? prompt.substring(0, 80) + '...' : prompt;

    html += `
      <div class="session" data-id="${{sid}}">
        <div class="session-header" onclick="toggleSession('${{sid}}')">
          <span class="arrow">&#x25B6;</span>
          <div class="session-title">${{titlePrompt}}</div>
          <span class="badge ${{statusClass}}">${{session.status || 'init'}}</span>
          <div class="session-stats">
            <span>&#x1f9ea; ${{session.experiment_count || 0}} exp</span>
            <span>&#x2705; ${{session.win_count || 0}} wins</span>
          </div>
        </div>
        <div class="session-body">
          <div class="session-id">Session: ${{sid}}</div>
          <div class="prompt-block">${{prompt}}</div>
    `;

    // Win/loss bar
    if (exps.length > 0) {{
      const wPct = (wins / total * 100).toFixed(1);
      const dPct = (discards / total * 100).toFixed(1);
      const ePct = (errors / total * 100).toFixed(1);
      html += `
        <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">
          Win ${{wPct}}% &middot; Discard ${{dPct}}% &middot; Error ${{ePct}}%
        </div>
        <div class="chart-bar">
          <div class="wins" style="width:${{wPct}}%"></div>
          <div class="discards" style="width:${{dPct}}%"></div>
          <div class="errors" style="width:${{ePct}}%"></div>
        </div>
      `;
    }}

    // Experiment timeline
    if (exps.length > 0) {{
      html += '<h3 style="font-size:14px;margin:12px 0 8px;">Experiments</h3><div class="timeline">';
      for (const exp of exps.slice(-30)) {{ // Show last 30
        const resultClass = exp.result || 'discard';
        html += `
          <div class="exp ${{resultClass}}">
            <div class="exp-header">
              <span class="exp-id">${{exp.experiment_id}}</span>
              <span class="exp-result ${{resultClass}}">${{(exp.result || '?').toUpperCase()}}</span>
            </div>
            <div class="exp-desc">${{exp.hypothesis ? (exp.hypothesis.length > 120 ? exp.hypothesis.substring(0, 120) + '...' : exp.hypothesis) : ''}}</div>
          </div>
        `;
      }}
      html += '</div>';
    }}

    // Win summaries
    const winSummaries = session._win_summaries || [];
    if (winSummaries.length > 0) {{
      html += '<div class="wins-section"><h3>&#x1f3c6; Wins</h3>';
      for (const win of winSummaries) {{
        // Extract title from markdown
        const titleMatch = win.summary.match(/^#\\s+(.+)/m);
        const title = titleMatch ? titleMatch[1] : win.id;
        html += `
          <div class="win-card">
            <h4>${{title}}</h4>
            <pre>${{win.summary.substring(0, 500)}}</pre>
          </div>
        `;
      }}
      html += '</div>';
    }}

    // Insights
    const insights = session.insights || [];
    if (insights.length > 0) {{
      html += '<h3 style="font-size:14px;margin:12px 0 8px;color:var(--purple);">&#x1f4a1; Insights</h3>';
      html += '<ul style="padding-left:20px;font-size:13px;color:var(--text-muted);">';
      for (const insight of insights.slice(-10)) {{
        html += `<li style="margin-bottom:4px;">${{insight}}</li>`;
      }}
      html += '</ul>';
    }}

    html += '</div></div>';
  }}

  html += '</div>';
  app.innerHTML = html;
}}

function toggleSession(id) {{
  const el = document.querySelector(`.session[data-id="${{id}}"]`);
  if (el) el.classList.toggle('open');
}}

render();
</script>
</body>
</html>""";


def main():
    if len(sys.argv) < 2:
        print("Usage: generate-omegaloop.py <OmegaLoop-dir>", file=sys.stderr)
        sys.exit(1)

    ol_dir = sys.argv[1]
    sessions = load_sessions(ol_dir)
    html = generate_html(sessions, ol_dir)

    output_path = os.path.join(ol_dir, "omegaloop.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"The OmegaLoop generated: {output_path}")
    print(f"  {len(sessions)} session(s) found")
    total_wins = sum(s.get("win_count", 0) for s in sessions)
    total_exps = sum(s.get("experiment_count", 0) for s in sessions)
    print(f"  {total_exps} total experiments, {total_wins} wins")


if __name__ == "__main__":
    main()
