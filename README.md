# Following Inflation

A FastAPI service that scrapes informal Cuban exchange rates (CUP) from [eltoque.com](https://eltoque.com/tasas-de-cambio-cuba) every hour, persists them to a SQLite database, and exposes them through a REST API and a Telegram bot.

## Features

- Automated scraping every hour via APScheduler (skips save when rates haven't changed)
- SQLite persistence with SQLAlchemy
- REST API built with FastAPI
- Telegram bot with current rates, history, and exchange rate charts
- Rotating log file (`app.log`, max 5 MB × 3 backups)
- Dockerized — single `docker compose up` to run everything
- Scraper, scheduler, and bot run in the same process as the API — no extra services needed

## Project Structure

```
following_inflation/
├── main.py               # App entry point: FastAPI app, lifespan, scheduler
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                  # Environment variables (not committed)
├── api/
│   └── routes.py         # /rates endpoints
├── bot/
│   └── bot.py            # Telegram bot handlers and chart generation
├── database/
│   ├── database.py       # SQLAlchemy engine, session, Base
│   └── models.py         # ExchangeRateRecord ORM model
└── scraper/
    └── scraper.py        # Scrapes eltoque.com
```

## Tracked Currencies

| Symbol | Currency |
|--------|----------|
| USD    | US Dollar |
| EUR    | Euro |
| MLC    | Moneda Libremente Convertible |
| CAD    | Canadian Dollar |
| MXN    | Mexican Peso |
| Zelle  | Zelle (USD) |
| CLA    | CLA |

All rates are expressed in **CUP (Cuban Peso)** per 1 unit of the foreign currency.

---

## Setup

### Option A — Docker (recommended)

```bash
# 1. Copy and fill in your token
cp .env.example .env   # or create .env manually (see Environment Variables below)

# 2. Build and start
docker compose up -d --build
```

The database is stored in a named Docker volume (`db_data`) and persists across restarts.

### Option B — Local virtual environment

```bash
git clone https://github.com/aldairlfp/following_inflation.git
cd following_inflation
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (see **Environment Variables** below), then:

```bash
uvicorn main:app --reload
```

On startup the app will:
1. Create the SQLite database (`exchange_rates.db`) if it does not exist
2. Scrape and save the current rates immediately
3. Schedule a scrape every hour
4. Start the Telegram bot in polling mode

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_TOKEN` | Yes | — | Token from [@BotFather](https://t.me/botfather) |
| `API_BASE_URL` | No | `http://localhost:8000` | Base URL of the FastAPI service |
| `DATABASE_URL` | No | `sqlite:///./exchange_rates.db` | SQLAlchemy database URL |

```env
TELEGRAM_TOKEN=your_bot_token_here
API_BASE_URL=http://localhost:8000
```

---

## API Reference

Interactive docs are available at `http://localhost:8000/docs` once the server is running.

### `GET /rates`

Returns the most recent saved records, newest first.

| Query param | Type | Default | Description |
|---|---|---|---|
| `limit` | int | 100 | Maximum number of records to return |

**Response**
```json
[
  {
    "id": 1,
    "timestamp": "2026-06-27T10:00:00",
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

### `GET /rates/history/{currency}`

Returns historical values for a single currency, ready for charting.

| Query param | Type | Default | Description |
|---|---|---|---|
| `months` | int | 3 | Months to look back — returns one **daily average** per day |
| `days` | int | — | If set (1–14), overrides `months` and returns raw **hourly** records |

Valid currencies: `usd`, `euro`, `mlc`, `cad`, `mxn`, `zelle`, `cla`

**Response**
```json
[
  { "timestamp": "2026-06-01T00:00:00", "value": 385.5 },
  { "timestamp": "2026-06-02T00:00:00", "value": 387.0 }
]
```

### `POST /rates/fetch`

Manually triggers a scrape and saves the result.

**Response**
```json
{ "message": "Rates fetched and saved successfully" }
```

---

## Telegram Bot

Start a conversation with your bot and use the following commands:

| Command | Description |
|---|---|
| `/start` | Show available commands |
| `/rates` | Current exchange rates (Cuba timezone) |
| `/history [n]` | Last *n* records (1–20, default 5) |
| `/graph [currency\|all]` | Daily average chart — last 3 months |
| `/graph [currency\|all] [days]` | Hourly chart — last *days* days (1–14) |

**Graph examples:**

```
/graph              → USD daily avg, last 3 months
/graph euro         → EUR daily avg, last 3 months
/graph usd 7        → USD hourly, last 7 days
/graph all          → all currencies daily avg, last 3 months
/graph all 3        → all currencies hourly, last 3 days
```

All timestamps are displayed in **Cuba time** (`America/Havana`), which automatically handles CST (UTC-5) and CDT (UTC-4).

---

## Logs

The app writes structured logs to `app.log` in the project root as well as to stdout:

```
2026-06-27 10:00:00,000 [INFO] __main__: Exchange rates saved: {'usd': 390.0, ...}
2026-06-27 11:00:00,000 [INFO] __main__: No changes in rates, skipping save.
```

- Max file size: **5 MB**
- Kept backups: **3** (`app.log`, `app.log.1`, `app.log.2`, `app.log.3`)

