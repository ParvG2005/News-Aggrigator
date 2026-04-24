# AI News Aggregator (YouTube + Free Web Sources)

Production-style daily AI news pipeline that scrapes YouTube and free public sources, creates digests, ranks by user profile, and emails a curated summary.

## Features

- YouTube ingestion via channel RSS + transcript enrichment.
- Free-source ingestion from RSS, arXiv, Hacker News, Reddit, and GitHub Releases.
- Deduped article store with configurable ingestion limits.
- Deterministic local digest, ranking, and email intro generation (no paid LLM dependency).
- Daily end-to-end pipeline with email output.

## Architecture

- `app/runner.py` - scraping entrypoint (YouTube + free sources).
- `app/services/process_youtube.py` - transcript backfill for new videos.
- `app/services/process_digest.py` - digest creation for undigested articles.
- `app/services/process_email.py` - ranking + email generation and send.
- `app/daily_runner.py` - orchestrates the full pipeline.

## Quick Start

1. Clone and enter the project.
2. Create `.env` from `app/example.env`.
3. Install dependencies:
   - `uv sync`
4. Create database tables:
   - `uv run python app/database/create_tables.py`
5. Run pipeline:
   - `uv run python main.py 24 10`

## Environment Variables

### Required

- `MY_EMAIL` - sender/recipient email (self-send by default).
- `APP_PASSWORD` - app password for SMTP login.

### Database

- `DATABASE_URL` - optional override (recommended for local SQLite).
- Postgres fallback vars:
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `POSTGRES_DB`
  - `POSTGRES_HOST`
  - `POSTGRES_PORT`

### External Source Controls

- `MAX_EXTERNAL_ARTICLES_TOTAL` - global max external items per run.
- `MAX_EXTERNAL_ARTICLES_PER_SOURCE` - max items from each RSS/feed source.
- `MAX_HN_ITEMS` - max Hacker News stories inspected.
- `MAX_REDDIT_ITEMS_PER_SUBREDDIT` - max selected Reddit posts per subreddit.
- `ENABLE_HACKERNEWS` - enable/disable Hacker News scraping.
- `ENABLE_REDDIT` - enable/disable Reddit scraping.
- `ENABLE_GITHUB_RELEASES` - enable/disable GitHub release feed scraping.

## Run

- `uv run python main.py 24 10`

## Notes

- This repository is configured to avoid committing local secrets (`.env`) and local databases (`*.db`).
- For stable local runs without Docker/Postgres, use:
  - `DATABASE_URL=sqlite:///./ai_news_v2.db`
