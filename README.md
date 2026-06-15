# Following Inflation

A FastAPI service that scrapes informal Cuban exchange rates (CUP) from [eltoque.com](https://eltoque.com/tasas-de-cambio-cuba) every 6 hours, persists them to a SQLite database, and exposes them through a REST API and a Telegram bot.

## Features

- Automated scraping every 6 hours via APScheduler
- SQLite persistence with SQLAlchemy
- REST API built with FastAPI
- Telegram bot for querying current and historical rates
- Scraper and bot run in the same process as the API — no extra services needed

## Project Structure

```
following_inflation/
├── main.py               # App entry point: FastAPI app, lifespan, scheduler
├── condig.py             # Legacy config (superseded by .env)
├── requirements.txt
├── .env                  # Environment variables (not committed)
├── api/
│   └── routes.py         # /rates endpoints
├── bot/
│   └── bot.py            # Telegram bot handlers
├── database/
│   ├── database.py       # SQLAlchemy engine, session, Base
│   └── models.py         # ExchangeRateRecord ORM model
└── scraper/
    └── scraper.py        # Scrapes eltoque.com
```

## Tracked Currencies

| Symbol | Currency        |
|--------|-----------------|
| USD    | US Dollar       |
| EUR    | Euro            |
| MLC    | Moneda Libremente Convertible |
| CAD    | Canadian Dollar |
| MXN    | Mexican Peso    |
| Zelle  | Zelle (USD)     |
| CLA    | CLA             |

All rates are expressed in **CUP (Cuban Peso)** per 1 unit of the foreign currency.

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/your-user/following_inflation.git
cd following_inflation
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=your_bot_token_here
API_BASE_URL=http://localhost:8000
```

> Get a bot token from [@BotFather](https://t.me/botfather) on Telegram.

### 4. Run

```bash
uvicorn main:app --reload
```

On startup the app will:
1. Create the SQLite database (`exchange_rates.db`) if it does not exist
2. Scrape and save the current rates immediately
3. Schedule a scrape every 6 hours
4. Start the Telegram bot in polling mode

## API Reference

Interactive docs are available at `http://localhost:8000/docs` once the server is running.

### `GET /rates`

Returns the most recent saved records.

| Query param | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 100 | Maximum number of records to return |

**Response**
```json
[
  {
    "id": 1,
    "timestamp": "2026-06-15T08:00:00",
    "usd": 390.0,
    "euro": 420.0,
    "mlc": 340.0,
    "cad": 285.0,
    "mxn": 19.5,
    "zelle": 390.0,
    "cla": 310.0
  }
]
```

### `GET /rates/latest`

Returns the single most recent record. Returns `404` if no data is available yet.

### `POST /rates/fetch`

Manually triggers a scrape and saves the result.

**Response**
```json
{ "message": "Rates fetched and saved successfully" }
```

## Telegram Bot

Start a conversation with your bot and use the following commands:

| Command | Description |
|---|---|
| `/start` | Show available commands |
| `/rates` | Current exchange rates |
| `/history [n]` | Last *n* records (1–20, default 5) |

The bot communicates with the API internally (`API_BASE_URL`) so it always reflects the same data as the REST endpoints.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_TOKEN` | Yes | — | Token from @BotFather |
| `API_BASE_URL` | No | `http://localhost:8000` | Base URL of the FastAPI service |

## .gitignore recommendation

Add the following to your `.gitignore` to avoid committing secrets and generated files:

```
.env
*.db
.venv/
__pycache__/
*.pyc
```
