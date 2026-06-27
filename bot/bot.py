import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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


HAVANA = ZoneInfo("America/Havana")


def _to_havana(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return dt.astimezone(HAVANA).replace(tzinfo=None)  # naive local time for matplotlib


def _format_record(record: dict) -> str:
    local = _to_havana(record["timestamp"])
    lines = [f"🕐 {local.strftime('%Y-%m-%d %H:%M')} (Cuba)\n"]
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
        "/graph [currency|all] [days] — Exchange rate chart\n"
        "  • /graph usd — daily avg, last 3 months\n"
        "  • /graph usd 7 — hourly, last 7 days\n"
        "  • /graph all — all currencies, last 3 months",
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
    arg = context.args[0].lower() if context.args else "usd"
    valid = set(CURRENCY_LABELS.keys())

    if arg not in valid and arg != "all":
        await update.message.reply_text(
            f"⚠️ Unknown currency <b>{arg}</b>.\n"
            f"Valid options: {', '.join(sorted(valid))}, all",
            parse_mode="HTML",
        )
        return

    try:
        days = int(context.args[1]) if len(context.args) > 1 else None
        if days is not None:
            days = max(1, min(days, 14))
    except (ValueError, IndexError):
        days = None

    if arg == "all":
        await _graph_all(update, days)
    else:
        await _graph_single(update, arg, days)


async def _graph_single(update, currency: str, days: int | None) -> None:
    if days is not None:
        params = {"days": days}
        title = f"{CURRENCY_LABELS[currency]} — Last {days}d hourly (CUP)"
        caption = f"📈 {CURRENCY_LABELS[currency]} — last {days} days (hourly)"
        date_fmt = "%b %d %H:%M"
    else:
        params = {"months": 3}
        title = f"{CURRENCY_LABELS[currency]} — Last 3 months, daily avg (CUP)"
        caption = f"📈 {CURRENCY_LABELS[currency]} — last 3 months (daily avg)"
        date_fmt = "%b %d"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/rates/history/{currency}", params=params
        )
    response.raise_for_status()
    data = response.json()

    if len(data) < 2:
        await update.message.reply_text("⚠️ Not enough data to plot a graph yet.")
        return

    timestamps = [_to_havana(d["timestamp"]) for d in data]
    values = [d["value"] for d in data]
    padding = (max(values) - min(values)) * 0.1 or 1

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(timestamps, values, linewidth=1.8, color="#4e8df5")
    ax.fill_between(timestamps, values, alpha=0.15, color="#4e8df5")
    ax.set_ylim(min(values) - padding, max(values) + padding)
    ax.set_title(title, fontsize=14, pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("CUP")
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
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


PALETTE = ["#4e8df5", "#f5824e", "#4ef59a", "#f5e04e", "#c44ef5", "#f54e4e", "#4ef5f0"]


async def _graph_all(update) -> None:
    async with httpx.AsyncClient() as client:
        responses = {
            currency: await client.get(
                f"{API_BASE_URL}/rates/history/{currency}", params=params
            )
            for currency in CURRENCY_LABELS
        }

    series = {}
    for currency, response in responses.items():
        response.raise_for_status()
        data = response.json()
        if len(data) >= 2:
            series[currency] = (
                [_to_havana(d["timestamp"]) for d in data],
                [d["value"] for d in data],
            )

    if not series:
        await update.message.reply_text("⚠️ Not enough data to plot a graph yet.")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    for (currency, (timestamps, values)), color in zip(series.items(), PALETTE):
        ax.plot(
            timestamps,
            values,
            linewidth=1.6,
            color=color,
            label=CURRENCY_LABELS[currency],
        )

    ax.set_title(title, fontsize=14, pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("CUP")
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    fig.autofmt_xdate()
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    await update.message.reply_photo(
        photo=buf,
        caption=caption,
    )


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rates", cmd_rates))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("graph", cmd_graph))
    return app
