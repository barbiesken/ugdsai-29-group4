"""
load_archival.py
================
Adapter that loads a Kaggle YouTube Trending dataset and writes rows in the
EXACT schema collect.py produces, so the rest of the pipeline works unchanged.

Supports two common schemas:

  A) datasnaek/youtube-new (2017-2018 era)
     Columns: video_id, trending_date (yy.dd.mm), title, channel_title,
              category_id, publish_time, tags, views, likes, dislikes,
              comment_count, thumbnail_link, comments_disabled, ...

  B) rsrishav/youtube-trending-video-dataset (2020+, daily updates)
     Columns: video_id, title, publishedAt, channelId, channelTitle,
              categoryId, trending_date, tags, view_count, likes,
              dislikes, comment_count, thumbnail_link, comments_disabled,
              ratings_disabled, description

Both produce the same downstream output: long-format snapshots that look
like collect.py wrote them, complete with synthesised snapshot_ts so the
lifecycle pipeline still has time-series structure.

USAGE
-----
    # Drop the IN .csv from Kaggle into data/archival/
    python scripts/load_archival.py data/archival/IN_youtube_trending_data.csv

    # Outputs:
    data/master_snapshots_archival.csv   <- normalised long-format snapshots
    data/archival_summary.txt            <- what was loaded

To MERGE archival + live collection:

    python scripts/load_archival.py data/archival/IN_youtube_trending_data.csv \
        --merge data/master_snapshots.csv \
        --out   data/master_snapshots_combined.csv
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# Target schema — must match collect.py.COLUMNS exactly
TARGET_COLUMNS = [
    "snapshot_ts", "snapshot_ts_ist", "trending_rank", "video_id",
    "title", "channel_id", "channel_title", "channel_subscriber_count",
    "category_id", "published_at", "duration_iso",
    "view_count", "like_count", "comment_count",
    "tags", "description_length",
    "default_audio_language", "default_language",
    "made_for_kids", "definition", "caption", "licensed_content",
    "thumbnail_url",
]


def detect_schema(df: pd.DataFrame) -> str:
    """Return 'A' for 2017 datasnaek, 'B' for rsrishav, or raise."""
    cols = set(df.columns)
    if "view_count" in cols and "channelId" in cols and "publishedAt" in cols:
        return "B"
    if "views" in cols and "channel_title" in cols and "publish_time" in cols:
        return "A"
    raise ValueError(
        f"Unrecognised schema. Columns found: {sorted(cols)[:15]}...\n"
        "Expected either datasnaek (views/channel_title/publish_time) "
        "or rsrishav (view_count/channelId/publishedAt) format."
    )


def parse_datasnaek_trending_date(s: str) -> datetime | None:
    """datasnaek format: 'yy.dd.mm' (e.g. '17.14.11' = 14 Nov 2017)."""
    try:
        parts = s.split(".")
        if len(parts) != 3:
            return None
        yy, dd, mm = int(parts[0]), int(parts[1]), int(parts[2])
        yyyy = 2000 + yy
        # Snapshot at 22:00 IST (matches our collector's evening run)
        dt = datetime(yyyy, mm, dd, 22, 0, tzinfo=IST).astimezone(UTC)
        return dt
    except Exception:
        return None


def parse_rsrishav_trending_date(s: str) -> datetime | None:
    """rsrishav format: ISO 8601 already (e.g. '2023-09-01T00:00:00Z')."""
    try:
        return pd.to_datetime(s, utc=True).to_pydatetime()
    except Exception:
        return None


def normalise_a(df: pd.DataFrame) -> pd.DataFrame:
    """Convert datasnaek schema → target schema."""
    out = pd.DataFrame()

    # Synthesise snapshot timestamps from the trending_date column
    snap_ts = df["trending_date"].astype(str).map(parse_datasnaek_trending_date)
    out["snapshot_ts"] = [
        ts.replace(microsecond=0).isoformat() if ts else "" for ts in snap_ts
    ]
    out["snapshot_ts_ist"] = [
        ts.astimezone(IST).replace(microsecond=0).isoformat() if ts else ""
        for ts in snap_ts
    ]

    # Trending rank not available in this dataset — synthesise per (snapshot, ranked by views)
    out["video_id"] = df["video_id"].astype(str)
    out["title"] = df["title"].fillna("").astype(str)
    out["channel_id"] = ""    # not available
    out["channel_title"] = df["channel_title"].fillna("").astype(str)
    out["channel_subscriber_count"] = ""
    out["category_id"] = df["category_id"].fillna("").astype(str)
    # publish_time is ISO already
    out["published_at"] = df["publish_time"].fillna("").astype(str)
    out["duration_iso"] = ""        # not in this dataset
    out["view_count"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    out["like_count"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)
    out["comment_count"] = pd.to_numeric(
        df["comment_count"], errors="coerce").fillna(0).astype(int)
    out["tags"] = df.get("tags", "").fillna("").astype(str).str.replace(
        r'^\["none"\]$', "", regex=True)
    # Tags in datasnaek are |-separated already, but in some files quoted
    out["tags"] = out["tags"].str.strip('"')
    desc = df.get("description", "").fillna("")
    out["description_length"] = desc.astype(str).str.len()
    out["default_audio_language"] = ""
    out["default_language"] = ""
    out["made_for_kids"] = ""
    out["definition"] = ""
    out["caption"] = ""
    out["licensed_content"] = ""
    out["thumbnail_url"] = df.get("thumbnail_link", "").fillna("").astype(str)

    # Compute trending_rank within each snapshot by view count
    out["trending_rank"] = (
        out.groupby("snapshot_ts")["view_count"]
        .rank(method="first", ascending=False).fillna(0).astype(int)
    )
    out = out[TARGET_COLUMNS]
    return out


def normalise_b(df: pd.DataFrame) -> pd.DataFrame:
    """Convert rsrishav schema → target schema."""
    out = pd.DataFrame()

    snap_ts = df["trending_date"].astype(str).map(parse_rsrishav_trending_date)
    out["snapshot_ts"] = [
        ts.replace(microsecond=0).isoformat() if ts else "" for ts in snap_ts
    ]
    out["snapshot_ts_ist"] = [
        ts.astimezone(IST).replace(microsecond=0).isoformat() if ts else ""
        for ts in snap_ts
    ]

    out["video_id"] = df["video_id"].astype(str)
    out["title"] = df["title"].fillna("").astype(str)
    out["channel_id"] = df.get("channelId", "").fillna("").astype(str)
    out["channel_title"] = df.get("channelTitle", "").fillna("").astype(str)
    out["channel_subscriber_count"] = ""
    out["category_id"] = df.get("categoryId", "").fillna("").astype(str)
    out["published_at"] = df.get("publishedAt", "").fillna("").astype(str)
    out["duration_iso"] = ""        # not present in rsrishav v1
    out["view_count"] = pd.to_numeric(df["view_count"], errors="coerce").fillna(0).astype(int)
    out["like_count"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
    out["comment_count"] = pd.to_numeric(
        df["comment_count"], errors="coerce").fillna(0).astype(int)
    out["tags"] = df.get("tags", "").fillna("").astype(str).str.strip('"')
    desc = df.get("description", "").fillna("")
    out["description_length"] = desc.astype(str).str.len()
    out["default_audio_language"] = ""
    out["default_language"] = ""
    out["made_for_kids"] = ""
    out["definition"] = ""
    out["caption"] = ""
    out["licensed_content"] = ""
    out["thumbnail_url"] = df.get("thumbnail_link", "").fillna("").astype(str)

    out["trending_rank"] = (
        out.groupby("snapshot_ts")["view_count"]
        .rank(method="first", ascending=False).fillna(0).astype(int)
    )
    out = out[TARGET_COLUMNS]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv", help="Path to the IN trending CSV from Kaggle")
    ap.add_argument("--out", default="data/master_snapshots_archival.csv",
                    help="Output path for normalised CSV")
    ap.add_argument("--merge", default=None,
                    help="Optional: path to live snapshots CSV to merge with")
    ap.add_argument("--limit-recent-days", type=int, default=None,
                    help="Optional: keep only the most recent N days of trending data")
    args = ap.parse_args()

    src = Path(args.input_csv)
    if not src.exists():
        print(f"ERROR: input file not found: {src}", file=sys.stderr)
        return 1

    print(f"Loading {src} ...")
    # Try common encodings
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(src, encoding=enc, low_memory=False)
            print(f"  loaded {len(df):,} rows with {enc} encoding")
            break
        except UnicodeDecodeError:
            continue
    else:
        print("ERROR: could not decode CSV with any common encoding")
        return 1

    schema = detect_schema(df)
    print(f"  detected schema: {schema} ({'datasnaek 2017-2018' if schema=='A' else 'rsrishav 2020+'})")

    if schema == "A":
        out = normalise_a(df)
    else:
        out = normalise_b(df)

    # Drop rows with empty snapshot_ts (couldn't parse the date)
    before = len(out)
    out = out[out["snapshot_ts"] != ""].copy()
    if before != len(out):
        print(f"  dropped {before - len(out)} rows with unparseable trending_date")

    if args.limit_recent_days:
        out["_ts"] = pd.to_datetime(out["snapshot_ts"], utc=True)
        cutoff = out["_ts"].max() - pd.Timedelta(days=args.limit_recent_days)
        out = out[out["_ts"] >= cutoff].drop(columns=["_ts"])
        print(f"  filtered to last {args.limit_recent_days} days: {len(out)} rows")

    print(f"  normalised: {len(out):,} rows")
    print(f"  unique videos: {out['video_id'].nunique():,}")
    print(f"  date range: {out['snapshot_ts'].min()}  →  {out['snapshot_ts'].max()}")
    print(f"  unique snapshots: {out['snapshot_ts'].nunique()}")

    # Optional merge with live data
    if args.merge:
        live_path = Path(args.merge)
        if not live_path.exists():
            print(f"WARN: live file not found, writing archival-only: {live_path}")
        else:
            live = pd.read_csv(live_path)
            print(f"  merging with live: {len(live)} rows from {live_path}")
            # Align columns
            for c in TARGET_COLUMNS:
                if c not in live.columns:
                    live[c] = ""
            live = live[TARGET_COLUMNS]
            combined = pd.concat([out, live], ignore_index=True)
            # Dedupe on (video_id, snapshot_ts)
            before = len(combined)
            combined = combined.drop_duplicates(subset=["video_id", "snapshot_ts"])
            print(f"  combined: {len(combined):,} rows ({before - len(combined)} duplicates removed)")
            out = combined

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nSaved → {out_path}")

    # Write a summary
    summary_path = out_path.parent / "archival_summary.txt"
    with summary_path.open("w") as f:
        f.write(f"Archival data load summary\n")
        f.write(f"==========================\n\n")
        f.write(f"Source: {src}\n")
        f.write(f"Schema detected: {schema}\n")
        f.write(f"Output: {out_path}\n\n")
        f.write(f"Rows: {len(out):,}\n")
        f.write(f"Unique videos: {out['video_id'].nunique():,}\n")
        f.write(f"Unique snapshots: {out['snapshot_ts'].nunique()}\n")
        f.write(f"Date range: {out['snapshot_ts'].min()} → {out['snapshot_ts'].max()}\n\n")
        f.write(f"Top categories by row count:\n")
        f.write(out["category_id"].value_counts().head(10).to_string())
    print(f"Summary  → {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
