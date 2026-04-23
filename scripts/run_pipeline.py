#!/usr/bin/env python3
"""Complete reliability pipeline: parse logs → score sessions → generate visual reports.

Usage:
  python3 scripts/run_pipeline.py                    # Run full pipeline
  python3 scripts/run_pipeline.py --notify telegram  # Also send to Telegram
  python3 scripts/run_pipeline.py --notify notion    # Attach to Notion page

This replaces needing to run trace_parser + scorer + image_generator separately.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "scores.db"


def run_step(name: str, cmd: list[str]) -> tuple[bool, str]:
    """Run a pipeline step, return (success, output)."""
    print(f"\n{'='*60}")
    print(f"▶  {name}")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        print(f"  ✓ Success")
        return True, result.stdout + result.stderr
    else:
        print(f"  ✗ Failed (exit {result.returncode})")
        return False, result.stderr


def get_summary() -> str:
    """Generate a concise human-readable summary."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total, AVG(composite) as avg FROM scores")
    row = cursor.fetchone()
    total, avg = row["total"], row["avg"]

    cursor.execute("""
        SELECT 
            CASE WHEN composite >= 80 THEN 'excellent'
                 WHEN composite >= 60 THEN 'good'
                 WHEN composite >= 40 THEN 'fair'
                 ELSE 'poor' END as tier,
            COUNT(*) as count
        FROM scores GROUP BY tier
    """)
    tiers = {r["tier"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("""
        SELECT session_id, composite
        FROM scores WHERE composite < 40
        ORDER BY composite ASC LIMIT 3
    """)
    poor = cursor.fetchall()
    conn.close()

    summary = f"📊 Reliability Report — Total: {total} sessions | Avg: {avg:.1f}\n"
    summary += f"   🟢 Excellent: {tiers.get('excellent',0)}  🟡 Good: {tiers.get('good',0)}  🟠 Fair: {tiers.get('fair',0)}  🔴 Poor: {tiers.get('poor',0)}\n"

    if poor:
        summary += f"\n⚠️  Poor sessions detected:\n"
        for p in poor:
            summary += f"   {p['session_id']}: {p['composite']:.1f}\n"

    return summary


def notify_telegram(message: str, image_path: Path | None = None):
    """Send report to Telegram (requires hermes telegram configured)."""
    try:
        if image_path and image_path.exists():
            # Send image with caption
            subprocess.run([
                "hermes", "send", "telegram",
                "--photo", str(image_path),
                "--caption", message[:1000]
            ], check=True)
            print("  ✓ Sent scorecard image to Telegram")
        else:
            subprocess.run(["hermes", "send", "telegram", message], check=True)
            print("  ✓ Sent text summary to Telegram")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Telegram send failed: {e}")


def notify_notion(image_path: Path):
    """Attach image to Notion project page (placeholder — implement per your DB)."""
    # TODO: Use notion API to attach image to the project page
    print(f"  ℹ️  Notion attachment not yet implemented — image at {image_path}")


def main():
    parser = argparse.ArgumentParser(description="Run full reliability pipeline")
    parser.add_argument("--notify", choices=["telegram", "notion"], help="Send results after completion")
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    args = parser.parse_args()

    print("="*60)
    print("  AGENT RELIABILITY PIPELINE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Step 1: Parse logs
    success, _ = run_step("Parse Gateway Logs", ["python3", "scripts/trace_parser.py"])
    if not success:
        print("\n❌ Pipeline failed at trace parsing")
        sys.exit(1)

    # Step 2: Score sessions
    success, scorer_out = run_step("Score Sessions", ["python3", "scripts/scorer.py"])
    if not success:
        print("\n❌ Pipeline failed at scoring")
        sys.exit(1)

    print(scorer_out[:1000])

    # Step 3: Generate images
    if not args.skip_images:
        success, _ = run_step(
            "Generate Visual Reports",
            ["python3", "scripts/image_generator.py", "--all"]
        )
        if not success:
            print("⚠️  Image generation failed (non-fatal)")

    # Step 4: Summary
    summary = get_summary()
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(summary)

    # Step 5: Notify
    if args.notify:
        latest_img = max(
            (PROJECT_ROOT / "prototypes" / "reports").glob("fleet-scorecard-*.png"),
            key=lambda p: p.stat().st_mtime,
            default=None
        )
        if args.notify == "telegram":
            notify_telegram(summary, latest_img)
        elif args.notify == "notion":
            notify_notion(latest_img)

    print("\nNext: open http://localhost:8899/cockpit-dashboard.html to explore")


if __name__ == "__main__":
    main()
