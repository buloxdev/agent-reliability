#!/usr/bin/env python3
"""Generate visual scorecard images for agent reliability reports.

Usage:
  python3 scripts/image_generator.py                    # Generate all variants
  python3 scripts/image_generator.py --template latest  # Just the latest scorecard
  python3 scripts/image_generator.py --template alert   # Alert version if poor sessions
  python3 scripts/image_generator.py --template cover   # Minimalist cover
  python3 scripts/image_generator.py --session <id>     # Scorecard for specific session

Outputs to: prototypes/reports/
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "scores.db"
OUTPUT_DIR = PROJECT_ROOT / "prototypes" / "reports"
HERMES_TOOL = "hermes"  # assume hermes CLI available in PATH


def get_stats() -> dict:
    """Fetch current reliability statistics from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM scores")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT AVG(composite), MIN(composite), MAX(composite) FROM scores")
    avg, mn, mx = cursor.fetchone()
    avg = round(avg, 1) if avg else 0.0

    cursor.execute("""
        SELECT 
            CASE 
                WHEN composite >= 80 THEN 'excellent'
                WHEN composite >= 60 THEN 'good'
                WHEN composite >= 40 THEN 'fair'
                ELSE 'poor'
            END as tier,
            COUNT(*) as count
        FROM scores GROUP BY tier
    """)
    tiers = {row["tier"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT AVG(consistency) as c, AVG(error_recovery) as r, AVG(tool_accuracy) as t, AVG(grounding) as g FROM scores")
    dims = cursor.fetchone()

    cursor.execute("SELECT MAX(timestamp) as latest FROM scores")
    latest_row = cursor.fetchone()
    latest = latest_row["latest"][:16] if latest_row and latest_row["latest"] else datetime.now().isoformat()[:16]

    conn.close()

    return {
        "total": total,
        "avg": avg,
        "min": round(mn, 1) if mn else 0.0,
        "max": round(mx, 1) if mx else 0.0,
        "tiers": tiers,
        "dimensions": {
            "consistency": round(dims["c"], 1) if dims["c"] else 0.0,
            "error_recovery": round(dims["r"], 1) if dims["r"] else 0.0,
            "tool_accuracy": round(dims["t"], 1) if dims["t"] else 0.0,
            "grounding": round(dims["g"], 1) if dims["g"] else 0.0,
        },
        "latest": latest,
    }


def get_session(session_id: str) -> dict | None:
    """Fetch a specific session's data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scores WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def build_prompt(template: str, stats: dict, session: dict | None = None) -> str:
    date_str = datetime.now().strftime("%b %d, %Y")
    if session:
        date_str = session.get("timestamp", date_str)[:10]

    if template == "latest":
        d = stats["dimensions"]
        return (f"Dark dashboard scorecard: 'Agent Reliability Scorecard — {date_str}'. "
                f"Main circular gauge showing composite {stats['avg']} in glowing blue, needle at {stats['avg']}/100. "
                f"Four horizontal bars: Consistency {d['consistency']}, Error Recovery {d['error_recovery']}, "
                f"Tool Accuracy {d['tool_accuracy']}, Grounding {d['grounding']}. "
                f"Right stats: Total {stats['total']}, Excellent {stats['tiers'].get('excellent',0)}, "
                f"Good {stats['tiers'].get('good',0)}, Fair {stats['tiers'].get('fair',0)}, Poor {stats['tiers'].get('poor',0)}. "
                f"Clean professional monitoring dashboard, dark theme, cyan accents.")

    elif template == "alert":
        has_poor = stats['tiers'].get('poor', 0) > 0
        return (f"Critical monitoring alert — red theme. Large 'ALERT — {stats['tiers'].get('poor',0)} Poor Sessions'. "
                f"Left: downward trending red line chart. Right: {min(3, len(stats.get('poor_sessions',[])))} warning cards with red scores. "
                f"Bottom: 'Review prompts, tools, models'. Urgent but professional.")

    elif template == "cover":
        return (f"Minimalist cover. Dark background. Title 'AGENT RELIABILITY SCORES' thin white. "
                f"Huge glowing number '{stats['avg']}' floating center. Small quadrant icons C/R/T/G. "
                f"Negative space, elegant premium.")

    elif template == "session" and session:
        details = json.loads(session.get("details", "{}") or "{}")
        highlights = details.get("highlights", [])[:2]
        return (f"Individual session SCORECARD — FAILED. Dark red alert theme. Top banner 'SESSION FAILED'. "
                f"Session ID: {session['session_id']} monospace. Composite: huge red {session['composite']:.1f}/100. "
                f"4 bars: Consistency {session['consistency']:.0f}%, Recovery {session['error_recovery']:.0f}%, "
                f"Tool {session['tool_accuracy']:.0f}%, Grounding {session['grounding']:.0f}%. "
                f"Root causes bullet list: {'; '.join(highlights)}. Bottom: 'Review prompt/tools/model'. "
                f"Security monitor aesthetic, serious.")

    else:
        raise ValueError(f"Unknown/missing data for template: {template}")


def call_image_tool(prompt: str, output_name: str, aspect: str = "landscape") -> Path:
    """Call the hermes image generation tool and save result."""
    output_path = OUTPUT_DIR / f"{output_name}.png"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Call hermes image generate tool
    # We invoke via hermes CLI since we're inside a Python script
    cmd = [
        HERMES_TOOL, "image", "generate",
        "--aspect-ratio", aspect,
        "--prompt", prompt,
        "--output", str(output_path)
    ]

    print(f"  Generating {output_name}.png ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  ⚠️  Image generation failed: {result.stderr[:200]}")
        # Create a placeholder text file so we know we tried
        placeholder = output_path.with_suffix(".txt")
        placeholder.write_text(f"Prompt: {prompt}\nError: {result.stderr[:200]}")
        return placeholder

    print(f"  ✓ Saved: {output_path}")
    return output_path


def update_index(images: list[Path]):
    """Update the gallery index.json with new image list."""
    index_path = OUTPUT_DIR / "index.json"
    entries = []
    for img in images:
        if img.exists() and img.suffix == ".png":
            stat = img.stat()
            entries.append({
                "filename": img.name,
                "type": img.stem.split('-')[0],
                "timestamp": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size": stat.st_size,
            })
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    index_path.write_text(json.dumps(entries, indent=2))
    print(f"  ✓ Updated gallery index ({len(entries)} images)")


def main():
    parser = argparse.ArgumentParser(description="Generate reliability scorecard images")
    parser.add_argument("--template", choices=["latest", "alert", "cover", "session"], default="latest")
    parser.add_argument("--all", action="store_true", help="Generate all template variants")
    parser.add_argument("--session", type=str, help="Session ID for per-session scorecard")
    parser.add_argument("--aspect", choices=["landscape", "portrait", "square"], default="landscape")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    stats = get_stats()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    date_tag = datetime.now().strftime("%Y%m%d-%H%M")
    generated = []

    templates = ["latest", "alert", "cover"] if args.all else [args.template]

    for tmpl in templates:
        if tmpl == "session" and args.session:
            session = get_session(args.session)
            if not session:
                print(f"❌ Session not found: {args.session}")
                sys.exit(1)
            prompt = build_prompt("session", stats, session)
            out_name = f"session-{args.session}-{date_tag}"
            aspect = "portrait"
        else:
            session_data = None
            prompt = build_prompt(tmpl, stats)
            out_name = f"fleet-{tmpl}-{date_tag}" if tmpl != "latest" else f"scorecard-{tmpl}-{date_tag}"
            aspect = args.aspect

        img_path = call_image_tool(prompt, out_name, aspect)
        generated.append(img_path)

    update_index(generated)

    print(f"\n✓ Generated {len(generated)} image(s) to {OUTPUT_DIR}")
    print("\nTo send to Telegram:")
    print(f"  hermes send telegram --photo {generated[0]} --caption 'Reliability report — avg {stats['avg']}'")


if __name__ == "__main__":
    main()
