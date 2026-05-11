"""
Builds notebooks/02_analysis.ipynb programmatically.
Avoids hand-writing JSON-with-escaped-strings which is fragile.
"""

import json
from pathlib import Path

NB = Path(__file__).resolve().parent.parent / "notebooks" / "02_analysis.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


cells = []

cells.append(md("""# Analysis: Clustering, PCA, Validation, Profiling, Association Mining

**UGDSAI 29 · Group 4 · Aaryan, Daksh, Mayank**

**Input:** `data/videos_features.csv` (one row per video, 25+ engineered features)
**Output:** plots, cluster assignments, association rules, the 4 hero visuals for the deck.

## Structure
1. Load and preprocess (impute, scale, encode)
2. PCA — explained variance and dominant axes
3. Clustering — K-Means scan, choose `k` carefully
4. Compare K-Means vs Agglomerative vs DBSCAN
5. Validate with silhouette + ARI
6. Profile the clusters and name them as viral archetypes
7. Hero visuals: 2D map, lifecycle curves, fingerprint heatmap
8. Association mining on tag baskets"""))

cells.append(code("""import sys; sys.path.insert(0, '../scripts')
import warnings; warnings.filterwarnings('ignore')
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.metrics.pairwise import euclidean_distances

from features import build_features
from analysis import (
    preprocess, run_pca, kmeans_scan, suggest_k,
    fit_kmeans, fit_dbscan, fit_agglomerative,
    k_distance_curve, profile_clusters, cluster_sizes,
    build_tag_baskets, mine_rules, umap_embed,
)

plt.rcParams.update({
    'figure.dpi': 110, 'savefig.dpi': 150, 'font.size': 10,
    'axes.spines.top': False, 'axes.spines.right': False,
})

# === SWITCH HERE WHEN REAL DATA IS READY ===
INPUT_CSV = '../data/master_snapshots_synthetic.csv'   # synthetic for dev
# INPUT_CSV = '../data/master_snapshots.csv'           # real data

FIG_DIR = Path('../docs/figures'); FIG_DIR.mkdir(parents=True, exist_ok=True)"""))

cells.append(md("## 1. Load and engineer features"))

cells.append(code("""snapshots = pd.read_csv(INPUT_CSV)
print(f'Snapshots: {len(snapshots):,} rows, {snapshots["video_id"].nunique():,} unique videos')

features = build_features(snapshots, min_obs=2)
print(f'Feature matrix: {features.shape[0]} videos x {features.shape[1]} features')
features.to_csv('../data/videos_features.csv')
features.head(3)"""))

cells.append(md("""## 2. Preprocessing — scale and encode

- **RobustScaler** for heavy-tailed numerics (view counts, durations, channel size)
- **StandardScaler** for ratios already on small scales
- **One-hot** for categoricals (category, channel-size bucket, language)"""))

cells.append(code("""pre = preprocess(features)
print(f'Final feature matrix shape: {pre.X.shape}')
print(f'  -> {len(pre.feature_names)} columns total')"""))

cells.append(md("""## 3. PCA

We retain enough components to explain 95% of variance. The cumulative-variance curve goes in the deck."""))

cells.append(code("""Xp, pca_model, n_comp = run_pca(pre.X, variance_target=0.95)
print(f'PCA -> {n_comp} components retained for 95% variance')

fig, ax = plt.subplots(figsize=(7, 3.5))
cum = np.cumsum(pca_model.explained_variance_ratio_)
ax.plot(range(1, len(cum)+1), cum, 'o-', color='#13315C')
ax.axhline(0.95, color='crimson', ls='--', lw=1, label='95% target')
ax.set_xlabel('Component'); ax.set_ylabel('Cumulative explained variance')
ax.set_title(f'PCA: {n_comp} components retain 95% variance')
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG_DIR/'pca_variance.png'); plt.show()"""))

cells.append(md("""### Top loadings on PC1 and PC2

These tell us what the **dominant axes of variation** are."""))

cells.append(code("""loadings = pd.DataFrame(pca_model.components_[:2].T,
                        index=pre.feature_names, columns=['PC1', 'PC2'])
print('Top |loadings| on PC1:')
print(loadings['PC1'].abs().sort_values(ascending=False).head(8).round(3))
print()
print('Top |loadings| on PC2:')
print(loadings['PC2'].abs().sort_values(ascending=False).head(8).round(3))"""))

cells.append(md("""## 4. K-Means scan: choose `k` carefully

We compute **silhouette**, **Calinski-Harabasz**, and **max-cluster-share** for k = 2..10.
Silhouette alone can be misleading: it tends to pick degenerate splits where one tiny dense cluster pulls away from a big blob. We disqualify any `k` where the largest cluster exceeds 55% of the data — those splits aren't useful for surfacing archetypes."""))

cells.append(code("""scan = kmeans_scan(Xp, k_range=range(2, 11))
scan.round(3)"""))

cells.append(code("""fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
axes[0].plot(scan['k'], scan['inertia'], 'o-', color='#13315C')
axes[0].set_title('Elbow (inertia)'); axes[0].set_xlabel('k'); axes[0].grid(alpha=0.3)
axes[1].plot(scan['k'], scan['silhouette'], 'o-', color='#13315C')
axes[1].set_title('Silhouette score'); axes[1].set_xlabel('k'); axes[1].grid(alpha=0.3)
axes[2].plot(scan['k'], scan['max_cluster_share'], 'o-', color='#13315C')
axes[2].axhline(0.55, color='crimson', ls='--', lw=1, label='disqualifying threshold')
axes[2].set_title('Max cluster share'); axes[2].set_xlabel('k')
axes[2].legend(); axes[2].grid(alpha=0.3)
fig.suptitle('K-Means model selection diagnostics', y=1.02)
fig.tight_layout(); fig.savefig(FIG_DIR/'kmeans_scan.png', bbox_inches='tight'); plt.show()

k_best = suggest_k(scan, max_imbalance=0.55)
print(f'Chosen k = {k_best} (highest silhouette among non-degenerate splits)')"""))

cells.append(md("## 5. Fit the chosen models and compare them"))

cells.append(code("""_, km_labels = fit_kmeans(Xp, k=k_best)
ag_labels = fit_agglomerative(Xp, k=k_best)

kd = k_distance_curve(Xp, k=5)
eps = float(np.percentile(kd, 90))
db_labels = fit_dbscan(Xp, eps=eps, min_samples=5)

print(f'K-Means    silhouette = {silhouette_score(Xp, km_labels):.3f}, sizes = {sorted(pd.Series(km_labels).value_counts().tolist(), reverse=True)}')
print(f'Agglom     silhouette = {silhouette_score(Xp, ag_labels):.3f}, sizes = {sorted(pd.Series(ag_labels).value_counts().tolist(), reverse=True)}')
if len(set(db_labels)) > 1 and (db_labels != -1).sum() > 5:
    mask = db_labels != -1
    print(f'DBSCAN     silhouette = {silhouette_score(Xp[mask], db_labels[mask]):.3f}, '
          f'noise = {(db_labels == -1).sum()}, sizes = {sorted(pd.Series(db_labels[mask]).value_counts().tolist(), reverse=True)}')
else:
    print('DBSCAN: not enough structure (mostly noise) -- expected; lifecycle data is dense')

print(f'ARI(KMeans, Agglomerative) = {adjusted_rand_score(km_labels, ag_labels):.3f}')
print('  -> high ARI means the two methods agree on the partition; the structure is real, not algorithm-dependent.')"""))

cells.append(md("""**Validation against ground truth (synthetic data only).**

Because we're developing on synthetic data with known archetype labels, we can compute ARI vs ground truth — this proves the pipeline works. *Skip this cell when running on real data.*"""))

cells.append(code("""if '_true_archetype' in features.columns:
    truth = features['_true_archetype']
    print(f'ARI(KMeans, ground truth) = {adjusted_rand_score(truth, km_labels):.3f}')
    print()
    print('Cross-tab (rows = ground-truth archetype, cols = predicted cluster):')
    print(pd.crosstab(truth, pd.Series(km_labels, index=features.index, name='cluster'),
                      margins=True))"""))

cells.append(md("## 6. Profile clusters"))

cells.append(code("""features = features.assign(cluster=km_labels)
prof = profile_clusters(features.drop(columns=['cluster']), km_labels)

interesting = [
    'peak_views_per_hour', 'mean_views_per_hour', 'half_life_hours',
    'chart_presence_ratio', 'returned_count', 'days_observed_on_chart',
    'mean_like_view_ratio', 'mean_comment_view_ratio',
    'duration_seconds', 'tag_count', 'channel_subs',
]
interesting = [c for c in interesting if c in prof.columns]
prof[interesting].round(2)"""))

cells.append(md("### Hero visual #1 — Cluster fingerprint heatmap"))

cells.append(code("""fig, ax = plt.subplots(figsize=(11, max(3, 0.45*k_best + 1)))
data = prof[interesting].values
im = ax.imshow(data, cmap='RdBu_r', vmin=-1.5, vmax=1.5, aspect='auto')
ax.set_xticks(range(len(interesting)))
ax.set_xticklabels([c.replace('_', ' ') for c in interesting], rotation=35, ha='right')
ax.set_yticks(range(k_best))
ax.set_yticklabels([f'Cluster {i}' for i in range(k_best)])
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        v = data[i, j]
        ax.text(j, i, f'{v:+.1f}', ha='center', va='center',
                color='white' if abs(v) > 0.9 else '#222', fontsize=8)
fig.colorbar(im, ax=ax, label='z-score vs all videos', shrink=0.8)
ax.set_title('Cluster fingerprint: feature z-scores per cluster', fontsize=11)
fig.tight_layout(); fig.savefig(FIG_DIR/'cluster_fingerprint.png', bbox_inches='tight'); plt.show()"""))

cells.append(md("""### Naming the archetypes

Read each row of the fingerprint and pick a name:
- High peak velocity + low half-life + low like/view -> **Firework**
- Low velocity + long half-life + high like/view + long duration -> **Marathon**
- Returned-count > 0 + medium velocity -> **Drumbeat**
- High velocity + LOW like/view + high tag count -> **Megaphone**
- Very short duration + high like/view + fast cycle -> **Snack**

Edit the `cluster_names` dict below after inspecting the fingerprint output."""))

cells.append(code("""# TODO: Edit this after inspecting the fingerprint heatmap above
cluster_names = {i: f'Cluster {i}' for i in range(k_best)}
# Example: cluster_names = {0: 'Firework', 1: 'Marathon', 2: 'Drumbeat', 3: 'Megaphone', 4: 'Snack'}

features['archetype'] = features['cluster'].map(cluster_names)
features.groupby('archetype').size().to_frame('n')"""))

cells.append(md("""### Top representative videos per cluster

For each cluster, find the videos closest to the centroid — these are the 'poster children' for the archetype."""))

cells.append(code("""first_snap = (snapshots.sort_values('snapshot_ts')
                        .groupby('video_id').first())

centroids = np.array([Xp[km_labels == c].mean(axis=0) for c in range(k_best)])
for c in range(k_best):
    mask = km_labels == c
    pts = Xp[mask]
    ids = features.index[mask]
    d = euclidean_distances(pts, centroids[c:c+1]).ravel()
    nearest = ids[np.argsort(d)[:3]]
    print(f'Cluster {c} ({cluster_names.get(c, "?")}, n={mask.sum()}):')
    for vid in nearest:
        if vid in first_snap.index:
            row = first_snap.loc[vid]
            title_str = str(row['title'])
            title = (title_str[:80] + '...') if len(title_str) > 80 else title_str
            print(f'  - {title}  [{row["channel_title"]}]')
    print()"""))

cells.append(md("""## 7. Hero visual #2 — Per-cluster lifecycle curves

For each cluster, plot the average view-count trajectory over time. This is the visual that makes the archetypes *click* — Marathon plateaus, Firework spikes-and-dies, Drumbeat re-enters, etc."""))

cells.append(code("""colors = plt.cm.tab10.colors

snap = snapshots.copy()
snap['snapshot_ts'] = pd.to_datetime(snap['snapshot_ts'], utc=True).dt.tz_convert(None)
snap = snap.merge(features[['cluster']], left_on='video_id', right_index=True)

snap = snap.sort_values(['video_id', 'snapshot_ts'])
snap['t0'] = snap.groupby('video_id')['snapshot_ts'].transform('min')
snap['hours_in'] = (snap['snapshot_ts'] - snap['t0']).dt.total_seconds() / 3600
snap['view_norm'] = snap.groupby('video_id')['view_count'].transform(
    lambda v: v / v.max() if v.max() > 0 else v
)

ncols = min(k_best, 4); nrows = int(np.ceil(k_best / ncols))
fig, axes = plt.subplots(nrows, ncols, figsize=(3.0*ncols, 2.6*nrows),
                         sharex=True, sharey=True)
axes = np.array(axes).reshape(-1)
for c in range(k_best):
    ax = axes[c]
    sub = snap[snap['cluster'] == c]
    for vid, grp in sub.groupby('video_id'):
        ax.plot(grp['hours_in'], grp['view_norm'],
                color=colors[c % 10], alpha=0.10, lw=0.7)
    if not sub.empty and sub['hours_in'].max() > 0:
        bins = np.arange(0, sub['hours_in'].max() + 12, 12)
        if len(bins) > 1:
            sub2 = sub.assign(bin=pd.cut(sub['hours_in'], bins, include_lowest=True))
            means = sub2.groupby('bin', observed=True)['view_norm'].mean()
            centers = [iv.mid for iv in means.index]
            ax.plot(centers, means.values, color=colors[c % 10], lw=2.4)
    ax.set_title(f'{cluster_names.get(c, f"Cluster {c}")}  (n={(km_labels==c).sum()})',
                 fontsize=10)
    ax.grid(alpha=0.3); ax.set_ylim(0, 1.05)
for ax in axes[k_best:]:
    ax.set_visible(False)
fig.supxlabel('Hours since first appearance on trending', fontsize=10)
fig.supylabel('Views (normalized)', fontsize=10)
fig.suptitle('Lifecycle curves by archetype', fontsize=12, y=1.02)
fig.tight_layout(); fig.savefig(FIG_DIR/'lifecycle_curves.png', bbox_inches='tight'); plt.show()"""))

cells.append(md("""## 8. Hero visual #3 — 2D embedding map

UMAP projection of all videos, coloured by archetype. *This is the title-page visual of the deck.*"""))

cells.append(code("""emb = umap_embed(Xp, n_neighbors=15)

fig, ax = plt.subplots(figsize=(8, 6.5))
for c in range(k_best):
    mask = km_labels == c
    ax.scatter(emb[mask, 0], emb[mask, 1],
               s=24, alpha=0.75, color=colors[c % 10],
               edgecolor='white', lw=0.3,
               label=f'{cluster_names.get(c, f"Cluster {c}")} (n={mask.sum()})')
    cx, cy = emb[mask, 0].mean(), emb[mask, 1].mean()
    ax.annotate(cluster_names.get(c, f'C{c}'), (cx, cy),
                fontsize=11, fontweight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', fc='white',
                          ec=colors[c % 10], lw=1.5, alpha=0.9))
ax.set_xticks([]); ax.set_yticks([])
ax.set_title('Trending video archetypes - UMAP projection', fontsize=12)
ax.legend(loc='best', fontsize=8, framealpha=0.9)
for spine in ax.spines.values(): spine.set_visible(False)
fig.tight_layout(); fig.savefig(FIG_DIR/'umap_map.png', bbox_inches='tight'); plt.show()"""))

cells.append(md("""## 9. Association mining on tag baskets

Apriori on the tags of each video. We filter to the top-80 most-common tags first to keep the search tractable, and require lift >= 1.5 for an interesting rule."""))

cells.append(code("""baskets = build_tag_baskets(snapshots, features.index)
rules = mine_rules(baskets, min_support=0.05, min_confidence=0.4, min_lift=1.5)
print(f'Rules found: {len(rules)}')
if not rules.empty:
    show = ['antecedents', 'consequents', 'support', 'confidence', 'lift']
    print('Top 15 by lift:')
    print(rules[show].head(15).to_string(index=False))"""))

cells.append(md("""### Per-cluster distinctive tags (lift)

Which tags are characteristic of each cluster, vs being generic across all videos?"""))

cells.append(code("""from collections import Counter
video_tags = (snapshots.sort_values('snapshot_ts')
                       .groupby('video_id')['tags'].first()
                       .fillna('')
                       .map(lambda s: set(t for t in s.split('|') if t)))
video_tags = video_tags.loc[features.index]

all_tag_count = Counter(t for tags in video_tags for t in tags)
n_total = len(video_tags)
p_overall = {t: c/n_total for t, c in all_tag_count.items()}

for c in range(k_best):
    in_cluster = video_tags[features['cluster'] == c]
    n_c = len(in_cluster)
    if n_c == 0: continue
    cluster_tag_count = Counter(t for tags in in_cluster for t in tags)
    rows = []
    for t, k in cluster_tag_count.items():
        if k < 3: continue
        p_in = k / n_c
        lift = p_in / p_overall[t]
        if lift > 1.5:
            rows.append((t, k, p_in, lift))
    rows.sort(key=lambda r: -r[3])
    name = cluster_names.get(c, f'Cluster {c}')
    print(f'{name} (n={n_c}) - distinctive tags (lift > 1.5):')
    for t, k, p, lift in rows[:8]:
        print(f'  {t:<25s}  in {k}/{n_c} videos  ({p:.1%}, lift={lift:.2f})')
    print()"""))

cells.append(md("## 10. Save outputs for the deck"))

cells.append(code("""out = features.copy()
out.to_csv('../data/videos_with_clusters.csv')
if not rules.empty:
    rules.head(50).to_csv('../data/top_association_rules.csv', index=False)
print('Saved: videos_with_clusters.csv, top_association_rules.csv')
print(f'Figures saved to: {FIG_DIR}')"""))


nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NB.write_text(json.dumps(nb, indent=1))
print(f"Wrote {NB} ({len(cells)} cells)")


# =====================================================================
# Feature engineering notebook
# =====================================================================

NB2 = Path(__file__).resolve().parent.parent / "notebooks" / "01_feature_engineering.ipynb"

cells2 = []

cells2.append(md("""# Feature Engineering: Long Snapshots -> Per-Video Lifecycle Features

**UGDSAI 29 · Group 4 · Aaryan, Daksh, Mayank**

This notebook implements Anant's directive: cluster at the **video level** using lifecycle-derived features, not at the (video, timestamp) level.

**Input:** `data/master_snapshots.csv` (long format, one row per snapshot observation)
**Output:** `data/videos_features.csv` (wide format, one row per unique video, 25+ engineered features)

**Feature themes (matching Anant's note):**
1. Velocity — how fast it grew
2. Decay — how fast it died
3. Retention — sticky vs flash
4. Engagement — audience response
5. Content & metadata — what the video itself is

The actual feature engineering logic lives in `scripts/features.py` so it can be unit-tested and re-used. This notebook is a thin walkthrough that calls into it.

## Switching from synthetic to real data

Change `INPUT_CSV` below to `'../data/master_snapshots.csv'` once collection has produced enough rows. Everything else just works."""))

cells2.append(code("""import sys; sys.path.insert(0, '../scripts')
import warnings; warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from features import build_features

pd.set_option('display.max_columns', 60)

# === SWITCH HERE WHEN REAL DATA IS READY ===
INPUT_CSV = '../data/master_snapshots_synthetic.csv'   # synthetic for dev
# INPUT_CSV = '../data/master_snapshots.csv'           # real data
OUTPUT_CSV = '../data/videos_features.csv'"""))

cells2.append(md("## 1. Load and understand the raw data"))

cells2.append(code("""df = pd.read_csv(INPUT_CSV)
print(f'Rows: {len(df):,}')
print(f'Unique videos: {df["video_id"].nunique():,}')
print(f'Snapshots: {df["snapshot_ts"].nunique()}')
df.head(3)"""))

cells2.append(code("""obs_per_video = df.groupby('video_id').size()
print('Observations per video:')
print(obs_per_video.describe().round(2))
print()
print('Videos seen N times:')
print(obs_per_video.value_counts().sort_index())"""))

cells2.append(md("""**Decision:** keep videos with **>= 2 snapshots** so velocity/decay are computable. Videos seen only once go to a singletons file for completeness but don't enter the clustering matrix."""))

cells2.append(md("""## 2. Run feature engineering

The work is encapsulated in `scripts/features.py` — `build_features()` takes the long-format DataFrame and returns the wide per-video matrix. This separates the *logic* (the script, version-controlled and testable) from the *narrative* (this notebook)."""))

cells2.append(code("""features = build_features(df, min_obs=2)
print(f'Feature matrix: {features.shape[0]} videos x {features.shape[1]} features')
print()
print('Missing values per column (top 10):')
print(features.isna().sum().sort_values(ascending=False).head(10))"""))

cells2.append(md("""## 3. Inspect the 5 themes

Group features by what they measure. This grouping is exactly how we'll explain them to the panel."""))

cells2.append(code("""themes = {
    'Velocity':   ['peak_views_per_hour', 'mean_views_per_hour', 'hours_to_first_trend'],
    'Decay':      ['decay_log_slope_48h', 'half_life_hours', 'days_observed_on_chart'],
    'Retention':  ['chart_presence_ratio', 'rank_volatility', 'returned_count'],
    'Engagement': ['mean_like_view_ratio', 'mean_comment_view_ratio',
                   'comment_like_ratio', 'engagement_growth'],
    'Content':    ['duration_seconds', 'is_short', 'title_length', 'title_caps_ratio',
                   'title_has_emoji', 'title_has_question', 'tag_count',
                   'mean_tag_length', 'description_length',
                   'category_id', 'channel_subs', 'channel_size_bucket', 'language'],
}
for theme, cols in themes.items():
    cols_present = [c for c in cols if c in features.columns]
    print(f'  {theme:11s} ({len(cols_present)} features): {cols_present}')"""))

cells2.append(md("## 4. Sanity check — feature distributions"))

cells2.append(code("""key_features = [
    'peak_views_per_hour', 'decay_log_slope_48h', 'chart_presence_ratio',
    'mean_like_view_ratio', 'duration_seconds', 'tag_count',
]

fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for ax, col in zip(axes.flat, key_features):
    features[col].dropna().hist(bins=40, ax=ax, color='#13315C', alpha=0.85)
    ax.set_title(col, fontsize=10)
    ax.grid(alpha=0.3)
fig.suptitle('Feature distributions - sanity check', fontsize=12)
fig.tight_layout(); plt.show()"""))

cells2.append(md("## 5. Save and we're done"))

cells2.append(code("""features.to_csv(OUTPUT_CSV)
print(f'Saved -> {OUTPUT_CSV}')
print(f'Shape: {features.shape}')
features.head()"""))

nb2 = {
    "cells": cells2,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NB2.write_text(json.dumps(nb2, indent=1))
print(f"Wrote {NB2} ({len(cells2)} cells)")
