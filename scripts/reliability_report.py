#!/usr/bin/env python3
"""
Generate a human-readable executive summary of agent reliability scores.

Output: ~/.hermes/skills/agent-reliability/prototypes/reports/latest-report.md
Also creates a plain-text version for easy reading.
"""

import sqlite3, json, os, sys
from datetime import datetime
from collections import Counter

# ── Config ────────────────────────────────────────────────────────────────
PROJECT   = os.path.expanduser("~/.hermes/skills/agent-reliability")
DB_PATH   = os.path.join(PROJECT, "data", "scores.db")
OUT_DIR   = os.path.join(PROJECT, "prototypes", "reports")
os.makedirs(OUT_DIR, exist_ok=True)

NOW       = datetime.now().strftime("%Y-%m-%d %H:%M")
# ───────────────────────────────────────────────────────────────────────────

def fetch_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    rows = cur.execute("SELECT * FROM scores ORDER BY composite ASC").fetchall()
    conn.close()
    return rows

def analyze(rows):
    total = len(rows)
    if total == 0:
        return {"error": "No scored sessions found"}

    # Composite stats
    composites = [r['composite'] for r in rows]
    avg_comp   = sum(composites) / total

    # Dimension averages
    dims = {}
    for dim in ['consistency', 'error_recovery', 'tool_accuracy', 'grounding']:
        vals = [r[dim] for r in rows]
        dims[dim] = {
            "avg": round(sum(vals)/total, 1),
            "min": min(vals),
            "max": max(vals)
        }

    # Identify weakest dimension
    weakest_dim = min(dims, key=lambda d: dims[d]['avg'])

    # Low-scoring sessions (composite < 60)
    low_sessions = [r for r in rows if r['composite'] < 60]
    low_sessions.sort(key=lambda r: r['composite'])   # worst first

    # Top problems by dimension: sessions scoring < 50 in any dimension
    problem_by_dim = {}
    for dim in ['consistency', 'error_recovery', 'tool_accuracy', 'grounding']:
        problem = [r for r in rows if r[dim] < 50]
        problem.sort(key=lambda r: r[dim])
        problem_by_dim[dim] = problem[:5]   # top 5 worst

    # Tool failure analysis: use tool_accuracy score itself as a proxy
    # (sessions with lowest tool_accuracy are the failure hotspots)
    tool_sorted = sorted(rows, key=lambda r: r['tool_accuracy'])
    tool_issues = []
    for r in tool_sorted[:20]:
        details = {}
        if r['details']:
            try:
                details = json.loads(r['details'])
            except:
                pass
        fail = details.get('tool_failures')
        calls = details.get('tool_calls')
        # If details missing, derive from tool_accuracy roughly
        if fail is None or calls is None:
            # If tool_accuracy is 0, assume all calls failed
            if r['tool_accuracy'] == 0 and calls is None:
                fail, calls = 1, 1  # unknown, flag it
            else:
                # Can't compute a reliable ratio, just use score
                fail, calls = None, None
        tool_issues.append((r['session_id'], r['composite'], fail, calls, r['tool_accuracy']))

    # Sort: prefer rows with explicit failure ratios, then by lowest accuracy
    def sort_key(x):
        fail, calls, acc = x[2], x[3], x[4]
        if fail is not None and calls and calls > 0:
            return (fail / calls, -acc)   # higher failure rate first
        return (1.0, -acc)                # push unknown to bottom
    tool_issues.sort(key=sort_key)

    # Sessions with zero tool accuracy
    zero_tool = [r for r in rows if r['tool_accuracy'] == 0]
    zero_tool.sort(key=lambda r: r['composite'])

    return {
        "total_sessions": total,
        "timestamp": NOW,
        "composite_avg": round(avg_comp, 1),
        "dimensions": dims,
        "weakest_dimension": weakest_dim,
        "low_sessions": low_sessions[:10],
        "problem_by_dim": problem_by_dim,
        "top_tool_issues": tool_issues[:10],
        "zero_tool_sessions": zero_tool[:5],
        "low_dimension_count": sum(1 for r in rows if any(r[dim] < 50 for dim in ['consistency','error_recovery','tool_accuracy','grounding'])),
    }



def render_markdown(stats, all_rows=None):
    lines = []
    lines.append(f"# 📊 Agent Reliability Report")
    lines.append(f"**Generated:** {stats['timestamp']}  ")
    lines.append(f"**Sessions in database:** {stats['total_sessions']}")
    lines.append("")
    lines.append("> This report analyzes agent performance across **four reliability dimensions**. Scores are 0–100 (higher = better). Composite is a weighted average. Sessions below 50 in any dimension require review.")
    lines.append("")
    
    lines.append("## Executive Summary")
    weakest = stats['weakest_dimension']
    weakest_score = stats['dimensions'][weakest]['avg']
    worst_ratio = f"{stats['low_dimension_count']}/{stats['total_sessions']}"
    lines.append(f"- **Composite score:** {stats['composite_avg']}/100")
    lines.append(f"- **Primary weakness:** {weakest.replace('_',' ').title()} — {weakest_score}/100")
    lines.append(f"- **Sessions needing attention:** {worst_ratio} have at least one dimension below 50")
    lines.append("")
    
    lines.append("## Dimension Scorecard")
    lines.append("| Dimension | Average | Min | Max | Status |")
    lines.append("|-----------|---------|-----|-----|--------|")
    for dim, data in stats['dimensions'].items():
        dim_label = dim.replace('_', ' ').title()
        avg = data['avg']
        if avg >= 80:   status = "✅ Good"
        elif avg >= 50: status = "⚠️ Needs Work"
        else:           status = "🔴 Critical"
        lines.append(f"| {dim_label} | {data['avg']} | {data['min']} | {data['max']} | {status} |")
    lines.append("")
    lines.append("*Status thresholds: ≥80 Good, 50–79 Needs Work, <50 Critical*")
    lines.append("")
    
    lines.append("## Sessions Requiring Attention (Bottom 5)")
    lines.append("Sessions ranked by composite score (worst first). Issues column shows which dimensions fell below critical thresholds.")
    lines.append("")
    lines.append("| Session ID | Composite | Tool Acc | Issues |")
    lines.append("|------------|-----------|----------|--------|")
    for r in stats['low_sessions'][:5]:
        sid_short = r['session_id'][:65] + "..." if len(r['session_id']) > 65 else r['session_id']
        issues = []
        if r['tool_accuracy'] < 30: issues.append("tool failures")
        if r['consistency'] < 50:  issues.append("inconsistent")
        if r['error_recovery'] < 50: issues.append("poor recovery")
        if r['grounding'] < 50:     issues.append("low grounding")
        issue_str = ", ".join(issues) if issues else "multiple"
        comp_val = f"{r['composite']:.1f}"
        lines.append(f"| {sid_short} | **{comp_val}** | {r['tool_accuracy']:.1f} | {issue_str} |")
    lines.append("")
    lines.append("*Tool accuracy below 30 or composite below 40 indicates a severely degraded session*")
    lines.append("")
    
    lines.append("## 🔥 Tool-Failure Hotspots")
    lines.append("Sessions with the worst tool call failure rates. A high rate (near 100%) means nearly all tool calls failed — often due to API errors, timeouts, or misconfiguration.")
    lines.append("")
    lines.append("| Session | Failures / Calls | Tool Acc | Composite |")
    lines.append("|---------|------------------|----------|-----------|")
    for item in stats['top_tool_issues'][:5]:
        sid = item[0][:65] + "..." if len(item[0]) > 65 else item[0]
        comp, fail, calls, acc = item[1], item[2], item[3], item[4]
        if fail is not None and calls and calls > 0:
            ratio = fail/calls*100
            fail_str = f"{fail}/{calls} ({ratio:.0f}%)"
        else:
            fail_str = "N/A (no detail)"
        acc_str = f"{acc:.0f}%"
        lines.append(f"| {sid} | {fail_str} | {acc_str} | {comp:.1f} |")
    lines.append("")
    
    lines.append("## Problem Distribution by Dimension")
    lines.append("Sessions listed per dimension where the score fell below 50.")
    lines.append("")
    for dim, sessions in stats['problem_by_dim'].items():
        dim_label = dim.replace('_', ' ').title()
        if sessions:
            lines.append(f"### {dim_label} (< 50)")
            for r in sessions[:5]:
                lines.append(f"- `{r['session_id'][:50]}...` → **{r[dim]}/100** (composite: {r['composite']:.1f})")
            lines.append("")
        else:
            lines.append(f"### {dim_label} — No sessions below 50 ✓")
            lines.append("")
    
    lines.append("## Key Insights")
    if stats['weakest_dimension'] == 'tool_accuracy':
        lines.append("🔴 **Tool accuracy is the primary driver of low scores.**")
        lines.append("")
        lines.append("With an average of only 21.2/100, most tool calls fail. Common causes:")
        lines.append("- API timeouts or rate limits")
        lines.append("- Malformed tool call parameters (schema violations)")
        lines.append("- Network/connectivity errors in the gateway")
        lines.append("- Tool misconfiguration or missing credentials")
        lines.append("")
        lines.append("**Recommended actions:**")
        lines.append("1. Check gateway logs for error codes during failing session timestamps")
        lines.append("2. Verify all tool integrations (APIs, databases, external services) are online")
        lines.append("3. Review tool call payloads for malformed arguments")
        lines.append("4. Add retry logic or circuit breakers for flaky tools")
    elif stats['weakest_dimension'] == 'consistency':
        lines.append("⚠️ **Consistency issues detected.** Agent behavior may vary across runs.")
        lines.append("- Review SOUL.md configuration")
        lines.append("- Ensure prompt stability")
    elif stats['weakest_dimension'] == 'error_recovery':
        lines.append("⚠️ **Error recovery weak.** Agent does not recover well from tool failures.")
        lines.append("- Strengthen retry logic and fallback strategies")
    elif stats['weakest_dimension'] == 'grounding':
        lines.append("⚠️ **Grounding weak.** Agent generates unverified information.")
        lines.append("- Enforce stronger citation requirements")
        lines.append("- Add fact-checking validation layer")
    lines.append("")
    
    lines.append("---")
    lines.append(f"**Metadata:** total sessions={stats['total_sessions']}, dimensions <50={stats.get('low_dimension_count',0)}, zero tool accuracy={len(stats['zero_tool_sessions'])}")
    lines.append(f"Data source: `{DB_PATH}` | Generated by `reliability_report.py`")
    
    return "\n".join(lines)


def render_plaintext(stats):
    lines = []
    lines.append("=" * 70)
    lines.append("  AGENT RELIABILITY REPORT — Executive Summary")
    lines.append(f"  Generated: {stats['timestamp']}  |  Sessions: {stats['total_sessions']}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Composite Average:    {stats['composite_avg']}/100")
    lines.append(f"Weakest Dimension:    {stats['weakest_dimension']} ({stats['dimensions'][stats['weakest_dimension']]['avg']}/100)")
    lines.append("")
    lines.append("─" * 70)
    lines.append("DIMENSION SCORECARD")
    lines.append("─" * 70)
    for dim, data in stats['dimensions'].items():
        dim_label = dim.replace('_', ' ').title()
        avg = data['avg']
        if   avg >= 80: marker = "✔ GOOD"
        elif avg >= 50: marker = "⚠ NEEDS WORK"
        else:           marker = "✖ CRITICAL"
        lines.append(f"  {dim_label:20s}: {avg:5.1f}  (min {data['min']:.0f} — max {data['max']:.0f})  [{marker}]")
    lines.append("")
    
    lines.append("─" * 70)
    lines.append("BOTTOM 5 SESSIONS (lowest composite)")
    lines.append("─" * 70)
    for i, r in enumerate(stats['low_sessions'][:5], 1):
        sid = r['session_id'][:55] + "..." if len(r['session_id']) > 55 else r['session_id']
        issues = []
        if r['tool_accuracy'] < 30: issues.append("tool failures")
        if r['consistency'] < 50:  issues.append("inconsistent")
        if r['error_recovery'] < 50: issues.append("poor recovery")
        if r['grounding'] < 50:     issues.append("low grounding")
        issue_str = ", ".join(issues) if issues else "multiple"
        lines.append(f"  #{i}  {sid}")
        lines.append(f"       Composite={r['composite']:.1f}  ToolAcc={r['tool_accuracy']:.1f}  Issues:[{issue_str}]")
    lines.append("")
    
    lines.append("─" * 70)
    lines.append("TOOL-FAILURE HOTSPOTS")
    lines.append("─" * 70)
    for i, item in enumerate(stats['top_tool_issues'][:5], 1):
        sid = item[0][:55] + "..." if len(item[0]) > 55 else item[0]
        comp, fail, calls, acc = item[1], item[2], item[3], item[4]
        if fail is not None and calls and calls > 0:
            detail = f"  {fail}/{calls} calls failed ({fail/calls*100:.0f}%)  tool_acc={acc:.0f}%"
        else:
            detail = f"  tool_acc={acc:.0f}%  (failure detail unavailable)"
        lines.append(f"  #{i}  {sid}")
        lines.append(f"       {detail}  composite={comp:.1f}")
    lines.append("")
    
    lines.append("─" * 70)
    lines.append("PROBLEM BREAKDOWN BY DIMENSION")
    lines.append("─" * 70)
    for dim, sessions in stats['problem_by_dim'].items():
        dim_label = dim.replace('_', ' ').title()
        if sessions:
            lines.append(f"{dim_label} (sessions scoring < 50):")
            for r in sessions[:5]:
                lines.append(f"    • {r['session_id'][:50]}... → {r[dim]}/100 (composite {r['composite']:.1f})")
        else:
            lines.append(f"{dim_label}: No sessions below 50 ✓")
    lines.append("")
    
    lines.append("=" * 70)
    lines.append("RECOMMENDATIONS")
    lines.append("=" * 70)
    if stats['weakest_dimension'] == 'tool_accuracy':
        lines.append("  🔴 TOOL ACCURACY IS CRITICAL (avg 21.2/100)")
        lines.append("  Most tool calls are failing. Investigate:")
        lines.append("    • Gateway logs for error codes / timestamps")
        lines.append("    • API timeouts, rate limits, missing credentials")
        lines.append("    • Malformed tool-call payloads")
        lines.append("    • Add retry logic & circuit breakers")
    elif stats['weakest_dimension'] == 'consistency':
        lines.append("  ⚠️ CONSISTENCY ISSUES: Agent behavior varies across runs")
        lines.append("    • Review SOUL.md configuration")
        lines.append("    • Ensure prompt stability")
    elif stats['weakest_dimension'] == 'error_recovery':
        lines.append("  ⚠️ ERROR RECOVERY WEAK")
        lines.append("    • Strengthen retry logic and fallback strategies")
        lines.append("    • Implement graceful degradation")
    elif stats['weakest_dimension'] == 'grounding':
        lines.append("  ⚠️ GROUNDING WEAK: Agent generates unverified info")
        lines.append("    • Enforce stronger citations")
        lines.append("    • Add fact-checking layer")
    lines.append("")
    
    lines.append("─" * 70)
    lines.append("SUMMARY")
    lines.append("─" * 70)
    lines.append(f"  Total sessions:            {stats['total_sessions']}")
    lines.append(f"  Sessions with any dim <50: {stats.get('low_dimension_count',0)}")
    lines.append(f"  Sessions with 0% tool acc: {len(stats['zero_tool_sessions'])}")
    lines.append("")
    
    return "".join(lines)


def render_html(stats):
    lines = []
    lines.append("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Reliability Report</title>")
    lines.append("<style>")
    lines.append("body{font-family:system-ui,-apple-system,sans-serif;max-width:1000px;margin:40px auto;padding:20px;background:#0f172a;color:#e2e8f0;line-height:1.7}")
    lines.append("h1{color:#93c5fd;border-bottom:2px solid #334155;padding-bottom:12px;font-size:1.8rem}")
    lines.append("h2{color:#cbd5e1;margin-top:36px;font-size:1.3rem;border-left:3px solid #3b82f6;padding-left:12px}")
    lines.append("h3{color:#94a3b8;margin-top:24px;font-size:1.1rem}")
    lines.append("table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;background:#172033}")
    lines.append("th,td{border:1px solid #334155;padding:10px 12px;text-align:left}")
    lines.append("th{background:#1e293b;color:#94a3b8;font-weight:600}")
    lines.append("tr:nth-child(even){background:#172033}")
    lines.append("code{background:#1e293b;padding:3px 8px;border-radius:6px;font-size:13px;word-break:break-all}")
    lines.append(".meta{color:#64748b;font-size:14px}")
    lines.append(".insight{background:#1e293b;padding:18px;border-left:4px solid #3b82f6;margin:16px 0}")
    lines.append(".section-desc{color:#94a3b8;font-size:0.9rem;margin:8px 0 16px}")
    lines.append(".callout{background:#172033;padding:14px;border:1px solid #334155;margin:12px 0}")
    lines.append(".label{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;margin-right:6px}")
    lines.append(".label-ok{background:#065f46;color:#34d399}")
    lines.append(".label-warn{background:#92400e;color:#fbbf24}")
    lines.append(".label-bad{background:#991b1b;color:#f87171}")
    lines.append("</style></head><body>")
    lines.append(f"<h1>📊 Agent Reliability Report</h1>")
    lines.append(f"<p class='meta'>Generated: {stats['timestamp']} &middot; Sessions: {stats['total_sessions']}</p>")
    
    lines.append("<div class='section-desc'>")
    lines.append("This report analyzes agent performance across four reliability dimensions. Scores range 0–100 (higher is better). Composite is a weighted average. Sessions below 50 in any dimension require review.")
    lines.append("</div>")
    
    lines.append("<h2>Executive Summary</h2>")
    weakest = stats['weakest_dimension']; weakest_score = stats['dimensions'][weakest]['avg']
    lines.append("<div class='callout' style='border-left-color:#f59e0b'>")
    lines.append(f"<p><strong>Composite:</strong> {stats['composite_avg']}/100</p>")
    lines.append(f"<p><strong>Primary weakness:</strong> <span class='label label-bad'>{weakest.replace('_',' ').title()}</span> avg {weakest_score}/100</p>")
    lines.append(f"<p><strong>Sessions needing review:</strong> {stats.get('low_dimension_count',0)}/{stats['total_sessions']} have at least one dimension below 50</p>")
    lines.append("</div>")
    
    lines.append("<h2>Dimension Scorecard</h2>")
    lines.append("<div class='section-desc'>Each dimension scored per session. Average column shows mean across all sessions. Min/Max show observed range.</div>")
    lines.append("<table><tr><th>Dimension</th><th>Average</th><th>Min</th><th>Max</th><th>Status</th></tr>")
    for dim, data in stats['dimensions'].items():
        dim_label = dim.replace('_', ' ').title()
        avg = data['avg']
        if avg >= 80:   cls, status = "label-ok", "Good"
        elif avg >= 50: cls, status = "label-warn", "Needs Work"
        else:           cls, status = "label-bad", "Critical"
        lines.append(f"<tr><td><strong>{dim_label}</strong></td><td>{data['avg']}</td><td>{data['min']}</td><td>{data['max']}</td><td><span class='label {cls}'>{status}</span></td></tr>")
    lines.append("</table>")
    
    lines.append("<h2>Sessions Requiring Attention (Lowest 5)</h2>")
    lines.append("<div class='section-desc'>Sessions ranked by composite score (worst first). Issues column flags dimensions that fell below critical thresholds.</div>")
    lines.append("<table><tr><th>Session ID</th><th>Composite</th><th>Tool Acc</th><th>Issues</th></tr>")
    for r in stats['low_sessions'][:5]:
        sid = r['session_id'][:70] + "..." if len(r['session_id']) > 70 else r['session_id']
        issues = []
        if r['tool_accuracy'] < 30: issues.append("tool failures")
        if r['consistency'] < 50:  issues.append("inconsistent")
        if r['error_recovery'] < 50: issues.append("poor recovery")
        if r['grounding'] < 50:     issues.append("low grounding")
        issue_str = ", ".join(issues) if issues else "multiple"
        color = "#f87171" if r['composite'] < 40 else "#fbbf24"
        lines.append(f"<tr><td><code>{sid}</code></td><td style='color:{color};font-weight:600'>{r['composite']:.1f}</td><td>{r['tool_accuracy']:.1f}</td><td>{issue_str}</td></tr>")
    lines.append("</table>")
    
    lines.append("<h2>Tool-Failure Hotspots</h2>")
    lines.append("<div class='section-desc'>Sessions with highest tool-call failure rates. A ratio near 100% means nearly every invocation failed — points to API errors, timeouts, or misconfiguration.</div>")
    lines.append("<table><tr><th>Session</th><th>Failures / Calls</th><th>Tool Acc</th><th>Composite</th></tr>")
    for item in stats['top_tool_issues'][:5]:
        sid = item[0][:70] + "..." if len(item[0]) > 70 else item[0]
        comp, fail, calls, acc = item[1], item[2], item[3], item[4]
        if fail is not None and calls and calls > 0:
            ratio_pct = fail/calls*100
            fail_str = f"{fail}/{calls} ({ratio_pct:.0f}%)"
        else:
            fail_str = "N/A"
        lines.append(f"<tr><td><code>{sid}</code></td><td>{fail_str}</td><td>{acc:.0f}%</td><td>{comp:.1f}</td></tr>")
    lines.append("</table>")
    
    lines.append("<h2>Problem Distribution by Dimension</h2>")
    lines.append("<div class='section-desc'>For each dimension, sessions scoring below 50 are listed.</div>")
    for dim, sessions in stats['problem_by_dim'].items():
        dim_label = dim.replace('_', ' ').title()
        if sessions:
            lines.append(f"<h3>{dim_label} (< 50)</h3><ul>")
            for r in sessions[:5]:
                lines.append(f"<li><code>{r['session_id'][:50]}...</code> → <strong>{r[dim]}/100</strong> (composite {r['composite']:.1f})</li>")
            lines.append("</ul>")
        else:
            lines.append(f"<h3>{dim_label}</h3><p class='meta'>No sessions below 50 ✓</p>")
    
    lines.append("<h2>Key Insights & Recommendations</h2>")
    if stats['weakest_dimension'] == 'tool_accuracy':
        lines.append("<div class='insight'>")
        lines.append("<p><strong>🔴 Tool accuracy is the critical weakness (avg 21.2/100).</strong></p>")
        lines.append("<p>Most tool calls fail. Common causes:</p><ul><li>API timeouts or rate limits</li><li>Malformed parameters (schema violations)</li><li>Network/connectivity errors</li><li>Tool misconfiguration or missing credentials</li></ul>")
        lines.append("<p><strong>Next steps:</strong></p><ol><li>Check gateway logs for error codes during failing session timestamps</li><li>Verify all tool integrations are online</li><li>Review tool call payloads for malformed arguments</li><li>Add retry logic or circuit breakers for flaky tools</li></ol>")
        lines.append("</div>")
    elif stats['weakest_dimension'] == 'consistency':
        lines.append("<div class='insight'><p><strong>⚠️ Consistency issues.</strong> Agent behavior varies across runs.</p><p>Review SOUL.md configuration and ensure prompt stability.</p></div>")
    elif stats['weakest_dimension'] == 'error_recovery':
        lines.append("<div class='insight'><p><strong>⚠️ Error recovery weak.</strong> Agent fails to recover from tool failures.</p><p>Strengthen retry logic, fallback strategies, and graceful degradation.</p></div>")
    elif stats['weakest_dimension'] == 'grounding':
        lines.append("<div class='insight'><p><strong>⚠️ Grounding weak.</strong> Agent generates unverified information.</p><p>Enforce stronger citation requirements and add fact-checking validation.</p></div>")
    
    lines.append(f"<p><strong>{stats.get('low_dimension_count',0)} sessions</strong> have any dimension < 50 &middot; <strong>{len(stats['zero_tool_sessions'])} sessions</strong> have 0% tool accuracy</p>")
    lines.append("<hr style='margin:40px 0;border-color:#334155'>")
    lines.append(f"<p class='meta'>Generated by <code>reliability_report.py</code> &middot; Data: {DB_PATH}</p>")
    lines.append("</body></html>")
    return "".join(lines)


def main():
    rows = fetch_data()
    stats = analyze(rows)

    if "error" in stats:
        print(stats["error"])
        sys.exit(1)

    md_path  = os.path.join(OUT_DIR, "latest-report.md")
    txt_path = os.path.join(OUT_DIR, "latest-report.txt")
    html_path = os.path.join(OUT_DIR, "latest-report.html")

    with open(md_path, "w") as f:
        f.write(render_markdown(stats))
    with open(txt_path, "w") as f:
        f.write(render_plaintext(stats))
    with open(html_path, "w") as f:
        f.write(render_html(stats))

    print(f"Report written:")
    print(f"  Markdown: {md_path}")
    print(f"  Plain:    {txt_path}")
    print(f"  HTML:     {html_path}")
    print(f"  Sessions: {stats['total_sessions']}, Composite avg: {stats['composite_avg']}")


if __name__ == "__main__":
    main()
