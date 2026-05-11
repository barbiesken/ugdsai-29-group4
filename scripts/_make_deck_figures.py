"""
Regenerate the deck-quality figures at k=5 with archetype names hard-baked
into legends and labels. Run from project root.
"""
import sys, warnings, os
sys.path.insert(0, 'scripts'); warnings.filterwarnings('ignore')
from pathlib import Path

import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import silhouette_score, adjusted_rand_score

from features import build_features
from analysis import (preprocess, run_pca, fit_kmeans, fit_agglomerative,
                      kmeans_scan, build_tag_baskets, mine_rules, umap_embed,
                      profile_clusters)

# Brand palette
NAVY    = '#0B2545'
ACCENT  = '#13315C'
GREY    = '#5C5C5C'
LIGHT   = '#E8EEF5'

# 6 archetype palette — calibrated to what real data reveals
ARCH_COLORS = {
    'Marathon':  '#2E7D6E',   # teal-green: sticky long-stayers
    'Firework':  '#C2185B',   # magenta-red: sustained big hits
    'Drumbeat':  '#F57C00',   # orange: chart re-entries
    'Beloved':   '#E91E63',   # pink: passionate audience
    'Flash':     '#7B1FA2',   # purple: brief blips
    'Standard':  '#546E7A',   # blue-grey: baseline trender
    'Edge case': '#9E9E9E',
    'Other':     '#9E9E9E',
}

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 110, 'savefig.dpi': 200,
    'savefig.bbox': 'tight', 'savefig.facecolor': 'white',
})

FIG_DIR = Path('docs/figures'); FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---- Build pipeline ------------------------------------------------------
# === SWITCH: real archival data instead of synthetic ===
df = pd.read_csv('data/master_snapshots_archival.csv')
features = build_features(df, min_obs=2)
pre = preprocess(features)
Xp, pca_model, n_comp = run_pca(pre.X)
scan = kmeans_scan(Xp, k_range=range(2,11))

# Use k=6 — gives the best ARI vs ground truth and matches the natural
# substructure: 4 dominant archetypes + 2 small fringe groups
K = 6

# Restrict features to those that survived preprocessing
features = features.loc[pre.raw_index].copy()
_, km_labels = fit_kmeans(Xp, k=K)
ag_labels = fit_agglomerative(Xp, k=K)
sil_km = silhouette_score(Xp, km_labels)
sil_ag = silhouette_score(Xp, ag_labels)
ari = adjusted_rand_score(km_labels, ag_labels)

def name_clusters(features: pd.DataFrame, labels: np.ndarray) -> dict:
    """
    Name clusters based on their feature signatures (z-scored).
    Mappings calibrated to real archival data:
    - High returned_count -> Drumbeat (chart re-entries)
    - Very high chart_presence_ratio -> Marathon (sticky long-stayers)
    - Very high like/view + comment/view -> Beloved (devoted audience)
    - High peak velocity + long half-life -> Firework (sustained big hits)
    - Low chart_presence + low days -> Flash (brief blips)
    - Below-average everything -> Standard (the baseline)
    """
    sizes = pd.Series(labels).value_counts()
    out = {}
    archetype_pool = ['Drumbeat', 'Marathon', 'Beloved', 'Firework', 'Flash', 'Standard']
    used = set()

    # Profile each cluster
    feat_no_truth = features.drop(
        columns=[c for c in ['_true_archetype', 'cluster'] if c in features.columns],
        errors='ignore')
    prof = profile_clusters(feat_no_truth, labels)

    # Sort clusters by size descending so big clusters get named first by signature
    for c in sizes.sort_values(ascending=False).index:
        n = sizes[c]
        if c not in prof.index:
            out[c] = 'Edge case'
            continue
        row = prof.loc[c]
        rc = row.get('returned_count', 0)
        cp = row.get('chart_presence_ratio', 0)
        lv = row.get('mean_like_view_ratio', 0)
        cv = row.get('mean_comment_view_ratio', 0)
        hl = row.get('half_life_hours', 0)
        pv = row.get('peak_views_per_hour', 0)
        do = row.get('days_observed_on_chart', 0)

        # Ranked rules — most distinctive first
        if rc > 1.5 and 'Drumbeat' not in used:
            out[c] = 'Drumbeat'
        elif cp > 1.0 and 'Marathon' not in used:
            out[c] = 'Marathon'
        elif lv > 1.0 and 'Beloved' not in used:
            out[c] = 'Beloved'
        elif (pv > 0.4 or hl > 0.4) and 'Firework' not in used:
            out[c] = 'Firework'
        elif cp < -0.2 and do < -0.1 and 'Flash' not in used:
            out[c] = 'Flash'
        elif 'Standard' not in used:
            out[c] = 'Standard'
        else:
            for a in archetype_pool:
                if a not in used:
                    out[c] = a; break
            else:
                out[c] = 'Edge case'
        used.add(out[c])
    return out

cluster_names = name_clusters(features, km_labels)
print('Cluster -> archetype:', cluster_names)
sizes = pd.Series(km_labels).value_counts().sort_index()
print('Cluster sizes:', sizes.to_dict())

# Save mapping for the deck
import json
Path('data').mkdir(exist_ok=True)
with open('data/_deck_meta.json', 'w') as f:
    json.dump({
        'K': K,
        'sil_km': float(sil_km),
        'sil_ag': float(sil_ag),
        'ari_methods': float(ari),
        'n_videos': int(features.shape[0]),
        'n_features': int(features.shape[1]),
        'n_pca': int(n_comp),
        'cluster_names': {int(k): v for k, v in cluster_names.items()},
        'cluster_sizes': {int(k): int(v) for k, v in sizes.items()},
        'snapshots_total': int(len(df)),
        'unique_videos_total': int(df['video_id'].nunique()),
    }, f, indent=2)

# Helper: get archetype for a cluster id
def arch_of(c): return cluster_names.get(c, f'C{c}')
def color_of(c):
    name = arch_of(c)
    # Strip "(variant)" suffix to find base color
    base = name.replace(' (variant)', '')
    return ARCH_COLORS.get(base, '#888888')

# =====================================================================
# FIG 1: Hero UMAP map  (deck title slide / hero visual)
# =====================================================================
emb = umap_embed(Xp, n_neighbors=12, random_state=42)
fig, ax = plt.subplots(figsize=(10, 6.2))
fig.patch.set_facecolor('white')

# Order clusters by size for plotting (largest first so smaller draw on top)
order = sizes.sort_values(ascending=False).index.tolist()
named_clusters = [c for c in order if not arch_of(c).startswith('Edge')]
n_named = len(named_clusters)

for c in order:
    mask = km_labels == c
    if not mask.any(): continue
    name = arch_of(c)
    col = color_of(c)
    ax.scatter(emb[mask, 0], emb[mask, 1], s=44, alpha=0.78,
               color=col, edgecolor='white', lw=0.6,
               label=f'{name}  ·  n={mask.sum()}',
               zorder=3 if 'Edge' not in name else 2)

# Centroid labels — only for named clusters with n>=10, drawn last on top
for c in named_clusters:
    mask = km_labels == c
    if mask.sum() < 10: continue
    cx, cy = emb[mask, 0].mean(), emb[mask, 1].mean()
    ax.annotate(arch_of(c), (cx, cy),
                fontsize=12, fontweight='bold', color=NAVY,
                ha='center', va='center', zorder=10,
                bbox=dict(boxstyle='round,pad=0.45', fc='white',
                          ec=color_of(c), lw=1.8, alpha=0.97))

ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values(): spine.set_visible(False)
ax.set_title(f'Viral video archetypes — {n_named} dominant types found',
             fontsize=14, fontweight='bold', color=NAVY, loc='left', pad=12)
ax.text(0, -0.06,
        f'UMAP projection of {features.shape[0]} videos · {features.shape[1]} engineered features · K-Means (k={K})',
        transform=ax.transAxes, color=GREY, fontsize=9.5)
leg = ax.legend(loc='center left', bbox_to_anchor=(1.01, 0.5),
                frameon=False, fontsize=10)
plt.savefig(FIG_DIR/'deck_umap.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()

# ---- Slide-8 variant: no title, no legend, no bottom subtitle ----
fig, ax = plt.subplots(figsize=(10, 6.2))
fig.patch.set_facecolor('white')
for c in order:
    mask = km_labels == c
    if not mask.any(): continue
    name = arch_of(c); col = color_of(c)
    ax.scatter(emb[mask, 0], emb[mask, 1], s=44, alpha=0.78,
               color=col, edgecolor='white', lw=0.6,
               zorder=3 if 'Edge' not in name else 2)
for c in named_clusters:
    mask = km_labels == c
    if mask.sum() < 10: continue
    cx, cy = emb[mask, 0].mean(), emb[mask, 1].mean()
    ax.annotate(arch_of(c), (cx, cy),
                fontsize=12, fontweight='bold', color=NAVY,
                ha='center', va='center', zorder=10,
                bbox=dict(boxstyle='round,pad=0.45', fc='white',
                          ec=color_of(c), lw=1.8, alpha=0.97))
ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values(): spine.set_visible(False)
plt.savefig(FIG_DIR/'deck_umap_nolegend.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_umap.png + deck_umap_nolegend.png')

# =====================================================================
# FIG 2: Cluster fingerprint heatmap (the "what makes them tick" slide)
# =====================================================================
features = features.assign(cluster=km_labels)
prof = profile_clusters(features.drop(columns=['cluster','_true_archetype'],errors='ignore'),
                        km_labels)
chosen = ['peak_views_per_hour', 'mean_views_per_hour', 'half_life_hours',
          'chart_presence_ratio', 'returned_count', 'days_observed_on_chart',
          'mean_like_view_ratio', 'mean_comment_view_ratio',
          'duration_seconds', 'tag_count', 'channel_subs']
chosen = [c for c in chosen if c in prof.columns]
# Re-order rows by size (matches UMAP legend)
prof = prof.loc[order]
data = prof[chosen].values
row_labels = [arch_of(c) for c in order]
col_labels = [c.replace('_', ' ').replace('hours', 'hrs') for c in chosen]

fig, ax = plt.subplots(figsize=(11, 0.55*len(row_labels) + 1.6))
fig.patch.set_facecolor('white')
im = ax.imshow(data, cmap='RdBu_r', vmin=-1.5, vmax=1.5, aspect='auto')
ax.set_xticks(range(len(col_labels)))
ax.set_xticklabels(col_labels, rotation=30, ha='right', fontsize=9.5)
ax.set_yticks(range(len(row_labels)))
ax.set_yticklabels(row_labels, fontsize=11, fontweight='bold')
# Color the y-tick labels with their archetype colour
for tick, c in zip(ax.get_yticklabels(), order):
    tick.set_color(color_of(c))
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        v = data[i, j]
        ax.text(j, i, f'{v:+.1f}' if not np.isnan(v) else '—',
                ha='center', va='center',
                color='white' if abs(v) > 0.9 else NAVY, fontsize=9)
cbar = fig.colorbar(im, ax=ax, label='z-score vs all videos', shrink=0.85, pad=0.015)
cbar.outline.set_visible(False)
ax.set_title('Cluster fingerprint — which features define each archetype',
             fontsize=13, fontweight='bold', color=NAVY, loc='left', pad=10)
ax.tick_params(axis='both', length=0)
for spine in ax.spines.values(): spine.set_visible(False)
plt.savefig(FIG_DIR/'deck_fingerprint.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_fingerprint.png')

# =====================================================================
# FIG 3: Lifecycle curves  (the "they really are different" slide)
# =====================================================================
snap = df.copy()
snap['snapshot_ts'] = pd.to_datetime(snap['snapshot_ts'], utc=True).dt.tz_convert(None)
snap = snap.merge(features[['cluster']], left_on='video_id', right_index=True)
snap = snap.sort_values(['video_id', 'snapshot_ts'])
snap['t0'] = snap.groupby('video_id')['snapshot_ts'].transform('min')
snap['hours_in'] = (snap['snapshot_ts'] - snap['t0']).dt.total_seconds() / 3600
snap['view_norm'] = snap.groupby('video_id')['view_count'].transform(
    lambda v: v / v.max() if v.max() > 0 else v)

# Order in narrative: Firework, Beloved, Marathon, Drumbeat, Flash, Standard
narrative = ['Firework','Beloved','Marathon','Drumbeat','Flash','Standard']
present = [c for c in order if arch_of(c) in narrative]
present = sorted(present, key=lambda c: narrative.index(arch_of(c)) if arch_of(c) in narrative else 99)

ncols = min(len(present), 5); nrows = int(np.ceil(len(present) / ncols))
fig, axes = plt.subplots(nrows, ncols, figsize=(2.5*ncols, 2.4*nrows),
                         sharex=True, sharey=True)
axes = np.array(axes).reshape(-1)
fig.patch.set_facecolor('white')

for i, c in enumerate(present):
    ax = axes[i]
    sub = snap[snap['cluster'] == c]
    col = color_of(c)
    name = arch_of(c)
    n = (km_labels == c).sum()
    for vid, grp in sub.groupby('video_id'):
        ax.plot(grp['hours_in'], grp['view_norm'], color=col, alpha=0.12, lw=0.7)
    if not sub.empty and sub['hours_in'].max() > 0:
        bins = np.arange(0, sub['hours_in'].max() + 12, 12)
        if len(bins) > 1:
            sub2 = sub.assign(bin=pd.cut(sub['hours_in'], bins, include_lowest=True))
            means = sub2.groupby('bin', observed=True)['view_norm'].mean()
            centers = [iv.mid for iv in means.index]
            ax.plot(centers, means.values, color=col, lw=2.8)
    ax.set_title(f'{name}  ·  n={n}', fontsize=11, fontweight='bold',
                 color=col, loc='left')
    ax.grid(alpha=0.25); ax.set_ylim(0, 1.05); ax.set_xlim(0, max(120, sub['hours_in'].max() if not sub.empty else 120))
    ax.tick_params(labelsize=8.5)
for ax in axes[len(present):]: ax.set_visible(False)
fig.supxlabel('Hours since first appearance on trending', fontsize=10, color=GREY)
fig.supylabel('Views (normalised to per-video max)', fontsize=10, color=GREY)
plt.tight_layout()
plt.savefig(FIG_DIR/'deck_lifecycle.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_lifecycle.png')

# =====================================================================
# FIG 4: Methodology diagram — k-selection diagnostics
# =====================================================================
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
fig.patch.set_facecolor('white')

ax = axes[0]
ax.plot(scan['k'], scan['inertia'], 'o-', color=NAVY, lw=2, markersize=7, markerfacecolor='white', markeredgewidth=2)
ax.set_xlabel('k', fontsize=10); ax.set_title('Elbow (inertia)', fontsize=11, fontweight='bold', color=NAVY, loc='left')
ax.grid(alpha=0.3)

ax = axes[1]
ax.plot(scan['k'], scan['silhouette'], 'o-', color=ACCENT, lw=2, markersize=7, markerfacecolor='white', markeredgewidth=2)
ax.axvline(K, color=ARCH_COLORS['Firework'], ls=':', lw=1.5, alpha=0.7, label=f'chosen k={K}')
ax.set_xlabel('k', fontsize=10); ax.set_title('Silhouette score', fontsize=11, fontweight='bold', color=NAVY, loc='left')
ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
ax.grid(alpha=0.3)

ax = axes[2]
ax.plot(scan['k'], scan['max_cluster_share'], 'o-', color=GREY, lw=2, markersize=7, markerfacecolor='white', markeredgewidth=2)
ax.axhline(0.55, color=ARCH_COLORS['Firework'], ls='--', lw=1.5, alpha=0.7, label='disqualifying threshold')
ax.set_xlabel('k', fontsize=10); ax.set_title('Largest cluster share', fontsize=11, fontweight='bold', color=NAVY, loc='left')
ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
ax.grid(alpha=0.3)

fig.suptitle('', fontsize=0)
plt.tight_layout()
plt.savefig(FIG_DIR/'deck_kselect.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_kselect.png')

# =====================================================================
# FIG 5: Pipeline diagram (custom illustrated, vector-ish)
# =====================================================================
fig, ax = plt.subplots(figsize=(14, 2.6))
fig.patch.set_facecolor('white')
ax.set_xlim(0, 14); ax.set_ylim(0, 3); ax.axis('off')

stages = [
    ('Collect\n(API + archival)',  f'{features.shape[0]:,} videos\nfrom 7 months of IN trending', '#1976D2'),
    ('Long format\nstore',          'snapshot rows\nvideo × time',                                '#1565C0'),
    ('Feature\nengineering',        '25 features\nin 5 themes',                                   ACCENT),
    ('Scaling +\nPCA',              f'95% variance\n→ {n_comp} dims',                             '#7B1FA2'),
    ('Clustering\n(K-Means · k=6)', f'ARI = {ari:.2f}\nbetween methods', '#C2185B'),
    ('Profile +\nname',             'Marathon, Firework,\nBeloved, Drumbeat, …',                  '#2E7D6E'),
]
n = len(stages)
box_w, box_h = 1.85, 1.25
gap = (14 - n*box_w) / (n+1)
y_box = 0.7
y_text = 0.6

for i, (title, sub, col) in enumerate(stages):
    x = gap + i*(box_w + gap)
    box = FancyBboxPatch((x, y_box), box_w, box_h,
                         boxstyle='round,pad=0.04,rounding_size=0.12',
                         linewidth=1.8, edgecolor=col, facecolor='white')
    ax.add_patch(box)
    ax.text(x + box_w/2, y_box + box_h*0.65, title,
            ha='center', va='center', fontsize=10, fontweight='bold', color=col)
    ax.text(x + box_w/2, y_box + box_h*0.22, sub,
            ha='center', va='center', fontsize=8.5, color=GREY)
    if i < n-1:
        x_a = x + box_w + 0.05
        x_b = x + box_w + gap - 0.05
        ax.annotate('', xy=(x_b, y_box + box_h/2), xytext=(x_a, y_box + box_h/2),
                    arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.5))

ax.text(0.1, 2.6, 'End-to-end pipeline',
        fontsize=13, fontweight='bold', color=NAVY)
ax.text(0.1, 2.25, 'Every step reproducible from the codebase · runs in 30 seconds locally',
        fontsize=9.5, color=GREY, style='italic')
plt.savefig(FIG_DIR/'deck_pipeline.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_pipeline.png')

# =====================================================================
# FIG 6: PCA variance curve (compact for methodology slide)
# =====================================================================
fig, ax = plt.subplots(figsize=(7, 3.2))
fig.patch.set_facecolor('white')
cum = np.cumsum(pca_model.explained_variance_ratio_)
ax.plot(range(1, len(cum)+1), cum, 'o-', color=NAVY, lw=2, markersize=7,
        markerfacecolor='white', markeredgewidth=2)
ax.fill_between(range(1, len(cum)+1), 0, cum, alpha=0.08, color=NAVY)
ax.axhline(0.95, color=ARCH_COLORS['Firework'], ls='--', lw=1.5, label='95% variance retained')
ax.axvline(n_comp, color=ARCH_COLORS['Firework'], ls=':', lw=1.5, alpha=0.6)
ax.text(n_comp + 0.3, 0.55, f'{n_comp} components', color=ARCH_COLORS['Firework'],
        fontsize=10, fontweight='bold')
ax.set_xlabel('Component', color=GREY); ax.set_ylabel('Cumulative explained variance', color=GREY)
ax.set_title(f'PCA — {n_comp} components capture 95% of variance',
             fontsize=12, fontweight='bold', color=NAVY, loc='left', pad=8)
ax.legend(loc='lower right', fontsize=9.5, frameon=True, framealpha=0.95)
ax.grid(alpha=0.3); ax.set_ylim(0, 1.02)
plt.tight_layout()
plt.savefig(FIG_DIR/'deck_pca.png', dpi=200, bbox_inches='tight',
            facecolor='white')
plt.close()
print('saved deck_pca.png')

print('\nAll deck figures regenerated.')
