# FanFeeder

Personalized sports news digest delivered twice daily by email. Pick your teams once — get top headlines and YouTube highlights every morning and afternoon.

**Live site:** [fanfeeder.fire-exit.com](https://fanfeeder.fire-exit.com)

---

## What it does

- Subscribers choose teams across **Soccer, NBA, NFL, MLB, NHL, Formula 1, and NCAA Men's**
- GitHub Actions runs at **7 AM and 5 PM ET** every day
- Each subscriber gets a personalized HTML email with:
  - Top 5 headlines per team (via Google News RSS)
  - Up to 3 YouTube highlights per team (via channel RSS + yt-dlp)
- Stories already seen in the last 3 days are filtered out so every digest is fresh

---

## Architecture

```
fanfeeder.fire-exit.com  (GitHub Pages — docs/)
        │
        ├── Subscribe / manage teams → Formspree → GitHub Actions
        │
        └── subscribers_index.json  (SHA-256 hashed email → team IDs)

GitHub Actions  (twice daily cron)
        │
        ├── process_subscription.py  — sync new subscribers from Formspree
        ├── main.py                  — fetch content, build HTML, send via Gmail SMTP
        └── Auto-commit subscribers_index.json → GitHub Pages

mcp/  (optional — Railway serverless)
        └── FastMCP server exposing live news queries to LLM environments
```

---

## Repository structure

```
src/
  main.py                # Orchestrator — fetch, build, send
  config.py              # Paths, SMTP settings, content limits
  news_fetcher.py        # Google News RSS with UA rotation + retry
  youtube_fetcher.py     # YouTube channel RSS + yt-dlp fallback
  email_builder.py       # HTML email template
  subscriber_loader.py   # Load teams.json and subscribers.json
  process_subscription.py# Sync Formspree submissions → subscribers.json
  seen_cache.py          # Per-subscriber 3-day dedup cache
  logo_checker.py        # Verify team logo URLs, fall back to Wikipedia

docs/                    # GitHub Pages static site
  index.html             # Subscribe page with team picker
  manage.html            # Add / remove teams for existing subscribers
  unsubscribe.html
  teams.json             # Full team catalog with logos and query strings
  subscribers_index.json # Auto-generated: sha256(email) → [team_ids]
  style.css
  app.js

mcp/
  main.py                # FastMCP server — see mcp/DEPLOY.md
  requirements.txt
  DEPLOY.md              # Railway deployment + Claude connector setup

data/
  subscribers.json       # Subscriber list (not committed with real emails)

.github/workflows/
  daily-digest.yml       # Twice-daily send + subscriber sync
  keepalive.yml          # Weekly job to prevent GitHub disabling schedules
```

---

## Setup

### 1. Fork and configure secrets

In GitHub → Settings → Secrets and variables → Actions, add:

| Secret | Description |
|---|---|
| `GMAIL_APP_PASSWORD` | 16-character Google app password for the sending Gmail account |
| `FORMSPREE_API_KEY` | Formspree API key (from your form dashboard) |
| `FORMSPREE_FORM_ID` | Formspree form ID (e.g. `mzdawwjk`) |

### 2. Enable GitHub Pages

Settings → Pages → Source: **Deploy from branch**, branch: `main`, folder: `/docs`.

### 3. Point your domain

Add a CNAME record pointing to `<your-username>.github.io` and set the custom domain in GitHub Pages settings.

### 4. Update config

Edit `src/config.py`:
```python
EMAIL_SENDER = "you@gmail.com"
SITE_URL = "https://your-domain.com"
```

---

## MCP Server (optional)

An optional [FastMCP](https://github.com/jlowin/fastmcp) server in `mcp/` lets LLMs query FanFeeder live:

> *"What's the latest news about my teams?"*
> *"Add the Lakers to my digest"*
> *"Show me Arsenal highlights"*

Deploy to Railway (serverless) and connect to Claude Desktop or claude.ai. See [`mcp/DEPLOY.md`](mcp/DEPLOY.md) for full instructions.

---

## Running locally

```bash
pip install -r requirements.txt
cd src
GMAIL_APP_PASSWORD=your_app_password python main.py --preview
```

`--preview` writes the first subscriber's digest to `preview.html` instead of sending email. To send to a single address:

```bash
python main.py --email you@example.com
```

---

## Tech stack

- **Python 3.12** — feedparser, requests, yt-dlp, python-dotenv, googlenewsdecoder
- **GitHub Actions** — cron scheduler, seen-cache via `actions/cache`
- **GitHub Pages** — static frontend
- **Formspree** — form backend (no server required)
- **Gmail SMTP** — email delivery
- **FastMCP** — MCP server (optional)
