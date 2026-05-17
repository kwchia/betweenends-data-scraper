# Betweenends Coach Results App

A Flask web app for archery coaches to consolidate tournament results from [Betweenends.com](https://www.betweenends.com). Filter results to your club's athletes across qualification, elimination, and team events.

## Features

- Multi-user accounts with club profiles and configurable aliases
- Tournament search (cached from Betweenends public API)
- Summary tab: medals, finish stats, highlights (top scores, comebacks, close matches)
- Per-event tabs with division breakdowns
- Docker deployment with PostgreSQL

## Quick start (Docker)

```bash
cp .env.example .env
# Edit SECRET_KEY in .env

docker compose up --build
```

Open http://localhost:5847

**Default login:** username `admin`, password `admin` (created automatically on first startup). Change these via `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD` in `.env` before first run, or register a new account and use that instead.

Then add clubs/aliases in Profile and search for a tournament.

**Note:** Ports 5000 and 8080 are commonly in use on Windows. This project maps the app to **5847** on your machine to avoid conflicts.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://betweenends:betweenends@localhost:5432/betweenends
export SECRET_KEY=dev-secret
export FLASK_APP=wsgi:app

flask db upgrade
python manage.py
```

## Running tests

```bash
pip install -r requirements.txt
pytest
```

## API note

This app uses the public `resultsapi.herokuapp.com` API that powers Betweenends results pages. It is undocumented and may change.

## Project structure

```
app/
  blueprints/     # auth, profile, tournaments routes
  services/       # API client, scoring, parsers, summary
  templates/      # Jinja2 HTML
  static/         # CSS and JS
migrations/       # Alembic database migrations
tests/
```
