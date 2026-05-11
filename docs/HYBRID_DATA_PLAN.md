# Hybrid Data Plan — Live API + Kaggle Archival

UGDSAI 29 · Group 4 · Updated 9 May 2026

We have ~4 days until the presentation. The honest play is **live collection from now until Tuesday + Kaggle archival data** combined into one analysis. This document is the playbook.

---

## Why hybrid

- 4 days of live data alone = ~80–150 unique videos. Thin for clustering.
- Kaggle archival alone = doesn't honour the proposal's "self-collected longitudinal" promise.
- **Hybrid**: 4 days of FRESH May 2026 trending data proves the live pipeline works, plus thousands of historical India trending rows give the clustering room to find archetypes.

The deck story becomes: *"We built a live collection pipeline and applied it to a larger archival dataset to surface durable patterns of viral video in India. The 4 days of live data confirms the pipeline still works on today's API."*

This is honest, methodologically defensible, and **stronger** than either alone.

---

## Step 1 — Get the live collection started TONIGHT (one person, 30 minutes)

Even if it's late, do this tonight so we have 4 full days of data by Tuesday.

1. Follow `docs/SETUP.md` Step 1 to get a YouTube API key.
2. Push the project to a GitHub repo, add `YT_API_KEY` as Actions secret.
3. Trigger the workflow manually once: Actions → "collect-trending" → "Run workflow".
4. Confirm `data/snapshots/snapshot_<date>.csv` was created.

The cron will fire automatically at 04:30 UTC and 16:30 UTC every day after that.

**By Wednesday morning:** you should have ~6–8 snapshots = 80–150 unique fresh trending videos. Stored at `data/master_snapshots.csv`.

---

## Step 2 — Get the archival dataset (one person, 10 minutes)

We're using **`rsrishav/youtube-trending-video-dataset`** on Kaggle. It's daily-updated, includes IN region, schema matches our pipeline.

### Download instructions

1. Go to <https://www.kaggle.com/datasets/rsrishav/youtube-trending-video-dataset>
2. Sign in (use any Google account; Kaggle is free)
3. Click "Download" (top-right of the dataset page)
4. You'll get a zip file. Inside it, find the **`IN_youtube_trending_data.csv`** file.
5. Copy it to: `data/archival/IN_youtube_trending_data.csv`

If that dataset is hard to access for any reason, the fallback is the older but always-mirrored **`datasnaek/youtube-new`**:
1. <https://www.kaggle.com/datasets/datasnaek/youtube-new>
2. Download → unzip → grab **`INvideos.csv`**
3. Copy to `data/archival/INvideos.csv`

The adapter handles both schemas automatically — it'll detect which one you have.

---

## Step 3 — Run the adapter (1 minute)

```bash
cd youtube_project
python scripts/load_archival.py data/archival/IN_youtube_trending_data.csv
```

(or `data/archival/INvideos.csv` if you used the fallback)

This produces `data/master_snapshots_archival.csv` in the EXACT format `collect.py` produces. The adapter:
- Detects which Kaggle schema you have
- Synthesises proper `snapshot_ts` timestamps from `trending_date`
- Computes per-snapshot `trending_rank` from view counts
- Pads the missing columns (channel_subscriber_count, duration_iso, etc.) so downstream code doesn't break

You can also limit to recent data only (recommended — older 2018 trending behaved very differently from today):

```bash
python scripts/load_archival.py data/archival/IN_youtube_trending_data.csv \
    --limit-recent-days 90 \
    --out data/master_snapshots_archival.csv
```

Or merge with live data once it's flowing:

```bash
python scripts/load_archival.py data/archival/IN_youtube_trending_data.csv \
    --limit-recent-days 90 \
    --merge data/master_snapshots.csv \
    --out data/master_snapshots_combined.csv
```

---

## Step 4 — Rerun the analysis

In `notebooks/02_analysis.ipynb`, change the input path:

```python
# OLD (synthetic)
INPUT_CSV = '../data/master_snapshots_synthetic.csv'

# NEW (combined)
INPUT_CSV = '../data/master_snapshots_combined.csv'
```

Run all cells. Inspect:
- `data/videos_features.csv` — the per-video feature matrix
- `docs/figures/*.png` — the four hero visuals
- `data/top_association_rules.csv` — the top tag co-occurrence rules

---

## Step 5 — Update the deck

The deck (`Group_4.pdf`) currently shows synthetic numbers. After Step 4 is run, regenerate:

```bash
python scripts/_make_deck_figures.py    # rebuilds figures with real data
python scripts/_build_deck.py           # rebuilds Group_4.pdf
```

The deck reads `data/_deck_meta.json` for the headline numbers (snapshot count, unique videos, ARI, etc.) so they update automatically.

**One slide needs manual editing** — `_build_deck.py` slide 11 (association rules) hardcodes the top rules from synthetic data. Open `_build_deck.py`, find the `rules = [...]` list in `slide_11()`, and replace with whatever the top 7 rules actually are from `data/top_association_rules.csv`.

---

## What to say on stage

Anant approved a self-collected longitudinal study. The honest framing is:

> *"We built and deployed a twice-daily YouTube Data API collector. Four days of live data from this past week proves the live pipeline works end-to-end on today's API. To give the clustering and association mining the volume they need to surface durable patterns, we combined those 4 fresh days with archival trending data covering [N months], also from the same YouTube Data API but pre-collected by the rsrishav community dataset. The features, methodology, and code path are identical for both — the only difference is when the API call happened."*

That's defensible, honest, and demonstrates more engineering than a pure live-only run.

---

## Timeline (4 days to presentation)

| Day | What |
|---|---|
| **Sat night** | API key + GitHub Actions live · Kaggle dataset downloaded |
| **Sun** | Run adapter, run analysis on archival-only data, see what archetypes emerge |
| **Mon** | Refine cluster naming, regenerate figures, edit slide 11 with real rules |
| **Tue** | Merge in 3 days of live data, rerun, finalise deck |
| **Tue night** | Dry-run the presentation. Time it. |
| **Wed** | Present. |

---

## What success looks like

- `data/master_snapshots_combined.csv` has > 5,000 rows
- `videos_features.csv` has > 500 unique videos with > 2 observations each
- Silhouette > 0.30 at the chosen k
- ARI between K-Means and Agglomerative > 0.7
- At least 3 archetypes are visually distinct on the UMAP map
- 10–20 association rules with lift > 2.0
- Deck dry-run lands at 10–11 minutes, leaving buffer for Q&A

If any of these miss, the deck still works — we just narrate around it. The methodology stands either way.
