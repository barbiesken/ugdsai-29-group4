"""
features.py
===========
Feature engineering for the YouTube Trending project.

Takes long-format snapshots (one row per (video_id, snapshot_ts)) and
produces a wide per-video feature matrix following Anant's directive.

5 themes:
    1. Velocity   - how fast it grew
    2. Decay      - how fast it died
    3. Retention  - sticky vs flash
    4. Engagement - audience response
    5. Content    - video / title / channel metadata
"""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ISO_DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "]+", flags=re.UNICODE
)


def parse_duration_seconds(iso: str) -> float:
    if not isinstance(iso, str):
        return np.nan
    m = ISO_DURATION.match(iso)
    if not m:
        return np.nan
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def title_caps_ratio(t: str) -> float:
    if not isinstance(t, str) or not t:
        return 0.0
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def channel_size_bucket(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "unknown"
    if pd.isna(n) or n < 0:
        return "unknown"
    if n < 10_000:        return "nano"
    if n < 100_000:       return "micro"
    if n < 1_000_000:     return "mid"
    if n < 10_000_000:    return "large"
    return "mega"


def _normalize_ts(s: pd.Series) -> pd.Series:
    """Convert any timestamp Series to tz-naive UTC datetime64[ns]."""
    s = pd.to_datetime(s, utc=True, errors="coerce")
    # Drop tz so numpy arithmetic works
    return s.dt.tz_convert(None)


# ---------------------------------------------------------------------------
# Theme 1: Velocity
# ---------------------------------------------------------------------------

def _velocity_for_video(g: pd.DataFrame) -> Dict[str, float]:
    g = g.sort_values("snapshot_ts")
    ts = g["snapshot_ts"].to_numpy().astype("datetime64[ns]")
    views = g["view_count"].to_numpy(dtype=float)
    pub = g["published_at"].iloc[0]

    if len(g) < 2:
        peak = mean = np.nan
    else:
        dh = (ts[1:] - ts[:-1]).astype("timedelta64[s]").astype(float) / 3600
        dv = views[1:] - views[:-1]
        with np.errstate(divide="ignore", invalid="ignore"):
            vph = np.where(dh > 0, dv / np.where(dh > 0, dh, 1), np.nan)
        peak = float(np.nanmax(vph)) if vph.size else np.nan
        mean = float(np.nanmean(vph)) if vph.size else np.nan

    if pd.notna(pub):
        try:
            h_first = (ts[0] - np.datetime64(pub)).astype("timedelta64[s]").astype(float) / 3600
        except Exception:
            h_first = np.nan
    else:
        h_first = np.nan

    return {
        "peak_views_per_hour": peak,
        "mean_views_per_hour": mean,
        "hours_to_first_trend": h_first,
    }


# ---------------------------------------------------------------------------
# Theme 2: Decay
# ---------------------------------------------------------------------------

def _decay_for_video(g: pd.DataFrame) -> Dict[str, float]:
    g = g.sort_values("snapshot_ts")
    ts = g["snapshot_ts"].to_numpy().astype("datetime64[ns]")
    views = g["view_count"].to_numpy(dtype=float)

    # Decay log-slope over last 48h
    if len(g) >= 2:
        last = ts[-1]
        cutoff = last - np.timedelta64(48, "h")
        mask = ts >= cutoff
        if mask.sum() >= 2 and (views[mask] > 0).all():
            h = (ts[mask] - ts[mask][0]).astype("timedelta64[s]").astype(float) / 3600
            # polyfit fails if h has zero variance (all identical times)
            if np.std(h) > 0:
                try:
                    slope = float(np.polyfit(h, np.log(views[mask] + 1), 1)[0])
                except (np.linalg.LinAlgError, ValueError):
                    slope = np.nan
            else:
                slope = np.nan
        else:
            slope = np.nan
    else:
        slope = np.nan

    days = pd.Series(pd.to_datetime(ts).date).nunique()

    # Half-life in hours
    hl = np.nan
    if len(g) >= 3:
        dh = (ts[1:] - ts[:-1]).astype("timedelta64[s]").astype(float) / 3600
        dv = views[1:] - views[:-1]
        valid = dh > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            vph = np.where(valid, dv / np.where(valid, dh, 1), np.nan)
        if np.any(~np.isnan(vph)):
            peak_idx = int(np.nanargmax(vph))
            peak = vph[peak_idx]
            if pd.notna(peak) and peak > 0:
                target = peak * 0.5
                after = vph[peak_idx:]
                below = np.where(after <= target)[0]
                step = float(np.nanmedian(dh[dh > 0])) if (dh > 0).any() else 12.0
                if len(below) > 0:
                    hl = float(below[0] * step)
                else:
                    hl = float((ts[-1] - ts[peak_idx]).astype("timedelta64[s]").astype(float) / 3600)

    return {
        "decay_log_slope_48h": slope,
        "half_life_hours": hl,
        "days_observed_on_chart": int(days),
    }


# ---------------------------------------------------------------------------
# Theme 3: Retention
# ---------------------------------------------------------------------------

def _retention_for_video(g: pd.DataFrame, snap_to_idx: Dict) -> Dict[str, float]:
    g = g.sort_values("snapshot_ts")
    seen_idx = sorted(
        snap_to_idx[ts] for ts in g["snapshot_ts"]
        if ts in snap_to_idx
    )
    if not seen_idx:
        return {"chart_presence_ratio": np.nan,
                "rank_volatility": np.nan,
                "returned_count": 0}
    span = seen_idx[-1] - seen_idx[0] + 1
    presence = len(seen_idx) / span
    rank_vol = float(g["trending_rank"].std()) if len(g) >= 2 else 0.0
    gaps = sum(1 for a, b in zip(seen_idx[:-1], seen_idx[1:]) if b - a > 1)
    return {
        "chart_presence_ratio": presence,
        "rank_volatility": rank_vol if pd.notna(rank_vol) else 0.0,
        "returned_count": gaps,
    }


# ---------------------------------------------------------------------------
# Theme 4: Engagement
# ---------------------------------------------------------------------------

def _engagement_for_video(g: pd.DataFrame) -> Dict[str, float]:
    g = g.sort_values("snapshot_ts")
    views = g["view_count"].astype(float).replace(0, np.nan)
    likes = g["like_count"].astype(float)
    comments = g["comment_count"].astype(float)
    like_view = (likes / views).to_numpy()
    comment_view = (comments / views).to_numpy()
    last_likes = float(likes.iloc[-1])
    last_comments = float(comments.iloc[-1])
    return {
        "mean_like_view_ratio": float(np.nanmean(like_view)),
        "mean_comment_view_ratio": float(np.nanmean(comment_view)),
        "comment_like_ratio": (last_comments / last_likes) if last_likes else np.nan,
        "engagement_growth": (
            float(like_view[-1] - like_view[0]) if len(g) >= 2 else np.nan
        ),
    }


# ---------------------------------------------------------------------------
# Theme 5: Content
# ---------------------------------------------------------------------------

def _content_table(df: pd.DataFrame) -> pd.DataFrame:
    first = (df.sort_values("snapshot_ts")
                .groupby("video_id").first())
    out = pd.DataFrame(index=first.index)
    out["duration_seconds"]   = first["duration_iso"].map(parse_duration_seconds)
    out["is_short"]           = (out["duration_seconds"] <= 60).astype(int)
    out["title_length"]       = first["title"].fillna("").map(len)
    out["title_caps_ratio"]   = first["title"].fillna("").map(title_caps_ratio)
    out["title_has_emoji"]    = first["title"].fillna("").map(
        lambda s: int(bool(EMOJI_RE.search(s)))
    )
    out["title_has_question"] = first["title"].fillna("").map(
        lambda s: int("?" in s)
    )
    out["tag_count"]          = first["tags"].fillna("").map(
        lambda s: 0 if s == "" else len(s.split("|"))
    )
    out["mean_tag_length"]    = first["tags"].fillna("").map(
        lambda s: float(np.mean([len(t) for t in s.split("|")])) if s else 0.0
    )
    out["description_length"] = first["description_length"]
    out["category_id"]        = first["category_id"].astype(str)
    out["channel_subs"]       = first["channel_subscriber_count"]
    out["channel_size_bucket"]= out["channel_subs"].map(channel_size_bucket)
    out["language"]           = (
        first["default_audio_language"].fillna(first["default_language"])
                                       .fillna("unknown")
    )
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_features(df: pd.DataFrame, min_obs: int = 2) -> pd.DataFrame:
    """
    Convert long-format snapshots into the per-video feature matrix.
    """
    df = df.copy()
    df["snapshot_ts"] = _normalize_ts(df["snapshot_ts"])
    df["published_at"] = _normalize_ts(df["published_at"])

    # Filter to videos with at least min_obs observations
    counts = df.groupby("video_id").size()
    keep = counts[counts >= min_obs].index
    df = df[df["video_id"].isin(keep)].copy()

    # Pre-compute snapshot index for retention features
    all_snaps = sorted(df["snapshot_ts"].unique())
    snap_to_idx = {s: i for i, s in enumerate(all_snaps)}

    # Per-video feature dicts
    rows = []
    for vid, g in df.groupby("video_id", sort=False):
        feats = {"video_id": vid}
        feats.update(_velocity_for_video(g))
        feats.update(_decay_for_video(g))
        feats.update(_retention_for_video(g, snap_to_idx))
        feats.update(_engagement_for_video(g))
        rows.append(feats)
    lifecycle = pd.DataFrame(rows).set_index("video_id")

    content = _content_table(df)
    features = lifecycle.join(content, how="inner")

    # Ground truth label if present (synthetic data)
    if "_true_archetype" in df.columns:
        truth = (df.sort_values("snapshot_ts")
                   .groupby("video_id")["_true_archetype"].first())
        features["_true_archetype"] = truth

    return features
