# UGDSAI 29 — Group 4

**Project:** What Goes Viral in India? A Longitudinal Study of YouTube Trending
**Members:** Aaryan, Daksh, Mayank
**Faculty:** Mr. Anant Mittal
**Presentation:** Wednesday 13 May 2026 · 10–12 minutes + Q&A

---

## Submission deliverables

| File | Purpose |
|---|---|
| **`Group_4.pdf`** | The 12-slide deck. Pitch-quality, 16:9, brand palette. |
| **`docs/SPEAKER_NOTES.md`** | What to say on each slide, slide-by-slide, with timing budget. |
| **`docs/QA_PREP.md`** | 25 likely faculty questions with rehearsed answers. **Read this Tuesday night.** |
| **`docs/PROJECT_PLAN.md`** | The methodology document (the v2 plan after Anant's feedback). |
| **This repository** | Full reproducible pipeline. |

---

## What the project found

On 9,100 unique videos from 7 months of Indian YouTube trending data, **six clusters emerge** with K-Means agreeing with Agglomerative at ARI = 0.55:

| Archetype | n | Defining feature (z-score) |
|---|---|---|
| **Firework** | 1,598 | Sustained big hits — Punjabi music drops |
| **Beloved** | 1,132 | +2.1 like/view — Tech creators, regional comedy |
| **Marathon** | 1,119 | +2.0 chart presence — Tamil daily soaps |
| **Drumbeat** | 112 | +6.5 returned-count — News cycles |
| **Flash** | 3,693 | Residual catchall (no distinctive lifecycle) |
| **Standard** | 1,446 | Baseline trender |

Association mining on tag baskets independently surfaces the same archetypes — Punjabi songs ↔ Firework, Technical Guruji ↔ Beloved, Priyamanaval ↔ Marathon, Telugu News ↔ Drumbeat. **Two unsupervised methods, two different feature spaces, one partition.**

---

## What's in this repository

```
youtube_project/
├── Group_4.pdf                                ← submission deck
├── README.md                                  ← you are here
├── docs/
│   ├── SPEAKER_NOTES.md                       ← slide-by-slide script
│   ├── QA_PREP.md                             ← 25 anticipated questions
│   ├── PROJECT_PLAN.md                        ← v2 plan post-Anant feedback
│   ├── HYBRID_DATA_PLAN.md                    ← live + archival strategy
│   ├── SETUP.md                               ← collector installation
│   └── figures/                               ← 8 deck-quality PNGs
├── scripts/
│   ├── collect.py                             ← live YouTube API collector
│   ├── load_archival.py                       ← Kaggle dataset adapter
│   ├── make_synthetic_data.py                 ← test-data generator
│   ├── features.py                            ← 25 lifecycle features
│   ├── analysis.py                            ← scaling/PCA/clustering/Apriori
│   ├── _build_notebooks.py                    ← regenerate notebooks
│   ├── _make_deck_figures.py                  ← regenerate deck figures
│   └── _build_deck.py                         ← regenerate Group_4.pdf
├── notebooks/
│   ├── 01_feature_engineering.ipynb           ← long → wide pipeline
│   └── 02_analysis.ipynb                      ← clustering & visuals
├── data/
│   ├── master_snapshots_archival.csv          ← 37,352 rows from 7 months
│   ├── videos_features.csv                    ← per-video feature matrix
│   └── _deck_*.json                           ← derived metadata
└── .github/workflows/collect.yml              ← cloud cron for live collection
```

---

## Final-week checklist

| Day | Task |
|---|---|
| **Sun (today)** | Read `QA_PREP.md` end-to-end. Each member picks 5 questions to answer aloud in front of a mirror. |
| **Mon** | First full dry-run, untimed. Don't worry about pace — focus on flow. |
| **Tue** | Two timed dry-runs. Target: 11:00 minutes. Hard limit: 12:00. Do them in the room you'll present in if possible. |
| **Tue night** | `Group_4.pdf` on USB stick + Drive + email — three copies. Speaker notes printed. |
| **Wed** | Arrive 30 min early. Test the projector. Take a deep breath. |

---

## How to regenerate everything

If you change `data/master_snapshots_*.csv` (e.g. when fresh live data arrives):

```bash
# 1. Regenerate the deck figures (uses real data)
python scripts/_make_deck_figures.py

# 2. Rebuild Group_4.pdf
python scripts/_build_deck.py

# 3. Optionally rebuild notebooks
python scripts/_build_notebooks.py
```

Total runtime: ~30 seconds.
