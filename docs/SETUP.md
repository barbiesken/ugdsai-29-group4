# YouTube Trending India — Collector Setup

UGDSAI 29 · Group 4 · Aaryan, Daksh, Mayank

This document gets the collector running in under 15 minutes.

---

## 1. One-time setup (do this tonight)

### a. Get a YouTube Data API v3 key

1. Go to <https://console.cloud.google.com>
2. Create a new project (any name, e.g. `ugdsai-29-yt`)
3. In the search bar, type **YouTube Data API v3** → click → **Enable**
4. Left sidebar → **APIs & Services → Credentials**
5. **Create Credentials → API key**
6. Copy the key. Treat it like a password — don't commit it to git.

### b. Install Python dependencies

The collector only needs `requests`:

```bash
pip install requests
```

That's it for collection. Analysis dependencies come later.

### c. Set the API key as an environment variable

**macOS / Linux:**
```bash
echo 'export YT_API_KEY="paste_your_key_here"' >> ~/.zshrc   # or ~/.bashrc
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
[Environment]::SetEnvironmentVariable("YT_API_KEY", "paste_your_key_here", "User")
```

Restart your terminal after this.

### d. Test it works

From the project root:

```bash
cd youtube_project
python scripts/collect.py
```

Expected output:
```
[2026-05-02T10:00:15+05:30] Starting collection for region=IN
OK: wrote 50 rows to master + snapshot at snapshot_2026-05-02_04-30-15Z.csv
```

You should now have:
- `data/snapshots/snapshot_<timestamp>.csv` — 50 rows, this run only
- `data/master_snapshots.csv` — same 50 rows, will grow with each run
- `data/run_log.csv` — one line per run (audit trail)

If you see an error: read it. The script logs every failure to `data/run_log.csv` so we can debug post-mortem.

---

## 2. Scheduling: pick ONE of the three options below

You need to run `collect.py` **twice a day for 10 days** (40 calls = 40 quota units, well below the 10,000/day free limit). Pick whichever you can keep alive.

| Option | Reliability | Setup time | Best for |
|---|---|---|---|
| A. GitHub Actions | ★★★★★ — runs even with all laptops off | ~10 min | The safe choice — recommended |
| B. Local cron | ★★★ — needs that laptop awake at 10am & 10pm | ~5 min | Mac/Linux users with one always-on machine |
| C. Manual reminder | ★★ — depends on humans | 0 min | Backup if A and B both fail |

### Option A — GitHub Actions (recommended)

Free, runs in the cloud, won't miss snapshots even if your laptops die.

1. Create a private GitHub repo named e.g. `ugdsai-yt-trending`.
2. Push the project (without the API key — it goes in step 5).
3. In repo settings → **Secrets and variables → Actions → New repository secret**
   - Name: `YT_API_KEY`
   - Value: your API key
4. Add the workflow file (already created at `.github/workflows/collect.yml`).
5. Push. The workflow auto-runs at the scheduled times.

The workflow file commits new snapshots back to the repo, so all three of you can pull the latest data anytime.

⚠️ GitHub Actions cron is in **UTC**. The schedule below fires at **10:00 IST and 22:00 IST** (= 04:30 UTC and 16:30 UTC).

### Option B — Local cron (Mac / Linux)

```bash
crontab -e
```

Add:
```cron
30 4 * * *  cd /full/path/to/youtube_project && /usr/bin/python3 scripts/collect.py >> data/cron.log 2>&1
30 16 * * * cd /full/path/to/youtube_project && /usr/bin/python3 scripts/collect.py >> data/cron.log 2>&1
```

Replace `/full/path/to/` and the python path (run `which python3` to find yours). The laptop must be awake at 10:00 and 16:30 UTC for these to fire.

### Option C — Phone alarms

If A and B both fail, set two phone alarms (10:00 and 22:00 IST). When the alarm goes off, run `python scripts/collect.py` manually. Document who's on duty each day in your group chat.

---

## 3. What "good" looks like after 10 days

- `data/master_snapshots.csv` should have **~1,000 rows** (50 videos × 20 snapshots, minus any churn)
- After deduplication on `video_id`, expect **300–600 unique videos**, each with **1–20 observations**
- `data/run_log.csv` should have ~20 `ok` rows and ideally zero `fail` rows

If you miss a single snapshot, the analysis is fine. If you miss four in a row, it starts to bite the longitudinal feature quality. Monitor `run_log.csv` daily.

---

## 4. Quick troubleshooting

**`YT_API_KEY env var is not set`** — environment variable isn't loaded in the shell where you ran the script. Open a new terminal and try again, or run `echo $YT_API_KEY` to verify it's set.

**`HTTP 403 - quota exceeded`** — extremely unlikely on this project. If it happens, wait 24h for the quota reset, or create a new GCP project + key.

**`HTTP 400 - API key not valid`** — key has restrictions on it. In Cloud Console → Credentials → click the key → set Application Restrictions to "None" (for project use) and API Restrictions to "YouTube Data API v3".

**Empty `items` list** — region temporarily has no chart available. The script will log a fail and continue; just rerun.

---

## 5. Daily checklist (Aaryan)

- Morning: run completed? check `run_log.csv`
- Evening: run completed? check `run_log.csv`
- Daily: glance at `master_snapshots.csv` row count — should grow by ~100 each day

That's the entire collection workflow.
