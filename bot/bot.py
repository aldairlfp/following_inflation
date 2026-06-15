import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import os
from dotenv import load_dotenv

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
        "/history [n] — Last <i>n</i> records (default 5)",
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


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rates", cmd_rates))
    app.add_handler(CommandHandler("history", cmd_history))
    return app
