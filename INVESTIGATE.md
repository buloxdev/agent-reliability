# Investigating "Needs Work" Reliability Scores

These are the Agent Reliability Scores from the hackathon dashboard. "Needs Work" means that dimension dropped below threshold. Here's your investigation workflow.

---

## Quick Health Check First

```bash
# 1. Is the scoring engine working?
python3 ~/.hermes/skills/agent-reliability/scripts/demo_scenario.py
# Expected: 4 scenarios with scores (Good: 100, Mixed: 91.7, Flaky: 57.7, Hallucinating: 25.6)
# If this fails, the core logic is broken — stop here.

# 2. Are real traces being parsed?
ls ~/.hermes/skills/agent-reliability/data/traces/*.json | wc -l
# Should be > 0. If zero, trace_parser didn't find logs.

# 3. Is the database populated?
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT COUNT(*) as sessions, AVG(composite) as avg_score FROM scores"
# Count should match trace file count. Avg should be ~40-80.
```

If any check fails, run the full pipeline:

```bash
cd ~/.hermes/skills/agent-reliability
python3 scripts/run_pipeline.py
```

---

## Step-by-Step Investigation

### Step 1: Find the actual failing sessions

The dashboard shows dimension averages. You need to find which specific sessions dragged the average down.

```bash
# Sessions with the worst Consistency scores
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT session_id, consistency, composite, details FROM scores \
   ORDER BY consistency ASC LIMIT 10"

# Sessions with Error Recovery = 0 (completely failed to recover)
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT session_id, consistency, error_recovery, composite \
   FROM scores WHERE error_recovery = 0 ORDER BY composite ASC"
```

The `details` column contains plain-English highlights explaining WHY the score was low. Read those first — they're the fastest clue.

### Step 2: Drill into a specific session

Take a session_id from Step 1 (e.g., `20260420_143022_a1b2c3`) and open the trace replay:

```bash
# Start the local server if not running
lsof -ti:8899 || (cd ~/.hermes/skills/agent-reliability/prototypes && python3 -m http.server 8899)

# Open in browser
open http://localhost:8899/trace-replay.html?session=20260420_143022_a1b2c3
```

**In the trace replay UI:**
- Press **Play** to watch the full session auto-advance
- Press **Step** to advance one event at a time
- Read the **"Issues"** panel at the bottom — it shows bullet points like:
  - "Tool output was available but omitted from the answer"
  - "fetch_import_status exceeded 1.5s timeout"
  - "Asserted confident numeric answer that contradicts tool output"

**What to look for:**
- When did the first failure occur?
- Did the agent notice the error?
- Did it retry (with same or different approach) or just give up?
- Did the final answer incorporate the tool results?

### Step 3: Correlate with gateway logs

If the trace replay shows a tool call failing, check the raw gateway logs for that session:

```bash
# Search the gateway log for that session ID
grep -A 5 -B 5 "20260420_143022_a1b2c3" ~/.hermes/logs/gateway.log | less

# Or search for specific error patterns across all sessions
grep -i "timeout\|readerror\|exception" ~/.hermes/logs/gateway.log | grep -c .
```

The memory notes a **network degradation spike** since Apr 18 (httpx.ReadError counts jumped from 2 → 22). If you see those errors in the logs, the issue is infrastructure, not the agent itself.

---

## What "Needs Work" Means by Dimension

### Consistency = 77 (min 20)
**Problem:** Agent gives different answers to similar queries; response times wildly variable.

**Investigate:**
- In `scores.db`, find sessions where `consistency < 60`
- Check if the same query was asked multiple times with different answers
- Look at the `details` JSON for "response_time_variance" or "repeated_errors"

**Common causes:**
- Non-deterministic tool outputs (e.g., fetch_import_status returns different data each call)
- Temperature too high (> 0.5) in the LLM settings
- System prompt not giving stable reasoning patterns

**Fixes:**
- Lower temperature to 0.1–0.3 in your model config
- Add few-shot examples showing consistent reasoning
- Add tool result caching if outputs are non-deterministic

### Error Recovery = 67.8 (min 0)
**Problem:** At least one session scored 0 — errors/timeouts happened and the agent never recovered.

**Investigate:**
```bash
# Find the sessions with error_recovery = 0
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT session_id, details FROM scores WHERE error_recovery = 0"
```
Read the `details->highlights` to see what error occurred and whether the agent tried to recover.

**Common causes:**
- Tool wrapper has no retry logic (one timeout = game over)
- Timeout too short for the operation (network slowness)
- Agent not instructed to retry on failure

**Fixes:**
- Increase tool timeouts (check tool config files)
- Add automatic retry (3 attempts with exponential backoff)
- Add explicit instruction in system prompt: "If a tool fails, retry up to 3 times with a different approach"

---

## Pattern Mining Across Sessions

Once you've inspected 3–5 individual sessions, look for patterns:

```bash
# Which tools are used most in low-scoring sessions?
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT json_each.value->>'name' as tool, COUNT(*) as count, AVG(composite) as avg_score \
   FROM scores, json_each(trace->'$.tool_calls') \
   WHERE composite < 60 \
   GROUP BY tool ORDER BY count DESC"

# Do low scores cluster by time of day? (check session_id timestamps)
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT substr(session_id, 1, 8) as date, COUNT(*) as low_sessions \
   FROM scores WHERE composite < 60 \
   GROUP BY date ORDER BY date DESC"

# Which model/provider scored worst?
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT model, provider, AVG(composite) as avg, COUNT(*) as sessions \
   FROM scores GROUP BY model, provider ORDER BY avg ASC"
```

**If a specific tool appears in most low-score sessions:**
- Check that tool's implementation — maybe it's broken or timing out
- Increase its timeout in the tool config

**If scores cluster at specific times:**
- Correlate with network degradation (memory: httpx.ReadError spikes Apr 18–20)
- Consider scheduling heavy tools during off-hours

**If a specific model scores worse:**
- Switch to a more reliable model for production tasks
- Adjust that model's system prompt specifically

---

## Set Up Automated Alerts (Cron)

Don't manually check the dashboard. Get notified when scores drop:

```bash
hermes cron create \
  --name "Agent Reliability Monitor" \
  --schedule "every 1h" \
  --prompt "Parse new Hermes sessions and score them. Report: total sessions, average composite, and list any sessions scoring < 40 with their top 3 issues from the highlights." \
  --skill agent-reliability
```

This runs hourly, parses only new logs, and notifies you if any session is critically bad.

---

## Known Gotchas

**Symptom:** Scores look wrong (e.g., tool_accuracy = 0 even though tools were called)
**Cause:** Trace format version mismatch. `trace_parser.py` output format changed; `scorer.py` expects old format.
**Check:**
```bash
python3 -c "import json; d=json.load(open('~/.hermes/skills/agent-reliability/data/traces/*.json')); print('turns' in d and 'sessions' not in d)"
```
Expected: False (new format). If so, scorer needs patching to handle `sessions[].tool_calls` instead of `turns[].tools`. See skill doc "Trace Format Version Mismatch" section.

**Symptom:** Dashboard shows demo data, not your real sessions
**Cause:** Prototypes load static JSON from `prototypes/data/`, not from `data/`.
**Fix:**
```bash
cd ~/.hermes/skills/agent-reliability
python3 scripts/run_pipeline.py  # this copies traces into prototypes/data/ automatically
```
Or manually:
```bash
cp -r data/traces prototypes/data/
cp data/traces-index.json prototypes/data/
cp data/sessions-store.json prototypes/data/
```

**Symptom:** Trace replay shows blank "Issues" panel or JS errors
**Cause:** Browser cache or missing DOM element.
**Fix:** Hard refresh (Ctrl+Shift+R). If persists, check `trace-replay.html` contains `<div id="reload-status">` and script defines `const statusEl` before the IIFE.

---

## Your Action Plan for This Dashboard

Given your current scores:
- **Consistency 77** (min 20): At least one session was wildly inconsistent. Find it via `ORDER BY consistency ASC LIMIT 1`, replay it, and check if a tool returned different values on similar calls or if the agent's reasoning path diverged.
- **Error Recovery 67.8** (min 0): Some session hit 0 — complete failure to recover. That's your highest priority. Identify that session and determine: was it a network timeout, tool exception, or something else? Add retry logic immediately.

**First command to run:**
```bash
sqlite3 ~/.hermes/skills/agent-reliability/data/scores.db \
  "SELECT session_id, error_recovery, details FROM scores WHERE error_recovery = 0 LIMIT 3"
```

That gives you the exact session IDs to investigate.
