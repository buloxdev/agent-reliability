# Agent Reliability Scores

**The credit score for AI agents.**

We scored 253 real agent sessions. The average composite score was **63.4**. One in four sessions was actively hallucinating, ignoring tool output, or failing to recover from errors. The worst session scored **25.6**.

You would not hire an employee without a resume. You should not deploy an agent without a reliability score.

---

## Watch It (30 Seconds)

<video src="remotion-video/out/video.mp4" width="100%" autoplay loop muted playsinline></video>

> No voiceover, no narration — just the problem, the score, and the dashboard. The same format we love in [ChuckSRQ's Hermes Artifact Preview](https://x.com/ChuckSRQ).

---

## The Problem

AI agents are black boxes. They call tools, time out, hallucinate numbers, and give confident answers that contradict their own data. The only way to find out is to manually read every log — or wait for a user to complain.

**Without this tool:** You grep logs for 2 hours to understand why an agent failed.  
**With this tool:** You look at a scorecard for 30 seconds.

---

## What It Actually Does

A **zero-dependency, rules-based scoring engine** that reads a structured log of an agent session and outputs 4 dimension scores (0-100) plus a composite.

No AI model. No cloud API. No external dependencies. Just a Python script that looks at:
- What the user asked
- What tools the agent called
- Whether the tools worked
- What the agent said back
- How long it took
- Whether it recovered from errors

**Input:** A JSON file describing one agent session.  
**Output:** 4 dimension scores + composite + human-readable explanation.

---

## Real Results (From 253 Sessions)

| Scenario | Composite | What Happened |
|----------|-----------|---------------|
| Good Agent | **100.0** | Right tools, correct data, clean response |
| Mixed Agent | **91.7** | Mostly good, one partial failure recovered |
| Flaky Agent | **57.7** | Timeouts, retries, inconsistent answers |
| Hallucinating Agent | **25.6** | Ignored real data, made up confident answers |

Fleet average: **63.4** — which means most deployed agents are unreliable enough to need intervention.

---

## The 4 Scores (With Real Examples)

Think of these like the components of a credit score:

### 1. Consistency — "Is it stable or all over the place?"

Penalizes wild response-time swings, repeated errors, and missing responses.

**Example:** The Flaky Agent scores **29.0** because its response times jump from 2.3s to 3.4s and it changes its answer after a retry.

### 2. Error Recovery — "When it breaks, does it fix itself?"

If an error is followed by a successful response within a few events, that is a recovery. If not, it is a failure.

**Example:** The Hallucinating Agent scores **0.0** because it hallucinated and never corrected itself. The Mixed Agent scores **100.0** because it acknowledged a partial failure and worked around it.

### 3. Tool Accuracy — "Does it use the right tools correctly?"

Rewards successful tool calls whose results appear in the final answer. Penalizes failed calls, ignored output, and irrelevant tool usage.

**Example:** The Hallucinating Agent scores **45.0** because it called `fetch_payments_dashboard` successfully, then completely ignored the result and made up its own number.

### 4. Grounding — "Is it making things up?"

Compares how much the agent wrote vs. how much data the tools returned. If the agent spews confident specifics while the tools returned little or nothing, that is a hallucination.

**Example:** The Hallucinating Agent scores **7.0** because it claimed "refunds are definitely down by 80 percent" and "exactly 3 refunds" while the tool returned **14 refunds** — it never used the real data.

---

## Why This Is Different

| | Agent Reliability Scores | LangSmith / Langfuse / Arize |
|---|---|---|
| **Dependencies** | Zero — pure Python stdlib | Requires cloud account + SDK |
| **Privacy** | Runs fully offline | Sends traces to third party |
| **Cost** | Free forever | Usage-based pricing |
| **Explainability** | Rules-based, deterministic scores | ML heuristics, opaque weights |
| **Setup** | `git clone` + `python3` | Account creation, API keys, SDK |
| **Philosophy** | You own the logic | You rent the dashboard |

---

## Try It in 30 Seconds

```bash
git clone https://github.com/buloxdev/hermes-agent-reliability.git
cd agent-reliability-scores

# Generate 4 demo agent sessions and score them
python3 scripts/demo_scenario.py

# Open the dashboard
open prototypes/cockpit-dashboard.html
```

You will see 4 scored sessions with plain-English explanations for every dimension.

---

## Write Your Own Trace

You do not need Hermes running. Just write a JSON file:

```json
{
  "session_id": "my-agent-session",
  "messages": [
    {"role": "user", "content": "What's the server uptime?"},
    {"role": "assistant", "content": "The server has been up for 14 days."}
  ],
  "tool_calls": [
    {
      "tool": "fetch_uptime",
      "success": true,
      "used_in_final_answer": true,
      "matched_user_request": true
    }
  ],
  "errors": [],
  "response_times": [1.2]
}
```

Save it to `data/traces/my-session.json`, then run:

```bash
python3 scripts/scorer.py
```

The scorer reads every `.json` file in `data/traces/`, computes scores, and stores them in `data/scores.db`.

---

## Real Usage (Hermes Integration)

If you run Hermes, you can score your actual agent sessions automatically:

```bash
# 1. Parse gateway logs + session transcripts into traces
python3 scripts/trace_parser.py

# 2. Score every session
python3 scripts/scorer.py

# 3. Open the dashboards
open prototypes/cockpit-dashboard.html
open prototypes/trace-replay.html
```

### As a Cron Job

```bash
hermes cron create \
  --name "Agent Reliability Score" \
  --prompt "Run: python3 ~/.hermes/skills/agent-reliability/scripts/trace_parser.py && python3 ~/.hermes/skills/agent-reliability/scripts/scorer.py" \
  --schedule "0 0 * * *" \
  --deliver telegram
```

### Compare Models / Providers

1. Run the same workflow through Provider A → score it
2. Run the same workflow through Provider B → score it
3. Compare composite scores + dimension breakdowns
4. Winner is the one with higher reliability, not just lower cost

### Catch Regressions

1. Score your agent (baseline)
2. Change your system prompt, tools, or model
3. Score again
4. Did reliability go up or down?

---

## Screenshots

### Mission Control Dashboard
![Agent Reliability Mission Control Dashboard](prototypes/screenshots/cockpit-dashboard.png)

### Trace Replay
![Agent Reliability Trace Replay](prototypes/screenshots/trace-replay.png)

---

## Components

| File | Purpose |
|------|---------|
| `scripts/demo_scenario.py` | **Start here.** Generates 4 synthetic scenarios and scores them |
| `scripts/scorer.py` | Reads trace JSON files and computes scores |
| `scripts/trace_parser.py` | Parses real Hermes gateway logs into trace format |
| `scripts/dashboard.py` | Generates a zero-dependency HTML dashboard |
| `scripts/monitor.py` | Live monitor that scans recent sessions and alerts on threshold breaches |
| `scripts/image_generator.py` | Generates visual scorecard PNGs for status updates |
| `prototypes/cockpit-dashboard.html` | Interactive overview — gauges, radar charts, fleet grid |
| `prototypes/trace-replay.html` | Step through any session event-by-event |
| `data/scores.db` | SQLite database with all scored sessions |
| `data/traces/*.json` | Parsed trace files (one per session) |

---

## Visual Reports

Auto-generated visual scorecards for each pipeline run. These images are suitable for:
- **Status updates** in Slack/Telegram/Discord
- **Notion project pages** — attach PNGs directly
- **GitHub README badges** — display current fleet health
- **Hackathon demo video** — included as scorecard scenes

```bash
# Generate all fleet-level templates
python3 scripts/image_generator.py --all

# Or run the complete pipeline (parse → score → images)
python3 scripts/run_pipeline.py
```

---

## Why It Matters

- **Trust** — "This agent scores 85, I can trust it for this task"
- **Debugging** — "Scored 25 on grounding because it ignored tool output — now I know exactly what to fix"
- **Comparison** — "Agent A scores 92, Agent B scores 58 on the same task — easy choice"
- **Monitoring** — "Scores dropped from 80 to 60 this week — something broke"

---

## Requirements

- Python 3.10+
- **No external dependencies** (zero-dep by design)
- Hermes gateway logs or session transcripts (optional — synthetic traces work standalone)
