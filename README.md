# Healthcare Startup Funding Finder: daily scraper

Checks the official page of every scheme in `data/schemes.json` once a day,
spots what changed, and keeps the website up to date.

## How it works

```
sources.yaml ──► fetch (polite: robots.txt, 3 s per host)
                   │
                   ▼
              main text only ──► compare with yesterday's snapshot (state/)
                   │ changed?
                   ▼
   rule-based signals (NL / FR / EN)         optional: Claude reads the page and
   "suspended", "geschorst", "suspendu",  ─► proposes field updates, each with a
   deadlines near "uiterste datum", ...      verbatim quote from the page
                   │
                   ▼
   high confidence + only status/status_note/next_deadline ──► applied to data/schemes.json
   everything else ──────────────────────────────────────────► "needs a human look"
                   │
                   ▼
   reports/YYYY-MM-DD.md  ──►  pull request on GitHub  ──►  you merge  ──►  site redeploys
```

What it does each run:

- **Scheme pages**: if the text changed, it flags the likely new status and any new
  future deadline. With a Claude API key it also proposes updates.
- **Overview pages** (`discovery` in `sources.yaml`): reports new lines, which is where new
  calls and new schemes usually show up first. These never change the data on their own.
- **Housekeeping**: clears deadlines that have passed, bumps `last_verified` on pages
  that were re-read and haven't changed, and reports sources that fail 3 runs in a row.

Nothing reaches the live site without a pull request you merge. Funding information is
the kind of thing people act on, so a person stays in the loop.

## Set-up (about 15 minutes)

1. Create a GitHub repository and push this folder to it.
2. **Settings → Pages → Source: GitHub Actions.** The `Deploy site` workflow publishes
   `site/public/` whenever `data/schemes.json` changes on `main`.
3. **Settings → Actions → General → Workflow permissions:** "Read and write" and
   "Allow GitHub Actions to create and approve pull requests".
4. Optional, recommended: **Settings → Secrets → Actions → `ANTHROPIC_API_KEY`**.
   Without it the scraper runs in rules-only mode and every change goes to review.
5. Put a real contact address in `user_agent` in `sources.yaml`. Some government sites
   block anonymous bots.
6. **Actions → Daily funding check → Run workflow** once. The first run only stores
   baseline snapshots, so the first real report comes the day after.

## Running it locally

```bash
pip install -r requirements.txt
python -m scraper.run                 # check and report only
python -m scraper.run --apply         # also write accepted updates to data/schemes.json
python -m scraper.run --only VL-04    # one scheme
python site/build_site.py             # rebuild site/public/index.html
python -m pytest -q                   # tests run offline with fixture pages
```

## Adding a scheme

1. Add a record to `data/schemes.json` (same fields as the others; `sizes` and `tags`
   drive the matching on the website).
2. Add its ID under `schemes:` in `sources.yaml` (plus `extra_urls` for call pages).

## Settings

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Turns on Claude extraction |
| `SCRAPER_MODEL` | `claude-sonnet-5-5` | Model used for extraction |
| `AUTO_APPLY_CONFIDENCE` | `0.85` | Minimum confidence to apply a change without review |

Cost: about 30 pages a day, and Claude is only called for pages that changed (usually a
handful a week), so API cost stays at a few euros a month. GitHub Actions minutes for a
public repo are free; a private repo uses roughly 5 minutes a day.

## Files

| Path | What |
|---|---|
| `data/schemes.json` | The dataset (single source of truth for the website) |
| `sources.yaml` | Which pages to check |
| `scraper/` | Fetching, text extraction, signals, Claude step, daily run |
| `state/` | Yesterday's page text per URL (committed so changes can be diffed) |
| `reports/` | One Markdown report per day with news, plus `latest.json` |
| `site/` | Website template and build script; output goes to `site/public/` |
| `.github/workflows/` | Daily check (05:17 Brussels winter time) and site deploy |
