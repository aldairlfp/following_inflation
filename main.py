import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from api.routes import router
from bot.bot import build_application
from database.database import Base, SessionLocal, engine
from database.models import ExchangeRateRecord
from scraper.scraper import get_rate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

scheduler = AsyncIOScheduler()


def _scrape_and_save():
    """Fetch exchange rates from the scraper and persist them to the database."""
    db = SessionLocal()
    try:
        rates = get_rate()
        last_rates = (
            db.query(ExchangeRateRecord)
            .order_by(ExchangeRateRecord.timestamp.desc())
            .first()
        )

        if rates == {
            "usd": last_rates.usd,
            "euro": last_rates.euro,
            "mlc": last_rates.mlc,
            "cad": last_rates.cad,
            "mxn": last_rates.mxn,
            "zelle": last_rates.zelle,
            "cla": last_rates.cla,
        }:
            logger.info("No changes in rates, skipping save.")
            return

        record = ExchangeRateRecord(**rates)
        db.add(record)
        db.commit()
        logger.info("Exchange rates saved: %s", rates)
    except Exception as exc:
        logger.error("Failed to scrape/save rates: %s", exc)
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- scraper scheduler ---
    _scrape_and_save()
    scheduler.add_job(_scrape_and_save, "interval", hours=1, id="scrape_rates")
    scheduler.start()

    # --- telegram bot ---
    telegram_app = build_application()
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)

    yield

    # --- shutdown ---
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()
    scheduler.shutdown()


app = FastAPI(title="Following Inflation", lifespan=lifespan)
app.include_router(router)
