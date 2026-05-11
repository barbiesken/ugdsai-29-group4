# Speaker Notes — Group 4 Deck
**UGDSAI 29 · What Goes Viral in India? · 12 slides · 10–12 minutes**

Total budget: **11 minutes** + 4–5 min Q&A. Each slide has its time below — practise twice with a stopwatch before Wednesday.

---

## Slide 1 — Title (0:30)
**Open with the question.**

> "Good morning. I'm [name], and with Daksh and Mayank we asked one question: what does it actually mean for a video to go viral in India? We had a hunch that 'going viral' isn't one thing — it's several different patterns wearing the same label. Over the next ten minutes we'll show you how we went looking for those patterns, what we found, and why the answer matters for anyone making, marketing, or studying video on YouTube."

**Pause for 2 seconds at the UMAP visual on the right.** Let the panel see the structure before you talk over it.

---

## Slide 2 — The Question (1:00)
**Make the hypothesis tangible before we touch any data.**

> "Three caricatures to set the scene. A daily soap stays on the trending chart for weeks — sticky. A music drop climbs hard, plateaus, and slips away in three days — flash. And there's a category we called 'loyal' — videos with massively higher engagement than their view counts predict, where small audiences care a lot. Three completely different shapes."

> "The question we asked is: can we find these archetypes in data, without telling the algorithm what to look for? That's why this is unsupervised. And can we predict which one a video belongs to from what we can see when it first appears on the trending chart?"

**The blue panel at the bottom is the thesis. Read it slowly.**

---

## Slide 3 — Why It Matters (1:00)
**Three stakeholders, three decisions. Stay concrete.**

> "Three reasons this isn't just academic. First, a creator deciding whether to make long-form or short-form has to know which archetype rewards which strategy — they're literally opposite. Second, a brand that wants to advertise has 24-48 hours to ride a Firework, but weeks to ride a Marathon. Burning ad budget on the wrong type is a real and expensive mistake. Third, a platform team studying its own recommender — if you're seeing more Drumbeat-shaped videos this quarter than last, that tells you something about how the algorithm is reshaping content."

**Don't dwell. The panel needs to know we know our audience, then move on.**

---

## Slide 4 — Data (1:30)
**Be transparent, lead with numbers.**

> "We collected 37,352 snapshots of 16,307 unique trending videos from India, spanning seven months. Two paths. One: a live YouTube Data API collector we built that runs twice daily and proves the pipeline works on today's API. Two: an archival dataset of Indian trending data — same API, same schema, just pre-collected. The pipeline reads both with one CSV path swap."

> "Why hybrid? Four days of fresh data alone wouldn't give us enough volume to find archetypes; archival alone wouldn't show that our pipeline still works on today's API. Together we get methodological honesty plus statistical power."

**The pipeline diagram in the middle is the visual anchor. Trace through it left-to-right with your finger or laser pointer.**

If anyone asks why archival: "Because the proposal was approved on twice-daily live collection over ten days. We built that pipeline and it runs. But we also wanted enough videos to do the clustering justice, so we layered the same pipeline over a larger archival window."

---

## Slide 5 — Feature Engineering (1:30)
**This is Anant's note made visible. Earn the slide.**

> "Anant's biggest pushback on our proposal was: cluster at the video level, not the snapshot level. Aggregate the lifecycle into features that describe how a video *behaved*, not just what it *was*. So we built 25 features in five themes."

**Walk through each card briefly.**

> "Velocity — how fast did views grow? Decay — how fast did they die? Retention — did the video stick or flash? Engagement — how did the audience respond? And content — the metadata we have about the video itself."

> "Every one of these is computed by aggregating across each video's snapshots. One row per video. That's the matrix the clustering sees."

**Don't read the column names — point at them. The panel can see the code.**

---

## Slide 6 — PCA (1:00)
**Quick, technical, move on.**

> "Engineered features are correlated by design — peak velocity and mean velocity tell similar stories. We ran PCA. Sixteen components retain 95% of the variance, and that's the basis we cluster on."

> "What do the top components mean? PC1 is essentially a velocity-versus-longevity axis. PC2 captures engagement intensity. The rest are content textures — duration, language, category. So the geometry has interpretable directions before we even cluster."

**This is a slide to NOT linger on. Panels who care will ask in Q&A.**

---

## Slide 7 — Choosing k (1:00)
**This is the methodologically rigorous slide. Anant will love it.**

> "We had a decision to make. Look at the silhouette score — it's highest at k=2. Naive answer: pick k=2. We didn't. Because at k=2, one cluster contains 80% of all videos. That's a degenerate split — the algorithm just isolated outliers from the bulk, it didn't discover structure."

> "So we built a third diagnostic: largest cluster share. Anything where one cluster exceeds 55% of the data, we disqualify. Among the remaining options, k=6 has the best Adjusted Rand Index between K-Means and Agglomerative — meaning two completely different clustering algorithms agree on the partition. That's our number."

**Beat. Then deliver this line:**

> "Silhouette alone would have lied to us. Silhouette plus balance plus inter-method agreement told us the truth."

---

## Slide 8 — Results (1:30) — **THE HERO SLIDE**
**Slow down. This is the moment.**

> "Here's what fell out. Six clusters on 9,100 videos. Methods agree at ARI 0.55 — strong convergent evidence the structure is real."

**Walk through the four named archetypes one at a time. Touch the cards.**

> "Firework — sustained big hits, dominated by Punjabi music drops. Beloved — videos with double the average like-to-view ratio, where small audiences are passionate. We see Technical Guruji and regional comedy here. Marathon — videos with double the chart-presence ratio. Tamil daily soaps that just refuse to leave. And Drumbeat — videos with six and a half times the average chart re-entry rate. News cycles that come back every time the story develops."

> "Then two fringe clusters — Flash, the residual catchall, and Standard, the baseline. Together those are 56% of all videos. The named archetypes are the 44% with distinctive lifecycles."

---

## Slide 9 — Lifecycle Curves (1:00)
**Visually obvious. Let the picture do the work.**

> "If you didn't believe me on the previous slide, this should settle it. Six normalised view trajectories. Firework climbs in 24 to 48 hours, plateaus, and slowly decays. Beloved looks ordinary in views — the special thing isn't shape, it's engagement. Marathon plateaus near the top and stays. And Drumbeat — see the dip and recovery? That's the chart-re-entry signature. These archetypes aren't just statistical artefacts. They have visibly different *behaviours*."

---

## Slide 10 — Cluster Fingerprint (0:45)
**Quick read of the heatmap.**

> "Same finding, viewed differently. Each row is an archetype, each column a feature, colour is z-score against the population. The deep red boxes are the signatures: Drumbeat's plus-six-point-five on returned-count, Marathon's plus-two on chart presence, Beloved's plus-two-point-one on like-to-view ratio. Each archetype is defined by one or two features it pegs hard, not many features it pegs softly."

---

## Slide 11 — Association Mining (1:00)
**The "two methods agree" slide.**

> "We then ran Apriori over the tag baskets. Over a thousand rules at lift greater than three. The interesting result isn't the rules themselves — it's that the tags converge on the *same* archetypes the geometry already found. Punjabi songs and Punjabi music live together — that's our Firework cluster. Technical Guruji, Hyderabadi comedy, regional creators — Beloved. Priyamanaval, the Tamil serial — Marathon. Breaking news, BJP, Congress — Drumbeat."

> "Two completely different unsupervised methods, on different feature spaces, arriving at the same partition. That's the strongest evidence we have that these archetypes are real, not artefacts of one technique."

---

## Slide 12 — So What (1:00)
**Land it.**

> "Five takeaways. One: trending in India is at least four distinguishable archetypes. Two: lifecycle features beat static metadata for separating them. Three: methods agree, structure is real. Four: tags reinforce the same archetypes — convergent evidence. Five: the same pipeline runs on a fresh API stream and on archival data without code changes — the methodology generalises."

> "Caveats we own: archival window is 2017–2018, India only, and Flash is a residual catchall not a real archetype. Where this could go: cross-region comparison, time-series tracking of archetype share, or a predictive layer that classifies a video's archetype from its first-snapshot metadata."

> "Thank you. We're happy to take questions."

**Smile. Hold eye contact. Don't fill silence.**

---

## Stage tactics

- **If you forget a number, don't make one up.** Say "I'd want to verify the exact figure" — it builds trust.
- **If a slide gets a question mid-talk**, answer briefly and signal "I have more on this in two slides" if relevant.
- **Q&A first answer is who-answers**: pre-decide. Aaryan handles data/methodology questions, Daksh handles feature engineering/PCA, Mayank handles clustering/results. If unsure, look at each other for a half-second — it's fine.
- **End on Slide 12.** Don't go back to slides during Q&A unless asked.

## Last-minute checklist (Tuesday night)

- [ ] Print these notes
- [ ] Print the deck (handout backup if projector fails)
- [ ] Time a full dry-run end-to-end. Target: 10:30. Hard limit: 12:00.
- [ ] Test the projector connector
- [ ] Charge laptop, bring charger
- [ ] Have `Group_4.pdf` on USB stick, in email, in Drive — three copies
