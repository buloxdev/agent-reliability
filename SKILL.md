---
name: agent-reliability
description: Monitor, trace, and score Hermes agent behavior — explain why decisions were made and measure consistency over time.
version: 1.0.0
author: Ant Dev
license: MIT
metadata:
  hermes:
    tags: [observability, reliability, hackathon, dashboard]
    related_skills: [hermes-agent, mission-control-dashboard]
---

# Agent Reliability Scores

An observability layer for Hermes agents. Parses gateway logs and session transcripts to compute reliability scores, detect anomalies, and generate human-readable reports.

## Quick Start (Standalone — No Hermes Required)

The fastest way to understand the tool is to run the demo scenarios. They generate synthetic agent sessions, score them, and print human-readable explanations for every dimension.

```bash
# Generate 4 demo scenarios and see why each score was assigned
python3 ~/.hermes/skills/agent-reliability/scripts/demo_scenario.py

# Open the dashboard to visualize results
open prototypes/cockpit-dashboard.html
```

This produces 4 scored sessions with plain-English breakdowns:
- **Good Agent** (100.0) — right tools, clean data, stable responses
- **Mixed Agent** (91.7) — partial failure but recovered
- **Flaky Agent** (57.7) — timeouts, retries, inconsistent answers
- **Hallucinating Agent** (25.6) — ignored tool data, made up confident answers

## Real Usage (With Hermes Logs)

```bash
# Parse gateway logs + session transcripts into traces
python3 ~/.hermes/skills/agent-reliability/scripts/trace_parser.py

# Score every session
python3 ~/.hermes/skills/agent-reliability/scripts/scorer.py

# Generate dashboard
python3 ~/.hermes/skills/agent-reliability/scripts/dashboard.py
```

## Components

| Script / Asset | Purpose |
|----------------|---------|
| `scripts/demo_scenario.py` | **Start here.** Generates 4 synthetic demo scenarios with human-readable score explanations |
| `scripts/trace_parser.py` | Parses `gateway.log` + session transcripts → structured JSON traces |
| `scripts/scorer.py` | Computes C/R/T/G scores from traces → SQLite `data/scores.db` |
| `scripts/dashboard.py` | Generates static `data/dashboard.html` from current scores |
| `scripts/run_pipeline.py` | **One-command full pipeline:** parse → score → generate visuals |
| `scripts/image_generator.py` | Generate visual scorecard images via AI (FAL) — template-based |
| `scripts/stamp_scorecards.py` | Overlay live stats onto pre-generated template images using ffmpeg |
| `prototypes/cockpit-dashboard.html` | Interactive fleet overview — gauges, radar, session grid |
| `prototypes/trace-replay.html` | Session drill-down — play/step through events with live score updates |
| `prototypes/reports/` | Auto-generated visual scorecards (PNG) + `index.html` gallery |
| `prototypes/reports/templates/` | High-quality AI-generated template images (base layer for stamping) |
| `data/scores.db` | SQLite database — all scored sessions |
| `data/traces/*.json` | Raw parsed session traces |
| `manim-video/` | Complete 32s demo video produced with Manim (all 5 scenes rendered) |

## Scoring Dimensions

- **Consistency** (0-100): Same/similar inputs → same/similar actions? Penalizes wild response-time variance, repeated errors, missing responses.
- **Error Recovery** (0-100): Did the agent retry/fix or silently fail? Checks if errors/timeouts are followed by successful responses.
- **Tool Accuracy** (0-100): Right tool for the job? Rewards successful calls whose results are used in the answer. Penalizes orphaned calls and irrelevant tools.
- **Grounding** (0-100): Claims backed by actual tool outputs? Compares assistant output length to tool output length. Penalizes confident claims unsupported by tool data.

## Data Storage

- Traces: `~/.hermes/skills/agent-reliability/data/traces/`
- Scores: `~/.hermes/skills/agent-reliability/data/scores.db` (SQLite)
- Dashboard: `~/.hermes/skills/agent-reliability/data/dashboard.html`

## Hackathon Prototypes

Two visual prototypes built for the hackathon (Apr 2026):
- `prototypes/cockpit-dashboard.html` — Dark-themed dashboard with animated gauge, radar charts, session fleet grid, score distribution histogram
- `prototypes/trace-replay.html` — Animated session replay with live score updates, event timeline, tool graph
- `prototypes/video-script.md` — 30-second demo video script

Serve locally: `cd prototypes && python3 -m http.server 8899`

## UI Lessons Learned (Apr 2026)

- **Monospace font overflow on large scores:** A 4rem monospace font with `line-height: 1` bleeds out of its line box, causing adjacent text ("Composite", "Waiting to start...") to overlap in the trace-replay Live Score panel. Fix: use `display: flex; flex-direction: column; gap: 10px` and raise `line-height` to `1.15`.
- **Fixed canvas width clipping:** A `<canvas width="1300">` gets clipped by `overflow: hidden` on narrow viewports, showing partial bars with labels colliding. Fix: remove fixed attributes, use CSS `width: 100%`, and read container size via `getBoundingClientRect()` at render time with `devicePixelRatio` scaling.
- **Tooltips:** Native `title` attributes don't work reliably in generated HTML dashboards. Use CSS `::after` + `data-tip` pattern instead:
  ```css
  .label { position: relative; cursor: default; }
  .label::after {
    content: attr(data-tip);
    position: absolute; bottom: 100%; left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.9); color: #fff;
    padding: 4px 8px; border-radius: 6px;
    white-space: nowrap; opacity: 0;
    pointer-events: none; transition: opacity 0.15s;
  }
  .label:hover::after { opacity: 1; }
  ```
- **Session labels:** Raw session IDs (`20260409_123550_81cfd0`) are unreadable in UI. Always format as human-readable: "Session Apr 9, 12:35"

## Documentation Lessons Learned (Apr 2026)

- **Lead with the standalone demo.** `demo_scenario.py` works without Hermes running and is the best entry point for understanding the tool. The original README front-loaded Hermes-specific setup and buried the demo.
- **Show concrete examples, not abstractions.** "Grounding measures whether claims are backed by tool outputs" is vague. "Hallucinating Agent scored 7.0 on Grounding because it claimed 'definitely down by 80%' while the tool returned 14 refunds" is clear.
- **Human-readable explanations are essential.** The `demo_scenario.py` output now includes plain-English breakdowns of why each dimension score was assigned. Numbers without explanations create confusion.

## Visual Reports (Apr 2026)

Auto-generated PNG scorecards for each pipeline run. Three templates:

| Template | Use Case | Orientation |
|----------|----------|-------------|
| `scorecard-latest` | Fleet overview — avg score, dimension bars, tier counts | Landscape |
| `alert` | Urgent notification when poor sessions (<40) detected | Landscape |
| `cover` | Minimalist hero for presentations / title cards | Landscape |

### Generate All Templates

```bash
# Full pipeline with visuals
python3 scripts/run_pipeline.py

# Or generate just the images (requires image generation tool)
python3 scripts/image_generator.py --all

# Generate a scorecard for a specific failing session
python3 scripts/image_generator.py --session 20260407_170358_4adf62e0
```

Output: `prototypes/reports/<type>-<timestamp>.png`

Visit `prototypes/reports/index.html` for a browsable gallery that auto-refreshes.

### Integration Tips

- **Telegram:** `python3 scripts/run_pipeline.py --notify telegram` sends the scorecard image + summary
- **Notion:** Attach PNGs directly to project pages
- **GitHub:** Include latest scorecard in README to show project health
- **Cron:** Hourly monitor already generates these (see `agent-reliability-monitor` cron job)

### Implementation Notes

The image generation uses a **template-stamping pattern**:
1. High-quality base images are generated once via AI (`image_generate` tool)
2. `stamp_scorecards.py` overlays live stats (avg score, counts) using text rendering
3. This avoids re-generating the entire graphic each run — faster, consistent style

If `ffmpeg drawtext` unavailable (common on macOS without full codec libs), the templates are used as-is (numbers may be stale). In production, use the `image_generate` tool directly for fully dynamic images.


### Trace Format Version Mismatch (Apr 2026)

**Symptom:** Newly parsed sessions score `tool_accuracy = 0` even though the transcript clearly shows tool calls being made.

**Root cause:** The `trace_parser.py` output format changed from:
```json
{ "session_id": "...", "turns": [{ "tools": [...], "answer": "..." }] }
```
to:
```json
{
  "sessions": [{
    "session_id": "...",
    "transcript_messages": [...],
    "tool_calls": [...],
    "tool_results": [...]
  }]
}
```

The `scorer.py` still reads `turns[].tools` which doesn't exist in the new format → zero tool count → score collapse.

**Fix options (pick one):**

1. **Rollback parser** to emit old format (quickest):
   In `trace_parser.py`, after constructing each session dict, add:
   ```python
   # Backward-compat: add turns array from new fields
   session['turns'] = convert_new_format_to_old(session)
   ```

2. **Upgrade scorer** to understand both formats (proper):
   In `scorer.py`, detect format:
   ```python
   if 'turns' in trace:
       # old path
   elif 'sessions' in trace:
       # new path: flatten sessions[0].tool_calls into turns-like structure
   ```

3. **Version the trace format** (future-proof):
   Have `trace_parser.py` write `{ "version": 2, "sessions": [...] }` and make scorer check version.

**Quick check:** Does your trace file have a top-level `turns` key or a `sessions` array?
```bash
python3 -c "import json; d=json.load(open('data/trarices/*.json')); print('turns' in d and 'sessions' not in d)"
```
False = new format. scorer.py needs updating.

**Current state:** Known issue; demo traces (old format) still work; new real traces show misleading scores until scorer is upgraded.


## When to Load


Load this skill when:
- User asks about agent performance or reliability
- Debugging why an agent made specific decisions
- Running post-session analysis or reports
- Demoing agent observability features


## Practical Testing & Troubleshooting (Apr 2026)

### Quick Health Check — "Is It Working?"

When you think the system is broken, run this checklist:

1. **Server running?**
   ```bash
   lsof -ti:8899 || (cd ~/.hermes/skills/agent-reliability/prototypes && python3 -m http.server 8899)
   ```
   If no process on 8899, the cockpit & trace replay UIs won't load.

2. **Scoring engine works?**
   ```bash
   python3 ~/.hermes/skills/agent-reliability/scripts/demo_scenario.py
   ```
   Should print 4 scenarios with scores (Good 100, Flaky 57.7, Hallucinating 25.6, Mixed 91.7). If this fails, the core logic is broken.

3. **Real data parsed?**
   ```bash
   ls ~/.hermes/skills/agent-reliability/data/traces/*.json | wc -l
   ```
   Should be > 0. If zero, the trace parser didn't find any gateway logs in `~/.hermes/logs/gateway.log` or `~/.hermes/sessions/`.

4. **Database populated?**
   ```bash
   sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db "SELECT COUNT(*), AVG(composite) FROM scores"
   ```
   Should return non-zero count and avg ~40-80. If count = 0, scorer hasn't run yet.

### Full End-to-End Test (Production Data)

```bash
cd ~/.hermes/skills/agent-reliability

# Step 1 — Parse new Hermes logs into traces
python3 scripts/trace_parser.py

# Step 2 — Score all traces (inserts new rows; preserves existing)
python3 scripts/scorer.py

# Step 3 — Open the interactive dashboard
#   (served automatically if already running on port 8899)
open http://localhost:8899/cockpit-dashboard.html
```

Expected outcome:
- `trace_parser.py` prints: `{"session_count": N, "output_path": ".../data/traces/YYYYMMDD_HHMMSS.json"}`
- `scorer.py` prints: `Scored M session(s); inserted K row(s)... Average composite: XX.XX`
- Dashboard loads and shows a fleet grid of colored session tiles.

### How to Actually Use the Scores

The dashboard is interactive. Here's the typical workflow:

```
[cockpit-dashboard.html]
  └─ Click any session tile (color-coded by score)
      ↓
[trace-replay.html?session=<id>]
  ├─ Press Play → watch the session replay with live score updates
  ├─ Press Step → advance one event at a time
  └─ Read the "Issues" panel at the bottom → see WHY the score is low
```

Focus on **sessions with Composite < 60** (red/orange tiles). For each:

1. **Read the highlights** — the scorer prints bullet points like:
   - `"Tool output was available but omitted from the answer"`
   - `"fetch_import_status exceeded 1.5s"`
   - `"Asserted confident numeric answer that contradicts tool output"`

2. **Find the turning point** in the trace replay timeline:
   - When did the tool call fail?
   - Did the agent notice the error?
   - Did it retry with a different approach, or just give up?
   - Did it incorporate the tool result into its final answer?

3. **Pattern-match across sessions**:
   - Are multiple low scores hitting the same tool (e.g., `fetch_import_status` always timing out)?
   - Are they all from the same model/provider?
   - Do they cluster around a specific time of day (network congestion)?

4. **Take action**:
   - **Tool failures** → Check tool implementation, increase timeout, add error handling
   - **Grounding issues** → Strengthen system prompt: "Always cite tool results. If tool output contradicts your prior knowledge, trust the tool."
   - **Inconsistent answers** → Add few-shot examples showing stable reasoning patterns
   - **Error Recovery = 0** → Add explicit retry logic or escalation path

### Automated Monitoring (Cron Job)

Schedule hourly checks so you don't have to manually run the pipeline:

```bash
hermes cron create \
  --name "Agent Reliability Monitor" \
  --schedule "every 1h" \
  --prompt "Parse new Hermes sessions and score them. Report total sessions, average composite, and list any sessions scoring < 40 with their top issues." \
  --skill agent-reliability
```

The cron will:
- Parse only new lines from `gateway.log` (idempotent)
- Score only new sessions (won't duplicate)
- Notify you if any session drops below threshold (40)

### Interpreting the Dimensions — What to Fix

| Dimension | What Low Score Means | Typical Fix |
|-----------|---------------------|-------------|
| **Consistency** (< 50) | Agent gives different answers to similar queries; response times wildly variable | Stabilize temperature (0.1–0.3); add few-shot examples; check for non-deterministic tool outputs |
| **Error Recovery** (0) | Errors/timeouts → no retry, no recovery, agent gives up | Add explicit retry logic in tool wrappers; increase timeout; add fallback tools |
| **Tool Accuracy** (< 50) | Wrong tool used, or tool succeeded but answer didn't use the result | Improve tool selection prompt; verify tool descriptions are clear; add validation: "Did you actually use the tool output?" |
| **Grounding** (< 30) | Agent made confident claims that contradict tool data (hallucination) | Strengthen prompt: "You MUST incorporate tool results. If tool says X, do not claim Y." Add grounding penalty in system message |

### SQL Queries for Debugging

Find sessions by issue pattern:
```sql
-- Sessions with tool output ignored (grounding issues)
SELECT session_id, composite, json_extract(details, '$.highlights')
FROM scores WHERE details LIKE '%ignored%tool%output%';

-- Sessions with no error recovery at all
SELECT session_id, error_recovery, composite
FROM scores WHERE error_recovery = 0 ORDER BY composite ASC;

-- Sessions that used a specific tool (replace tool_name)
SELECT s.session_id, s.composite, t.tool, t.status
FROM scores s
JOIN (
  SELECT session_id, json_each.value->>'name' as tool, json_each.value->>'status' as status
  FROM traces, json_each(trace->'$.tool_calls')
) t ON s.session_id = t.session_id
WHERE t.tool LIKE '%your_tool_name%';
```

### Known Pitfalls

- **Gateway log path**: By default `trace_parser.py` looks at `~/.hermes/logs/gateway.log`. If your log is elsewhere, pass `--log-path /path/to/log`.
- **Duplicate sessions**: The scorer deduplicates by `session_id`. If you re-run on the same log file, only new sessions are inserted.
- **Prototypes are static**: The HTML dashboards show a fixed snapshot at generation time. They are not auto-refreshing from `scores.db` (future enhancement).
- **Time zone**: Session timestamps are stored as ISO 8601 with UTC offset. Dashboard converts to local timezone automatically.
- **Network degradation**: If `httpx.ReadError` appears in gateway logs (see memory), some tool calls will fail → lower Tool Accuracy scores. Root cause is infrastructure, not the agent itself.

### Debugging Checklist (Apr 2026)

If the dashboard or trace-replay "just shows the demo" or fails silently:

1. **Paths are wrong** — `trace-replay.html` fetches `/data/sessions-store.json` and `/data/traces-index.json`. These are served from `prototypes/data/`, not project root `data/`. Run `scripts/run_pipeline.py` or manually copy:
   ```bash
   cp -r ~/.hermes/skills/agent-reliability/data/* ~/.hermes/skills/agent-reliability/prototypes/data/
   ```
   This includes `sessions-store.json`, `traces-index.json`, and `traces/` subdirectory.

2. **Trace files missing** — `traces-index.json` may point to files that aren't in `prototypes/data/traces/`. Verify:
   ```bash
   ls prototypes/data/traces/$(python3 -c "import json; print(json.load(open('prototypes/data/traces-index.json'))['<some-session-id>'])")
   ```
   If missing, recopy the `data/traces/` directory as above.

3. **`statusEl` JavaScript error** — If `trace-replay.html` shows the demo and the status bar is empty/blank, the IIFE threw `ReferenceError: statusEl is not defined` because the element was never added to the DOM. Fix: ensure the HTML contains `<div id="reload-status">` and the script declares `const statusEl = document.getElementById('reload-status')` BEFORE the IIFE runs.

4. **Click handler uses `this` incorrectly** — Dashboard cards with inline `onclick="window.open('trace-replay.html?session=' + this.getAttribute('data-session-id'))"` will fail because `this` is `window` in a string handler. Replace with: `onclick="window.open('trace-replay.html?session=${s.name}', '_blank')"` where `s.name` is the session ID embedded directly.

5. **Browser cache** — Old HTML/JS may be cached. Hard refresh (`Ctrl+Shift+R`) or append a cache-buster query param (`?_bypass=<timestamp>`) to verify fixes are being served.

6. **Histogram explains score gaps** — If fleet average (e.g., 63.4) seems inconsistent with top-12 scores (80+), add a histogram (see "Adding a Histogram" below) to reveal the true distribution. The average is pulled down by a long tail of low-scoring sessions.

### Adding a Histogram to the Dashboard

The fleet average can be misleading when top performers skew perception. A distribution histogram shows the real shape of the data:

- Compute distinct latest scores per session from `scores.db`
- Bin into 5-point ranges (60-64, 65-69, etc.)
- Render as horizontal bar chart with color-coded tiers
- Use `max(bin_counts)` to normalize bar widths to 100%
- Insert into `cockpit-dashboard.html` replacing the canvas sparkline

See commit `histogram-addition-20260422` for implementation details.

### Skill Loading Tip

Load this skill whenever the user:
- Says "why did the agent do X"
- Shows you a failed session transcript
- Asks to audit agent performance over time
- Wants to prove improvement before/after a prompt change

---

## Quick Investigation Guide

**When you see a dashboard with "Needs Work" flags**, start here:

1. Read `INVESTIGATE.md` in this skill directory — it's a step-by-step troubleshooting guide written for the user's terminal.
2. Run the health checks and SQL queries to find the actual failing sessions.
3. Use `trace-replay.html` to step through the session and read the "Issues" panel.
4. Correlate with gateway logs for network/timeout patterns.

The document includes:
- Health check commands (demo_scenario, trace count, DB count)
- SQL queries to find worst sessions by dimension
- Pattern mining (which tools fail most, time-of-day clustering)
- Cron job setup for automated alerts
- Known gotchas (trace format mismatch, dashboard showing demo data, JS errors)

Path: `~/.hermes/skills/agent-reliability/INVESTIGATE.md`

