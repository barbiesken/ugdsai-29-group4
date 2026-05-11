"""
make_synthetic_data.py
======================
Generates a realistic synthetic master_snapshots.csv that matches the schema
of collect.py's output. Used to develop and test the analysis pipeline
BEFORE real collection data is available.

Design: 5 latent archetypes are seeded with distinct lifecycle signatures.
After feature engineering, the clustering algorithms should rediscover them.

Run:
    python scripts/make_synthetic_data.py
    -> writes data/master_snapshots.csv (synthetic flag in filename)
"""

from __future__ import annotations

import csv
import math
import random
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

random.seed(42)
np.random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUT_CSV = DATA_DIR / "master_snapshots_synthetic.csv"

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# Match collect.py exactly
COLUMNS = [
    "snapshot_ts", "snapshot_ts_ist", "trending_rank", "video_id",
    "title", "channel_id", "channel_title", "channel_subscriber_count",
    "category_id", "published_at", "duration_iso",
    "view_count", "like_count", "comment_count",
    "tags", "description_length",
    "default_audio_language", "default_language",
    "made_for_kids", "definition", "caption", "licensed_content",
    "thumbnail_url",
]

# 10-day collection window, twice daily
START = datetime(2026, 5, 2, 4, 30, tzinfo=UTC)   # 10:00 IST = 04:30 UTC
SNAPSHOTS = []
for day in range(10):
    SNAPSHOTS.append(START + timedelta(days=day))                  # 10:00 IST
    SNAPSHOTS.append(START + timedelta(days=day, hours=12))        # 22:00 IST


# ---------------------------------------------------------------------------
# Archetype templates
# ---------------------------------------------------------------------------
# Each archetype has a different lifecycle behaviour. Feature engineering
# should reveal these differences and clustering should rediscover them.

ARCHETYPES = {
    "marathon": {
        # Slow-burn educational: long videos, climbs slowly, stays for days,
        # high like/view ratio, low comment churn.
        "share": 0.18,
        "duration_range": (600, 2400),    # 10-40 min
        "publish_lag_hours_range": (24, 240),  # published 1-10 days before trending
        "n_appearances_range": (8, 18),
        "view_curve": "logarithmic",
        "peak_velocity_kvph_range": (15, 80),
        "like_view_range": (0.04, 0.10),
        "comment_view_range": (0.0008, 0.003),
        "tag_count_range": (12, 30),
        "category_pool": ["27", "28", "26"],   # Education, Sci&Tech, How-to
        "title_caps_ratio_range": (0.05, 0.20),
        "title_emoji_prob": 0.10,
        "channel_subs_range": (50_000, 5_000_000),
    },
    "firework": {
        # News / music drops: spikes hard, dies fast, moderate engagement,
        # short to medium duration.
        "share": 0.30,
        "duration_range": (90, 480),
        "publish_lag_hours_range": (1, 12),
        "n_appearances_range": (2, 6),
        "view_curve": "spike",
        "peak_velocity_kvph_range": (300, 1500),
        "like_view_range": (0.02, 0.06),
        "comment_view_range": (0.001, 0.005),
        "tag_count_range": (8, 25),
        "category_pool": ["10", "25", "24"],   # Music, News, Entertainment
        "title_caps_ratio_range": (0.10, 0.40),
        "title_emoji_prob": 0.45,
        "channel_subs_range": (500_000, 30_000_000),
    },
    "drumbeat": {
        # Recurring weekly creators: mid velocity, multiple chart re-entries.
        "share": 0.20,
        "duration_range": (480, 1500),
        "publish_lag_hours_range": (12, 72),
        "n_appearances_range": (4, 10),
        "view_curve": "stepped",   # we'll add re-entry behaviour
        "peak_velocity_kvph_range": (60, 250),
        "like_view_range": (0.03, 0.07),
        "comment_view_range": (0.002, 0.006),
        "tag_count_range": (10, 22),
        "category_pool": ["24", "23", "22"],   # Entertainment, Comedy, People
        "title_caps_ratio_range": (0.05, 0.25),
        "title_emoji_prob": 0.30,
        "channel_subs_range": (200_000, 10_000_000),
    },
    "megaphone": {
        # Engineered/promoted: high velocity, suspiciously flat engagement,
        # low like/view despite high views, lots of generic tags.
        "share": 0.12,
        "duration_range": (60, 360),
        "publish_lag_hours_range": (2, 24),
        "n_appearances_range": (3, 8),
        "view_curve": "ramp",
        "peak_velocity_kvph_range": (200, 700),
        "like_view_range": (0.005, 0.020),       # NOTABLY LOW
        "comment_view_range": (0.0002, 0.0010),  # NOTABLY LOW
        "tag_count_range": (25, 45),             # NOTABLY HIGH (keyword stuffing)
        "category_pool": ["24", "22", "10"],
        "title_caps_ratio_range": (0.20, 0.50),
        "title_emoji_prob": 0.60,
        "channel_subs_range": (10_000, 1_000_000),
    },
    "snack": {
        # Shorts: very short duration, fast cycle, high view/comment ratio.
        "share": 0.20,
        "duration_range": (10, 60),
        "publish_lag_hours_range": (1, 24),
        "n_appearances_range": (2, 5),
        "view_curve": "spike",
        "peak_velocity_kvph_range": (400, 2000),
        "like_view_range": (0.06, 0.14),
        "comment_view_range": (0.0005, 0.002),
        "tag_count_range": (3, 15),
        "category_pool": ["24", "22", "23"],
        "title_caps_ratio_range": (0.05, 0.30),
        "title_emoji_prob": 0.55,
        "channel_subs_range": (100_000, 20_000_000),
    },
}

# Tag pools per archetype — we want association rules to find these
TAG_POOLS = {
    "marathon": ["education", "tutorial", "explained", "lecture", "iitjee",
                 "neet", "physics", "biology", "history", "documentary",
                 "longform", "deep dive", "analysis", "study", "concept"],
    "firework": ["breaking", "news", "live", "official", "music video",
                 "song", "trailer", "release", "viral", "trending",
                 "exclusive", "first look", "premiere", "today"],
    "drumbeat": ["episode", "weekly", "podcast", "comedy", "vlog",
                 "reaction", "review", "interview", "show", "series",
                 "season", "part 2", "ep", "talkshow"],
    "megaphone": ["viral", "trending", "fyp", "shorts", "trending now",
                  "must watch", "best", "top", "amazing", "shocking",
                  "you wont believe", "omg", "wow", "subscribe", "share",
                  "like", "comment", "follow", "support", "indian", "india"],
    "snack": ["shorts", "ytshorts", "viral", "fyp", "trending",
              "funny", "comedy", "cute", "wholesome", "satisfying",
              "asmr", "dance", "reels"],
}

CATEGORY_NAMES = {
    "10": "Music", "22": "People & Blogs", "23": "Comedy",
    "24": "Entertainment", "25": "News & Politics",
    "26": "Howto & Style", "27": "Education", "28": "Science & Tech",
}

LANGUAGES_BY_ARCHETYPE = {
    "marathon": ["en", "hi"],
    "firework": ["hi", "en", "ta", "te"],
    "drumbeat": ["hi", "en"],
    "megaphone": ["hi", "en"],
    "snack": ["hi", "en", "pa"],
}


# ---------------------------------------------------------------------------
# Per-video generation
# ---------------------------------------------------------------------------

def random_id(n: int = 11) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "_-", k=n))


def make_title(archetype: str) -> str:
    pool = TAG_POOLS[archetype]
    base = random.choice([
        "What is {}?",
        "{} - explained in 10 minutes",
        "BREAKING: {} (LIVE)",
        "{} | Episode {}",
        "Top 10 {} you must watch",
        "{} song official video",
        "{} reaction",
        "{} review 2026",
        "{} short #shorts",
        "How to {}",
    ])
    word = random.choice(pool).title()
    return base.format(word, random.randint(1, 50))


def make_tags(archetype: str, n: int) -> list[str]:
    pool = TAG_POOLS[archetype]
    # Mostly archetype tags, plus some generic noise
    own = random.sample(pool, k=min(n - 2, len(pool)))
    noise = random.sample(["india", "2026", "viral", "trending", "youtube"], k=2)
    return own + noise


def parse_iso_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    out = "PT"
    if h: out += f"{h}H"
    if m: out += f"{m}M"
    if s or (not h and not m): out += f"{s}S"
    return out


def view_trajectory(archetype: str, n: int, peak_vph_k: float) -> list[float]:
    """Return cumulative view counts at each of n snapshots (12h apart)."""
    hours = np.array([12 * i for i in range(n)], dtype=float)
    if archetype == "logarithmic" or archetype == "marathon":
        # Slow growth, log-ish
        v = peak_vph_k * 1000 * np.log1p(hours / 12) * 8
    elif archetype == "spike" or archetype == "firework" or archetype == "snack":
        # Rapid spike, then slow tail
        v = peak_vph_k * 1000 * (1 - np.exp(-hours / 18)) * 12
    elif archetype == "stepped" or archetype == "drumbeat":
        # Linear-ish climb, mild plateau
        v = peak_vph_k * 1000 * np.power(hours / 12 + 1, 0.7) * 6
    elif archetype == "ramp" or archetype == "megaphone":
        # Suspiciously linear
        v = peak_vph_k * 1000 * (hours / 12 + 1) * 5
    else:
        v = peak_vph_k * 1000 * hours
    # Add small multiplicative noise so we don't get perfect curves
    noise = np.random.lognormal(0, 0.10, size=v.shape)
    return list(np.maximum(v * noise, 1).astype(int))


def generate_videos(n_total: int = 450) -> list[dict]:
    """
    Generate the latent video universe with archetype assignments.
    Returns one dict per video with all the per-video state we need.
    """
    videos = []
    for archetype, spec in ARCHETYPES.items():
        n = int(round(n_total * spec["share"]))
        for _ in range(n):
            n_apps = random.randint(*spec["n_appearances_range"])
            duration_s = random.randint(*spec["duration_range"])
            peak_vph_k = random.uniform(*spec["peak_velocity_kvph_range"])

            video = {
                "_archetype": archetype,        # ground truth, used only for validation
                "video_id": random_id(),
                "channel_id": "UC" + random_id(22),
                "channel_title": f"Channel_{archetype}_{random.randint(1,9999)}",
                "channel_subs": random.randint(*spec["channel_subs_range"]),
                "category_id": random.choice(spec["category_pool"]),
                "duration_s": duration_s,
                "duration_iso": parse_iso_duration(duration_s),
                "title": make_title(archetype),
                "tags": make_tags(archetype, random.randint(*spec["tag_count_range"])),
                "description_length": random.randint(50, 3000),
                "n_appearances": n_apps,
                "first_snapshot_idx": random.randint(0, max(0, len(SNAPSHOTS) - n_apps)),
                "view_curve": spec["view_curve"],
                "peak_vph_k": peak_vph_k,
                "like_view_ratio": random.uniform(*spec["like_view_range"]),
                "comment_view_ratio": random.uniform(*spec["comment_view_range"]),
                "language": random.choice(LANGUAGES_BY_ARCHETYPE[archetype]),
                "publish_lag_h": random.uniform(*spec["publish_lag_hours_range"]),
                "title_caps_ratio": random.uniform(*spec["title_caps_ratio_range"]),
                "has_emoji": random.random() < spec["title_emoji_prob"],
            }
            videos.append(video)

    random.shuffle(videos)
    return videos


def video_appears_at_snapshot(video: dict, snap_idx: int) -> bool:
    """Drumbeat archetype has chart re-entries; others are contiguous."""
    first = video["first_snapshot_idx"]
    last = first + video["n_appearances"] - 1
    if snap_idx < first or snap_idx > last:
        return False
    if video["_archetype"] == "drumbeat":
        # Drop out for ~30% of the middle window to simulate re-entries
        rel = (snap_idx - first) / max(1, video["n_appearances"] - 1)
        if 0.3 < rel < 0.6 and random.random() < 0.4:
            return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    videos = generate_videos(n_total=450)
    print(f"Generated {len(videos)} videos across "
          f"{len({v['_archetype'] for v in videos})} archetypes")

    # Pre-compute view trajectories per video
    for v in videos:
        traj = view_trajectory(v["view_curve"], v["n_appearances"], v["peak_vph_k"])
        # Pad with zeros before first appearance so we can index by snap_idx
        v["view_traj"] = traj

    rows = []
    for snap_idx, snap_dt in enumerate(SNAPSHOTS):
        # Pick which videos are "on the chart" at this snapshot
        candidates = [v for v in videos if video_appears_at_snapshot(v, snap_idx)]
        # Take top 50 by current views (mimics chart behaviour)
        # First need their current views
        for v in candidates:
            offset = snap_idx - v["first_snapshot_idx"]
            v["_current_views"] = v["view_traj"][offset]
        candidates.sort(key=lambda v: v["_current_views"], reverse=True)
        on_chart = candidates[:50]

        for rank, v in enumerate(on_chart, start=1):
            views = v["_current_views"]
            likes = int(views * v["like_view_ratio"] *
                        np.random.lognormal(0, 0.05))
            comments = int(views * v["comment_view_ratio"] *
                           np.random.lognormal(0, 0.10))
            published_at = (snap_dt - timedelta(hours=v["publish_lag_h"]
                                                + (snap_idx - v["first_snapshot_idx"]) * 12))
            row = {
                "snapshot_ts": snap_dt.replace(microsecond=0).isoformat(),
                "snapshot_ts_ist": snap_dt.astimezone(IST).replace(microsecond=0).isoformat(),
                "trending_rank": rank,
                "video_id": v["video_id"],
                "title": v["title"],
                "channel_id": v["channel_id"],
                "channel_title": v["channel_title"],
                "channel_subscriber_count": v["channel_subs"],
                "category_id": v["category_id"],
                "published_at": published_at.replace(microsecond=0).isoformat(),
                "duration_iso": v["duration_iso"],
                "view_count": int(views),
                "like_count": likes,
                "comment_count": comments,
                "tags": "|".join(v["tags"]),
                "description_length": v["description_length"],
                "default_audio_language": v["language"],
                "default_language": v["language"],
                "made_for_kids": "False",
                "definition": "hd",
                "caption": "false",
                "licensed_content": "False",
                "thumbnail_url": f"https://i.ytimg.com/vi/{v['video_id']}/hqdefault.jpg",
                # ground-truth label kept ONLY for validation; will not be used in training
                "_true_archetype": v["_archetype"],
                "_title_caps_ratio_seed": v["title_caps_ratio"],
                "_has_emoji_seed": v["has_emoji"],
            }
            rows.append(row)

    # Write
    extra_cols = ["_true_archetype", "_title_caps_ratio_seed", "_has_emoji_seed"]
    fieldnames = COLUMNS + extra_cols
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    n_unique_videos = len({r["video_id"] for r in rows})
    print(f"Unique videos: {n_unique_videos}")
    from collections import Counter
    by_arch = Counter(r["_true_archetype"] for r in rows)
    by_unique_arch = Counter()
    seen = set()
    for r in rows:
        if r["video_id"] not in seen:
            seen.add(r["video_id"])
            by_unique_arch[r["_true_archetype"]] += 1
    print("Snapshots per archetype:", dict(by_arch))
    print("Unique videos per archetype:", dict(by_unique_arch))


if __name__ == "__main__":
    main()
