"""
analysis.py
===========
End-to-end analysis pipeline for the YouTube Trending project.

Pipeline:
    1. Preprocess (impute, scale, encode categoricals)
    2. PCA with explained-variance plot
    3. K-Means with elbow + silhouette (k = 2..10)
    4. DBSCAN with k-distance heuristic
    5. Agglomerative clustering for comparison
    6. Validation: silhouette per algo, ARI between algos
    7. Cluster profiling: per-cluster feature means, distinctive tags
    8. Association mining on tag baskets (Apriori)

This file is the engine. The notebook loads it and runs sections.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score, calinski_harabasz_score, silhouette_score,
)
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

# Numerical features that benefit from RobustScaler (heavy tails)
ROBUST_NUMERIC = [
    "peak_views_per_hour", "mean_views_per_hour", "hours_to_first_trend",
    "half_life_hours", "channel_subs", "duration_seconds",
    "title_length", "description_length", "tag_count", "mean_tag_length",
    "rank_volatility",
]
# Numerical features that are already ratios/small (StandardScaler is fine)
STANDARD_NUMERIC = [
    "decay_log_slope_48h", "days_observed_on_chart",
    "chart_presence_ratio", "returned_count",
    "mean_like_view_ratio", "mean_comment_view_ratio",
    "comment_like_ratio", "engagement_growth",
    "title_caps_ratio",
]
BINARY_FEATURES = [
    "is_short", "title_has_emoji", "title_has_question",
]
CATEGORICAL_FEATURES = [
    "category_id", "channel_size_bucket", "language",
]


@dataclass
class PreprocessedData:
    X: np.ndarray              # final feature matrix used for clustering
    feature_names: List[str]   # column names of X
    raw_index: pd.Index        # video IDs (index of original feature DF)
    raw_features: pd.DataFrame # for profiling later


def preprocess(features: pd.DataFrame) -> PreprocessedData:
    """Impute, scale, encode → final numerical matrix for clustering."""
    df = features.copy()
    # Drop ground-truth column so it doesn't leak into clustering
    truth = df.pop("_true_archetype") if "_true_archetype" in df.columns else None

    # Drop columns that are entirely NaN (would have no median to impute with)
    fully_empty = [c for c in df.columns if df[c].isna().all()]
    if fully_empty:
        df = df.drop(columns=fully_empty)

    # Log-transform heavy-tailed features (lognormal-distributed in real data).
    # Using signed log1p so negative values (decay rates) survive.
    HEAVY_TAILED = [
        "peak_views_per_hour", "mean_views_per_hour", "channel_subs",
        "duration_seconds", "description_length",
    ]
    for col in HEAVY_TAILED:
        if col in df.columns:
            df[col] = np.sign(df[col]) * np.log1p(np.abs(df[col]))

    # Winsorise (clip) all numeric features at the 1st and 99th percentiles
    # to reduce the influence of extreme outliers on the geometry. This is
    # standard for clustering on real-world data with heavy tails.
    NUM_FOR_CLIP = ROBUST_NUMERIC + STANDARD_NUMERIC
    for col in NUM_FOR_CLIP:
        if col in df.columns:
            lo = df[col].quantile(0.01)
            hi = df[col].quantile(0.99)
            if pd.notna(lo) and pd.notna(hi) and hi > lo:
                df[col] = df[col].clip(lo, hi)

    # Impute missing values
    for col in ROBUST_NUMERIC + STANDARD_NUMERIC:
        if col in df.columns:
            med = df[col].median()
            if pd.isna(med):
                med = 0.0
            df[col] = df[col].fillna(med)
    for col in BINARY_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("unknown").astype(str)

    # Drop rows with ANY remaining infinity or NaN to prevent crashes downstream
    numeric_cols = [c for c in df.columns
                    if c in ROBUST_NUMERIC + STANDARD_NUMERIC + BINARY_FEATURES]
    finite_mask = np.isfinite(df[numeric_cols].to_numpy()).all(axis=1)
    if not finite_mask.all():
        df = df[finite_mask].copy()

    parts = []
    feature_names = []

    # Robust-scaled numeric
    have = [c for c in ROBUST_NUMERIC if c in df.columns]
    if have:
        rs = RobustScaler().fit_transform(df[have])
        parts.append(rs); feature_names.extend(have)
    # Standard-scaled numeric
    have = [c for c in STANDARD_NUMERIC if c in df.columns]
    if have:
        ss = StandardScaler().fit_transform(df[have])
        parts.append(ss); feature_names.extend(have)
    # Binary as-is
    have = [c for c in BINARY_FEATURES if c in df.columns]
    if have:
        parts.append(df[have].to_numpy(dtype=float)); feature_names.extend(have)
    # One-hot categoricals
    have = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    if have:
        enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        ohe = enc.fit_transform(df[have])
        parts.append(ohe)
        feature_names.extend([
            f"{c}={v}" for c, vals in zip(have, enc.categories_) for v in vals
        ])

    X = np.hstack(parts)
    raw = features.loc[df.index].drop(columns=["_true_archetype"], errors="ignore").copy()
    return PreprocessedData(X=X, feature_names=feature_names,
                            raw_index=df.index, raw_features=raw)


# ---------------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------------

def run_pca(X: np.ndarray, variance_target: float = 0.95) -> Tuple[np.ndarray, PCA, int]:
    pca = PCA(n_components=variance_target, random_state=42)
    Xp = pca.fit_transform(X)
    return Xp, pca, Xp.shape[1]


# ---------------------------------------------------------------------------
# Clustering: K-Means scan
# ---------------------------------------------------------------------------

def kmeans_scan(X: np.ndarray, k_range: range = range(2, 11),
                random_state: int = 42) -> pd.DataFrame:
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels) if k > 1 else np.nan
        chs = calinski_harabasz_score(X, labels) if k > 1 else np.nan
        # Imbalance: largest cluster as fraction of total
        sizes = pd.Series(labels).value_counts()
        max_share = float(sizes.max()) / len(labels)
        rows.append({
            "k": k,
            "inertia": km.inertia_,
            "silhouette": sil,
            "calinski_harabasz": chs,
            "max_cluster_share": max_share,
        })
    return pd.DataFrame(rows)


def suggest_k(scan: pd.DataFrame, max_imbalance: float = 0.55) -> int:
    """
    Pick k by silhouette, but DISQUALIFY degenerate splits where one cluster
    contains > max_imbalance of the data. This prevents the classic trap
    where silhouette picks k=2 with one big blob + one tiny outlier cluster.
    """
    candidates = scan[scan["max_cluster_share"] <= max_imbalance]
    if candidates.empty:
        # Fall back to highest silhouette regardless
        return int(scan.loc[scan["silhouette"].idxmax(), "k"])
    return int(candidates.loc[candidates["silhouette"].idxmax(), "k"])


def fit_kmeans(X: np.ndarray, k: int, random_state: int = 42) -> Tuple[KMeans, np.ndarray]:
    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    labels = km.fit_predict(X)
    return km, labels


# ---------------------------------------------------------------------------
# Clustering: DBSCAN and Agglomerative
# ---------------------------------------------------------------------------

def fit_dbscan(X: np.ndarray, eps: float, min_samples: int = 5) -> np.ndarray:
    db = DBSCAN(eps=eps, min_samples=min_samples)
    return db.fit_predict(X)


def fit_agglomerative(X: np.ndarray, k: int) -> np.ndarray:
    ag = AgglomerativeClustering(n_clusters=k, linkage="ward")
    return ag.fit_predict(X)


def k_distance_curve(X: np.ndarray, k: int = 5) -> np.ndarray:
    """Return sorted k-th nearest-neighbour distances. Elbow is the eps choice."""
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    d, _ = nn.kneighbors(X)
    return np.sort(d[:, k])


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

def profile_clusters(features: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Per-cluster mean of every numeric feature, plus z-score vs all data."""
    df = features.copy()
    if "_true_archetype" in df.columns:
        df = df.drop(columns=["_true_archetype"])
    df["cluster"] = labels
    numeric = df.select_dtypes(include=[np.number])
    means = numeric.groupby(df["cluster"]).mean()
    overall_mean = numeric.mean()
    overall_std = numeric.std().replace(0, 1)
    zscore = (means - overall_mean) / overall_std
    return zscore


def cluster_sizes(labels: np.ndarray) -> pd.Series:
    s = pd.Series(labels).value_counts().sort_index()
    s.index.name = "cluster"
    s.name = "n_videos"
    return s


# ---------------------------------------------------------------------------
# Association mining on tag baskets
# ---------------------------------------------------------------------------

def build_tag_baskets(snapshots_long: pd.DataFrame, video_ids: pd.Index) -> List[List[str]]:
    """For each (filtered) video, return its first-snapshot tag list."""
    first = (snapshots_long.sort_values("snapshot_ts")
                            .groupby("video_id").first())
    first = first.loc[first.index.intersection(video_ids)]
    baskets = (first["tags"].fillna("")
                            .map(lambda s: [t for t in s.split("|") if t])
                            .tolist())
    return baskets


def mine_rules(baskets: List[List[str]],
               min_support: float = 0.05,
               min_confidence: float = 0.5,
               min_lift: float = 1.2,
               keep_top_n_tags: int = 80) -> pd.DataFrame:
    """
    Apriori → association rules.

    Filters baskets to the top-N most-frequent tags first to keep memory
    bounded. With keep_top_n_tags=80 and ~300 baskets, peak memory stays
    well under 1GB.
    """
    try:
        from mlxtend.frequent_patterns import apriori, association_rules
        from mlxtend.preprocessing import TransactionEncoder
    except ImportError:
        return pd.DataFrame()

    # Filter to top-N most-frequent tags
    from collections import Counter
    tag_counts = Counter(t for b in baskets for t in b)
    keep_tags = {t for t, _ in tag_counts.most_common(keep_top_n_tags)}
    filtered = [[t for t in b if t in keep_tags] for b in baskets]
    filtered = [b for b in filtered if b]   # drop empty baskets
    if not filtered:
        return pd.DataFrame()

    te = TransactionEncoder()
    te_ary = te.fit(filtered).transform(filtered)
    df = pd.DataFrame(te_ary, columns=te.columns_)
    freq = apriori(df, min_support=min_support, use_colnames=True,
                   max_len=3, low_memory=True)
    if freq.empty:
        return pd.DataFrame()
    rules = association_rules(freq, metric="confidence",
                              min_threshold=min_confidence,
                              num_itemsets=len(df))
    rules = rules[rules["lift"] >= min_lift]
    return rules.sort_values("lift", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2D embedding for the hero map
# ---------------------------------------------------------------------------

def umap_embed(X: np.ndarray, n_neighbors: int = 15, random_state: int = 42) -> np.ndarray:
    try:
        import umap
        return umap.UMAP(n_neighbors=n_neighbors, random_state=random_state).fit_transform(X)
    except Exception:
        # Fallback to PCA
        return PCA(n_components=2, random_state=random_state).fit_transform(X)
