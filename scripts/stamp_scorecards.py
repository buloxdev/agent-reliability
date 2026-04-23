#!/usr/bin/env python3
"""Stamp live stats onto pre-generated visual templates using ffmpeg.

Given we have beautiful AI-generated template images, this script overlays
the current reliability statistics (avg score, counts, timestamps) as text,
producing fresh scorecards without re-generating the entire graphic.

Usage:
  python3 scripts/stamp_scorecards.py --output-dir prototypes/reports

Dependencies: ffmpeg (for drawtext filter)
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "scores.db"
TEMPLATE_DIR = PROJECT_ROOT / "prototypes" / "reports" / "templates"
OUTPUT_DIR = PROJECT_ROOT / "prototypes" / "reports"


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) total, AVG(composite) avg, MIN(composite) mn, MAX(composite) mx FROM scores")
    row = cur.fetchone()
    cur.execute("SELECT AVG(consistency) c, AVG(error_recovery) r, AVG(tool_accuracy) t, AVG(grounding) g FROM scores")
    dims = cur.fetchone()
    cur.execute("""
        SELECT CASE WHEN composite>=80 THEN 'excellent' WHEN composite>=60 THEN 'good'
                    WHEN composite>=40 THEN 'fair' ELSE 'poor' END tier, COUNT(*) cnt
        FROM scores GROUP BY tier
    """)
    tiers = {r['tier']: r['cnt'] for r in cur.fetchall()}
    cur.execute("SELECT COUNT(*) cnt FROM scores WHERE composite < 40")
    poor_count = cur.fetchone()['cnt']
    conn.close()

    return {
        "total": row['total'],
        "avg": round(row['avg'], 1) if row['avg'] else 0.0,
        "min": round(row['mn'], 1),
        "max": round(row['mx'], 1),
        "tiers": tiers,
        "poor_count": poor_count,
        "dimensions": {
            "consistency": round(dims['c'], 1) if dims['c'] else 0.0,
            "error_recovery": round(dims['r'], 1) if dims['r'] else 0.0,
            "tool_accuracy": round(dims['t'], 1) if dims['t'] else 0.0,
            "grounding": round(dims['g'], 1) if dims['g'] else 0.0,
        },
    }


def stamp_image(template_name: str, stats: dict, output_name: str) -> Path | None:
    """Overlay dynamic stats text onto a template image using ffmpeg."""
    template_path = TEMPLATE_DIR / template_name
    output_path = OUTPUT_DIR / output_name

    if not template_path.exists():
        print(f"  ⚠️  Template missing: {template_path}")
        return None

    now = datetime.now().strftime("%b %d, %Y — %H:%M")

    # Build drawtext filters
    # We overlay multiple text elements at different positions
    filters = []

    # Common font (use AbandonedWeight for that tech look, fallback to sans-serif)
    font = "fontfile=/Library/Fonts/Arial.ttf:fontsize=42:fontcolor=white"
    # But ffmpeg drawtext uses simpler syntax: "text='...':x=10:y=10:fontsize=42:fontcolor=white"

    # Big composite number overlay — bottom right of the gauge area
    filters.append(
        f"drawtext=text='{stats['avg']}':x=655:y=340:fontsize=96:fontcolor=#e5e7eb:fontweight=bold"
    )

    # Date at top right
    filters.append(
        f"drawtext=text='{now}':x=1000:y=40:fontsize=24:fontcolor=#6b7280"
    )

    # Tiers on the right stat panel (approximately where they appear)
    y_start = 600
    tier_order = ['excellent', 'good', 'fair', 'poor']
    tier_labels = {'excellent': 'Excellent (80+)', 'good': 'Good (60-79)', 'fair': 'Fair (40-59)', 'poor': 'Poor (<40)'}
    colors = {'excellent': '#10b981', 'good': '#6366f1', 'fair': '#f59e0b', 'poor': '#ef4444'}
    for i, tier in enumerate(tier_order):
        count = stats['tiers'].get(tier, 0)
        label = tier_labels[tier]
        filters.append(
            f"drawtext=text='{label}: {count}':x=780:y={y_start + i*55}:fontsize=22:fontcolor={colors[tier]}"
        )

    # Total sessions at top-left of stat panel
    filters.append(
        f"drawtext=text='Total Sessions: {stats['total']}':x=780:y={y_start-80}:fontsize=28:fontcolor=#e5e7eb:fontweight=bold"
    )

    # Dimensions bars (just the numbers on the bars)
    dim_y_start = 480
    dims = stats['dimensions']
    dim_order = ['consistency', 'error_recovery', 'tool_accuracy', 'grounding']
    for i, dim in enumerate(dim_order):
        val = dims[dim]
        filters.append(
            f"drawtext=text='{dim.capitalize()}':x=100:y={dim_y_start + i*60}:fontsize=24:fontcolor=#e5e7eb"
        )
        filters.append(
            f"drawtext=text='{val:.1f}':x=500:y={dim_y_start + i*60}:fontsize=24:fontcolor=#6366f1:fontweight=bold"
        )

    filter_str = ",".join([f"[0]{f}[out]" for f in filters]).replace("[0]drawtext", "drawtext")

    cmd = [
        "ffmpeg", "-y", "-i", str(template_path),
        "-vf", filter_str,
        "-frames:v", "1",
        str(output_path)
    ]

    # Debug: show the filter chain (first 3)
    print(f"  Stamping {template_name} → {output_name}")
    print(f"    filter chain: {filter_str[:200]}...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and output_path.exists():
        print(f"  ✓ Saved: {output_path} ({output_path.stat().st_size:,} bytes)")
        return output_path
    else:
        print(f"  ⚠️  ffmpeg error: {result.stderr[:300]}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Stamp live stats onto scorecard templates")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--template-dir", type=Path, default=TEMPLATE_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    stats = get_stats()
    ts = datetime.now().strftime("%Y%m%d-%H%M")

    print("="*60)
    print("STAMPING SCORECARDS WITH LIVE STATS")
    print("="*60)
    print(f"Avg: {stats['avg']}  |  Total: {stats['total']}  |  Poor: {stats['poor_count']}")

    generated = []

    # 1. Latest fleet scorecard
    out1 = stamp_image(
        "fleet-scorecard-latest.png",
        stats,
        f"scorecard-latest-{ts}.png"
    )
    if out1: generated.append(out1)

    # 2. Alert card (only if poor sessions exist)
    if stats['poor_count'] > 0:
        out2 = stamp_image(
            "reliability-alert.png",
            stats,
            f"alert-{ts}.png"
        )
        if out2: generated.append(out2)

    # 3. Cover (doesn't need dynamic text really, just timestamp)
    out3 = stamp_image(
        "scorecard-cover.png",
        stats,
        f"cover-{ts}.png"
    )
    if out3: generated.append(out3)

    # Update index JSON
    index = []
    for img_path in generated:
        st = img_path.stat()
        index.append({
            "filename": img_path.name,
            "type": img_path.stem.split('-')[0],
            "timestamp": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "size": st.st_size,
        })
    index.sort(key=lambda x: x["timestamp"], reverse=True)
    (args.output_dir / "index.json").write_text(json.dumps(index, indent=2))
    print(f"\n✓ Updated gallery index: {len(index)} images")

    print(f"\n📁 View: file://{args.output_dir}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
