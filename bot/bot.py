import io

import httpx
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import os
from dotenv import load_dotenv

matplotlib.use("Agg")  # non-interactive backend, safe for servers

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

CURRENCY_LABELS = {
    "usd": "🇺🇸 USD",
    "euro": "🇪🇺 EUR",
    "mlc": "💳 MLC",
    "cad": "🇨🇦 CAD",
    "mxn": "🇲🇽 MXN",
    "zelle": "💵 Zelle",
    "cla": "🏦 CLA",
}


def _format_record(record: dict) -> str:
    lines = [f"🕐 {record['timestamp'][:16].replace('T', ' ')} UTC\n"]
    for field, label in CURRENCY_LABELS.items():
        value = record.get(field)
        if value is not None:
            lines.append(f"  {label}: <b>{value:,.2f}</b> CUP")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 <b>Following Inflation Bot</b>\n\n"
        "Available commands:\n"
        "/rates — Current exchange rates\n"
        "/history [n] — Last <i>n</i> records (default 5)\n"
        "/graph [currency] — Price chart for the last 3 months (default: usd)",
        parse_mode="HTML",
    )


async def cmd_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/rates/latest")

    if response.status_code == 404:
        await update.message.reply_text("⚠️ No data available yet.")
        return

    response.raise_for_status()
    record = response.json()

    await update.message.reply_text(
        f"📊 <b>Current rates</b>\n\n{_format_record(record)}",
        parse_mode="HTML",
    )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        limit = int(context.args[0]) if context.args else 5
        limit = max(1, min(limit, 20))
    except (ValueError, IndexError):
        limit = 5

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/rates", params={"limit": limit})

    response.raise_for_status()
    records = response.json()

    if not records:
        await update.message.reply_text("⚠️ No history available yet.")
        return

    parts = [f"📈 <b>Last {len(records)} records</b>\n"]
    for record in records:
        parts.append(_format_record(record))
        parts.append("─" * 20)

    await update.message.reply_text("\n".join(parts), parse_mode="HTML")


async def cmd_graph(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    currency = context.args[0].lower() if context.args else "usd"
    valid = set(CURRENCY_LABELS.keys())

    if currency not in valid:
        await update.message.reply_text(
            f"⚠️ Unknown currency <b>{currency}</b>.\n"
            f"Valid options: {', '.join(sorted(valid))}",
            parse_mode="HTML",
        )
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/rates/history/{currency}", params={"months": 3}
        )

    response.raise_for_status()
    data = response.json()

    if len(data) < 2:
        await update.message.reply_text("⚠️ Not enough data to plot a graph yet.")
        return

    timestamps = [
        __import__("datetime").datetime.fromisoformat(d["timestamp"]) for d in data
    ]
    values = [d["value"] for d in data]

    padding = (max(values) - min(values)) * 0.1 or 1

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(timestamps, values, linewidth=1.8, color="#4e8df5")
    ax.fill_between(timestamps, values, alpha=0.15, color="#4e8df5")
    ax.set_ylim(min(values) - padding, max(values) + padding)
    ax.set_title(
        f"{CURRENCY_LABELS[currency]} — Last 3 months (CUP)", fontsize=14, pad=12
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("CUP")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    fig.autofmt_xdate()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    await update.message.reply_photo(
        photo=buf,
        caption=f"📈 {CURRENCY_LABELS[currency]} exchange rate — last 3 months",
    )


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rates", cmd_rates))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("graph", cmd_graph))
    return app
