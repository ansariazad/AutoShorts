#!/usr/bin/env python3
"""
AutoShorts Analytics Checker — Daily performance tracker.

Checks YouTube Analytics for uploaded videos and logs:
  - Views per video
  - Which topics perform best
  - Which formats work best
  - Recommends what to make more of

Usage:
  python3 scripts/check_analytics.py           # Check all recent uploads
  python3 scripts/check_analytics.py --top 5   # Show top 5 performers
  python3 scripts/check_analytics.py --suggest  # AI suggests next topics
"""

import json
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / 'scripts'))

from topic_tracker import TopicTracker


def get_youtube_stats(video_ids):
    """Fetch view counts from YouTube API for uploaded videos."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        token_path = PROJECT / 'config' / 'youtube_token.json'
        if not token_path.exists():
            print("⚠️  YouTube token not found — can't fetch analytics")
            return {}

        creds = Credentials.from_authorized_user_file(
            str(token_path),
            ['https://www.googleapis.com/auth/youtube.readonly']
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        youtube = build('youtube', 'v3', credentials=creds)

        stats = {}
        # Batch in groups of 50
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            ids_str = ','.join(batch)
            resp = youtube.videos().list(
                part='statistics',
                id=ids_str
            ).execute()

            for item in resp.get('items', []):
                vid_id = item['id']
                s = item.get('statistics', {})
                stats[vid_id] = {
                    'views': int(s.get('viewCount', 0)),
                    'likes': int(s.get('likeCount', 0)),
                    'comments': int(s.get('commentCount', 0)),
                }

        return stats
    except Exception as e:
        print(f"⚠️  YouTube API error: {e}")
        return {}


def update_performance(tracker_db_path, stats):
    """Update performance data in the tracker database."""
    conn = sqlite3.connect(tracker_db_path)
    c = conn.cursor()

    for vid_id, data in stats.items():
        # Find the upload
        c.execute("SELECT id FROM uploads WHERE youtube_id = ?", (vid_id,))
        row = c.fetchone()
        if row:
            upload_id = row[0]
            c.execute("""
                INSERT OR REPLACE INTO performance (upload_id, views, likes, checked_at)
                VALUES (?, ?, ?, ?)
            """, (upload_id, data['views'], data['likes'], datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_performance_report(tracker_db_path):
    """Generate performance report from database."""
    conn = sqlite3.connect(tracker_db_path)
    c = conn.cursor()

    # Get all uploads with performance data
    c.execute("""
        SELECT u.topic, u.title, u.script_format, u.visual_style, u.voice_id,
               u.upload_time, u.youtube_id, u.youtube_url,
               p.views, p.likes
        FROM uploads u
        LEFT JOIN performance p ON u.id = p.upload_id
        ORDER BY COALESCE(p.views, 0) DESC
    """)

    rows = c.fetchall()
    conn.close()

    report = []
    for row in rows:
        report.append({
            'topic': row[0],
            'title': row[1],
            'format': row[2],
            'visual': row[3],
            'voice': row[4],
            'upload_time': row[5],
            'youtube_id': row[6],
            'youtube_url': row[7],
            'views': row[8] or 0,
            'likes': row[9] or 0,
        })

    return report


def analyze_performance(report):
    """Analyze what works and what doesn't."""
    if not report:
        print("📊 No upload data yet. Upload some videos first!")
        return

    print(f"\n{'='*60}")
    print(f"📊 PERFORMANCE ANALYSIS — {len(report)} videos")
    print(f"{'='*60}")

    total_views = sum(r['views'] for r in report)
    avg_views = total_views / len(report) if report else 0

    print(f"\n  Total views: {total_views:,}")
    print(f"  Average views: {avg_views:,.0f}")

    # Top performers
    top = sorted(report, key=lambda x: x['views'], reverse=True)[:5]
    print(f"\n  🏆 TOP 5 PERFORMERS:")
    for i, r in enumerate(top, 1):
        print(f"    {i}. [{r['views']:,} views] {r['topic'][:40]}")
        print(f"       Format: {r['format']} | Voice: {r['voice']} | Visual: {r['visual']}")

    # Worst performers
    bottom = sorted(report, key=lambda x: x['views'])[:3]
    print(f"\n  ❌ BOTTOM 3 (avoid these patterns):")
    for r in bottom:
        print(f"    [{r['views']:,} views] {r['topic'][:40]} — format: {r['format']}")

    # Format analysis
    format_perf = {}
    for r in report:
        fmt = r['format'] or 'unknown'
        if fmt not in format_perf:
            format_perf[fmt] = {'views': 0, 'count': 0}
        format_perf[fmt]['views'] += r['views']
        format_perf[fmt]['count'] += 1

    print(f"\n  📝 FORMAT PERFORMANCE:")
    for fmt, data in sorted(format_perf.items(), key=lambda x: x[1]['views'], reverse=True):
        avg = data['views'] / data['count'] if data['count'] > 0 else 0
        print(f"    {fmt}: {data['count']} videos, avg {avg:,.0f} views")

    # Voice analysis
    voice_perf = {}
    for r in report:
        v = r['voice'] or 'unknown'
        if v not in voice_perf:
            voice_perf[v] = {'views': 0, 'count': 0}
        voice_perf[v]['views'] += r['views']
        voice_perf[v]['count'] += 1

    print(f"\n  🎤 VOICE PERFORMANCE:")
    for v, data in sorted(voice_perf.items(), key=lambda x: x[1]['views'], reverse=True):
        avg = data['views'] / data['count'] if data['count'] > 0 else 0
        print(f"    {v}: {data['count']} videos, avg {avg:,.0f} views")

    # Recommendations
    print(f"\n  💡 RECOMMENDATIONS:")
    if top and top[0]['views'] > avg_views * 2:
        print(f"    🔥 '{top[0]['topic'][:30]}...' is a HIT — make 3 more variations!")
    best_fmt = max(format_perf.items(), key=lambda x: x[1]['views'] / max(x[1]['count'], 1))[0] if format_perf else None
    if best_fmt:
        print(f"    📝 Best format: '{best_fmt}' — use this more often")
    best_voice = max(voice_perf.items(), key=lambda x: x[1]['views'] / max(x[1]['count'], 1))[0] if voice_perf else None
    if best_voice:
        print(f"    🎤 Best voice: '{best_voice}' — audiences prefer this one")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AutoShorts Analytics Checker')
    parser.add_argument('--top', type=int, default=10, help='Show top N performers')
    parser.add_argument('--suggest', action='store_true', help='AI-suggest next topics')
    parser.add_argument('--fetch', action='store_true', help='Fetch latest stats from YouTube')
    args = parser.parse_args()

    tracker = TopicTracker()
    stats = tracker.get_stats()

    if stats['total_uploads'] == 0:
        print("📊 No uploads recorded yet.")
        print("   Run: python3 scripts/daily_scheduler.py --dry-run")
        print("   to start uploading videos first.")
        return

    if args.fetch:
        # Get all video IDs
        import sqlite3
        conn = sqlite3.connect(tracker.db_path)
        c = conn.cursor()
        c.execute("SELECT youtube_id FROM uploads WHERE youtube_id IS NOT NULL AND youtube_id != ''")
        video_ids = [row[0] for row in c.fetchall()]
        conn.close()

        if video_ids:
            print(f"📡 Fetching stats for {len(video_ids)} videos...")
            yt_stats = get_youtube_stats(video_ids)
            if yt_stats:
                update_performance(tracker.db_path, yt_stats)
                print(f"  ✅ Updated {len(yt_stats)} videos")
        else:
            print("⚠️  No YouTube video IDs found in database")

    report = get_performance_report(tracker.db_path)
    analyze_performance(report)


if __name__ == '__main__':
    main()
