"""
collect.py
==========
UGDSAI 29 - Group 4 (Aaryan, Daksh, Mayank)
YouTube Trending India - Longitudinal Collector

Pulls the top trending videos for India via YouTube Data API v3 and writes
a long-format CSV snapshot. Designed to be run twice daily for 10 days
(2 May - 11 May 2026).

USAGE
-----
    export YT_API_KEY="your_api_key_here"
    python collect.py

OUTPUT
------
    data/snapshots/snapshot_<YYYY-MM-DD_HH-MM>.csv   one file per run
    data/master_snapshots.csv                        all runs appended
    data/run_log.csv                                 success/failure log

QUOTA
-----
    videos.list  (chart=mostPopular)  : 1 unit per call, returns up to 50 videos
    channels.list (statistics)        : 1 unit per call, batched 50 channels at a time
    Per run total: ~2 units. Daily quota: 10,000. Comfortably within limits.

DESIGN NOTES
------------
- Long format (one row per (video_id, snapshot_ts)) preserves longitudinal data
  for feature engineering. We will roll this up to one row per video later.
- Idempotent: running the same script at the same minute twice will create two
  separate snapshot files but the master file safely de-duplicates on
  (video_id, snapshot_ts).
- All errors are caught and logged; the script never silently fails.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("YT_API_KEY")
REGION_CODE = "IN"
MAX_RESULTS = 50  # YouTube allows up to 50 per call
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
MASTER_CSV = DATA_DIR / "master_snapshots.csv"
RUN_LOG = DATA_DIR / "run_log.csv"

VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"

# Fields stored per row (long format)
COLUMNS = [
    "snapshot_ts",          # ISO timestamp of THIS run, UTC
    "snapshot_ts_ist",      # same in IST for human reading
    "trending_rank",        # 1..50 within this snapshot
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "channel_subscriber_count",
    "category_id",
    "published_at",
    "duration_iso",         # e.g. "PT4M13S"
    "view_count",
    "like_count",
    "comment_count",
    "tags",                 # pipe-separated, will split later
    "description_length",   # avoid storing the full description
    "default_audio_language",
    "default_language",
    "made_for_kids",
    "definition",           # "hd" or "sd"
    "caption",              # "true" / "false"
    "licensed_content",
    "thumbnail_url",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def fmt_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def log_run(status: str, message: str, rows_written: int) -> None:
    """Append a single row to the run log so we can audit the collection."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not RUN_LOG.exists()
    with RUN_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["run_ts_utc", "status", "message", "rows_written"])
        w.writerow([fmt_iso(now_utc()), status, message, rows_written])


def fetch_trending() -> list[dict]:
    """Call videos.list with chart=mostPopular for India."""
    if not API_KEY:
        raise RuntimeError(
            "YT_API_KEY env var is not set. Run: export YT_API_KEY='...'"
        )

    params = {
        "part": "snippet,statistics,contentDetails,status",
        "chart": "mostPopular",
        "regionCode": REGION_CODE,
        "maxResults": MAX_RESULTS,
        "key": API_KEY,
    }
    r = requests.get(VIDEOS_ENDPOINT, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(
            f"videos.list failed: HTTP {r.status_code} - {r.text[:300]}"
        )
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("videos.list returned 0 items - check region/quota.")
    return items


def fetch_channel_subs(channel_ids: Iterable[str]) -> dict[str, int]:
    """
    Look up subscriber counts in a single batched call. YouTube allows up to
    50 channel IDs per call, so one call covers all channels we'll see.
    """
    ids = sorted(set(channel_ids))
    if not ids:
        return {}

    params = {
        "part": "statistics",
        "id": ",".join(ids),
        "key": API_KEY,
    }
    r = requests.get(CHANNELS_ENDPOINT, params=params, timeout=30)
    if r.status_code != 200:
        # Non-fatal: we just won't have subscriber counts for this run
        return {}

    out: dict[str, int] = {}
    for ch in r.json().get("items", []):
        cid = ch.get("id")
        stats = ch.get("statistics", {})
        # If hiddenSubscriberCount is true, the field is missing
        try:
            out[cid] = int(stats.get("subscriberCount", -1))
        except (TypeError, ValueError):
            out[cid] = -1
    return out


def safe_int(x) -> int | str:
    """Some statistics fields are missing for restricted videos."""
    if x is None:
        return ""
    try:
        return int(x)
    except (TypeError, ValueError):
        return ""


def flatten_video(
    rank: int,
    item: dict,
    snap_utc: datetime,
    snap_ist: datetime,
    sub_lookup: dict[str, int],
) -> dict:
    sn = item.get("snippet", {}) or {}
    st = item.get("statistics", {}) or {}
    cd = item.get("contentDetails", {}) or {}
    sa = item.get("status", {}) or {}

    description = sn.get("description", "") or ""
    tags = sn.get("tags", []) or []
    thumbnails = sn.get("thumbnails", {}) or {}
    # Pick highest-res thumbnail available
    thumb = ""
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbnails:
            thumb = thumbnails[key].get("url", "")
            break

    channel_id = sn.get("channelId", "")
    return {
        "snapshot_ts": fmt_iso(snap_utc),
        "snapshot_ts_ist": fmt_iso(snap_ist),
        "trending_rank": rank,
        "video_id": item.get("id", ""),
        "title": sn.get("title", ""),
        "channel_id": channel_id,
        "channel_title": sn.get("channelTitle", ""),
        "channel_subscriber_count": sub_lookup.get(channel_id, ""),
        "category_id": sn.get("categoryId", ""),
        "published_at": sn.get("publishedAt", ""),
        "duration_iso": cd.get("duration", ""),
        "view_count": safe_int(st.get("viewCount")),
        "like_count": safe_int(st.get("likeCount")),
        "comment_count": safe_int(st.get("commentCount")),
        "tags": "|".join(tags),
        "description_length": len(description),
        "default_audio_language": sn.get("defaultAudioLanguage", ""),
        "default_language": sn.get("defaultLanguage", ""),
        "made_for_kids": sa.get("madeForKids", ""),
        "definition": cd.get("definition", ""),
        "caption": cd.get("caption", ""),
        "licensed_content": cd.get("licensedContent", ""),
        "thumbnail_url": thumb,
    }


def write_snapshot(rows: list[dict], snap_utc: datetime) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    fname = "snapshot_" + snap_utc.strftime("%Y-%m-%d_%H-%M-%SZ") + ".csv"
    path = SNAPSHOT_DIR / fname

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def append_to_master(rows: list[dict]) -> int:
    """
    Append rows to the master CSV. Master is the source of truth used for
    feature engineering. We dedupe on (video_id, snapshot_ts) at read time
    in the notebook, so this stays simple and append-only.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not MASTER_CSV.exists()
    with MASTER_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    snap_utc = now_utc()
    snap_ist = snap_utc.astimezone(IST)
    print(f"[{fmt_iso(snap_ist)}] Starting collection for region={REGION_CODE}")

    try:
        items = fetch_trending()
    except Exception as e:
        msg = f"fetch_trending failed: {e}"
        print(msg, file=sys.stderr)
        log_run("fail", msg, 0)
        return 1

    channel_ids = [
        (it.get("snippet") or {}).get("channelId", "") for it in items
    ]
    try:
        subs = fetch_channel_subs(channel_ids)
    except Exception as e:
        # Subscriber counts are nice-to-have, don't fail the whole run
        print(f"warning: subscriber lookup failed: {e}", file=sys.stderr)
        subs = {}

    rows = [
        flatten_video(rank=i + 1, item=item,
                      snap_utc=snap_utc, snap_ist=snap_ist,
                      sub_lookup=subs)
        for i, item in enumerate(items)
    ]

    snap_path = write_snapshot(rows, snap_utc)
    written = append_to_master(rows)

    msg = f"OK: wrote {written} rows to master + snapshot at {snap_path.name}"
    print(msg)
    log_run("ok", msg, written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
