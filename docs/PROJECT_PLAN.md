# Project Plan v2 — After Anant's Feedback

UGDSAI 29 · Group 4 · Aaryan, Daksh, Mayank
Last updated: 2 May 2026

---

## What Anant told us (and what it means)

> *"Clearly define the clustering entity. For stronger and cleaner results, consider clustering at the video level using lifecycle-derived features (velocity, decay, retention, engagement, etc.) rather than treating every timestamp as an independent datapoint."*

> *"Focus heavily on feature engineering, cluster interpretation, and visual storytelling. The final presentation will be great if the clusters clearly translate into meaningful viral archetypes."*

**Translation into our plan:**

| What he said | What we'll do |
|---|---|
| Clustering entity = one video | Long-format snapshots feed feature engineering, but the clustering matrix has one row per unique video. |
| Lifecycle features | Velocity, decay, retention, engagement — engineered by aggregating across snapshots per video. |
| Heavy feature engineering | ~25 features grouped into 5 themes; this is where most of the technical work goes. |
| Cluster interpretation | Every cluster gets a name, a one-line description, and a "poster-child" exemplar video. |
| Visual storytelling | Per-cluster lifecycle curves, a 2D embedding map, tag-cooccurrence networks. |
| Longitudinal still useful | Used as feature-engineering input AND as supplementary "how do videos in each archetype evolve over time" story. |

This document reflects all of the above.

---

## 1. Data architecture

We maintain two tables:

| Table | Grain | Used for |
|---|---|---|
| `data/master_snapshots.csv` | one row per (video_id, snapshot_ts) | feature engineering input; supplementary lifecycle plots |
| `videos_features.csv` | **one row per video** | **the clustering matrix** |

Pipeline:
```
collect.py (twice daily)
    └─> master_snapshots.csv  (long format, ~1000 rows)
           │
           ▼
    feature_engineering.ipynb
           └─> videos_features.csv  (wide format, 300–600 rows)
                  │
                  ▼
           analysis.ipynb
              ├─ scaling
              ├─ PCA
              ├─ clustering (K-Means, DBSCAN, Agglomerative)
              ├─ silhouette / elbow / ARI validation
              ├─ cluster profiling & naming
              └─ association mining on tag baskets
```

---

## 2. Feature engineering — the heart of the project

Every feature listed below is computed *per video* by aggregating across that video's snapshots. Group features by theme — this is also how we'll explain them to the panel.

### 2.1 Velocity — how fast it grew

| Feature | Definition |
|---|---|
| `peak_views_per_hour` | max of (Δviews / Δhours) across consecutive snapshots |
| `mean_views_per_hour` | mean of (Δviews / Δhours) across consecutive snapshots |
| `hours_to_first_trend` | hours from `published_at` to first snapshot the video appears in |

### 2.2 Decay — how fast it died

| Feature | Definition |
|---|---|
| `decay_log_slope_48h` | linear fit of `log(views)` vs hours over the last 48h of observations; slope |
| `half_life_hours` | hours from peak velocity to 50% of peak velocity |
| `days_observed_on_chart` | unique days the video appears in any snapshot |

### 2.3 Retention — sticky vs flash signal

| Feature | Definition |
|---|---|
| `chart_presence_ratio` | (snapshots seen) / (snapshots from publish to last seen) |
| `rank_volatility` | std-dev of `trending_rank` across snapshots |
| `returned_count` | number of times the video left and re-entered the chart |

### 2.4 Engagement — audience response

| Feature | Definition |
|---|---|
| `mean_like_view_ratio` | mean of `like_count / view_count` across snapshots |
| `mean_comment_view_ratio` | mean of `comment_count / view_count` |
| `comment_like_ratio` | comments / likes (controversy proxy) |
| `engagement_growth` | last-snapshot like/view ratio minus first-snapshot like/view ratio |

### 2.5 Content & metadata

| Feature | Definition |
|---|---|
| `duration_seconds` | parse ISO-8601 duration string |
| `is_short` | `duration_seconds <= 60` |
| `title_length` | chars in title |
| `title_caps_ratio` | uppercase letters / total letters |
| `title_has_emoji` | regex test |
| `title_has_question` | does title contain `?` |
| `tag_count` | number of pipe-separated tags |
| `mean_tag_length` | mean chars per tag |
| `description_length` | already in raw data |
| `category_id` | one-hot encoded |
| `channel_size_bucket` | nano (<10k) / micro (<100k) / mid (<1M) / large (<10M) / mega (≥10M) |
| `language` | from `default_audio_language` or detected from title |

That's 25 features. Some are correlated by design — that's fine, PCA will handle it.

---

## 3. Analysis plan

### 3.1 Scaling
- `RobustScaler` for skewed numerical features (view counts, durations)
- `StandardScaler` for ratio features
- One-hot for categorical

### 3.2 PCA
- Fit on the full feature matrix
- Decide retained dimensions by **95% explained variance** rule
- Plot cumulative variance curve (deck slide)
- Inspect top loadings of PC1, PC2 — these get verbal names like *"velocity-longevity axis"*

### 3.3 Clustering — three algorithms, compared
- **K-Means** with `k` chosen by elbow + silhouette scan from 2..10
- **DBSCAN** with `eps` chosen by k-distance plot
- **Agglomerative** (Ward linkage) with same `k` as K-Means for direct comparison

### 3.4 Validation
- Silhouette score for each algorithm
- Bootstrap silhouette: 100 resamples, report mean ± std
- ARI between K-Means and Agglomerative — reported as a "do the methods agree?" metric

### 3.5 Cluster profiling
For each cluster, compute and display:
- Size (n videos, % of total)
- Mean of every feature, plus its rank vs other clusters
- Top 5 most-representative videos (closest to centroid)
- Top 5 most-distinctive tags (highest TF-IDF over the cluster vs the rest)

### 3.6 Association mining
- Scope: video-tag baskets, all videos
- Algorithm: Apriori (start) → FP-Growth if Apriori is too slow
- Filters: support ≥ 0.05, confidence ≥ 0.5, lift ≥ 1.2
- Interpret: top-10 rules overall, plus top-3 rules *within each cluster*

---

## 4. The viral archetypes — name them now

Decide the storytelling vocabulary up front. After clustering we'll map clusters → names. If we get 4 clusters, we pick 4 names from this list. If 5, we pick 5.

| Tentative name | Hypothesised signature |
|---|---|
| **The Marathon** | low velocity, low decay, high retention, high like/view → educational, long-form |
| **The Firework** | high velocity, fast decay, low retention → news, music drops |
| **The Drumbeat** | moderate velocity, multiple chart re-entries → recurring shows, weekly creators |
| **The Megaphone** | high velocity, suspiciously flat engagement curve → promoted/engineered |
| **The Snack** | very short duration, fast cycle, high view/comment ratio → Shorts ecosystem |

Final names will be confirmed only after the clusters are profiled. Don't pre-commit.

---

## 5. Visual storytelling — the slides that close the deck

These are the four hero visuals the deck is built around. Build them first, then write the narration around them:

1. **The 2D map.** UMAP embedding of all videos, coloured by cluster, with the top 3 most-representative video thumbnails placed at each cluster centroid as small images. *Title slide vibe: "This is what virality looks like in India, May 2026."*

2. **Per-cluster lifecycle curves.** A small-multiples plot: one mini chart per cluster showing the *average* video's view-curve over time. Marathon plateaus, Firework spikes-and-dies. Visually obvious in two seconds.

3. **Cluster fingerprint heatmap.** Rows = clusters, columns = features (z-scored). Reds and blues at a glance show which features drive which cluster. This is the "what makes each archetype tick" slide.

4. **Tag co-occurrence network per cluster.** Small graphs, one per cluster, nodes = tags, edge weight = lift. Tells the story of which tag bundles "live in" each archetype.

---

## 6. Deck structure (10 minutes)

| # | Slide | Owner | Time |
|---|---|---|---|
| 1 | Title + question | All | 0:30 |
| 2 | Why this question matters | Aaryan | 0:30 |
| 3 | Data collection (longitudinal pipeline diagram) | Aaryan | 1:00 |
| 4 | Feature engineering — the 5 themes | Daksh | 1:30 |
| 5 | PCA — variance, top loadings, axes named | Daksh | 1:00 |
| 6 | Clustering — algorithm comparison + chosen `k` | Mayank | 1:00 |
| 7 | **The 2D map** (hero visual) | Mayank | 1:00 |
| 8 | **The 5 archetypes** (lifecycle curves + fingerprint) | All — one each | 2:30 |
| 9 | Association rules — what tags live where | Daksh | 0:30 |
| 10 | So what? Stakeholder takeaways | Aaryan | 0:30 |

Strict time discipline: nothing more than its allocation. Practise twice the day before.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Collector misses snapshots | GitHub Actions runs cloud-side; daily check on `run_log.csv` |
| Final video count too low (<300 unique videos) | YouTube India trending churns daily; 10 days × 50 videos × ~30% churn ≈ 350+. If short, extend collection to day 11. |
| Clusters look uninterpretable | Have a fallback: present k=3 if k=5 doesn't separate well. Better to nail 3 archetypes than to gesture at 5 noisy ones. |
| Association rules are trivial | Filter aggressively (lift ≥ 1.5, support ≥ 0.05). Show fewer, stronger rules. |
| Live demo of the map fails | Embed every chart as a static image in the PDF deck. No live Python during the 10 minutes. |

---

## 8. Definition of "done" for each phase

- **Collection:** `master_snapshots.csv` has ≥ 800 rows by day 10 morning.
- **Feature engineering:** `videos_features.csv` has ≥ 300 unique videos and 25 features, no NaNs except where genuinely missing (documented).
- **Modelling:** silhouette > 0.30 on the chosen clustering, ARI between methods reported.
- **Insights:** every cluster has a name, a one-line description, and a poster-child video.
- **Deck:** all four hero visuals are PNG-exported and embedded; deck PDF is exactly 10–12 slides; ≤ 12 minutes on dry-run.

When all five are checked off, we submit.
