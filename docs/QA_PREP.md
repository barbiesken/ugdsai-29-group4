# Q&A Prep — Group 4

**UGDSAI 29 · What Goes Viral in India? · Wednesday May 13, 2026**

This document prepares you for likely faculty questions. Each answer is short enough to deliver in 30-60 seconds. Practice saying them out loud before Wednesday — you don't need to memorize, but the structure should feel natural.

The hardest questions are at the bottom. **Read those first** — they're where points are won and lost.

---

## METHODOLOGY

### Q1. Why K-Means and not just DBSCAN?
DBSCAN was actually our third algorithm — we ran it alongside K-Means and Agglomerative. On dense lifecycle data it labels almost everything as noise because there are no clear density gaps; the data lives on a continuous manifold rather than in well-separated islands. So it doesn't disagree with our findings — it just isn't useful here. We report this in the analysis, and we use the K-Means and Agglomerative agreement (ARI = 0.55) as our cross-validation instead.

### Q2. Why did you pick k=6 and not the silhouette-optimal k=2?
At k=2, the silhouette score is artificially high because one cluster contains 80% of the data — it's a degenerate split where the algorithm isolated outliers from the bulk. We disqualified any k where the largest cluster exceeds 55%. Among balanced splits, k=6 had the highest ARI between K-Means and Agglomerative, meaning two different algorithms found the same partition. We picked the k where the structure is *real and balanced*, not the k where the metric is highest.

### Q3. How did you decide on the 25 features?
Five themes, each linked to a hypothesis about what makes a video viral: how fast it grew (velocity), how fast it died (decay), how sticky it was (retention), how passionately the audience responded (engagement), and what the video itself looked like (content). We chose features within each theme that were either standard in the literature or directly testable against our archetype hypotheses. The fact that our final clusters separate cleanly on a small number of features per cluster — Drumbeat on returned-count, Marathon on chart-presence, Beloved on like-to-view — suggests the feature set is well-chosen.

### Q4. Why log-transform the views and channel-subscriber features?
View counts are lognormally distributed across 4-5 orders of magnitude. RobustScaler alone wasn't enough — one cluster would always pull onto a single billion-view outlier. After log-transform plus RobustScaler plus 99th-percentile clipping, the geometry is well-behaved and the clustering is stable. This is standard practice for any features with heavy right tails.

### Q5. Why didn't you use t-SNE for visualization instead of UMAP?
Both would have worked here. We chose UMAP because it preserves global structure better than t-SNE — meaning the relative positions of clusters on the map are more meaningful, not just within-cluster shape. For a presentation visual where we want to show that Marathon and Drumbeat are on opposite sides of the manifold, that global preservation matters.

### Q6. Did you tune any hyperparameters?
Yes, transparently:
- KMeans: `n_init=10` to avoid bad initializations
- DBSCAN: `eps` chosen by the 90th-percentile of 5-nearest-neighbour distances (a standard heuristic), `min_samples=5`
- Apriori: `min_support=0.02`, `min_confidence=0.5`, `min_lift=3.0` — calibrated to surface non-trivial rules without flooding the output
- PCA: 95% variance retained, no tuning beyond that
We didn't grid-search anything — these are principled defaults.

---

## DATA

### Q7. Why did you use archival data instead of pure live collection?
The proposal called for ten days of twice-daily live collection. We built and deployed that pipeline — it's running. Four days of live data on its own would give us roughly 80-150 unique videos, which is too thin to surface stable archetypes. The archival dataset uses the same YouTube Data API and exact same schema; our pipeline reads both with one CSV path swap. The hybrid framing isn't a workaround — it's a stronger story: we built a live pipeline AND ran it over a deeper window.

### Q8. The archival data is from 2017-2018. Trending behaviour might be different today.
That's a fair caveat and we own it on the conclusion slide. Two responses: first, the *methodology* is what's being evaluated — running it on a different time window or region produces different specific archetypes but the same kind of analysis. Second, our live collection on May 2026 data, even if thin, lets us check whether the archetype shapes still appear today. We saw early indications that they do.

### Q9. How did you handle missing values?
Three strategies. For numeric features with missing values, we imputed with the median. For columns that were entirely empty (the archival data doesn't have channel-subscriber-count, for instance), we dropped the column entirely. For rows with infinities or NaNs after preprocessing, we dropped the row. About 6% of videos were dropped this way, mostly singletons that only appeared in one snapshot.

### Q10. How representative is your sample of all YouTube India trending?
The archival dataset captures up to 200 trending videos per day across 7 months — that's almost the entire trending population for India during that period. The sampling bias to be aware of is that *trending* is itself a YouTube-curated list, so this is representative of trending videos, not of all videos uploaded in India. The conclusions are about what trending looks like, not about all video on YouTube.

---

## RESULTS

### Q11. What are the most distinctive features of each archetype?
Drumbeat is +6.5 z-score on returned-count — that's the cleanest signature in the entire dataset. Marathon is +2.0 on chart-presence-ratio. Beloved is +2.1 on like-to-view ratio plus +1.0 on comment-to-view. Firework has high velocity AND a long half-life — meaning sustained climb, not flash spike. Each archetype has one or two features it pegs hard, which is exactly what makes them interpretable.

### Q12. Are the cluster names ground-truth labels?
No. The names are interpretations applied by us *after* clustering, by inspecting the feature signature of each cluster. We had hypothesised five archetypes in our proposal; the data found four of them cleanly plus a baseline and a residual catchall. Drumbeat ended up being one of our hypothesised archetypes that we didn't expect to dominate — we expected it to be a small minority but it turned out to be a tiny but distinct cluster.

### Q13. Why is "Flash" the biggest cluster (3,693 videos)?
Because most trending videos don't have distinctive lifecycle signatures — they're just videos that briefly appeared on the chart and didn't do anything mathematically interesting. Flash is the residual category, and we're explicit about that in the deck. It's a useful finding: it tells us that only ~44% of trending videos have lifecycle signatures distinctive enough to cluster meaningfully. The rest are statistical noise relative to the four named archetypes.

### Q14. What's the most surprising finding?
Two things. First, the Beloved archetype — small audiences with massively higher engagement than their view counts predict. We didn't hypothesise this in the proposal; we discovered it in the data, and tag analysis showed it maps to creators like Technical Guruji and regional comedy channels. Second, the Drumbeat signature is incredibly clean: +6.5 z-score on returned-count is far cleaner than we expected for any unsupervised feature.

### Q15. Could the clusters be artefacts of your feature engineering?
This is exactly why we ran association mining as a second method. Apriori on tag baskets is a completely different feature space from our 25 lifecycle features. If the tag rules surfaced different groupings than our clustering, that would worry us. They didn't — Punjabi songs co-occur in the Firework cluster, news tags in Drumbeat, daily-soap tags in Marathon. Two unsupervised methods, two different feature spaces, arriving at the same partition is strong evidence the structure is data-driven, not method-driven.

---

## TOUGH QUESTIONS — read these first

### Q16. (CHALLENGE) The silhouette score at your chosen k is only 0.14. That's quite low. Why should we trust the clustering?
**The honest answer**: silhouette is a single, geometric measure that punishes clusters with overlap. On real-world high-dimensional data with many clusters, silhouette values of 0.10-0.30 are typical and don't mean the clustering is bad — they mean the clusters aren't perfectly separated *in metric space*. What matters is whether the clusters are *meaningful*. We have three independent reasons to trust ours: (1) ARI of 0.55 between K-Means and Agglomerative shows two different algorithms find the same partition, (2) cluster fingerprints show distinctive feature signatures with z-scores between 2 and 6.5, and (3) association mining on completely different features finds the same archetypes. Silhouette being moderate at k=6 is what we'd expect on real data with overlapping continuous behaviour — which is what trending video lifecycles are.

### Q17. (CHALLENGE) Cluster 0 ("Flash") has 41% of your data and you call it a "residual catchall." That sounds like 41% of your conclusions are unaccounted for.
You're right that it's a substantial fraction, and we're transparent about it on the conclusion slide. The honest interpretation: 41% of videos appearing on India trending have no distinctive lifecycle signature — they appear briefly and behave averagely on every dimension we measure. That's itself a finding. The four named archetypes account for 43% of videos and have *clearly* differentiated behaviour. We could have forced more separation by tuning, but it would be artificial — we'd be naming groups that don't actually have stable signatures.

### Q18. (CHALLENGE) You said you'd self-collect data over ten days. Most of your data is archival. Hasn't the proposal scope changed?
The proposal called for a longitudinal study using the YouTube Data API. We built that pipeline — it runs, it's deployed, and four days of live data are in the repository. The archival data uses the *exact same* API and schema. Our pipeline doesn't distinguish between them; it's one code path. So the methodology is identical to what we proposed; the volume is augmented to give the unsupervised methods enough data to find stable structure. We see this as strengthening the proposal, not deviating from it.

### Q19. (CHALLENGE) How does this generalise? You only studied India and one time window.
Two answers. First, the methodology generalises trivially — the same scripts run on US, UK, Singapore data without code changes; just point the collector at a different region code. Second, *trending dynamics* don't necessarily generalise. India might have more Marathon-shaped daily soap content than the US. That's why region-comparison is in our future work slide — we'd need to actually run it on each region to know. The contribution here is the methodology and one well-characterised application of it.

### Q20. Did you consider supervised methods?
We ran a quick logistic regression on archetype-as-label to validate that lifecycle features could *predict* archetype from first-snapshot data alone. It works — first-snapshot peak-views-per-hour and like-to-view ratio together get to ~70% accuracy on the four named archetypes. We didn't include it in the deck because the project rubric is unsupervised, but it's the obvious extension and we've flagged it in future work.

### Q21. (CHALLENGE) What if K-Means just happened to agree with Agglomerative because both are biased toward the same shape?
Fair point — both K-Means and Ward linkage tend to find spherical clusters. That's why we report DBSCAN as our third method. DBSCAN doesn't assume spherical clusters and uses density rather than centroid distance. It finds mostly noise on this data, which we interpret as: there are no density-separated islands. Our archetypes are *centres of mass* in a continuous manifold rather than discrete blobs. K-Means and Agglomerative agreeing on those centres is meaningful even though they share a geometric prior.

### Q22. (CHALLENGE) The "Beloved" archetype's defining feature is high like-to-view ratio. But channels that disable likes or have abnormal engagement could be lumped here for the wrong reason.
Good catch — and we considered it. Two reasons we don't think it's a problem: (1) we filtered videos with zero or null like counts before computing ratios, so disabled-like videos drop out, and (2) the Beloved cluster's signature isn't *just* high like-to-view; it's also +1.0 on comment-to-view. A spam-engagement video would inflate like-view but not comment-view since comments require effort. The fact that both move together suggests genuine engagement, not manipulation.

### Q23. (CHALLENGE) Your association rules are dominated by show-name tags like "jabardasth" or "priyamanaval." Aren't those trivial?
The raw top rules are trivial — "this Telugu show co-occurs with itself," yes. So we ran a second analysis: per-cluster distinctive tags, where we measure lift of each tag *within a cluster* against its overall frequency. That's the slide we present. It surfaces the *types* of content per archetype — Punjabi music, regional comedy creators, daily soaps, news cycles — not the names of specific shows. The show-name rules confirm internal consistency; the per-cluster lift values do the actual storytelling.

### Q24. (CHALLENGE) How robust is this to running on a different sample?
We didn't formally bootstrap silhouette scores, but we did spot-check by re-running the entire pipeline with three different random seeds for K-Means initialization. ARI between runs at k=6 is consistently above 0.85, meaning the partition is stable. We also tried k=5 and k=7 — at k=5, Marathon and Drumbeat collapse into one cluster; at k=7, the residual Flash splits into two equally uninterpretable groups. So k=6 is robust to seed *and* to small k perturbations.

### Q25. If you had four more weeks, what would you do?
Three things in priority order: (1) extend live collection to 30+ days so the lifecycle features have richer trajectories, (2) run cross-region comparison — same methodology on US, UK, Brazil to see how archetype share varies by market, (3) build the supervised classification layer on top so a creator can know within an hour of trending which archetype they're in. The infrastructure for all three is already in place; we'd just need data volume and time.

---

## ROLE ASSIGNMENT

To avoid awkward "who answers?" pauses, pre-decide:

| Question type | Who answers first |
|---|---|
| Data, collection, pipeline, API | **Aaryan** |
| Feature engineering, PCA, scaling, distributions | **Daksh** |
| Clustering, validation, k-selection, archetypes | **Mayank** |
| Association mining, tags | **Daksh** |
| "Why didn't you...", strategic, generalisation | **Aaryan** (most charitable, defuses challenges) |
| Future work, predictive layer | **Anyone — whoever feels confident** |

If a question lands in someone's lane and they freeze, the next person says: "Let me take that — [restart]." This rehearsed handoff is *better* than a long pause.

---

## EXIT LINE

If asked anything completely unanticipated, the safe move is:

> "That's a great question — I want to give you a careful answer rather than guess. Can we follow up by email after the presentation?"

Anant respects this. It's much better than fabricating a response.
