# Smart Internship Match

A personal decision-support pipeline for an internship search: fetch real postings,
structure them with a local LLM, score them against my own skills, draft grounded
cover-letter openings for the best matches, and track outcomes — covered end to end
in `REPORT.md`.

- **Source: Jooble** (not France Travail — see `REPORT.md` for why), a real issued
  API key, weekly cloud fetch via `.github/workflows/fetch_offers.yml`.
- **Local only** (never in GitHub Actions — no GPU runner): `extract_offers.py`,
  `match_offers.py`, `draft_cv.py`, `compute_outcomes.py`, `check_monitoring.py`.
  Needs [Ollama](https://ollama.com) running with `qwen3:8b` pulled.
- **Dashboard:** `docs/index.html` — pipeline health, search effectiveness, and
  outcome KPIs, each chart argued in `REPORT.md`. `docs/sanity.html` is the raw-data
  sanity check, not the dashboard.
- **Never committed:** `.env`, `data/offers/{merged,structured,matches_all_local}.json`,
  `output/cv_drafts/`, `data/applications/tracker.csv` (personal — only its
  aggregate, `docs/data/outcomes.json`, is published).

Real run (2026-11-14): 30 offers fetched, top match 0.920 (a Python internship,
coverage 100%), 24/30 scored 0.0 (mostly thin extraction from Jooble's truncated
snippets — a real, documented limitation, not a bug).

## Running it yourself

```
python scripts/fetch_offers_jooble.py   # needs JOOBLE_API_KEY env var (or via Actions)
python scripts/merge_offer_sources.py
python scripts/extract_offers.py        # needs Ollama running locally
python scripts/match_offers.py
python scripts/draft_cv.py              # drafts output/cv_drafts/, review before using
python scripts/compute_outcomes.py      # reads data/applications/tracker.csv
python scripts/check_monitoring.py      # Stage 6 monitoring check
```
